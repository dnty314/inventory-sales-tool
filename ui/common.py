# ui/common.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, colorchooser
from typing import Callable, Optional, Tuple

from utils import auto_foreground_for_bg

# 統一モードの Treeview 交互行（先頭タグ。カテゴリ色タグが後ろで上書き）
TREE_TAG_STRIPE = "ui_stripe"


def register_rich_treeview(tree) -> None:
    from ui.theme import rich_ui_active

    if not rich_ui_active():
        return
    tree.tag_configure(TREE_TAG_STRIPE, background="#f1f5f9")


def tree_row_tags(row_index: int, *extra: str) -> Tuple[str, ...]:
    from ui.theme import rich_ui_active

    tags = [t for t in extra if t]
    if rich_ui_active() and row_index % 2 == 1:
        tags.insert(0, TREE_TAG_STRIPE)
    return tuple(tags)


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


def pick_color(parent, *, initial: Optional[str] = None) -> Optional[str]:
    kw = {"parent": parent}
    if initial:
        kw["initialcolor"] = initial
    c = colorchooser.askcolor(**kw)
    if not c or not c[1]:
        return None
    return c[1]


class CategoryItemSelector(ttk.Frame):
    """
    2段階プルダウン: カテゴリ → 商品
    """
    def __init__(
        self,
        parent,
        store,
        *,
        include_disabled_items: bool = False,
        on_change: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.store = store
        self.include_disabled_items = include_disabled_items
        self.on_change = on_change
        # 親が self.selector = CategoryItemSelector(...) の代入を終えるまで on_change を呼ばない
        self._suppress_change = True

        self.var_cat = tk.StringVar(value="")
        self.var_item = tk.StringVar(value="")

        ttk.Label(self, text="カテゴリ").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.cb_cat = ttk.Combobox(self, textvariable=self.var_cat, state="readonly", width=30)
        self.cb_cat.grid(row=0, column=1, sticky="w", padx=4, pady=2)

        ttk.Label(self, text="商品").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        self.cb_item = ttk.Combobox(self, textvariable=self.var_item, state="readonly", width=40)
        self.cb_item.grid(row=0, column=3, sticky="w", padx=4, pady=2)

        self.cb_cat.bind("<<ComboboxSelected>>", lambda e: self._on_cat_selected())
        self.cb_item.bind("<<ComboboxSelected>>", lambda e: self._emit_change())
        self.var_cat.trace_add("write", lambda *_: self._emit_change())
        self.var_item.trace_add("write", lambda *_: self._emit_change())
        self.refresh_all()
        self._suppress_change = False
        if self.on_change:
            self.after_idle(self._emit_change)

    def _emit_change(self) -> None:
        if self._suppress_change:
            return
        if self.on_change:
            self.on_change()

    def _on_cat_selected(self) -> None:
        self._refresh_items()
        self._emit_change()

    def refresh_all(self):
        cats = self.store.list_categories(include_disabled_items=self.include_disabled_items)
        self.cb_cat["values"] = cats
        if cats and self.var_cat.get() not in cats:
            self.var_cat.set(cats[0])
        self._refresh_items()
        self._emit_change()

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
