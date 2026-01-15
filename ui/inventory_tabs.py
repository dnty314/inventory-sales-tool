# ui/inventory_tabs.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("TkAgg")
from matplotlib import rcParams
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from utils import safe_int, parse_date_yyyy_mm_dd
from ui.common import (
    CategoryItemSelector,
    confirm_soft_delete,
    confirm_dangerous_delete,
    pick_color,
    apply_category_row_tags,
)

rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = ["Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans CJK JP", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False


def calc_inventory_total(store) -> int:
    """在庫総額（無効商品は除外）"""
    total = 0
    for it in store.data.get("items", {}).values():
        if it.get("disabled", False):
            continue
        total += int(it.get("stock", 0) or 0) * int(it.get("unit_price", 0) or 0)
    return int(total)


class InventoryTabs(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        # --- Prominent total bar ---
        style = ttk.Style()
        try:
            style.configure("InvTotalCaption.TLabel", font=("", 12, "bold"))
            style.configure("InvTotalValue.TLabel", font=("", 18, "bold"))
        except Exception:
            pass

        total_bar = ttk.LabelFrame(self, text="在庫 総額")
        total_bar.pack(fill="x", padx=8, pady=(8, 6))

        self.var_inventory_total = tk.StringVar(value="")
        ttk.Label(total_bar, text="合計", style="InvTotalCaption.TLabel").pack(side="left", padx=(10, 8), pady=6)
        ttk.Label(total_bar, textvariable=self.var_inventory_total, style="InvTotalValue.TLabel").pack(side="left", padx=(0, 12), pady=6)
        ttk.Button(total_bar, text="更新", command=self.refresh_all).pack(side="right", padx=10, pady=6)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.tab_master = ItemMasterFrame(nb, store, tabs=self)
        self.tab_single = SingleMovementFrame(nb, store, tabs=self)
        self.tab_batch = BatchMovementFrame(nb, store, tabs=self)
        self.tab_hist = InventoryHistoryFrame(nb, store)
        self.tab_graph = InventoryGraphFrame(nb, store)

        nb.add(self.tab_master, text="商品マスタ")
        nb.add(self.tab_single, text="単発（IN/OUT/ADJUST）")
        nb.add(self.tab_batch, text="一括（IN/OUT）")
        nb.add(self.tab_hist, text="在庫履歴（一覧）")
        nb.add(self.tab_graph, text="在庫履歴（グラフ）")

        self.nb = nb
        self.refresh_all()

    def refresh_all(self):
        self.tab_master.refresh()
        self.tab_single.refresh()
        self.tab_batch.refresh()
        self.tab_hist.refresh()
        self.tab_graph.refresh()
        self.var_inventory_total.set(self.store.money_str(calc_inventory_total(self.store)))


class ItemMasterFrame(ttk.Frame):
    def __init__(self, parent, store, tabs: Optional[InventoryTabs] = None):
        super().__init__(parent)
        self.store = store
        self.tabs = tabs

        frm = ttk.LabelFrame(self, text="商品マスタ登録/更新")
        frm.pack(fill="x", padx=8, pady=8)

        self.var_sku = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_stock = tk.StringVar()

        ttk.Label(frm, text="SKU").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.var_sku, width=20).grid(row=0, column=1, sticky="w", padx=4, pady=2)

        ttk.Label(frm, text="商品名").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.var_name, width=30).grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ttk.Label(frm, text="単価").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.var_price, width=20).grid(row=1, column=1, sticky="w", padx=4, pady=2)

        ttk.Label(frm, text="カテゴリ（候補＋手入力）").grid(row=1, column=2, sticky="w", padx=4, pady=2)
        self.cb_cat = ttk.Combobox(frm, textvariable=self.var_cat, width=30, state="normal")
        self.cb_cat.grid(row=1, column=3, sticky="w", padx=4, pady=2)

        ttk.Label(frm, text="在庫（初期/上書き）").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.var_stock, width=20).grid(row=2, column=1, sticky="w", padx=4, pady=2)

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=3, sticky="e", padx=4, pady=2)
        ttk.Button(btns, text="追加/更新", command=self.on_upsert).pack(side="left", padx=4)
        ttk.Button(btns, text="入力リセット", command=self.on_reset).pack(side="left", padx=4)

        table = ttk.LabelFrame(self, text="商品一覧（選択して操作）")
        table.pack(fill="both", expand=True, padx=8, pady=8)

        self.var_show_disabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(table, text="無効商品も表示", variable=self.var_show_disabled, command=self.refresh).pack(anchor="w", padx=4, pady=2)

        cols = ("sku", "name", "category", "unit_price", "stock", "disabled")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=14)
        for c, w in [("sku", 120), ("name", 240), ("category", 160), ("unit_price", 120), ("stock", 80), ("disabled", 80)]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_row)

        ops = ttk.Frame(table)
        ops.pack(fill="x", padx=4, pady=4)

        ttk.Button(ops, text="無効化（削除）", command=self.on_disable).pack(side="left", padx=4)
        ttk.Button(ops, text="復活（有効化）", command=self.on_enable).pack(side="left", padx=4)
        ttk.Button(ops, text="完全削除（確認語入力）", command=self.on_hard_delete).pack(side="left", padx=4)

        self.refresh()

    def _category_values(self) -> List[str]:
        cats = set()
        for it in self.store.data.get("items", {}).values():
            c = (it.get("category") or "").strip()
            if c:
                cats.add(c)
        for c in (self.store.data.get("category_colors", {}) or {}).keys():
            c = (c or "").strip()
            if c:
                cats.add(c)
        return sorted(cats)

    def _selected_sku(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return str(vals[0]) if vals else None

    def on_select_row(self, _evt=None):
        sku = self._selected_sku()
        if not sku:
            return
        it = self.store.get_item(sku)
        self.var_sku.set(sku)
        self.var_name.set(it.get("name", ""))
        self.var_price.set(str(it.get("unit_price", 0)))
        self.var_cat.set(it.get("category", ""))
        self.var_stock.set(str(it.get("stock", 0)))

    def on_upsert(self):
        sku = self.var_sku.get().strip()
        name = self.var_name.get().strip()
        price = safe_int(self.var_price.get(), None)
        cat = self.var_cat.get().strip()
        stock = safe_int(self.var_stock.get(), 0)

        if not sku:
            messagebox.showwarning("入力", "SKUを入力してください", parent=self)
            return
        if not name:
            messagebox.showwarning("入力", "商品名を入力してください", parent=self)
            return
        if price is None or price < 0:
            messagebox.showwarning("入力", "単価が不正です", parent=self)
            return
        if not cat:
            messagebox.showwarning("入力", "カテゴリを入力してください", parent=self)
            return
        if stock is None or stock < 0:
            messagebox.showwarning("入力", "在庫が不正です", parent=self)
            return

        try:
            self.store.upsert_item(sku, name, int(price), cat, int(stock))
            messagebox.showinfo("成功", "商品を追加/更新しました", parent=self)
            if self.tabs is not None:
                self.tabs.refresh_all()
            else:
                self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_reset(self):
        self.var_sku.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_cat.set("")
        self.var_stock.set("")

    def on_disable(self):
        sku = self._selected_sku()
        if not sku:
            messagebox.showwarning("操作", "商品を選択してください", parent=self)
            return
        try:
            self.store.disable_item(sku)
            if self.tabs is not None:
                self.tabs.refresh_all()
            else:
                self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_enable(self):
        sku = self._selected_sku()
        if not sku:
            messagebox.showwarning("操作", "商品を選択してください", parent=self)
            return
        try:
            self.store.enable_item(sku)
            if self.tabs is not None:
                self.tabs.refresh_all()
            else:
                self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_hard_delete(self):
        sku = self._selected_sku()
        if not sku:
            messagebox.showwarning("操作", "商品を選択してください", parent=self)
            return
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="商品 完全削除"):
            return
        try:
            self.store.hard_delete_item(sku)
            if self.tabs is not None:
                self.tabs.refresh_all()
            else:
                self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def refresh(self):
        self.cb_cat["values"] = self._category_values()

        self.tree.delete(*self.tree.get_children())
        show_disabled = self.var_show_disabled.get()
        for sku, it in sorted(self.store.data.get("items", {}).items(), key=lambda x: x[0]):
            if (not show_disabled) and it.get("disabled", False):
                continue
            self.tree.insert("", "end", values=(
                sku,
                it.get("name", ""),
                it.get("category", ""),
                self.store.money_str(it.get("unit_price", 0)),
                it.get("stock", 0),
                "YES" if it.get("disabled", False) else "",
            ))


class SingleMovementFrame(ttk.Frame):
    def __init__(self, parent, store, tabs: Optional[InventoryTabs] = None):
        super().__init__(parent)
        self.store = store
        self.tabs = tabs

        box = ttk.LabelFrame(self, text="単発 入出庫 / 在庫調整")
        box.pack(fill="x", padx=8, pady=8)

        self.var_action = tk.StringVar(value="IN")
        self.var_qty = tk.StringVar(value="1")
        self.var_note = tk.StringVar(value="")

        ttk.Label(box, text="操作").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Combobox(box, textvariable=self.var_action, values=["IN", "OUT", "ADJUST"], state="readonly", width=10)\
            .grid(row=0, column=1, sticky="w", padx=4, pady=2)

        ttk.Label(box, text="数量").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Combobox(box, textvariable=self.var_qty, values=[str(i) for i in range(0, 1001)], state="readonly", width=10)\
            .grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ttk.Label(box, text="メモ").grid(row=0, column=4, sticky="w", padx=4, pady=2)
        ttk.Entry(box, textvariable=self.var_note, width=30).grid(row=0, column=5, sticky="w", padx=4, pady=2)

        self.selector = CategoryItemSelector(box, store)
        self.selector.grid(row=1, column=0, columnspan=6, sticky="w", padx=4, pady=2)

        # --- simulation (pre-check) ---
        sim = ttk.LabelFrame(self, text="シミュレーション（実行前）")
        sim.pack(fill="x", padx=8, pady=(0, 8))

        self.var_sim_amount = tk.StringVar(value="")
        self.var_sim_total_after = tk.StringVar(value="")
        ttk.Label(sim, text="明細金額（予測）:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(sim, textvariable=self.var_sim_amount, font=("", 11, "bold")).grid(row=0, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(sim, text="在庫総額（更新後 予測）:").grid(row=0, column=2, sticky="w", padx=20, pady=4)
        ttk.Label(sim, textvariable=self.var_sim_total_after, font=("", 11, "bold")).grid(row=0, column=3, sticky="w", padx=6, pady=4)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btns, text="実行", command=self.on_apply).pack(side="right", padx=4)
        ttk.Button(btns, text="入力リセット", command=self.on_reset).pack(side="right", padx=4)

        # poll to reflect selector changes (CategoryItemSelector may not expose variables)
        self._preview_last_key = None
        self.after(200, self._preview_tick)

        self.refresh()

    def on_reset(self):
        self.var_action.set("IN")
        self.var_qty.set("1")
        self.var_note.set("")
        self.selector.refresh_all()
        self._update_preview()

    def _compute_preview(self) -> Optional[Tuple[int, int]]:
        sku = self.selector.get_selected_sku()
        action = self.var_action.get().strip().upper()
        qty = safe_int(self.var_qty.get(), None)
        if not sku or qty is None:
            return None

        it = self.store.data.get("items", {}).get(sku)
        if not it or it.get("disabled", False):
            return None

        unit = int(it.get("unit_price", 0) or 0)
        stock_before = int(it.get("stock", 0) or 0)
        current_total = calc_inventory_total(self.store)

        if action == "IN":
            amount = int(qty) * unit
        elif action == "OUT":
            amount = -int(qty) * unit
        elif action == "ADJUST":
            amount = (int(qty) - stock_before) * unit
        else:
            return None

        total_after = current_total + amount
        return amount, total_after

    def _update_preview(self):
        res = self._compute_preview()
        if res is None:
            self.var_sim_amount.set("")
            self.var_sim_total_after.set("")
        else:
            amount, total_after = res
            self.var_sim_amount.set(self.store.money_str(amount))
            self.var_sim_total_after.set(self.store.money_str(total_after))

    def _preview_tick(self):
        key = (self.selector.get_selected_sku(), self.var_action.get(), self.var_qty.get())
        if key != self._preview_last_key:
            self._preview_last_key = key
            self._update_preview()
        self.after(200, self._preview_tick)

    def on_apply(self):
        sku = self.selector.get_selected_sku()
        if not sku:
            messagebox.showwarning("操作", "商品を選択してください", parent=self)
            return

        action = self.var_action.get().strip().upper()
        qty = safe_int(self.var_qty.get(), -1)
        note = self.var_note.get()

        try:
            # preview for message
            preview = self._compute_preview()

            self.store.apply_movement(action, sku, int(qty), note)

            # after
            total_after = calc_inventory_total(self.store)
            if preview is not None:
                amount, _ = preview
                msg = f"在庫を更新しました。\n\n明細金額: {self.store.money_str(amount)}\n在庫総額（更新後）: {self.store.money_str(total_after)}"
            else:
                msg = f"在庫を更新しました。\n\n在庫総額（更新後）: {self.store.money_str(total_after)}"

            messagebox.showinfo("成功", msg, parent=self)

            if self.tabs is not None:
                self.tabs.refresh_all()
            else:
                self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def refresh(self):
        self.selector.refresh_all()
        self._update_preview()


class BatchMovementFrame(ttk.Frame):
    def __init__(self, parent, store, tabs: Optional[InventoryTabs] = None):
        super().__init__(parent)
        self.store = store
        self.tabs = tabs
        self.lines: List[Dict[str, Any]] = []

        top = ttk.LabelFrame(self, text="一括 入出庫（IN / OUT）")
        top.pack(fill="x", padx=8, pady=8)

        self.var_action = tk.StringVar(value="IN")
        self.var_qty = tk.StringVar(value="1")
        self.var_note = tk.StringVar(value="")

        ttk.Label(top, text="操作").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Combobox(top, textvariable=self.var_action, values=["IN", "OUT"], state="readonly", width=10)\
            .grid(row=0, column=1, sticky="w", padx=4, pady=2)

        ttk.Label(top, text="数量").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Combobox(top, textvariable=self.var_qty, values=[str(i) for i in range(0, 1001)], state="readonly", width=10)\
            .grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ttk.Label(top, text="メモ").grid(row=0, column=4, sticky="w", padx=4, pady=2)
        ttk.Entry(top, textvariable=self.var_note, width=30).grid(row=0, column=5, sticky="w", padx=4, pady=2)

        self.selector = CategoryItemSelector(top, store)
        self.selector.grid(row=1, column=0, columnspan=8, sticky="w", padx=4, pady=2)

        ttk.Button(top, text="明細に追加", command=self.on_add_line).grid(row=0, column=6, sticky="w", padx=8, pady=2)
        ttk.Button(top, text="明細をクリア", command=self.on_clear_lines).grid(row=0, column=7, sticky="w", padx=4, pady=2)

        # simulation
        sim = ttk.LabelFrame(self, text="シミュレーション（実行前）")
        sim.pack(fill="x", padx=8, pady=(0, 8))
        self.var_batch_amount = tk.StringVar(value="")
        self.var_batch_total_after = tk.StringVar(value="")
        ttk.Label(sim, text="明細合計（予測）:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(sim, textvariable=self.var_batch_amount, font=("", 11, "bold")).grid(row=0, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(sim, text="在庫総額（更新後 予測）:").grid(row=0, column=2, sticky="w", padx=20, pady=4)
        ttk.Label(sim, textvariable=self.var_batch_total_after, font=("", 11, "bold")).grid(row=0, column=3, sticky="w", padx=6, pady=4)

        mid = ttk.LabelFrame(self, text="一括明細")
        mid.pack(fill="both", expand=True, padx=8, pady=8)

        cols = ("sku", "name", "qty", "note")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        for c, w, t in [("sku", 140, "SKU"), ("name", 260, "商品名"), ("qty", 80, "数量"), ("note", 360, "メモ")]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        bot = ttk.Frame(self)
        bot.pack(fill="x", padx=8, pady=8)
        ttk.Button(bot, text="一括反映", command=self.on_apply_batch).pack(side="right", padx=4)

        self.refresh()
        self._update_batch_preview()

    def _batch_amount_sum(self) -> int:
        action = self.var_action.get().strip().upper()
        s = 0
        for ln in self.lines:
            sku = ln.get("sku", "")
            qty = int(ln.get("qty", 0) or 0)
            it = self.store.data.get("items", {}).get(sku, {})
            unit = int(it.get("unit_price", 0) or 0)
            if action == "IN":
                s += qty * unit
            else:
                s += -qty * unit
        return int(s)

    def _update_batch_preview(self):
        amount = self._batch_amount_sum()
        total_after = calc_inventory_total(self.store) + amount
        self.var_batch_amount.set(self.store.money_str(amount))
        self.var_batch_total_after.set(self.store.money_str(total_after))

    def on_add_line(self):
        sku = self.selector.get_selected_sku()
        if not sku:
            messagebox.showwarning("操作", "商品を選択してください", parent=self)
            return
        qty = safe_int(self.var_qty.get(), -1)
        if qty is None or qty < 0:
            messagebox.showwarning("入力", "数量が不正です", parent=self)
            return
        note = self.var_note.get().strip()

        it = self.store.get_item(sku)
        self.lines.append({"sku": sku, "qty": int(qty), "note": note})
        self.tree.insert("", "end", values=(sku, it.get("name", ""), int(qty), note))

        self.var_qty.set("1")
        self.var_note.set("")
        self._update_batch_preview()

    def on_clear_lines(self):
        self.lines = []
        self.tree.delete(*self.tree.get_children())
        self._update_batch_preview()

    def on_apply_batch(self):
        if not self.lines:
            messagebox.showwarning("操作", "明細が空です", parent=self)
            return
        action = self.var_action.get().strip().upper()

        try:
            amount = self._batch_amount_sum()
            self.store.apply_batch_movement(action, self.lines)

            total_after = calc_inventory_total(self.store)
            msg = f"一括反映しました。\n\n明細合計: {self.store.money_str(amount)}\n在庫総額（更新後）: {self.store.money_str(total_after)}"
            messagebox.showinfo("成功", msg, parent=self)

            self.on_clear_lines()
            if self.tabs is not None:
                self.tabs.refresh_all()
            else:
                self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def refresh(self):
        self.selector.refresh_all()
        self._update_batch_preview()


class InventoryHistoryFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)

        default_include = bool(self.store.get_setting("show_deleted_by_default", False))
        self.var_include_deleted = tk.BooleanVar(value=default_include)
        ttk.Checkbutton(top, text="削除済みも表示", variable=self.var_include_deleted, command=self.refresh).pack(side="left", padx=4)

        ttk.Button(top, text="選択行を削除（ゴミ箱）", command=self.on_soft_delete).pack(side="left", padx=6)
        ttk.Button(top, text="選択行を復元", command=self.on_restore).pack(side="left", padx=6)
        ttk.Button(top, text="選択行を完全削除（確認語入力）", command=self.on_hard_delete).pack(side="left", padx=6)
        ttk.Button(top, text="削除済みを完全消去（パージ）", command=self.on_purge).pack(side="left", padx=12)

        colorfrm = ttk.LabelFrame(self, text="カテゴリ色（履歴一覧の行背景色）")
        colorfrm.pack(fill="x", padx=8, pady=6)
        self.var_color_cat = tk.StringVar(value="")
        ttk.Label(colorfrm, text="カテゴリ").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.cb_cat = ttk.Combobox(colorfrm, textvariable=self.var_color_cat, state="readonly", width=30)
        self.cb_cat.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Button(colorfrm, text="色を設定", command=self.on_set_color).grid(row=0, column=2, sticky="w", padx=6, pady=2)

        table = ttk.Frame(self)
        table.pack(fill="both", expand=True, padx=8, pady=8)

        cols = (
            "id", "ts", "action", "sku", "name", "category", "qty",
            "unit_price", "amount", "inventory_total_after",
            "stock_after", "note", "deleted"
        )
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=18)

        widths = {
            "id": 120, "ts": 160, "action": 70, "sku": 120, "name": 220, "category": 140,
            "qty": 60, "unit_price": 110, "amount": 120, "inventory_total_after": 150,
            "stock_after": 90, "note": 220, "deleted": 70
        }
        label_map = {
            "id": "ID", "ts": "日時", "action": "操作", "sku": "SKU", "name": "商品名", "category": "カテゴリ",
            "qty": "数量", "unit_price": "単価", "amount": "金額", "inventory_total_after": "在庫総額(後)",
            "stock_after": "在庫(後)", "note": "メモ", "deleted": "削除"
        }
        for c in cols:
            self.tree.heading(c, text=label_map.get(c, c))
            self.tree.column(c, width=widths.get(c, 120), anchor="w")
        self.tree.pack(fill="both", expand=True)

        self.refresh()

    def _selected_id(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return str(vals[0]) if vals else None

    def on_soft_delete(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "履歴行を選択してください", parent=self)
            return
        ok, reason = confirm_soft_delete(self, "在庫履歴 削除")
        if not ok:
            return
        try:
            self.store.soft_delete_inventory_history(rid, reason)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_restore(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "履歴行を選択してください", parent=self)
            return
        try:
            self.store.restore_inventory_history(rid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_hard_delete(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "履歴行を選択してください", parent=self)
            return
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="在庫履歴 完全削除"):
            return
        try:
            self.store.hard_delete_inventory_history(rid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_purge(self):
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="在庫履歴 パージ"):
            return
        try:
            self.store.purge_deleted_inventory_history()
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_set_color(self):
        cat = self.var_color_cat.get().strip()
        if not cat:
            messagebox.showwarning("操作", "カテゴリを選択してください", parent=self)
            return
        color = pick_color(self, initial=self.store.get_category_color(cat) or "#FFFFFF")
        if not color:
            return
        try:
            self.store.set_category_color(cat, color)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())

        cats = self.store.list_categories(include_disabled_items=True)
        self.cb_cat["values"] = cats
        if cats and self.var_color_cat.get() not in cats:
            self.var_color_cat.set(cats[0])

        include_deleted = self.var_include_deleted.get()
        rows = self.store.list_inventory_history(include_deleted=include_deleted)

        apply_category_row_tags(self.tree, self.store)

        for r in rows:
            sku = r.get("sku", "")
            it = self.store.data.get("items", {}).get(sku, {})
            name = it.get("name", "(削除済み商品)")
            cat = it.get("category", "")

            tag = f"cat::{cat}" if cat in (self.store.data.get("category_colors", {}) or {}) else ""
            self.tree.insert("", "end", values=(
                r.get("id", ""),
                r.get("ts", ""),
                r.get("action", ""),
                sku,
                name,
                cat,
                r.get("qty", 0),
                self.store.money_str(r.get("unit_price", 0)),
                self.store.money_str(r.get("amount", 0)),                 # store側が未対応でも0表示
                self.store.money_str(r.get("inventory_total_after", 0)),  # store側が未対応でも0表示
                r.get("stock_after", 0),
                r.get("note", ""),
                "YES" if r.get("deleted", False) else "",
            ), tags=(tag,) if tag else ())


class InventoryGraphFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        top = ttk.LabelFrame(self, text="在庫推移グラフ")
        top.pack(fill="x", padx=8, pady=6)

        self.var_cat = tk.StringVar(value="")
        self.var_sku = tk.StringVar(value="")
        self.var_from = tk.StringVar(value="")
        self.var_to = tk.StringVar(value="")

        ttk.Label(top, text="カテゴリ").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.cb_cat = ttk.Combobox(top, textvariable=self.var_cat, state="readonly", width=28)
        self.cb_cat.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        self.cb_cat.bind("<<ComboboxSelected>>", lambda e: self._on_cat_changed())

        ttk.Label(top, text="商品").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        self.cb_sku = ttk.Combobox(top, textvariable=self.var_sku, state="readonly", width=30)
        self.cb_sku.grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ttk.Label(top, text="From (YYYY-MM-DD)").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(top, textvariable=self.var_from, width=16).grid(row=1, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(top, text="To (YYYY-MM-DD)").grid(row=1, column=2, sticky="w", padx=4, pady=2)
        ttk.Entry(top, textvariable=self.var_to, width=16).grid(row=1, column=3, sticky="w", padx=4, pady=2)

        ttk.Button(top, text="表示", command=self.plot).grid(row=1, column=4, sticky="w", padx=6, pady=2)
        ttk.Button(top, text="7日", command=lambda: self._preset_days(7)).grid(row=1, column=5, sticky="w", padx=4, pady=2)
        ttk.Button(top, text="30日", command=lambda: self._preset_days(30)).grid(row=1, column=6, sticky="w", padx=4, pady=2)
        ttk.Button(top, text="クリア", command=self._clear_range).grid(row=1, column=7, sticky="w", padx=4, pady=2)

        fig = Figure(figsize=(10, 5), dpi=100)
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        self.fig = fig

        self.refresh()

    def _preset_days(self, days: int):
        end = datetime.now()
        start = end - timedelta(days=days)
        self.var_from.set(start.strftime("%Y-%m-%d"))
        self.var_to.set(end.strftime("%Y-%m-%d"))
        self.plot()

    def _clear_range(self):
        self.var_from.set("")
        self.var_to.set("")
        self.plot()

    def _on_cat_changed(self):
        cat = self.var_cat.get().strip()
        if not cat:
            self.cb_sku["values"] = []
            self.var_sku.set("")
            return
        items = self.store.list_items_by_category(cat, include_disabled=False)
        skus = [sku for sku, _ in items]
        self.cb_sku["values"] = skus
        if skus:
            self.var_sku.set(skus[0])

    def refresh(self):
        cats = self.store.list_categories(include_disabled_items=False)
        self.cb_cat["values"] = cats
        if cats and self.var_cat.get() not in cats:
            self.var_cat.set(cats[0])
        self._on_cat_changed()
        self.plot()

    def plot(self):
        sku = self.var_sku.get().strip()
        self.ax.clear()

        if not sku:
            self.ax.set_title("商品を選択してください")
            self.canvas.draw()
            return

        start_dt = parse_date_yyyy_mm_dd(self.var_from.get().strip()) if self.var_from.get().strip() else None
        end_dt = parse_date_yyyy_mm_dd(self.var_to.get().strip()) if self.var_to.get().strip() else None

        hist = self.store.list_inventory_history(include_deleted=False)

        xs, ys = [], []
        for r in hist:
            if r.get("sku") != sku:
                continue
            ts = r.get("ts", "")
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if start_dt and dt < start_dt:
                continue
            if end_dt and dt > end_dt:
                continue
            xs.append(dt)
            ys.append(int(r.get("stock_after", 0) or 0))

        it = self.store.get_item(sku)
        self.ax.plot(xs, ys)
        self.ax.set_title(f"在庫推移: {it.get('name','')} ({sku})")
        self.ax.set_xlabel("日時")
        self.ax.set_ylabel("在庫数")
        self.fig.autofmt_xdate()
        self.canvas.draw()
