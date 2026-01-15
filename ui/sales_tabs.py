# ui/sales_tabs.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from utils import safe_int, parse_date_yyyy_mm_dd
from ui.common import CategoryItemSelector, confirm_soft_delete, confirm_dangerous_delete


class SalesTabs(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.tab_customers = CustomerFrame(nb, store)
        self.tab_input = SalesInputFrame(nb, store)
        self.tab_history = SalesHistoryFrame(nb, store)
        self.tab_summary = SalesSummaryFrame(nb, store)

        nb.add(self.tab_customers, text="顧客リスト")
        nb.add(self.tab_input, text="売上入力（顧客別）")
        nb.add(self.tab_history, text="売上履歴（期間指定）")
        nb.add(self.tab_summary, text="売上集計")

        self.nb = nb

    def refresh_all(self):
        self.tab_customers.refresh()
        self.tab_input.refresh()
        self.tab_history.refresh()
        self.tab_summary.refresh()


class CustomerFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        frm = ttk.LabelFrame(self, text="顧客登録/更新")
        frm.pack(fill="x", padx=8, pady=8)

        self.var_cid = tk.StringVar()
        self.var_name = tk.StringVar()

        ttk.Label(frm, text="顧客ID").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.var_cid, width=20).grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(frm, text="顧客名").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.var_name, width=30).grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ttk.Button(frm, text="追加/更新", command=self.on_upsert).grid(row=0, column=4, sticky="w", padx=6, pady=2)
        ttk.Button(frm, text="入力リセット", command=self.on_reset).grid(row=0, column=5, sticky="w", padx=4, pady=2)

        table = ttk.LabelFrame(self, text="顧客一覧（選択して操作）")
        table.pack(fill="both", expand=True, padx=8, pady=8)

        self.var_show_disabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(table, text="無効顧客も表示", variable=self.var_show_disabled, command=self.refresh).pack(anchor="w", padx=4, pady=2)

        cols = ("cid", "name", "disabled")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=16)
        for c, w in [("cid", 140), ("name", 280), ("disabled", 80)]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        ops = ttk.Frame(table)
        ops.pack(fill="x", padx=4, pady=4)
        ttk.Button(ops, text="無効化（削除）", command=self.on_disable).pack(side="left", padx=4)
        ttk.Button(ops, text="復活（有効化）", command=self.on_enable).pack(side="left", padx=4)
        ttk.Button(ops, text="完全削除（確認語入力）", command=self.on_hard_delete).pack(side="left", padx=4)

        self.var_force_orphan = tk.BooleanVar(value=False)
        ttk.Checkbutton(ops, text="売上参照があっても強制削除（非推奨）", variable=self.var_force_orphan).pack(side="left", padx=10)

        self.refresh()

    def on_reset(self):
        self.var_cid.set("")
        self.var_name.set("")

    def on_upsert(self):
        try:
            self.store.upsert_customer(self.var_cid.get(), self.var_name.get())
            messagebox.showinfo("成功", "顧客を追加/更新しました", parent=self)
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
        if not confirm_dangerous_delete(self, phrase=phrase, title="顧客 完全削除"):
            return
        try:
            self.store.hard_delete_customer(cid, allow_orphan=self.var_force_orphan.get())
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        show_disabled = self.var_show_disabled.get()
        for cid, cu in sorted(self.store.data.get("customers", {}).items(), key=lambda x: x[0]):
            if (not show_disabled) and cu.get("disabled", False):
                continue
            self.tree.insert("", "end", values=(cid, cu.get("name", ""), "YES" if cu.get("disabled", False) else ""))


class SalesInputFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store
        self.lines: List[Dict[str, Any]] = []

        top = ttk.LabelFrame(self, text="売上入力（在庫は変わりません）")
        top.pack(fill="x", padx=8, pady=8)

        self.var_cid = tk.StringVar(value="")
        ttk.Label(top, text="顧客").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.cb_customer = ttk.Combobox(top, textvariable=self.var_cid, state="readonly", width=40)
        self.cb_customer.grid(row=0, column=1, sticky="w", padx=4, pady=2)

        self.selector = CategoryItemSelector(top, store)
        self.selector.grid(row=1, column=0, columnspan=8, sticky="w", padx=4, pady=2)

        self.var_qty = tk.StringVar(value="1")
        self.var_note = tk.StringVar(value="")
        ttk.Label(top, text="数量").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Combobox(top, textvariable=self.var_qty, values=[str(i) for i in range(0, 101)], state="readonly", width=10)\
            .grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ttk.Label(top, text="メモ").grid(row=0, column=4, sticky="w", padx=4, pady=2)
        ttk.Entry(top, textvariable=self.var_note, width=30).grid(row=0, column=5, sticky="w", padx=4, pady=2)

        ttk.Button(top, text="明細に追加", command=self.on_add_line).grid(row=0, column=6, sticky="w", padx=8, pady=2)
        ttk.Button(top, text="明細をクリア", command=self.on_clear_lines).grid(row=0, column=7, sticky="w", padx=4, pady=2)

        mid = ttk.LabelFrame(self, text="売上明細（まとめて反映）")
        mid.pack(fill="both", expand=True, padx=8, pady=8)

        cols = ("sku", "name", "qty", "unit_price", "line_total", "note")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        widths = {"sku": 140, "name": 240, "qty": 60, "unit_price": 110, "line_total": 120, "note": 260}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        bot = ttk.Frame(self)
        bot.pack(fill="x", padx=8, pady=8)
        self.var_total = tk.StringVar(value="合計: 0")
        ttk.Label(bot, textvariable=self.var_total).pack(side="left", padx=4)
        ttk.Button(bot, text="売上としてまとめて反映", command=self.on_apply).pack(side="right", padx=4)

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

        self.lines.append({"sku": sku, "qty": qty, "note": self.var_note.get()})
        self.tree.insert("", "end", values=(
            sku,
            it.get("name", ""),
            qty,
            self.store.money_str(unit),
            self.store.money_str(line_total),
            self.var_note.get(),
        ))
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
            messagebox.showinfo("成功", "売上を反映しました", parent=self)
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
        top.pack(fill="x", padx=8, pady=6)

        default_include = bool(self.store.get_setting("show_deleted_by_default", False))
        self.var_include_deleted = tk.BooleanVar(value=default_include)
        ttk.Checkbutton(top, text="削除済みも表示", variable=self.var_include_deleted, command=self.refresh).pack(side="left", padx=4)

        ttk.Button(top, text="選択行を削除（ゴミ箱）", command=self.on_soft_delete).pack(side="left", padx=6)
        ttk.Button(top, text="選択行を復元", command=self.on_restore).pack(side="left", padx=6)
        ttk.Button(top, text="選択行を完全削除（確認語入力）", command=self.on_hard_delete).pack(side="left", padx=6)
        ttk.Button(top, text="削除済みを完全消去（パージ）", command=self.on_purge).pack(side="left", padx=12)

        filterf = ttk.LabelFrame(self, text="期間指定（YYYY-MM-DD）")
        filterf.pack(fill="x", padx=8, pady=6)

        self.var_from = tk.StringVar(value="")
        self.var_to = tk.StringVar(value="")
        ttk.Label(filterf, text="From").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(filterf, textvariable=self.var_from, width=16).grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(filterf, text="To").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Entry(filterf, textvariable=self.var_to, width=16).grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ttk.Button(filterf, text="表示", command=self.refresh).grid(row=0, column=4, sticky="w", padx=6, pady=2)

        table = ttk.Frame(self)
        table.pack(fill="both", expand=True, padx=8, pady=8)

        cols = ("id", "ts", "cid", "customer", "sku", "item", "qty", "unit_price", "line_total", "note", "deleted")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=18)
        widths = {
            "id": 120, "ts": 160, "cid": 100, "customer": 160,
            "sku": 120, "item": 200, "qty": 60, "unit_price": 110, "line_total": 120,
            "note": 200, "deleted": 70
        }
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="both", expand=True)

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

    def on_soft_delete(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "売上行を選択してください", parent=self)
            return
        ok, reason = confirm_soft_delete(self, "売上履歴 削除")
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
            messagebox.showwarning("操作", "売上行を選択してください", parent=self)
            return
        try:
            self.store.restore_sales(rid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_hard_delete(self):
        rid = self._selected_id()
        if not rid:
            messagebox.showwarning("操作", "売上行を選択してください", parent=self)
            return
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="売上履歴 完全削除"):
            return
        try:
            self.store.hard_delete_sales(rid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def on_purge(self):
        phrase = self.store.get_setting("danger_confirm_phrase", "DELETE")
        if not confirm_dangerous_delete(self, phrase=phrase, title="売上履歴 削除済みの完全消去"):
            return
        try:
            n = self.store.purge_deleted_sales()
            messagebox.showinfo("完了", f"削除済み {n} 件を完全消去しました", parent=self)
            self.refresh()
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())

        include_deleted = self.var_include_deleted.get()
        rows = self.store.list_sales(include_deleted=include_deleted)
        rows = self._filter_by_range(rows)

        customers = self.store.data.get("customers", {})
        items = self.store.data.get("items", {})

        for r in rows:
            cid = r.get("cid", "")
            sku = r.get("sku", "")
            cu = customers.get(cid, {})
            it = items.get(sku, {})
            self.tree.insert("", "end", values=(
                r.get("id", ""),
                r.get("ts", ""),
                cid,
                cu.get("name", "(削除済み顧客)"),
                sku,
                it.get("name", "(削除済み商品)"),
                r.get("qty", 0),
                self.store.money_str(r.get("unit_price", 0)),
                self.store.money_str(r.get("line_total", 0)),
                r.get("note", ""),
                "YES" if r.get("deleted", False) else "",
            ))


class SalesSummaryFrame(ttk.Frame):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store

        top = ttk.LabelFrame(self, text="売上集計（期間指定）")
        top.pack(fill="x", padx=8, pady=8)

        self.var_from = tk.StringVar(value="")
        self.var_to = tk.StringVar(value="")
        ttk.Label(top, text="From (YYYY-MM-DD)").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(top, textvariable=self.var_from, width=16).grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(top, text="To (YYYY-MM-DD)").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Entry(top, textvariable=self.var_to, width=16).grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ttk.Button(top, text="集計", command=self.refresh).grid(row=0, column=4, sticky="w", padx=6, pady=2)

        self.var_total_all = tk.StringVar(value="全体合計: 0")
        ttk.Label(top, textvariable=self.var_total_all).grid(row=1, column=0, columnspan=6, sticky="w", padx=4, pady=4)

        table = ttk.LabelFrame(self, text="顧客別合計")
        table.pack(fill="both", expand=True, padx=8, pady=8)

        cols = ("cid", "name", "total")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=18)
        for c, w in [("cid", 140), ("name", 260), ("total", 140)]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

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

        for cid, name in self.store.list_customers(include_disabled=True):
            total = self.store.sum_sales(start_ts=start_ts, end_ts=end_ts, cid=cid)
            self.tree.insert("", "end", values=(cid, name, self.store.money_str(total)))
