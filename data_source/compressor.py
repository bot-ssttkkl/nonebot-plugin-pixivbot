import asyncio
import functools

from concurrent.futures.thread import ThreadPoolExecutor
from io import BytesIO
from PIL import Image, ImageFile
from .pkg_context import context
from ..config import Config


conf: Config = context.require(Config)


@context.register_singleton(enabled=conf.pixiv_compression_enabled,
                            max_size=conf.pixiv_compression_max_size,
                            quantity=conf.pixiv_compression_quantity)
class Compressor:
    def __init__(self, enabled, max_size, quantity) -> None:
        self.enabled = enabled
        self.max_size = max_size
        self.quantity = quantity
        self._executor = ThreadPoolExecutor(2, "compressor")

    async def compress(self, content: bytes) -> bytes:
        if self.enabled:
            loop = asyncio.get_running_loop()
            task = loop.run_in_executor(
                self._executor, functools.partial(self._compress, content))
            return await task
        else:
            return content

    def _compress(self, content: bytes) -> bytes:
        p = ImageFile.Parser()
        p.feed(content)
        img = p.close()

        w, h = img.size
        if w > self.max_size or h > self.max_size:
            ratio = min(self.max_size / w,
                        self.max_size / h)
            img_cp = img.resize(
                (int(ratio * w), int(ratio * h)), Image.ANTIALIAS)
        else:
            img_cp = img.copy()
        img_cp = img_cp.convert("RGB")

        with BytesIO() as bio:
            img_cp.save(bio, format="JPEG", optimize=True,
                        quantity=self.quantity)
            return bio.getvalue()
