from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class DataSourceNotReadyError(RuntimeError):
    pass

