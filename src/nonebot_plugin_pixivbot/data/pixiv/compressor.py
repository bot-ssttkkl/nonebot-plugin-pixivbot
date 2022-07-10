import asyncio
import functools
import multiprocessing
from concurrent.futures.thread import ThreadPoolExecutor
from io import BytesIO

from PIL import Image, ImageFile


class Compressor:
    def __init__(self, enabled, max_size, quantity) -> None:
        self.enabled = enabled
        self.max_size = max_size
        self.quantity = quantity

        if enabled:
            cpu_count = multiprocessing.cpu_count()
            self._executor = ThreadPoolExecutor(cpu_count, "compressor")
            # logger.info(f"A ThreadPool with {cpu_count} worker(s) was created for compression")

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
