# ui/common.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, colorchooser
from typing import Optional, Tuple

from utils import auto_foreground_for_bg


def confirm_soft_delete(parent, title: str = "削除確認") -> Tuple[bool, str]:
    ok = messagebox.askyesno(
        title,
        "削除（ゴミ箱へ移動）します。\n\n元に戻せますが、一覧からは消えます。\n続行しますか？",
        parent=parent
    )
    if not ok:
        return (False, "")
    reason = simpledialog.askstring(title, "削除理由（任意）:", parent=parent) or ""
    return (True, reason)


def confirm_dangerous_delete(parent, phrase: str = "DELETE", title: str = "危険操作の確認") -> bool:
    ok = messagebox.askyesno(
        title,
        "この操作は元に戻せません。\n\n本当に続行しますか？",
        parent=parent
    )
    if not ok:
        return False
    s = simpledialog.askstring(title, f"続行するには {phrase} と入力してください。", parent=parent)
    return (s == phrase)


def pick_color(parent) -> Optional[str]:
    c = colorchooser.askcolor(parent=parent)
    if not c or not c[1]:
        return None
    return c[1]


class CategoryItemSelector(ttk.Frame):
    """
    2段階プルダウン: カテゴリ → 商品
    """
    def __init__(self, parent, store, *, include_disabled_items: bool = False):
        super().__init__(parent)
        self.store = store
        self.include_disabled_items = include_disabled_items

        self.var_cat = tk.StringVar(value="")
        self.var_item = tk.StringVar(value="")

        ttk.Label(self, text="カテゴリ").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.cb_cat = ttk.Combobox(self, textvariable=self.var_cat, state="readonly", width=30)
        self.cb_cat.grid(row=0, column=1, sticky="w", padx=4, pady=2)

        ttk.Label(self, text="商品").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        self.cb_item = ttk.Combobox(self, textvariable=self.var_item, state="readonly", width=40)
        self.cb_item.grid(row=0, column=3, sticky="w", padx=4, pady=2)

        self.cb_cat.bind("<<ComboboxSelected>>", lambda e: self._refresh_items())
        self.refresh_all()

    def refresh_all(self):
        cats = self.store.list_categories(include_disabled_items=self.include_disabled_items)
        self.cb_cat["values"] = cats
        if cats and self.var_cat.get() not in cats:
            self.var_cat.set(cats[0])
        self._refresh_items()

    def _refresh_items(self):
        cat = self.var_cat.get()
        items = self.store.list_items_by_category(cat, include_disabled=self.include_disabled_items)
        labels = [f"{sku} | {name}" for sku, name in items]
        self.cb_item["values"] = labels
        if labels:
            if self.var_item.get() not in labels:
                self.var_item.set(labels[0])
        else:
            self.var_item.set("")

    def get_selected_sku(self) -> Optional[str]:
        s = self.var_item.get()
        if " | " not in s:
            return None
        return s.split(" | ", 1)[0].strip()

    def get_selected_category(self) -> str:
        return self.var_cat.get().strip()


def apply_category_row_tags(tree: ttk.Treeview, store):
    for cat, color in store.data.get("category_colors", {}).items():
        fg = auto_foreground_for_bg(color)
        tree.tag_configure(f"cat::{cat}", background=color, foreground=fg)
