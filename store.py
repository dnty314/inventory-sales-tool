# store.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from utils import now_str, new_id, atomic_write_json, load_json_or_default, format_money


def _default_settings() -> Dict[str, Any]:
    return {
        "theme": "",                 # ttk theme name
        "price_mode": "int",         # "int" | "float"
        "price_decimals": 2,         # used when price_mode == "float"
        "danger_confirm_phrase": "DELETE",
        "show_deleted_by_default": False,
    }


def _default_data() -> Dict[str, Any]:
    return {
        "items": {},
        "customers": {},
        "inventory_history": [],
        "sales": [],
        "category_colors": {},
        "settings": _default_settings(),
    }


class StoreJSON:
    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = load_json_or_default(path, _default_data())
        self._normalize()
        self._save()

    # -------------------------
    # Internal
    # -------------------------
    def _normalize(self) -> None:
        d = self.data
        for k, v in _default_data().items():
            if k not in d:
                d[k] = v

        # settings
        if "settings" not in d or not isinstance(d["settings"], dict):
            d["settings"] = _default_settings()
        for k, v in _default_settings().items():
            d["settings"].setdefault(k, v)

        # items
        for sku, it in d["items"].items():
            it.setdefault("disabled", False)
            it.setdefault("stock", 0)
            it.setdefault("created_at", it.get("created_at") or now_str())
            it.setdefault("updated_at", it.get("updated_at") or now_str())

        # customers
        for cid, cu in d["customers"].items():
            cu.setdefault("disabled", False)
            cu.setdefault("created_at", cu.get("created_at") or now_str())
            cu.setdefault("updated_at", cu.get("updated_at") or now_str())

        # history
        for r in d["inventory_history"]:
            r.setdefault("id", new_id("IH"))
            r.setdefault("deleted", False)

        for r in d["sales"]:
            r.setdefault("id", new_id("S"))
            r.setdefault("deleted", False)

    def _save(self) -> None:
        atomic_write_json(self.path, self.data)

    # -------------------------
    # Settings
    # -------------------------
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.data.get("settings", {}).get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self.data.setdefault("settings", _default_settings())
        self.data["settings"][key] = value
        self._save()

    def reset_settings(self) -> None:
        self.data["settings"] = _default_settings()
        self._save()

    def money_str(self, value: float) -> str:
        mode = self.get_setting("price_mode", "int")
        decimals = int(self.get_setting("price_decimals", 2) or 2)
        return format_money(value, mode=mode, decimals=decimals)

    # -------------------------
    # Read helpers
    # -------------------------
    def list_categories(self, include_disabled_items: bool = False) -> List[str]:
        cats = set()
        for _, it in self.data["items"].items():
            if (not include_disabled_items) and it.get("disabled", False):
                continue
            cats.add(it.get("category", ""))
        return sorted([c for c in cats if c])

    def list_items_by_category(self, category: str, include_disabled: bool = False) -> List[Tuple[str, str]]:
        out = []
        for sku, it in self.data["items"].items():
            if it.get("category") != category:
                continue
            if (not include_disabled) and it.get("disabled", False):
                continue
            out.append((sku, it.get("name", "")))
        out.sort(key=lambda x: x[1])
        return out

    def get_item(self, sku: str) -> Dict[str, Any]:
        if sku not in self.data["items"]:
            raise ValueError("商品（SKU）が見つかりません")
        return self.data["items"][sku]

    def list_customers(self, include_disabled: bool = False) -> List[Tuple[str, str]]:
        out = []
        for cid, cu in self.data["customers"].items():
            if (not include_disabled) and cu.get("disabled", False):
                continue
            out.append((cid, cu.get("name", "")))
        out.sort(key=lambda x: x[1])
        return out

    # -------------------------
    # Item master
    # -------------------------
    def upsert_item(self, sku: str, name: str, unit_price: int, category: str, stock: int) -> None:
        sku = sku.strip()
        if not sku:
            raise ValueError("SKUが空です")
        if not name.strip():
            raise ValueError("商品名が空です")
        if not category.strip():
            raise ValueError("カテゴリが空です")
        if unit_price < 0:
            raise ValueError("単価が不正です")
        if stock < 0:
            raise ValueError("在庫が不正です")

        items = self.data["items"]
        ts = now_str()
        if sku not in items:
            items[sku] = {
                "name": name.strip(),
                "unit_price": int(unit_price),
                "category": category.strip(),
                "stock": int(stock),
                "disabled": False,
                "created_at": ts,
                "updated_at": ts,
            }
        else:
            it = items[sku]
            it["name"] = name.strip()
            it["unit_price"] = int(unit_price)
            it["category"] = category.strip()
            it["stock"] = int(stock)
            it["updated_at"] = ts
        self._save()

    def disable_item(self, sku: str) -> None:
        it = self.get_item(sku)
        it["disabled"] = True
        it["updated_at"] = now_str()
        self._save()

    def enable_item(self, sku: str) -> None:
        it = self.get_item(sku)
        it["disabled"] = False
        it["updated_at"] = now_str()
        self._save()

    def hard_delete_item(self, sku: str, allow_orphan: bool = False) -> None:
        used_in_inv = any((r.get("sku") == sku and not r.get("deleted", False))
                          for r in self.data.get("inventory_history", []))
        used_in_sales = any((r.get("sku") == sku and not r.get("deleted", False))
                            for r in self.data.get("sales", []))
        if (used_in_inv or used_in_sales) and not allow_orphan:
            raise ValueError("履歴に参照があるため完全削除できません（無効化を使用してください）")
        if sku in self.data["items"]:
            del self.data["items"][sku]
            self._save()

    # -------------------------
    # Customers
    # -------------------------
    def upsert_customer(self, cid: str, name: str) -> None:
        cid = cid.strip()
        if not cid:
            raise ValueError("顧客IDが空です")
        if not name.strip():
            raise ValueError("顧客名が空です")
        cus = self.data["customers"]
        ts = now_str()
        if cid not in cus:
            cus[cid] = {
                "name": name.strip(),
                "disabled": False,
                "created_at": ts,
                "updated_at": ts,
            }
        else:
            cu = cus[cid]
            cu["name"] = name.strip()
            cu["updated_at"] = ts
        self._save()

    def disable_customer(self, cid: str) -> None:
        if cid not in self.data["customers"]:
            raise ValueError("顧客IDが見つかりません")
        self.data["customers"][cid]["disabled"] = True
        self.data["customers"][cid]["updated_at"] = now_str()
        self._save()

    def enable_customer(self, cid: str) -> None:
        if cid not in self.data["customers"]:
            raise ValueError("顧客IDが見つかりません")
        self.data["customers"][cid]["disabled"] = False
        self.data["customers"][cid]["updated_at"] = now_str()
        self._save()

    def hard_delete_customer(self, cid: str, allow_orphan: bool = False) -> None:
        used_in_sales = any((r.get("cid") == cid and not r.get("deleted", False))
                            for r in self.data.get("sales", []))
        if used_in_sales and not allow_orphan:
            raise ValueError("売上履歴に参照があるため完全削除できません（無効化を使用してください）")
        if cid in self.data["customers"]:
            del self.data["customers"][cid]
            self._save()

    # -------------------------
    # Inventory movements
    # -------------------------
    def apply_movement(self, action: str, sku: str, qty: int, note: str = "") -> str:
        action = action.strip().upper()
        if action not in ("IN", "OUT", "ADJUST"):
            raise ValueError("操作が不正です")
    
        it = self.get_item(sku)
        if it.get("disabled", False):
            raise ValueError("無効化された商品は操作できません")
        if qty < 0:
            raise ValueError("数量が不正です")
    
        stock_before = int(it.get("stock", 0))
    
        if action == "IN":
            stock_after = stock_before + qty
            amount = qty * int(it.get("unit_price", 0))
        elif action == "OUT":
            if stock_before < qty:
                raise ValueError("在庫不足です")
            stock_after = stock_before - qty
            amount = -qty * int(it.get("unit_price", 0))
        else:  # ADJUST
            stock_after = qty
            amount = (stock_after - stock_before) * int(it.get("unit_price", 0))
    
        it["stock"] = stock_after
        it["updated_at"] = now_str()
    
        inventory_total_after = self.calc_inventory_total()
    
        rec = {
            "id": new_id("IH"),
            "ts": now_str(),
            "action": action,
            "sku": sku,
            "qty": qty,
            "unit_price": int(it.get("unit_price", 0)),
            "amount": amount,
            "stock_after": stock_after,
            "inventory_total_after": inventory_total_after,
            "note": note or "",
            "deleted": False,
        }
    
        self.data["inventory_history"].append(rec)
        self._save()
        return rec["id"]


    def apply_batch_movement(self, action: str, lines: List[Dict[str, Any]]) -> List[str]:
        action = action.strip().upper()
        if action not in ("IN", "OUT"):
            raise ValueError("一括はIN/OUTのみ対応です")

        for ln in lines:
            sku = ln["sku"]
            qty = int(ln["qty"])
            it = self.get_item(sku)
            if it.get("disabled", False):
                raise ValueError(f"無効化された商品が含まれています: {sku}")
            if qty < 0:
                raise ValueError("数量が不正です")
            if action == "OUT" and int(it.get("stock", 0)) < qty:
                raise ValueError(f"在庫不足: {sku}")

        ids = []
        for ln in lines:
            ids.append(self.apply_movement(action, ln["sku"], int(ln["qty"]), ln.get("note", "")))
        return ids

    # -------------------------
    # Inventory history
    # -------------------------
    def list_inventory_history(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        out = []
        for r in self.data.get("inventory_history", []):
            if (not include_deleted) and r.get("deleted", False):
                continue
            out.append(r)
        out.sort(key=lambda x: x.get("ts", ""))
        return out

    def soft_delete_inventory_history(self, record_id: str, reason: str = "") -> None:
        for r in self.data.get("inventory_history", []):
            if r.get("id") == record_id:
                r["deleted"] = True
                r["deleted_at"] = now_str()
                r["deleted_reason"] = reason or ""
                self._save()
                return
        raise ValueError("対象の在庫履歴が見つかりません")

    def restore_inventory_history(self, record_id: str) -> None:
        for r in self.data.get("inventory_history", []):
            if r.get("id") == record_id:
                r["deleted"] = False
                r.pop("deleted_at", None)
                r.pop("deleted_reason", None)
                self._save()
                return
        raise ValueError("対象の在庫履歴が見つかりません")

    def hard_delete_inventory_history(self, record_id: str) -> None:
        before = len(self.data.get("inventory_history", []))
        self.data["inventory_history"] = [r for r in self.data.get("inventory_history", []) if r.get("id") != record_id]
        if len(self.data["inventory_history"]) == before:
            raise ValueError("対象の在庫履歴が見つかりません")
        self._save()

    def purge_deleted_inventory_history(self) -> int:
        hist = self.data.get("inventory_history", [])
        before = len(hist)
        self.data["inventory_history"] = [r for r in hist if not r.get("deleted", False)]
        self._save()
        return before - len(self.data["inventory_history"])

    # -------------------------
    # Sales
    # -------------------------
    def add_sales(self, cid: str, sku: str, qty: int, note: str = "") -> str:
        if cid not in self.data["customers"]:
            raise ValueError("顧客IDが見つかりません")
        if self.data["customers"][cid].get("disabled", False):
            raise ValueError("無効化された顧客には登録できません")

        it = self.get_item(sku)
        if it.get("disabled", False):
            raise ValueError("無効化された商品は売上に登録できません")

        qty = int(qty)
        if qty < 0:
            raise ValueError("数量が不正です")

        unit_price = int(it.get("unit_price", 0))
        line_total = unit_price * qty

        rec_id = new_id("S")
        rec = {
            "id": rec_id,
            "ts": now_str(),
            "cid": cid,
            "sku": sku,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
            "note": note or "",
            "deleted": False,
        }
        self.data["sales"].append(rec)
        self._save()
        return rec_id

    def add_sales_batch(self, cid: str, lines: List[Dict[str, Any]]) -> List[str]:
        ids = []
        for ln in lines:
            ids.append(self.add_sales(cid, ln["sku"], int(ln["qty"]), ln.get("note", "")))
        return ids

    def list_sales(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        out = []
        for r in self.data.get("sales", []):
            if (not include_deleted) and r.get("deleted", False):
                continue
            out.append(r)
        out.sort(key=lambda x: x.get("ts", ""))
        return out

    def soft_delete_sales(self, record_id: str, reason: str = "") -> None:
        for r in self.data.get("sales", []):
            if r.get("id") == record_id:
                r["deleted"] = True
                r["deleted_at"] = now_str()
                r["deleted_reason"] = reason or ""
                self._save()
                return
        raise ValueError("対象の売上履歴が見つかりません")

    def restore_sales(self, record_id: str) -> None:
        for r in self.data.get("sales", []):
            if r.get("id") == record_id:
                r["deleted"] = False
                r.pop("deleted_at", None)
                r.pop("deleted_reason", None)
                self._save()
                return
        raise ValueError("対象の売上履歴が見つかりません")

    def hard_delete_sales(self, record_id: str) -> None:
        before = len(self.data.get("sales", []))
        self.data["sales"] = [r for r in self.data.get("sales", []) if r.get("id") != record_id]
        if len(self.data["sales"]) == before:
            raise ValueError("対象の売上履歴が見つかりません")
        self._save()

    def purge_deleted_sales(self) -> int:
        sales = self.data.get("sales", [])
        before = len(sales)
        self.data["sales"] = [r for r in sales if not r.get("deleted", False)]
        self._save()
        return before - len(self.data["sales"])
    
    def calc_inventory_total(self) -> int:
        total = 0
        for it in self.data.get("items", {}).values():
            if it.get("disabled", False):
                continue
            total += int(it.get("stock", 0)) * int(it.get("unit_price", 0))
        return total

    # -------------------------
    # Aggregations
    # -------------------------
    def sum_sales(self, start_ts: Optional[str] = None, end_ts: Optional[str] = None, cid: Optional[str] = None) -> int:
        total = 0
        for r in self.data.get("sales", []):
            if r.get("deleted", False):
                continue
            ts = r.get("ts", "")
            if start_ts and ts < start_ts:
                continue
            if end_ts and ts > end_ts:
                continue
            if cid and r.get("cid") != cid:
                continue
            total += int(r.get("line_total", 0))
        return total

    # -------------------------
    # Category colors
    # -------------------------
    def set_category_color(self, category: str, hex_color: str) -> None:
        category = category.strip()
        if not category:
            raise ValueError("カテゴリが空です")
        self.data["category_colors"][category] = hex_color
        self._save()

    def get_category_color(self, category: str) -> Optional[str]:
        return self.data.get("category_colors", {}).get(category)
