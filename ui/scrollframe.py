# ui/scrollframe.py — 縦スクロール可能な領域（中身は body に配置）
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk
from typing import Optional


class VerticalScrollFrame(ttk.Frame):
    """
    Canvas + スクロールバー。子ウィジェットは body に pack/grid する。
    ノートブック内のタブなど、縦に長い UI で下端が見切れるのを防ぐ。
    """

    _wheel_router_installed: bool = False

    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self._vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._vsb.grid(row=0, column=1, sticky="ns")

        self.body = ttk.Frame(self._canvas)
        self._content_win = self._canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>", self._on_body_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._install_global_wheel_router_once()
        self.after_idle(self._on_body_configure)

    def _install_global_wheel_router_once(self) -> None:
        if VerticalScrollFrame._wheel_router_installed:
            return
        top = self.winfo_toplevel()
        top.bind_all("<MouseWheel>", VerticalScrollFrame._global_wheel, add="+")
        top.bind_all("<Button-4>", VerticalScrollFrame._global_wheel, add="+")
        top.bind_all("<Button-5>", VerticalScrollFrame._global_wheel, add="+")
        VerticalScrollFrame._wheel_router_installed = True

    def _on_body_configure(self, _event: Optional[tk.Event] = None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def update_scrollregion(self) -> None:
        """一覧更新後などに呼ぶとスクロール範囲を再計算。"""
        self._on_body_configure()

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._content_win, width=max(int(event.width), 1))
        self._on_body_configure()

    def _scroll(self, event: tk.Event) -> None:
        if event.delta:
            if sys.platform == "darwin":
                self._canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif getattr(event, "num", None) == 4:
            self._canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self._canvas.yview_scroll(3, "units")

    @classmethod
    def _find_enclosing(cls, w: tk.Misc) -> Optional["VerticalScrollFrame"]:
        while w is not None:
            if isinstance(w, cls):
                return w
            w = w.master  # type: ignore[assignment]
        return None

    @classmethod
    def _global_wheel(cls, event: tk.Event) -> None:
        target = cls._find_enclosing(event.widget)
        if target is not None:
            target._scroll(event)

