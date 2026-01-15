# models.py
from dataclasses import dataclass


@dataclass
class Item:
    sku: str
    name: str
    unit_price: int
    category: str
    stock: int = 0
    disabled: bool = False


@dataclass
class Customer:
    cid: str
    name: str
    disabled: bool = False
