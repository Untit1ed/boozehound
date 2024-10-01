from typing import Any, List, Optional, Type, Union

from pydantic import BaseModel, Field, model_validator

from models.category import Category
from models.country import Country
from models.price_history import PriceHistory
from utils.type_utils import get_float

BCL_PRODUCT_URL = "https://www.bcliquorstores.com/product/"


class Product(BaseModel):
    upc: Optional[str] = None
    sku: Optional[str] = None
    volume: Optional[Union[str, float]] = None  # Volume in liters
    unitSize: Optional[int]  # Number of units in the package
    alcoholPercentage: Optional[float]
    name: Optional[str]
    image: Optional[str]
    productType: Optional[str] = None
    tastingDescription: Optional[Union[str, bool]] = None

    country: Optional[Country]
    category: Optional[Category]
    subCategory: Optional[Category]
    subSubCategory: Optional[Category]
    price_history: Optional[PriceHistory] = None

    def get_numeric_volume(self) -> float:
        return get_float(self.volume)

    def get_numeric_current_price(self) -> float:
        return get_float(self.price_history.current_price if self.price_history else 0)

    def get_numeric_regular_price(self) -> float:
        return get_float(self.price_history.regular_price if self.price_history else 0)

    def get_numeric_unit_size(self) -> int:
        return self.unitSize if self.unitSize else 1

    def price_per_milliliter(self) -> float:
        volume_ml = self.get_numeric_volume() * 1000
        current_price = self.get_numeric_current_price()
        unit_size = self.get_numeric_unit_size()
        total_volume_ml = volume_ml * unit_size
        if total_volume_ml > 0:
            return current_price / total_volume_ml
        return float('inf')  # to ensure products with zero or invalid volume are ranked lowest

    def alcohol_score(self) -> float:
        return self.alcoholPercentage if self.alcoholPercentage else 0

    def combined_score(self) -> float:
        # Inverse of price per milliliter to prioritize cheaper products and add alcohol score
        price_per_ml = self.price_per_milliliter()
        # Add 1 to avoid division by zero issues
        return (1 / price_per_ml if price_per_ml > 0 else 1) * (self.alcohol_score() + 1)

    def bcl_url(self) -> str:
        return f"{BCL_PRODUCT_URL}{self.sku}"

    def combined_category(self) -> str:
        # Combine productType and productCategory
        return self.productType if self.productType else self.category.description

    def full_category(self) -> List[Category]:
        return [self.category, self.subCategory, self.subSubCategory]

    @model_validator(mode='before')
    @classmethod
    def validate_fields(cls: Type['Product'], values: dict) -> dict:
        # Populate UPC
        values = cls.populate_upc_from_list_or_sku(values)

        # Fix image
        values = cls.fix_image(values)

        # Populate Country object
        values = cls.combine_country_fields(values)

        # populate SubSubCategory
        values = cls.combine_sub_sub_category(values)

        # Populate PriceHistory object
        values = cls.combine_history_fields(values)

        return values

    @classmethod
    def combine_country_fields(cls: Type['Product'], values: dict) -> dict:
        country_name = values.pop('countryName', None)
        country_code = values.pop('countryCode', None)
        if country_name or country_code:
            values['country'] = Country(name=country_name, code=country_code)
        return values

    @classmethod
    def combine_sub_sub_category(cls: Type['Product'], values: dict) -> dict:
        subSubCategory = values.pop('class', None)
        if subSubCategory:
            values['subSubCategory'] = subSubCategory
        return values

    @classmethod
    def populate_upc_from_list_or_sku(cls: Type['Product'], values: dict) -> dict:
        # Extract 'b' from the nested structure if it exists
        if 'upc' in values and isinstance(values['upc'], list):
            if len(values['upc']):
                values['upc'] = values['upc'][0]
            else:
                values['upc'] = values['sku']

        return values

    @classmethod
    def fix_image(cls: Type['Product'], values: dict) -> dict:
        # Extract 'b' from the nested structure if it exists
        if 'image' in values and values['image']:
            values['image'] = values['image'].replace('http://', 'https://', 1).replace('.jpeg', '.jpg', 1)

        return values

    @classmethod
    def combine_history_fields(cls: Type['Product'], values: dict) -> dict:
        upc = values.get('upc')
        sku = values.get('sku')
        last_updated = values.pop('last_updated', None)
        currentPrice = values.pop('currentPrice', None)
        regularPrice = values.pop('regularPrice', None)
        promotion_start_date = values.pop('promotionStartDate', None)
        promotion_end_date = values.pop('promotionEndDate', None)
        if upc and last_updated:
            values['price_history'] = PriceHistory(
                upc=upc, sku=sku, last_updated=last_updated, current_price=currentPrice, regular_price=regularPrice,
                promotion_start_date=promotion_start_date, promotion_end_date=promotion_end_date
            )
        return values

    def to_json_model(self) -> dict[str, Any]:
        data = self.model_dump(include={'name', 'image', 'tastingDescription'})
        data.update({
            'combined_score': int(self.combined_score()),
            'country': self.country.to_json_model(),
            'category': self.category.description,
            'alcohol': self.alcohol_score(),
            'volume': self.get_numeric_volume(),
            'price' : self.price_history.to_json_model() if self.price_history else None,
            'unit_size': self.get_numeric_unit_size(),
            'url': self.bcl_url(),
            'ppml': self.price_per_milliliter(),
            'full_category': [x.to_json_model() for x in self.full_category() if x],
        })

        return data

    class Config:
        frozen = True

    def __hash__(self):
        return hash((self.name, self.sku))

    def __eq__(self, other):
        if isinstance(other, Product):
            return self.name == other.name and self.sku == other.sku  # and self.upc == other.upc
        return False

    # sort
    def __lt__(self, other):
        if isinstance(other, Product):
            return self.sku < other.sku
        return NotImplemented
