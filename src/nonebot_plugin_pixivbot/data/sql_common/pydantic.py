from typing import Type, Callable, Optional, Any

from pydantic import BaseModel
from sqlalchemy import TypeDecorator, Dialect

from ..sql_common import JSON


class PydanticModel(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, t_model: Type[BaseModel],
                 dumps_default: Optional[Callable[[Any], Any]] = None,
                 # loads_object_hook: Optional[Optional[Callable[[dict[Any, Any]], Any]]] = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.t_model = t_model
        self.dumps_default = dumps_default
        # self.loads_object_hook = loads_object_hook

    def process_bind_param(self, value: Optional[BaseModel], dialect: Dialect) -> Optional[dict]:
        if value is None:
            return None
        return self._dumps(value.dict())

    def process_result_value(self, value: Optional[dict], dialect: Dialect) -> Optional[BaseModel]:
        if value is None:
            return None
        return self.t_model.parse_obj(value)

    def _dumps_default(self, obj: Any) -> Any:
        if self.dumps_default:
            return self.dumps_default(obj)
        else:
            raise TypeError(f'Object of type {obj.__class__.__name__} '
                            f'is not JSON serializable')

    def _dumps(self, obj: Any) -> Any:
        if obj is None:
            return None

        if isinstance(obj, (str, int, float, bool)):
            return obj

        if isinstance(obj, (list, tuple)):
            return [self._dumps(x) for x in obj]

        if isinstance(obj, dict):
            new_dict = {}
            for key in obj:
                if key is not None and not isinstance(key, (str, int, float)):
                    key = self._dumps_default(key)

                new_value = self._dumps(obj[key])
                if not (obj[key] is new_value):
                    new_dict[key] = new_value
            if len(new_dict) != 0:
                return {**obj, **new_dict}
            else:
                return obj

        return self._dumps_default(obj)
