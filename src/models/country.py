from typing import Optional

from pydantic import BaseModel


class Country(BaseModel):
    name: str
    code: Optional[str]

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
