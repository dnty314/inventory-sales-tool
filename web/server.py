# web/server.py — ローカルブラウザ用 API + 静的 UI
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from utils import parse_date_yyyy_mm_dd
from web.deps import store_ctx

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="在庫・売上管理（Web）", version="0.1")


class ItemUpsert(BaseModel):
    sku: str
    name: str
    unit_price: int = Field(ge=0)
    category: str
    stock: int = Field(ge=0)


class MovementIn(BaseModel):
    action: str
    sku: str
    qty: int = Field(ge=0)
    note: str = ""


class MoveLine(BaseModel):
    sku: str
    qty: int = Field(ge=0)
    note: str = ""


class MovementBatchIn(BaseModel):
    """一括入出庫（IN / OUT のみ。store.apply_batch_movement と同じ制約）。"""
    action: str
    lines: List[MoveLine]


class CustomerUpsert(BaseModel):
    cid: str
    name: str


class SalesLine(BaseModel):
    sku: str
    qty: int = Field(ge=0)
    note: str = ""


class SalesBatchIn(BaseModel):
    cid: str
    lines: List[SalesLine]


def _err(e: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(e))


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"ok": "yes"}


@app.get("/api/snapshot")
def snapshot() -> Dict[str, Any]:
    with store_ctx() as s:
        snap = s.dashboard_snapshot()
        return {
            **snap,
            "inventory_value_fmt": s.money_str(snap["inventory_value"]),
            "sales_today_fmt": s.money_str(snap["sales_today"]),
        }


@app.get("/api/items")
def api_items(include_disabled: bool = False) -> List[Dict[str, Any]]:
    with store_ctx() as s:
        rows = []
        for sku, it in sorted(s.data["items"].items(), key=lambda x: x[0]):
            if (not include_disabled) and it.get("disabled", False):
                continue
            rows.append(
                {
                    "sku": sku,
                    "name": it.get("name", ""),
                    "unit_price": it.get("unit_price", 0),
                    "category": it.get("category", ""),
                    "stock": it.get("stock", 0),
                    "disabled": it.get("disabled", False),
                }
            )
        return rows


@app.get("/api/categories")
def api_categories() -> List[str]:
    with store_ctx() as s:
        return s.list_categories(include_disabled_items=True)


@app.get("/api/categories/{category}/skus")
def api_skus_in_category(category: str, include_disabled: bool = False) -> List[Dict[str, str]]:
    with store_ctx() as s:
        pairs = s.list_items_by_category(category, include_disabled=include_disabled)
        return [{"sku": a, "name": b} for a, b in pairs]


@app.post("/api/items")
def api_items_upsert(body: ItemUpsert) -> Dict[str, str]:
    with store_ctx() as s:
        try:
            s.upsert_item(body.sku, body.name, body.unit_price, body.category, body.stock)
        except Exception as e:
            raise _err(e)
        return {"ok": "saved"}


@app.post("/api/items/{sku}/disable")
def api_item_disable(sku: str) -> Dict[str, str]:
    with store_ctx() as s:
        try:
            s.disable_item(sku)
        except Exception as e:
            raise _err(e)
        return {"ok": "disabled"}


@app.post("/api/items/{sku}/enable")
def api_item_enable(sku: str) -> Dict[str, str]:
    with store_ctx() as s:
        try:
            s.enable_item(sku)
        except Exception as e:
            raise _err(e)
        return {"ok": "enabled"}


@app.delete("/api/items/{sku}")
def api_item_delete(sku: str, allow_orphan: bool = False) -> Dict[str, str]:
    with store_ctx() as s:
        try:
            s.hard_delete_item(sku, allow_orphan=allow_orphan)
        except Exception as e:
            raise _err(e)
        return {"ok": "deleted"}


@app.post("/api/inventory/move")
def api_inventory_move(body: MovementIn) -> Dict[str, str]:
    with store_ctx() as s:
        try:
            s.apply_movement(body.action, body.sku, body.qty, body.note)
        except Exception as e:
            raise _err(e)
        return {"ok": "moved"}


@app.post("/api/inventory/move-batch")
def api_inventory_move_batch(body: MovementBatchIn) -> Dict[str, Any]:
    with store_ctx() as s:
        raw = [{"sku": ln.sku.strip(), "qty": ln.qty, "note": ln.note or ""} for ln in body.lines]
        raw = [ln for ln in raw if ln["sku"] and ln["qty"] > 0]
        if not raw:
            raise HTTPException(status_code=400, detail="有効な行がありません（SKU と数量を確認してください）")
        try:
            ids = s.apply_batch_movement(body.action, raw)
        except Exception as e:
            raise _err(e)
        return {"ok": "moved", "ids": ids, "count": len(ids)}


@app.get("/api/inventory/history")
def api_inv_history(
    include_deleted: bool = False,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None
    if start:
        try:
            parse_date_yyyy_mm_dd(start)
        except Exception:
            raise HTTPException(status_code=400, detail="開始日の形式が不正です（YYYY-MM-DD）")
        start_ts = f"{start.strip()} 00:00:00"
    if end:
        try:
            parse_date_yyyy_mm_dd(end)
        except Exception:
            raise HTTPException(status_code=400, detail="終了日の形式が不正です（YYYY-MM-DD）")
        end_ts = f"{end.strip()} 23:59:59"
    if start_ts and end_ts and start_ts > end_ts:
        raise HTTPException(status_code=400, detail="開始日は終了日以前にしてください")

    with store_ctx() as s:
        rows = s.list_inventory_history(include_deleted=include_deleted)
        out = []
        for r in rows:
            ts = r.get("ts", "")
            if start_ts and ts < start_ts:
                continue
            if end_ts and ts > end_ts:
                continue
            sku = r.get("sku", "")
            it = s.data.get("items", {}).get(sku, {})
            out.append(
                {
                    **r,
                    "item_name": it.get("name", ""),
                    "category": it.get("category", ""),
                }
            )
        return out


@app.get("/api/inventory/chart/{sku}")
def api_inv_chart(sku: str, start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
    with store_ctx() as s:
        start_d = parse_date_yyyy_mm_dd(start) if start else None
        end_d = parse_date_yyyy_mm_dd(end) if end else None
        hist = s.list_inventory_history(include_deleted=False)
        points = []
        for r in hist:
            if r.get("sku") != sku:
                continue
            ts = r.get("ts", "")
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            day = dt.date()
            if start_d and day < start_d:
                continue
            if end_d and day > end_d:
                continue
            points.append({"x": ts, "y": int(r.get("stock_after", 0) or 0)})
        name = ""
        try:
            name = s.get_item(sku).get("name", "")
        except Exception:
            name = "（参照なし）"
        return {"sku": sku, "name": name, "points": points}


@app.get("/api/customers")
def api_customers(include_disabled: bool = False) -> List[Dict[str, Any]]:
    with store_ctx() as s:
        out = []
        for cid, name in s.list_customers(include_disabled=include_disabled):
            cu = s.data["customers"][cid]
            out.append({"cid": cid, "name": name, "disabled": cu.get("disabled", False)})
        return out


@app.post("/api/customers")
def api_customers_upsert(body: CustomerUpsert) -> Dict[str, str]:
    with store_ctx() as s:
        try:
            s.upsert_customer(body.cid, body.name)
        except Exception as e:
            raise _err(e)
        return {"ok": "saved"}


@app.post("/api/sales")
def api_sales_batch(body: SalesBatchIn) -> Dict[str, Any]:
    with store_ctx() as s:
        lines = [{"sku": ln.sku, "qty": ln.qty, "note": ln.note} for ln in body.lines]
        try:
            ids = s.add_sales_batch(body.cid, lines)
        except Exception as e:
            raise _err(e)
        return {"ok": "saved", "ids": ids}


@app.get("/api/sales")
def api_sales_list(include_deleted: bool = False) -> List[Dict[str, Any]]:
    with store_ctx() as s:
        rows = s.list_sales(include_deleted=include_deleted)
        out = []
        for r in rows:
            cid = r.get("cid", "")
            sku = r.get("sku", "")
            out.append(
                {
                    **r,
                    "customer_name": s.resolve_customer_name(cid),
                    "item_name": s.resolve_item_name(sku),
                }
            )
        return out


@app.get("/")
def index_page() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
