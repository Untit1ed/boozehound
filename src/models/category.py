from typing import Any, Optional

from pydantic import BaseModel


class Category(BaseModel):
    id: int
    description: Optional[str]


    def to_json_model(self) -> dict[str, Any]:
        data = self.model_dump(include={'id', 'description'})
        return data

    class Config:
        frozen = True

    def __hash__(self):
        return hash((self.id, self.description))

    def __eq__(self, other):
        if isinstance(other, Category):
            return self.id == other.id and self.description == other.description
        return False

    def __lt__(self, other):
        if isinstance(other, Category):
            return self.id < other.id
        return NotImplemented
