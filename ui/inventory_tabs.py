# ui/inventory_tabs.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import matplotlib

matplotlib.use("TkAgg")
from matplotlib import rcParams
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from utils import safe_int, parse_int_optional, parse_date_yyyy_mm_dd
from ui.common import (
    CategoryItemSelector,
    confirm_soft_delete,
    confirm_dangerous_delete,
    pick_color,
    apply_category_row_tags,
    register_rich_treeview,
    tree_row_tags,
)
from ui.theme import rich_ui_active
from ui.scrollframe import VerticalScrollFrame

rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = [
    "Hiragino Sans",
    "Hiragino Maru Gothic ProN",
    "Yu Gothic",
    "Meiryo",
    "MS Gothic",
    "Noto Sans CJK JP",
    "DejaVu Sans",
]
rcParams["axes.unicode_minus"] = False


class InventoryTabs(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        hero = ttk.LabelFrame(self, text="在庫サマリー", style="Card.TLabelframe")
        hero.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))

        self.var_inventory_total = tk.StringVar(value="")
        row = ttk.Frame(hero)
        row.pack(fill="x", padx=4, pady=6)
        ttk.Label(row, text="在庫評価額（有効商品のみ）", style="HeroCaption.TLabel").pack(side="left", padx=(4, 8))
        ttk.Label(row, textvariable=self.var_inventory_total, style="HeroValue.TLabel").pack(side="left")
        ttk.Button(row, text="一覧を更新", command=self.refresh_all, style="Toolbar.TButton").pack(side="right", padx=6)

        vscroll = VerticalScrollFrame(self)
        vscroll.grid(row=1, column=0, sticky="nsew")

        nb = ttk.Notebook(vscroll.body)
        _np = (10, 10) if rich_ui_active() else (6, 6)
        nb.pack(fill="x", expand=False, padx=_np[0], pady=_np[1])

        self.tab_master = ItemMasterFrame(nb, store, tabs=self)
        self.tab_single = SingleMovementFrame(nb, store, tabs=self)
        self.tab_batch = BatchMovementFrame(nb, store, tabs=self)
        self.tab_hist = InventoryHistoryFrame(nb, store)
        self.tab_graph = InventoryGraphFrame(nb, store)

        nb.add(self.tab_master, text="商品マスタ")
        nb.add(self.tab_single, text="単発入出庫")
        nb.add(self.tab_batch, text="一括入出庫")
        nb.add(self.tab_hist, text="在庫履歴")
        nb.add(self.tab_graph, text="在庫グラフ")

        self.nb = nb
        self._body_scroll = vscroll
        nb.bind("<<NotebookTabChanged>>", self._on_inner_notebook_tab)

        # matplotlib の plot は重いので起動直後は遅延。タブ表示を先に描画する。
        self.refresh_all(defer_graph=True)

    def _on_inner_notebook_tab(self, _event=None) -> None:
        """先に Tk の再描画を進め、スクロール領域とグラフは少し後で更新（真っ白な間を短くする）。"""
        self.update_idletasks()
        self.after(1, self._body_scroll.update_scrollregion)
        try:
            current = self.nb.nametowidget(self.nb.select())
        except tk.TclError:
            return
        if current is self.tab_graph:
            self.after(2, self.tab_graph.refresh)

    def refresh_all(self, *, defer_graph: bool = False) -> None:
        self.tab_master.refresh()
        self.tab_single.refresh()
        self.tab_batch.refresh()
        self.tab_hist.refresh()
        if not defer_graph:
            self.tab_graph.refresh()
        self.var_inventory_total.set(self.store.money_str(self.store.calc_inventory_total()))
        self.after(1, self._body_scroll.update_scrollregion)


class ItemMasterFrame(ttk.Frame):
    def __init__(self, parent, store, tabs: Optional[InventoryTabs] = None):
        super().__init__(parent)
        self.store = store
        self.tabs = tabs

        frm = ttk.LabelFrame(self, text="商品の登録・更新", style="Card.TLabelframe")
        frm.pack(fill="x", padx=10, pady=10)

        self.var_sku = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_stock = tk.StringVar()

        ttk.Label(frm, text="SKU").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(frm, textvariable=self.var_sku, width=22).grid(row=0, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(frm, text="商品名").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(frm, textvariable=self.var_name, width=34).grid(row=0, column=3, sticky="w", padx=4, pady=4)

        ttk.Label(frm, text="単価（円）").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(frm, textvariable=self.var_price, width=22).grid(row=1, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(frm, text="カテゴリ").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        self.cb_cat = ttk.Combobox(frm, textvariable=self.var_cat, width=32, state="normal")
        self.cb_cat.grid(row=1, column=3, sticky="w", padx=4, pady=4)

        ttk.Label(frm, text="在庫数量").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(frm, textvariable=self.var_stock, width=22).grid(row=2, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(frm, text="※マスタ上の在庫を直接上書きします（履歴は増えません）", foreground="#666").grid(
            row=2, column=2, columnspan=2, sticky="w", padx=4, pady=4
        )

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=4, sticky="e", padx=4, pady=8)
        ttk.Button(btns, text="保存", command=self.on_upsert, style="Accent.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text="入力クリア", command=self.on_reset, style="Toolbar.TButton").pack(side="left", padx=4)

        table = ttk.LabelFrame(self, text="商品一覧", style="Card.TLabelframe")
        table.pack(fill="x", expand=False, padx=10, pady=(0, 10))

        self.var_show_disabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(table, text="無効（アーカイブ）した商品も表示", variable=self.var_show_disabled, command=self.refresh).pack(
            anchor="w", padx=6, pady=4
        )

        cols = ("sku", "name", "category", "unit_price", "stock", "disabled")
        headings = {
            "sku": "SKU",
            "name": "商品名",
            "category": "カテゴリ",
            "unit_price": "単価",
            "stock": "在庫",
            "disabled": "無効",
        }
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=14)
        for c, w in [("sku", 120), ("name", 240), ("category", 160), ("unit_price", 110), ("stock", 72), ("disabled", 56)]:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="x", expand=False, padx=6, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_row)
        register_rich_treeview(self.tree)

        ops = ttk.Frame(table)
        ops.pack(fill="x", padx=6, pady=6)
        ttk.Button(ops, text="無効化", command=self.on_disable, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(ops, text="有効化", command=self.on_enable, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(ops, text="完全削除…", command=self.on_hard_delete, style="Toolbar.TButton").pack(side="left", padx=4)
        self.var_force_orphan = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            ops,
            text="履歴に参照があっても強制削除（非推奨）",
            variable=self.var_force_orphan,
        ).pack(side="left", padx=12)

        self.refresh()

    def _category_values(self) -> List[str]:
        return self.store.list_master_categories()

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
        price = parse_int_optional(self.var_price.get())
        cat = self.var_cat.get().strip()
        stock = parse_int_optional(self.var_stock.get())

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
            messagebox.showinfo("成功", "商品を保存しました", parent=self)
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
            messagebox.showwarning("操作", "一覧から商品を選択してください", parent=self)
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
            messagebox.showwarning("操作", "一覧から商品を選択してください", parent=self)
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
            messagebox.showwarning("操作", "一覧から商品を選択してください", parent=self)
            return
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="商品の完全削除"):
            return
        try:
            self.store.hard_delete_item(sku, allow_orphan=self.var_force_orphan.get())
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
        idx = 0
        for sku, it in sorted(self.store.data.get("items", {}).items(), key=lambda x: x[0]):
            if (not show_disabled) and it.get("disabled", False):
                continue
            self.tree.insert(
                "",
                "end",
                values=(
                    sku,
                    it.get("name", ""),
                    it.get("category", ""),
                    self.store.money_str(it.get("unit_price", 0)),
                    it.get("stock", 0),
                    "はい" if it.get("disabled", False) else "",
                ),
                tags=tree_row_tags(idx),
            )
            idx += 1


class SingleMovementFrame(ttk.Frame):
    def __init__(self, parent, store, tabs: Optional[InventoryTabs] = None):
        super().__init__(parent)
        self.store = store
        self.tabs = tabs

        box = ttk.LabelFrame(self, text="入庫・出庫・在庫調整", style="Card.TLabelframe")
        box.pack(fill="x", padx=10, pady=10)

        self.var_action = tk.StringVar(value="IN")
        self.var_qty = tk.StringVar(value="1")
        self.var_note = tk.StringVar(value="")

        ttk.Label(box, text="操作").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            box,
            textvariable=self.var_action,
            values=["IN", "OUT", "ADJUST"],
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(box, text="数量").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Combobox(box, textvariable=self.var_qty, values=[str(i) for i in range(0, 1001)], state="readonly", width=10).grid(
            row=0, column=3, sticky="w", padx=4, pady=4
        )

        ttk.Label(box, text="メモ").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Entry(box, textvariable=self.var_note, width=28).grid(row=0, column=5, sticky="w", padx=4, pady=4)

        self.selector = CategoryItemSelector(box, store, on_change=self._update_preview)
        self.selector.grid(row=1, column=0, columnspan=6, sticky="w", padx=4, pady=6)

        for v in (self.var_action, self.var_qty, self.var_note):
            v.trace_add("write", lambda *_: self._update_preview())

        sim = ttk.LabelFrame(self, text="実行前プレビュー", style="Card.TLabelframe")
        sim.pack(fill="x", padx=10, pady=(0, 8))

        self.var_sim_amount = tk.StringVar(value="")
        self.var_sim_total_after = tk.StringVar(value="")
        ttk.Label(sim, text="この操作の評価額変化").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(sim, textvariable=self.var_sim_amount, style="HeroValue.TLabel").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(sim, text="実行後の在庫評価額").grid(row=0, column=2, sticky="w", padx=16, pady=6)
        ttk.Label(sim, textvariable=self.var_sim_total_after, style="HeroValue.TLabel").grid(row=0, column=3, sticky="w", padx=8, pady=6)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="反映", command=self.on_apply, style="Accent.TButton").pack(side="right", padx=6)
        ttk.Button(btns, text="リセット", command=self.on_reset, style="Toolbar.TButton").pack(side="right", padx=6)

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
        qty = parse_int_optional(self.var_qty.get())
        if not sku or qty is None:
            return None

        it = self.store.data.get("items", {}).get(sku)
        if not it or it.get("disabled", False):
            return None

        unit = int(it.get("unit_price", 0) or 0)
        stock_before = int(it.get("stock", 0) or 0)
        current_total = self.store.calc_inventory_total()

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
            self.var_sim_amount.set("—")
            self.var_sim_total_after.set("—")
        else:
            amount, total_after = res
            self.var_sim_amount.set(self.store.money_str(amount))
            self.var_sim_total_after.set(self.store.money_str(total_after))

    def on_apply(self):
        sku = self.selector.get_selected_sku()
        if not sku:
            messagebox.showwarning("操作", "商品を選択してください", parent=self)
            return

        action = self.var_action.get().strip().upper()
        qty = safe_int(self.var_qty.get(), -1)
        note = self.var_note.get()

        try:
            preview = self._compute_preview()
            self.store.apply_movement(action, sku, int(qty), note)
            total_after = self.store.calc_inventory_total()
            if preview is not None:
                amount, _ = preview
                msg = (
                    f"在庫を更新しました。\n\n"
                    f"評価額の変化: {self.store.money_str(amount)}\n"
                    f"在庫評価額（更新後）: {self.store.money_str(total_after)}"
                )
            else:
                msg = f"在庫を更新しました。\n\n在庫評価額（更新後）: {self.store.money_str(total_after)}"

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

        top = ttk.LabelFrame(self, text="一括で入庫または出庫", style="Card.TLabelframe")
        top.pack(fill="x", padx=10, pady=10)

        self.var_action = tk.StringVar(value="IN")
        self.var_qty = tk.StringVar(value="1")
        self.var_note = tk.StringVar(value="")

        ttk.Label(top, text="操作").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(top, textvariable=self.var_action, values=["IN", "OUT"], state="readonly", width=12).grid(
            row=0, column=1, sticky="w", padx=4, pady=4
        )

        ttk.Label(top, text="数量").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Combobox(top, textvariable=self.var_qty, values=[str(i) for i in range(0, 1001)], state="readonly", width=10).grid(
            row=0, column=3, sticky="w", padx=4, pady=4
        )

        ttk.Label(top, text="メモ").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.var_note, width=26).grid(row=0, column=5, sticky="w", padx=4, pady=4)

        self.selector = CategoryItemSelector(top, store, on_change=self._update_batch_preview)
        self.selector.grid(row=1, column=0, columnspan=8, sticky="w", padx=4, pady=6)

        ttk.Button(top, text="明細に追加", command=self.on_add_line, style="Toolbar.TButton").grid(
            row=0, column=6, sticky="w", padx=8, pady=4
        )
        ttk.Button(top, text="明細クリア", command=self.on_clear_lines, style="Toolbar.TButton").grid(
            row=0, column=7, sticky="w", padx=4, pady=4
        )

        self.var_action.trace_add("write", lambda *_: self._update_batch_preview())

        sim = ttk.LabelFrame(self, text="プレビュー", style="Card.TLabelframe")
        sim.pack(fill="x", padx=10, pady=(0, 8))
        self.var_batch_amount = tk.StringVar(value="")
        self.var_batch_total_after = tk.StringVar(value="")
        ttk.Label(sim, text="明細の評価額合計").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(sim, textvariable=self.var_batch_amount, style="HeroValue.TLabel").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(sim, text="反映後の在庫評価額").grid(row=0, column=2, sticky="w", padx=16, pady=6)
        ttk.Label(sim, textvariable=self.var_batch_total_after, style="HeroValue.TLabel").grid(row=0, column=3, sticky="w", padx=8, pady=6)

        mid = ttk.LabelFrame(self, text="明細リスト", style="Card.TLabelframe")
        mid.pack(fill="x", expand=False, padx=10, pady=(0, 8))

        cols = ("sku", "name", "qty", "note")
        heads = {"sku": "SKU", "name": "商品名", "qty": "数量", "note": "メモ"}
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        for c, w in [("sku", 140), ("name", 260), ("qty", 72), ("note", 320)]:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="x", expand=False, padx=6, pady=6)
        register_rich_treeview(self.tree)

        bot = ttk.Frame(self)
        bot.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bot, text="一括で反映", command=self.on_apply_batch, style="Accent.TButton").pack(side="right", padx=6)

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
        total_after = self.store.calc_inventory_total() + amount
        self.var_batch_amount.set(self.store.money_str(amount))
        self.var_batch_total_after.set(self.store.money_str(total_after))

    def on_add_line(self):
        sku = self.selector.get_selected_sku()
        if not sku:
            messagebox.showwarning("操作", "商品を選択してください", parent=self)
            return
        qty = safe_int(self.var_qty.get(), -1)
        if qty < 0:
            messagebox.showwarning("入力", "数量が不正です", parent=self)
            return
        note = self.var_note.get().strip()

        it = self.store.get_item(sku)
        row_i = len(self.lines)
        self.lines.append({"sku": sku, "qty": int(qty), "note": note})
        self.tree.insert(
            "",
            "end",
            values=(sku, it.get("name", ""), int(qty), note),
            tags=tree_row_tags(row_i),
        )

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
            total_after = self.store.calc_inventory_total()
            msg = (
                f"一括反映しました。\n\n"
                f"評価額の合計変化: {self.store.money_str(amount)}\n"
                f"在庫評価額（更新後）: {self.store.money_str(total_after)}"
            )
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
        top.pack(fill="x", padx=10, pady=8)

        default_include = bool(self.store.get_setting("show_deleted_by_default", False))
        self.var_include_deleted = tk.BooleanVar(value=default_include)
        ttk.Checkbutton(top, text="削除済み行も表示", variable=self.var_include_deleted, command=self.refresh).pack(side="left", padx=4)

        ttk.Label(top, text="絞り込み").pack(side="left", padx=(16, 4))
        self.var_filter = tk.StringVar(value="")
        ent = ttk.Entry(top, textvariable=self.var_filter, width=28)
        ent.pack(side="left", padx=4)
        ent.bind("<KeyRelease>", lambda e: self.refresh())
        ttk.Button(top, text="CSV出力", command=self.on_export_csv, style="Toolbar.TButton").pack(side="right", padx=6)

        row2 = ttk.Frame(self)
        row2.pack(fill="x", padx=10, pady=(0, 6))
        ttk.Button(row2, text="選択を論理削除", command=self.on_soft_delete, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(row2, text="選択を復元", command=self.on_restore, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(row2, text="選択を完全削除…", command=self.on_hard_delete, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(row2, text="削除済みをパージ…", command=self.on_purge, style="Toolbar.TButton").pack(side="left", padx=12)

        colorfrm = ttk.LabelFrame(self, text="一覧の行色（カテゴリ別）", style="Card.TLabelframe")
        colorfrm.pack(fill="x", padx=10, pady=6)
        self.var_color_cat = tk.StringVar(value="")
        ttk.Label(colorfrm, text="カテゴリ").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.cb_cat = ttk.Combobox(colorfrm, textvariable=self.var_color_cat, state="readonly", width=30)
        self.cb_cat.grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Button(colorfrm, text="色を選択", command=self.on_set_color, style="Toolbar.TButton").grid(row=0, column=2, sticky="w", padx=8, pady=6)

        table = ttk.Frame(self)
        table.pack(fill="x", expand=False, padx=10, pady=(0, 10))

        cols = (
            "id",
            "ts",
            "action",
            "sku",
            "name",
            "category",
            "qty",
            "unit_price",
            "amount",
            "inventory_total_after",
            "stock_after",
            "note",
            "deleted",
        )
        headings = {
            "id": "ID",
            "ts": "日時",
            "action": "操作",
            "sku": "SKU",
            "name": "商品名",
            "category": "カテゴリ",
            "qty": "数量",
            "unit_price": "単価",
            "amount": "金額",
            "inventory_total_after": "在庫評価額(後)",
            "stock_after": "在庫(後)",
            "note": "メモ",
            "deleted": "削除",
        }
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=16)
        widths = {
            "id": 120,
            "ts": 150,
            "action": 64,
            "sku": 110,
            "name": 200,
            "category": 120,
            "qty": 52,
            "unit_price": 90,
            "amount": 100,
            "inventory_total_after": 120,
            "stock_after": 72,
            "note": 180,
            "deleted": 52,
        }
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="x", expand=False)
        register_rich_treeview(self.tree)

        self.refresh()

    def _selected_id(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return str(vals[0]) if vals else None

    def on_export_csv(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("すべて", "*.*")],
            title="在庫履歴を保存",
        )
        if not path:
            return
        try:
            n = self.store.export_inventory_history_csv(path, include_deleted=self.var_include_deleted.get())
            messagebox.showinfo("CSV", f"{n} 件を出力しました。\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_soft_delete(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "行を選択してください", parent=self)
            return
        ok, reason = confirm_soft_delete(self, "在庫履歴の削除")
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
            messagebox.showwarning("操作", "行を選択してください", parent=self)
            return
        try:
            self.store.restore_inventory_history(rid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_hard_delete(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "行を選択してください", parent=self)
            return
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="在庫履歴の完全削除"):
            return
        try:
            self.store.hard_delete_inventory_history(rid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_purge(self):
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="削除済み履歴の消去"):
            return
        try:
            n = self.store.purge_deleted_inventory_history()
            messagebox.showinfo("完了", f"論理削除済み {n} 件を消去しました。", parent=self)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_set_color(self):
        cat = self.var_color_cat.get().strip()
        if not cat:
            messagebox.showwarning("操作", "カテゴリを選んでください", parent=self)
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

        q = (self.var_filter.get() or "").strip().lower()
        if q:
            filtered = []
            for r in rows:
                sku = r.get("sku", "")
                it = self.store.data.get("items", {}).get(sku, {})
                blob = " ".join(
                    [
                        str(r.get("id", "")),
                        str(r.get("ts", "")),
                        str(r.get("action", "")),
                        sku,
                        str(it.get("name", "")),
                        str(it.get("category", "")),
                        str(r.get("note", "")),
                    ]
                ).lower()
                if q in blob:
                    filtered.append(r)
            rows = filtered

        apply_category_row_tags(self.tree, self.store)

        for i, r in enumerate(rows):
            sku = r.get("sku", "")
            it = self.store.data.get("items", {}).get(sku, {})
            name = it.get("name", "（参照なし）")
            cat = it.get("category", "")
            tag = f"cat::{cat}" if cat in (self.store.data.get("category_colors", {}) or {}) else ""
            self.tree.insert(
                "",
                "end",
                values=(
                    r.get("id", ""),
                    r.get("ts", ""),
                    r.get("action", ""),
                    sku,
                    name,
                    cat,
                    r.get("qty", 0),
                    self.store.money_str(r.get("unit_price", 0)),
                    self.store.money_str(r.get("amount", 0)),
                    self.store.money_str(r.get("inventory_total_after", 0)),
                    r.get("stock_after", 0),
                    r.get("note", ""),
                    "はい" if r.get("deleted", False) else "",
                ),
                tags=tree_row_tags(i, tag),
            )


class InventoryGraphFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        top = ttk.LabelFrame(self, text="条件", style="Card.TLabelframe")
        top.pack(fill="x", padx=10, pady=10)

        self.var_cat = tk.StringVar(value="")
        self.var_sku = tk.StringVar(value="")
        self.var_from = tk.StringVar(value="")
        self.var_to = tk.StringVar(value="")

        ttk.Label(top, text="カテゴリ").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.cb_cat = ttk.Combobox(top, textvariable=self.var_cat, state="readonly", width=28)
        self.cb_cat.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self.cb_cat.bind("<<ComboboxSelected>>", lambda e: self._on_cat_changed())

        ttk.Label(top, text="商品（SKU）").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.cb_sku = ttk.Combobox(top, textvariable=self.var_sku, state="readonly", width=30)
        self.cb_sku.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        ttk.Label(top, text="開始日").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.var_from, width=14).grid(row=1, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(top, text="終了日").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.var_to, width=14).grid(row=1, column=3, sticky="w", padx=4, pady=4)

        ttk.Label(top, text="YYYY-MM-DD（空欄は全期間）", foreground="#666").grid(row=1, column=4, sticky="w", padx=8)

        ttk.Button(top, text="再描画", command=self.plot, style="Accent.TButton").grid(row=0, column=4, sticky="w", padx=8, pady=4)
        ttk.Button(top, text="直近7日", command=lambda: self._preset_days(7), style="Toolbar.TButton").grid(row=0, column=5, sticky="w", padx=4)
        ttk.Button(top, text="直近30日", command=lambda: self._preset_days(30), style="Toolbar.TButton").grid(row=0, column=6, sticky="w", padx=4)
        ttk.Button(top, text="期間クリア", command=self._clear_range, style="Toolbar.TButton").grid(row=0, column=7, sticky="w", padx=4)

        fig = Figure(figsize=(9, 3.6), dpi=100)
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(fig, master=self)
        tw = self.canvas.get_tk_widget()
        tw.configure(height=340)
        tw.pack(fill="x", expand=False, padx=10, pady=(0, 10))
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

        start_d = None
        end_d = None
        try:
            if self.var_from.get().strip():
                start_d = parse_date_yyyy_mm_dd(self.var_from.get())
            if self.var_to.get().strip():
                end_d = parse_date_yyyy_mm_dd(self.var_to.get())
        except Exception:
            messagebox.showerror("入力エラー", "日付は YYYY-MM-DD で入力してください", parent=self)
            self.canvas.draw()
            return

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
            day = dt.date()
            if start_d and day < start_d:
                continue
            if end_d and day > end_d:
                continue
            xs.append(dt)
            ys.append(int(r.get("stock_after", 0) or 0))

        try:
            it = self.store.get_item(sku)
            title_name = it.get("name", "")
        except Exception:
            title_name = "（削除済み参照）"

        if not xs:
            self.ax.set_title(f"{title_name}（{sku}）— 該当データなし")
        else:
            self.ax.plot(xs, ys, marker="o", markersize=3)
            self.ax.set_title(f"在庫推移: {title_name}（{sku}）")
        self.ax.set_xlabel("日時")
        self.ax.set_ylabel("在庫数量")
        self.fig.autofmt_xdate()
        self.canvas.draw()
