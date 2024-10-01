from typing import Any, Optional

from pydantic import BaseModel


class Country(BaseModel):
    name: str
    code: str

    def to_json_model(self) -> dict[str, Any]:
        data = self.model_dump(include={'name', 'code'})
        return data

    class Config:
        frozen = True

    def __hash__(self):
        return hash((self.name, self.code))

    def __eq__(self, other):
        if isinstance(other, Country):
            return self.name == other.name and self.code == other.code
        return False

    # sort
    def __lt__(self, other):
        if isinstance(other, Country):
            return self.code < other.code
        return NotImplemented
