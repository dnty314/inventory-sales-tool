# models.py
"""商品・顧客の論理モデル（参考用）。実行時の永続化は store の dict が正です。"""
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
