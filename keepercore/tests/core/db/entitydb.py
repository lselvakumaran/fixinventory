from typing import Union, Optional, List, AsyncGenerator, Type, Callable


from core.db.entitydb import EntityDb, T
from core.model.typed_model import from_js, to_js
from core.types import Json


class InMemoryDb(EntityDb[T]):
    def __init__(self, t_type: Type[T], key_fn: Callable[[T], str]):
        self.items: dict[str, Json] = {}
        self.t_type = t_type
        self.key_fn = key_fn

    async def all(self) -> AsyncGenerator[T, None]:
        for js in self.items.values():
            yield from_js(js, self.t_type)

    async def update_many(self, elements: List[T]) -> None:
        for elem in elements:
            key = self.key_fn(elem)
            self.items[key] = to_js(key)

    async def get(self, key: str) -> Optional[T]:
        js = self.items.get(key)
        return from_js(js, self.t_type) if js else None

    async def update(self, t: T) -> T:
        self.items[self.key_fn(t)] = to_js(t)
        return t

    async def delete(self, key_or_object: Union[str, T]) -> None:
        key = key_or_object if isinstance(key_or_object, str) else self.key_fn(key_or_object)
        self.items.pop(key, None)

    async def create_update_schema(self) -> None:
        pass

    async def wipe(self) -> bool:
        self.items = {}
        return True
