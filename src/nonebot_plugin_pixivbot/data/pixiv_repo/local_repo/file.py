import json
import os
from pathlib import Path
from typing import AsyncGenerator, Union, Generic, TypeVar, Type, List, Callable, Any

import aiofiles
from nonebot import logger
from nonebot_plugin_localstore import get_cache_dir
from pydantic import ValidationError, BaseModel
from pydantic.generics import GenericModel

from .base import LocalPixivRepo
from ..errors import NoSuchItemError
from ..lazy_illust import LazyIllust
from ..models import PixivRepoMetadata
from ...local_tag import LocalTagRepo
from ....config import Config
from ....enums import RankingMode
from ....global_context import context
from ....model import Illust, User

T = TypeVar("T")


class FileModel(GenericModel, Generic[T]):
    content: T
    metadata: PixivRepoMetadata


conf = context.require(Config)
local_tags = context.require(LocalTagRepo)


def mkdirs_for_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


@context.register_singleton()
class FilePixivRepo(LocalPixivRepo):
    def __init__(self):
        self.root = get_cache_dir("nonebot_plugin_pixivbot")

    T_Content = TypeVar("T_Content", bound=BaseModel)

    async def _read_single(self, file: Path, t_content: Type[T_Content], expires_in: int) \
            -> AsyncGenerator[Union[T_Content, PixivRepoMetadata], None]:
        if not file.exists():
            raise NoSuchItemError()

        try:
            async with aiofiles.open(file, 'r', encoding="utf-8") as f:
                obj = json.loads(await f.read())
                model = FileModel[t_content].parse_obj(obj)
                model.metadata.check_is_expired(expires_in)
                yield model.metadata
                yield model.content
        except (KeyError, ValueError, ValidationError) as e:
            logger.opt(exception=e).warning(
                f"[local] deleting invalid file {file}")
            os.remove(file)
            raise NoSuchItemError()

    async def _write_single(self, file: Path, content: T_Content, metadata: PixivRepoMetadata):
        mkdirs_for_parent(file)
        s = FileModel(content=content, metadata=metadata).json()
        async with aiofiles.open(file, 'w+', encoding="utf-8") as f:
            await f.write(s)

    async def _read_list(self, file: Path, t_content: Type[T_Content], expires_in: int, offset: int = 0) \
            -> AsyncGenerator[Union[T_Content, PixivRepoMetadata], None]:
        if not file.exists():
            raise NoSuchItemError()

        try:
            async with aiofiles.open(file, 'r', encoding="utf-8") as f:
                obj = json.loads(await f.read())
                model = FileModel[List[t_content]].parse_obj(obj)
                model.metadata.check_is_expired(expires_in)
                yield model.metadata.copy(update={"pages": 0})
                for x in model.content:
                    if offset == 0:
                        yield x
                    else:
                        offset -= 1
                yield model.metadata
        except (KeyError, ValueError, ValidationError) as e:
            logger.opt(exception=e).warning(
                f"[local] deleting invalid file {file}")
            os.remove(file)
            raise NoSuchItemError()

    async def _append_list(self, file: Path, t_content: Type[T_Content],
                           content: List[T_Content], metadata: PixivRepoMetadata,
                           content_key: Callable[[T_Content], Any],
                           append_at_begin: bool = False) -> bool:
        # 返回值表示content中是否有已经存在于集合的文档
        if not file.exists():
            current_content = []
        else:
            async with aiofiles.open(file, 'r', encoding="utf-8") as f:
                obj = json.loads(await f.read())
                model = FileModel[List[t_content]].parse_obj(obj)
                current_content = model.content

        keys = set(map(content_key, current_content))
        has_duplicated = False

        for c in content:
            c_key = content_key(c)
            if c_key not in keys:
                keys.add(c_key)
                if append_at_begin:
                    current_content.insert(0, c)
                else:
                    current_content.append(c)
            else:
                has_duplicated = True

        s = FileModel[List[t_content]](
            content=current_content, metadata=metadata).json()
        mkdirs_for_parent(file)
        async with aiofiles.open(file, 'w+', encoding="utf-8") as f:
            await f.write(s)

        return has_duplicated

    # ================ illust_detail ================
    async def illust_detail(self, illust_id: int) \
            -> AsyncGenerator[Union[Illust, PixivRepoMetadata], None]:
        logger.debug(f"[local] illust_detail {illust_id}")

        file = self.root / "illust_detail" / f"{illust_id}.json"
        async for x in self._read_single(file, Illust, conf.pixiv_illust_detail_cache_expires_in):
            yield x

    async def update_illust_detail(self, illust: Illust, metadata: PixivRepoMetadata):
        logger.debug(f"[local] update illust_detail {illust.id} {metadata}")

        file = self.root / "illust_detail" / f"{illust.id}.json"
        await self._write_single(file, illust, metadata)

        # TODO: 同样改成文件
        if conf.pixiv_tag_translation_enabled:
            await local_tags.update_from_illusts([illust])

    # ================ user_detail ================
    async def user_detail(self, user_id: int) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.debug(f"[local] user_detail {user_id}")

        file = self.root / "user_detail" / f"{user_id}.json"
        async for x in self._read_single(file, User, conf.pixiv_user_detail_cache_expires_in):
            yield x

    async def update_user_detail(self, user: User, metadata: PixivRepoMetadata):
        logger.debug(f"[local] update user_detail {user.id} {metadata}")

        file = self.root / "user_detail" / f"{user.id}.json"
        await self._write_single(file, user, metadata)

    # ================ search_illust ================
    async def search_illust(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] search_illust {word}")

        file = self.root / "search_illust" / f"{word}.json"
        async for x in self._read_list(file, Illust, conf.pixiv_search_illust_cache_expires_in, offset):
            if isinstance(x, PixivRepoMetadata):
                yield x
            elif isinstance(x, Illust):
                yield LazyIllust(x.id, x)

    async def invalidate_search_illust(self, word: str):
        logger.debug(f"[local] invalidate search_illust {word}")
        file = self.root / "search_illust" / f"{word}.json"
        os.remove(file)

    async def append_search_illust(self, word: str, content: List[Union[Illust, LazyIllust]],
                                   metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append search_illust {word} "
                     f"({len(content)} items) "
                     f"{metadata}")
        file = self.root / "search_illust" / f"{word}.json"
        content: List[Illust] = [
            await x.get() if isinstance(x, LazyIllust) else x
            for x in content
        ]
        return await self._append_list(file, Illust, content, metadata, lambda x: x.id)

    # ================ search_user ================
    async def search_user(self, word: str, *, offset: int = 0) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.debug(f"[local] search_user {word}")

        file = self.root / "search_user" / f"{word}.json"
        async for x in self._read_list(file, User, conf.pixiv_search_user_cache_expires_in, offset):
            if isinstance(x, PixivRepoMetadata):
                yield x
            elif isinstance(x, User):
                yield x

    async def invalidate_search_user(self, word: str):
        logger.debug(f"[local] invalidate search_user {word}")
        file = self.root / "search_user" / f"{word}.json"
        os.remove(file)

    async def append_search_user(self, word: str, content: List[User],
                                 metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append search_user {word} "
                     f"({len(content)} items) "
                     f"{metadata}")

        file = self.root / "search_user" / f"{word}.json"
        return await self._append_list(file, User, content, metadata, lambda x: x.id)

    # ================ user_illusts ================
    async def user_illusts(self, user_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] user_illusts {user_id}")

        file = self.root / "user_illusts" / f"{user_id}.json"
        async for x in self._read_list(file, Illust, conf.pixiv_user_illusts_cache_expires_in, offset):
            if isinstance(x, PixivRepoMetadata):
                yield x
            elif isinstance(x, Illust):
                yield LazyIllust(x.id, x)

    async def invalidate_user_illusts(self, user_id: int):
        logger.debug(f"[local] invalidate user_illusts {user_id}")
        file = self.root / "user_illusts" / f"{user_id}.json"
        os.remove(file)

    async def append_user_illusts(self, user_id: int,
                                  content: List[Union[Illust, LazyIllust]],
                                  metadata: PixivRepoMetadata,
                                  append_at_begin: bool = False) -> bool:
        logger.debug(f"[local] append user_illusts {user_id} "
                     f"{'at begin ' if append_at_begin else ''}"
                     f"({len(content)} items) "
                     f"{metadata}")

        file = self.root / "user_illusts" / f"{user_id}.json"
        content: List[Illust] = [
            await x.get() if isinstance(x, LazyIllust) else x
            for x in content
        ]
        return await self._append_list(file, Illust, content, metadata, lambda x: x.id, append_at_begin)

    # ================ user_bookmarks ================
    async def user_bookmarks(self, user_id: int = 0, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] user_bookmarks {user_id}")

        file = self.root / "user_bookmarks" / f"{user_id}.json"
        async for x in self._read_list(file, Illust, conf.pixiv_user_bookmarks_cache_expires_in, offset):
            if isinstance(x, PixivRepoMetadata):
                yield x
            elif isinstance(x, Illust):
                yield LazyIllust(x.id, x)

    async def invalidate_user_bookmarks(self, user_id: int):
        logger.debug(f"[local] invalidate user_bookmarks {user_id}")
        file = self.root / "user_bookmarks" / f"{user_id}.json"
        os.remove(file)

    async def append_user_bookmarks(self, user_id: int,
                                    content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata,
                                    append_at_begin: bool = False) -> bool:
        logger.debug(f"[local] append user_bookmarks {user_id} "
                     f"{'at begin ' if append_at_begin else ''} "
                     f"({len(content)} items) "
                     f"{metadata}")

        file = self.root / "user_bookmarks" / f"{user_id}.json"
        content: List[Illust] = [
            x.content if isinstance(x, LazyIllust) else x
            for x in content
        ]
        content = list(filter(lambda x: x is not None, content))
        return await self._append_list(file, Illust, content, metadata, lambda x: x.id, append_at_begin)

    # ================ recommended_illusts ================
    async def recommended_illusts(self, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] recommended_illusts")

        file = self.root / "other" / "recommended_illusts.json"
        async for x in self._read_list(file, Illust, conf.pixiv_other_cache_expires_in, offset):
            if isinstance(x, PixivRepoMetadata):
                yield x
            elif isinstance(x, Illust):
                yield LazyIllust(x.id, x)

    async def invalidate_recommended_illusts(self):
        logger.debug(f"[local] invalidate recommended_illusts")
        file = self.root / "other" / "recommended_illusts.json"
        os.remove(file)

    async def append_recommended_illusts(self, content: List[Union[Illust, LazyIllust]],
                                         metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append recommended_illusts "
                     f"({len(content)} items) "
                     f"{metadata}")

        file = self.root / "other" / "recommended_illusts.json"
        content: List[Illust] = [
            await x.get() if isinstance(x, LazyIllust) else x
            for x in content
        ]
        return await self._append_list(file, Illust, content, metadata, lambda x: x.id)

    # ================ related_illusts ================
    async def related_illusts(self, illust_id: int, *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[local] related_illusts {illust_id}")

        file = self.root / "related_illusts" / f"{illust_id}.json"
        async for x in self._read_list(file, Illust, conf.pixiv_related_illusts_cache_expires_in, offset):
            if isinstance(x, PixivRepoMetadata):
                yield x
            elif isinstance(x, Illust):
                yield LazyIllust(x.id, x)

    async def invalidate_related_illusts(self, illust_id: int):
        logger.debug(f"[local] invalidate related_illusts")
        file = self.root / "related_illusts" / f"{illust_id}.json"
        os.remove(file)

    async def append_related_illusts(self, illust_id: int, content: List[Union[Illust, LazyIllust]],
                                     metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append related_illusts {illust_id} "
                     f"({len(content)} items) "
                     f"{metadata}")

        file = self.root / "related_illusts" / f"{illust_id}.json"
        content: List[Illust] = [
            await x.get() if isinstance(x, LazyIllust) else x
            for x in content
        ]
        return await self._append_list(file, Illust, content, metadata, lambda x: x.id)

    # ================ illust_ranking ================
    async def illust_ranking(self, mode: Union[str, RankingMode], *, offset: int = 0) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        if isinstance(mode, str):
            mode = RankingMode[mode]

        logger.debug(f"[local] illust_ranking {mode}")

        file = self.root / "illust_ranking" / f"{mode}.json"
        async for x in self._read_list(file, Illust, conf.pixiv_illust_ranking_cache_expires_in, offset):
            if isinstance(x, PixivRepoMetadata):
                yield x
            elif isinstance(x, Illust):
                yield LazyIllust(x.id, x)

    async def invalidate_illust_ranking(self, mode: RankingMode):
        logger.debug(f"[local] invalidate illust_ranking")
        file = self.root / "illust_ranking" / f"{mode}.json"
        os.remove(file)

    async def append_illust_ranking(self, mode: RankingMode, content: List[Union[Illust, LazyIllust]],
                                    metadata: PixivRepoMetadata) -> bool:
        logger.debug(f"[local] append illust_ranking {mode} "
                     f"({len(content)} items) "
                     f"{metadata}")

        file = self.root / "illust_ranking" / f"{mode}.json"
        content: List[Illust] = [
            await x.get() if isinstance(x, LazyIllust) else x
            for x in content
        ]
        return await self._append_list(file, Illust, content, metadata, lambda x: x.id)

    # ================ image ================
    async def image(self, illust: Illust, page: int = 0) -> AsyncGenerator[Union[bytes, PixivRepoMetadata], None]:
        logger.debug(f"[local] image {illust.id}")

        metadata_file = self.root / "image" / \
            f"{illust.id}_{page}_metadata.json"
        image_file = self.root / "image" / f"{illust.id}_{page}.jpg"

        if not metadata_file.exists() or image_file:
            raise NoSuchItemError()

        try:
            async with aiofiles.open(metadata_file, 'r', encoding="utf-8") as f:
                obj = json.loads(await f.read())
                metadata = PixivRepoMetadata.parse_obj(obj).check_is_expired(
                    conf.pixiv_download_cache_expires_in)

            async with aiofiles.open(image_file, 'rb') as f:
                content = f.read()

            yield metadata
            yield content
        except (KeyError, ValueError, ValidationError) as e:
            if metadata_file.exists():
                logger.opt(exception=e).warning(
                    f"[local] deleting invalid file {metadata_file}")
                os.remove(metadata_file)
            if image_file.exists():
                logger.opt(exception=e).warning(
                    f"[local] deleting invalid file {image_file}")
                os.remove(image_file)
            raise NoSuchItemError()

    async def update_image(self, illust_id: int, page: int,
                           content: bytes, metadata: PixivRepoMetadata):
        logger.debug(f"[local] update image {illust_id} {metadata}")

        metadata_file = self.root / "image" / \
            f"{illust_id}_{page}_metadata.json"
        image_file = self.root / "image" / f"{illust_id}_{page}.jpg"

        
        mkdirs_for_parent(metadata_file)
        mkdirs_for_parent(image_file)

        async with aiofiles.open(metadata_file, 'w+', encoding="utf-8") as f:
            await f.write(metadata.json())

        async with aiofiles.open(image_file, 'wb+') as f:
            await f.write(content)

    async def invalidate_all(self):
        os.removedirs(self.root)

    async def clean_expired(self):
        logger.debug(f"[local] clean_expired")

        # TODO
