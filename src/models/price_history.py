from datetime import date, datetime
from typing import Optional, Union

from pydantic import BaseModel


class PriceHistory(BaseModel):
    upc: str
    sku: Optional[str] = None
    last_updated: datetime
    regular_price: Optional[Union[str, float]] = None
    current_price: Optional[Union[str, float]] = None
    promotion_start_date: Optional[date] = None
    promotion_end_date: Optional[date] = None

    class Config:
        frozen = True

    def __hash__(self):
        return hash((
            self.upc,
            # self.sku,
            self.last_updated
        ))

    def __eq__(self, other):
        if isinstance(other, PriceHistory):
            conditions = [
                self.upc == other.upc,
                # self.sku == other.sku,
                self.last_updated == other.last_updated
            ]

            return all(conditions)
        return False
