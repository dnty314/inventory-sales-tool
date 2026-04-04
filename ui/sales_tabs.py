# ui/sales_tabs.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils import safe_int, parse_date_yyyy_mm_dd
from ui.common import (
    CategoryItemSelector,
    confirm_soft_delete,
    confirm_dangerous_delete,
    register_rich_treeview,
    tree_row_tags,
)
from ui.theme import rich_ui_active
from ui.scrollframe import VerticalScrollFrame


class SalesTabs(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        vscroll = VerticalScrollFrame(self)
        vscroll.grid(row=0, column=0, sticky="nsew")

        nb = ttk.Notebook(vscroll.body)
        _np = (10, 10) if rich_ui_active() else (6, 6)
        nb.pack(fill="x", expand=False, padx=_np[0], pady=_np[1])

        self.tab_customers = CustomerFrame(nb, store)
        self.tab_input = SalesInputFrame(nb, store)
        self.tab_history = SalesHistoryFrame(nb, store)
        self.tab_summary = SalesSummaryFrame(nb, store)

        nb.add(self.tab_customers, text="顧客")
        nb.add(self.tab_input, text="売上入力")
        nb.add(self.tab_history, text="売上履歴")
        nb.add(self.tab_summary, text="売上集計")

        self.nb = nb
        self._body_scroll = vscroll
        nb.bind("<<NotebookTabChanged>>", self._on_inner_notebook_tab)

    def _on_inner_notebook_tab(self, _event=None) -> None:
        self.update_idletasks()
        self.after(1, self._body_scroll.update_scrollregion)

    def refresh_all(self):
        self.tab_customers.refresh()
        self.tab_input.refresh()
        self.tab_history.refresh()
        self.tab_summary.refresh()
        self.after(1, self._body_scroll.update_scrollregion)


class CustomerFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        frm = ttk.LabelFrame(self, text="顧客の登録・更新", style="Card.TLabelframe")
        frm.pack(fill="x", padx=10, pady=10)

        self.var_cid = tk.StringVar()
        self.var_name = tk.StringVar()

        ttk.Label(frm, text="顧客ID").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(frm, textvariable=self.var_cid, width=20).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(frm, text="顧客名").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(frm, textvariable=self.var_name, width=34).grid(row=0, column=3, sticky="w", padx=4, pady=4)

        ttk.Button(frm, text="保存", command=self.on_upsert, style="Accent.TButton").grid(row=0, column=4, sticky="w", padx=8, pady=4)
        ttk.Button(frm, text="クリア", command=self.on_reset, style="Toolbar.TButton").grid(row=0, column=5, sticky="w", padx=4, pady=4)

        table = ttk.LabelFrame(self, text="顧客一覧", style="Card.TLabelframe")
        table.pack(fill="x", expand=False, padx=10, pady=(0, 10))

        self.var_show_disabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(table, text="無効な顧客も表示", variable=self.var_show_disabled, command=self.refresh).pack(anchor="w", padx=6, pady=4)

        cols = ("cid", "name", "disabled")
        heads = {"cid": "顧客ID", "name": "顧客名", "disabled": "無効"}
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=16)
        for c, w in [("cid", 140), ("name", 300), ("disabled", 56)]:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="x", expand=False, padx=6, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        register_rich_treeview(self.tree)

        ops = ttk.Frame(table)
        ops.pack(fill="x", padx=6, pady=6)
        ttk.Button(ops, text="無効化", command=self.on_disable, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(ops, text="有効化", command=self.on_enable, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(ops, text="完全削除…", command=self.on_hard_delete, style="Toolbar.TButton").pack(side="left", padx=4)
        self.var_force_orphan = tk.BooleanVar(value=False)
        ttk.Checkbutton(ops, text="売上参照があっても強制削除（非推奨）", variable=self.var_force_orphan).pack(side="left", padx=12)

        self.refresh()

    def on_reset(self):
        self.var_cid.set("")
        self.var_name.set("")

    def on_upsert(self):
        try:
            self.store.upsert_customer(self.var_cid.get(), self.var_name.get())
            messagebox.showinfo("成功", "顧客を保存しました", parent=self)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def _selected_cid(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        return str(self.tree.item(sel[0], "values")[0])

    def on_select(self, _e=None):
        cid = self._selected_cid()
        if not cid:
            return
        cu = self.store.data.get("customers", {}).get(cid, {})
        self.var_cid.set(cid)
        self.var_name.set(cu.get("name", ""))

    def on_disable(self):
        cid = self._selected_cid()
        if not cid:
            messagebox.showwarning("操作", "顧客を選択してください", parent=self)
            return
        try:
            self.store.disable_customer(cid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_enable(self):
        cid = self._selected_cid()
        if not cid:
            messagebox.showwarning("操作", "顧客を選択してください", parent=self)
            return
        try:
            self.store.enable_customer(cid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_hard_delete(self):
        cid = self._selected_cid()
        if not cid:
            messagebox.showwarning("操作", "顧客を選択してください", parent=self)
            return
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="顧客の完全削除"):
            return
        try:
            self.store.hard_delete_customer(cid, allow_orphan=self.var_force_orphan.get())
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        show_disabled = self.var_show_disabled.get()
        idx = 0
        for cid, cu in sorted(self.store.data.get("customers", {}).items(), key=lambda x: x[0]):
            if (not show_disabled) and cu.get("disabled", False):
                continue
            self.tree.insert(
                "",
                "end",
                values=(cid, cu.get("name", ""), "はい" if cu.get("disabled", False) else ""),
                tags=tree_row_tags(idx),
            )
            idx += 1


class SalesInputFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store
        self.lines: List[Dict[str, Any]] = []

        top = ttk.LabelFrame(self, text="売上明細の作成（在庫数は変わりません）", style="Card.TLabelframe")
        top.pack(fill="x", padx=10, pady=10)

        self.var_cid = tk.StringVar(value="")
        ttk.Label(top, text="顧客").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.cb_customer = ttk.Combobox(top, textvariable=self.var_cid, state="readonly", width=42)
        self.cb_customer.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        self.selector = CategoryItemSelector(top, store)
        self.selector.grid(row=1, column=0, columnspan=8, sticky="w", padx=4, pady=6)

        self.var_qty = tk.StringVar(value="1")
        self.var_note = tk.StringVar(value="")
        ttk.Label(top, text="数量").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Combobox(top, textvariable=self.var_qty, values=[str(i) for i in range(0, 101)], state="readonly", width=8).grid(
            row=0, column=3, sticky="w", padx=4, pady=4
        )

        ttk.Label(top, text="メモ").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.var_note, width=28).grid(row=0, column=5, sticky="w", padx=4, pady=4)

        ttk.Button(top, text="明細に追加", command=self.on_add_line, style="Toolbar.TButton").grid(row=0, column=6, sticky="w", padx=8, pady=4)
        ttk.Button(top, text="明細クリア", command=self.on_clear_lines, style="Toolbar.TButton").grid(row=0, column=7, sticky="w", padx=4, pady=4)

        mid = ttk.LabelFrame(self, text="未登録の売上明細", style="Card.TLabelframe")
        mid.pack(fill="x", expand=False, padx=10, pady=(0, 8))

        cols = ("sku", "name", "qty", "unit_price", "line_total", "note")
        heads = {
            "sku": "SKU",
            "name": "商品名",
            "qty": "数量",
            "unit_price": "単価",
            "line_total": "金額",
            "note": "メモ",
        }
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        widths = {"sku": 130, "name": 240, "qty": 56, "unit_price": 100, "line_total": 110, "note": 240}
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="x", expand=False, padx=6, pady=6)
        register_rich_treeview(self.tree)

        bot = ttk.Frame(self)
        bot.pack(fill="x", padx=10, pady=(0, 10))
        self.var_total = tk.StringVar(value="合計: 0")
        ttk.Label(bot, textvariable=self.var_total, style="HeroValue.TLabel").pack(side="left", padx=6)
        ttk.Button(bot, text="売上として登録", command=self.on_apply, style="Accent.TButton").pack(side="right", padx=6)

        self.refresh()

    def _refresh_customers(self):
        customers = self.store.list_customers(include_disabled=False)
        labels = [f"{cid} | {name}" for cid, name in customers]
        self.cb_customer["values"] = labels
        if labels:
            if self.var_cid.get() not in labels:
                self.var_cid.set(labels[0])
        else:
            self.var_cid.set("")

    def _selected_customer_id(self) -> Optional[str]:
        s = self.var_cid.get()
        if " | " not in s:
            return None
        return s.split(" | ", 1)[0].strip()

    def on_add_line(self):
        cid = self._selected_customer_id()
        if not cid:
            messagebox.showwarning("操作", "顧客を選択してください", parent=self)
            return
        sku = self.selector.get_selected_sku()
        if not sku:
            messagebox.showwarning("操作", "商品を選択してください", parent=self)
            return
        qty = safe_int(self.var_qty.get(), -1)
        if qty < 0:
            messagebox.showwarning("入力", "数量が不正です", parent=self)
            return

        it = self.store.get_item(sku)
        unit = int(it.get("unit_price", 0))
        line_total = unit * qty

        row_i = len(self.lines)
        self.lines.append({"sku": sku, "qty": qty, "note": self.var_note.get()})
        self.tree.insert(
            "",
            "end",
            values=(
                sku,
                it.get("name", ""),
                qty,
                self.store.money_str(unit),
                self.store.money_str(line_total),
                self.var_note.get(),
            ),
            tags=tree_row_tags(row_i),
        )
        self.var_note.set("")
        self._update_total()

    def on_clear_lines(self):
        self.lines = []
        self.tree.delete(*self.tree.get_children())
        self._update_total()

    def _update_total(self):
        total = 0
        for ln in self.lines:
            it = self.store.get_item(ln["sku"])
            total += int(it.get("unit_price", 0)) * int(ln["qty"])
        self.var_total.set(f"合計: {self.store.money_str(total)}")

    def on_apply(self):
        cid = self._selected_customer_id()
        if not cid:
            messagebox.showwarning("操作", "顧客を選択してください", parent=self)
            return
        if not self.lines:
            messagebox.showwarning("操作", "明細が空です", parent=self)
            return
        try:
            self.store.add_sales_batch(cid, self.lines)
            messagebox.showinfo("成功", "売上を登録しました", parent=self)
            self.on_clear_lines()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def refresh(self):
        self._refresh_customers()
        self.selector.refresh_all()
        self._update_total()


class SalesHistoryFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        default_include = bool(self.store.get_setting("show_deleted_by_default", False))
        self.var_include_deleted = tk.BooleanVar(value=default_include)
        ttk.Checkbutton(top, text="削除済みも表示", variable=self.var_include_deleted, command=self.refresh).pack(side="left", padx=4)

        ttk.Label(top, text="絞り込み").pack(side="left", padx=(16, 4))
        self.var_quick = tk.StringVar(value="")
        ent = ttk.Entry(top, textvariable=self.var_quick, width=26)
        ent.pack(side="left", padx=4)
        ent.bind("<KeyRelease>", lambda e: self.refresh())

        ttk.Button(top, text="CSV出力", command=self.on_export_csv, style="Toolbar.TButton").pack(side="right", padx=6)

        row2 = ttk.Frame(self)
        row2.pack(fill="x", padx=10, pady=(0, 6))
        ttk.Button(row2, text="選択を論理削除", command=self.on_soft_delete, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(row2, text="選択を復元", command=self.on_restore, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(row2, text="選択を完全削除…", command=self.on_hard_delete, style="Toolbar.TButton").pack(side="left", padx=4)
        ttk.Button(row2, text="削除済みをパージ…", command=self.on_purge, style="Toolbar.TButton").pack(side="left", padx=12)

        filterf = ttk.LabelFrame(self, text="期間（YYYY-MM-DD）", style="Card.TLabelframe")
        filterf.pack(fill="x", padx=10, pady=6)

        self.var_from = tk.StringVar(value="")
        self.var_to = tk.StringVar(value="")
        ttk.Label(filterf, text="開始").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(filterf, textvariable=self.var_from, width=14).grid(row=0, column=1, sticky="w", padx=4, pady=6)
        ttk.Label(filterf, text="終了").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(filterf, textvariable=self.var_to, width=14).grid(row=0, column=3, sticky="w", padx=4, pady=6)
        ttk.Button(filterf, text="適用", command=self.refresh, style="Toolbar.TButton").grid(row=0, column=4, sticky="w", padx=10, pady=6)

        table = ttk.Frame(self)
        table.pack(fill="x", expand=False, padx=10, pady=(0, 10))

        cols = ("id", "ts", "cid", "customer", "sku", "item", "qty", "unit_price", "line_total", "note", "deleted")
        heads = {
            "id": "ID",
            "ts": "日時",
            "cid": "顧客ID",
            "customer": "顧客名",
            "sku": "SKU",
            "item": "商品名",
            "qty": "数量",
            "unit_price": "単価",
            "line_total": "金額",
            "note": "メモ",
            "deleted": "削除",
        }
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=18)
        widths = {
            "id": 110,
            "ts": 148,
            "cid": 88,
            "customer": 140,
            "sku": 110,
            "item": 180,
            "qty": 48,
            "unit_price": 88,
            "line_total": 100,
            "note": 160,
            "deleted": 48,
        }
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="x", expand=False)
        register_rich_treeview(self.tree)

        self.refresh()

    def _selected_id(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        return str(self.tree.item(sel[0], "values")[0])

    def _filter_by_range(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from_s = self.var_from.get().strip()
        to_s = self.var_to.get().strip()
        if not from_s and not to_s:
            return rows

        try:
            start_ts = None
            end_ts = None
            if from_s:
                start_ts = datetime.combine(parse_date_yyyy_mm_dd(from_s), datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
            if to_s:
                end_ts = datetime.combine(parse_date_yyyy_mm_dd(to_s), datetime.max.time()).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            messagebox.showerror("入力エラー", "日付は YYYY-MM-DD 形式で入力してください", parent=self)
            return rows

        out = []
        for r in rows:
            ts = r.get("ts", "")
            if start_ts and ts < start_ts:
                continue
            if end_ts and ts > end_ts:
                continue
            out.append(r)
        return out

    def on_export_csv(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("すべて", "*.*")],
            title="売上履歴を保存",
        )
        if not path:
            return
        try:
            n = self.store.export_sales_csv(path, include_deleted=self.var_include_deleted.get())
            messagebox.showinfo("CSV", f"{n} 件を出力しました。\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_soft_delete(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "行を選択してください", parent=self)
            return
        ok, reason = confirm_soft_delete(self, "売上履歴の削除")
        if not ok:
            return
        try:
            self.store.soft_delete_sales(rid, reason)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_restore(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "行を選択してください", parent=self)
            return
        try:
            self.store.restore_sales(rid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_hard_delete(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "行を選択してください", parent=self)
            return
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="売上履歴の完全削除"):
            return
        try:
            self.store.hard_delete_sales(rid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_purge(self):
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="削除済み売上の消去"):
            return
        try:
            n = self.store.purge_deleted_sales()
            messagebox.showinfo("完了", f"論理削除済み {n} 件を消去しました。", parent=self)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())

        include_deleted = self.var_include_deleted.get()
        rows = self.store.list_sales(include_deleted=include_deleted)
        rows = self._filter_by_range(rows)

        q = (self.var_quick.get() or "").strip().lower()
        if q:
            filtered = []
            for r in rows:
                cid = r.get("cid", "")
                sku = r.get("sku", "")
                blob = " ".join(
                    [
                        str(r.get("id", "")),
                        str(r.get("ts", "")),
                        cid,
                        self.store.resolve_customer_name(cid),
                        sku,
                        self.store.resolve_item_name(sku),
                        str(r.get("note", "")),
                    ]
                ).lower()
                if q in blob:
                    filtered.append(r)
            rows = filtered

        for i, r in enumerate(rows):
            cid = r.get("cid", "")
            sku = r.get("sku", "")
            self.tree.insert(
                "",
                "end",
                values=(
                    r.get("id", ""),
                    r.get("ts", ""),
                    cid,
                    self.store.resolve_customer_name(cid),
                    sku,
                    self.store.resolve_item_name(sku),
                    r.get("qty", 0),
                    self.store.money_str(r.get("unit_price", 0)),
                    self.store.money_str(r.get("line_total", 0)),
                    r.get("note", ""),
                    "はい" if r.get("deleted", False) else "",
                ),
                tags=tree_row_tags(i),
            )


class SalesSummaryFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        top = ttk.LabelFrame(self, text="期間を指定して集計", style="Card.TLabelframe")
        top.pack(fill="x", padx=10, pady=10)

        self.var_from = tk.StringVar(value="")
        self.var_to = tk.StringVar(value="")
        ttk.Label(top, text="開始日").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(top, textvariable=self.var_from, width=14).grid(row=0, column=1, sticky="w", padx=4, pady=6)
        ttk.Label(top, text="終了日").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(top, textvariable=self.var_to, width=14).grid(row=0, column=3, sticky="w", padx=4, pady=6)
        ttk.Label(top, text="YYYY-MM-DD（空欄は全期間）", foreground="#666").grid(row=0, column=4, sticky="w", padx=10)

        ttk.Button(top, text="集計する", command=self.refresh, style="Accent.TButton").grid(row=0, column=5, sticky="w", padx=10, pady=6)

        self.var_total_all = tk.StringVar(value="全体合計: 0")
        ttk.Label(top, textvariable=self.var_total_all, style="HeroValue.TLabel").grid(row=1, column=0, columnspan=6, sticky="w", padx=6, pady=8)

        table = ttk.LabelFrame(self, text="顧客別の合計", style="Card.TLabelframe")
        table.pack(fill="x", expand=False, padx=10, pady=(0, 10))

        cols = ("cid", "name", "total")
        heads = {"cid": "顧客ID", "name": "顧客名", "total": "合計金額"}
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=18)
        for c, w in [("cid", 120), ("name", 280), ("total", 140)]:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="x", expand=False, padx=6, pady=6)
        register_rich_treeview(self.tree)

        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())

        from_s = self.var_from.get().strip()
        to_s = self.var_to.get().strip()

        start_ts = None
        end_ts = None
        try:
            if from_s:
                start_ts = datetime.combine(parse_date_yyyy_mm_dd(from_s), datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
            if to_s:
                end_ts = datetime.combine(parse_date_yyyy_mm_dd(to_s), datetime.max.time()).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            if from_s or to_s:
                messagebox.showerror("入力エラー", "日付は YYYY-MM-DD 形式で入力してください", parent=self)
                return

        all_total = self.store.sum_sales(start_ts=start_ts, end_ts=end_ts, cid=None)
        self.var_total_all.set(f"全体合計: {self.store.money_str(all_total)}")

        for idx, (cid, name) in enumerate(self.store.list_customers(include_disabled=True)):
            total = self.store.sum_sales(start_ts=start_ts, end_ts=end_ts, cid=cid)
            self.tree.insert(
                "",
                "end",
                values=(cid, name, self.store.money_str(total)),
                tags=tree_row_tags(idx),
            )
