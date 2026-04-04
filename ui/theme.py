# ui/theme.py — アプリ全体の ttk スタイル
from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# 統一モード（clam/alt）時のみ True — Treeview ストライプ等で参照
_rich_ui_active: bool = False


def rich_ui_active() -> bool:
    return _rich_ui_active


def pick_native_theme(style: ttk.Style) -> str:
    """OS が提供するネイティブ系テーマ（見た目は OS ごとに大きく異なる）。"""
    names = style.theme_names()
    if sys.platform == "darwin" and "aqua" in names:
        return "aqua"
    if sys.platform == "win32":
        for t in ("vista", "xpnative", "winnative"):
            if t in names:
                return t
    for t in ("clam", "alt", "default"):
        if t in names:
            return t
    return style.theme_use() or "default"


def pick_unified_theme(style: ttk.Style) -> str:
    names = style.theme_names()
    for t in ("clam", "alt", "default"):
        if t in names:
            return t
    return pick_native_theme(style)


def pick_default_theme(style: ttk.Style, *, ui_mode: str) -> str:
    if (ui_mode or "unified") == "native":
        return pick_native_theme(style)
    return pick_unified_theme(style)


def _sync_title_strip(root: tk.Misc) -> None:
    """app が root._title_chrome に用意した枠の高さ・色を同期（設定変更後も呼ばれる）。"""
    ch = getattr(root, "_title_chrome", None)
    if ch is None:
        return
    if _rich_ui_active:
        ch.configure(height=5, bg="#3730a3")
    else:
        try:
            bg = root.cget("background")
        except tk.TclError:
            bg = "#f0f0f0"
        ch.configure(height=1, bg=bg)


def configure_app_styles(root: tk.Misc, style: ttk.Style) -> None:
    global _rich_ui_active

    try:
        default_font = tkfont.nametofont("TkDefaultFont")
        family = default_font.actual("family")
        size = int(default_font.actual("size") or 10)
    except Exception:
        family, size = ("Helvetica", 10)

    families = set(tkfont.families())
    jp_candidates = (
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Yu Gothic UI",
        "Yu Gothic",
        "Meiryo",
        "MS Gothic",
        "Noto Sans CJK JP",
    )
    if sys.platform == "darwin":
        ui_family = next((f for f in jp_candidates if f in families), family)
    else:
        ui_family = next((f for f in ("Yu Gothic UI", "Yu Gothic", "Meiryo", "MS Gothic") if f in families), family)

    th = style.theme_use()
    unified_chrome = th in ("clam", "alt", "default")
    _rich_ui_active = unified_chrome

    if unified_chrome:
        # ダッシュボード風パレット（slate + indigo）
        bg_page = "#f1f5f9"
        bg_header = "#ffffff"
        bg_sheet = "#ffffff"
        bg_card = bg_page
        border = "#e2e8f0"
        border_strong = "#cbd5e1"
        text_main = "#0f172a"
        text_muted = "#64748b"
        primary = "#4f46e5"
        primary_hover = "#6366f1"
        primary_press = "#4338ca"
        tree_sel = "#e0e7ff"
        tab_idle = "#e2e8f0"
        tab_sel = "#ffffff"

        sz = size + 1

        try:
            root.configure(background=bg_page)
        except Exception:
            pass

        style.configure(".", font=(ui_family, sz), background=bg_page, foreground=text_main)
        style.configure("TFrame", background=bg_page)
        style.configure("TLabel", background=bg_page, foreground=text_main)
        style.configure("TLabelframe", background=bg_page, foreground=text_main)
        style.configure("TLabelframe.Label", background=bg_page, foreground=text_main, font=(ui_family, sz, "bold"))
        style.configure("TCheckbutton", background=bg_page, foreground=text_main, font=(ui_family, sz))
        style.configure("TRadiobutton", background=bg_page, foreground=text_main, font=(ui_family, sz))

        style.configure("TNotebook", background=bg_page, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(16, 8),
            font=(ui_family, sz, "bold"),
            background=tab_idle,
            foreground=text_muted,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", tab_sel), ("active", tab_idle)],
            foreground=[("selected", "#3730a3"), ("!selected", text_muted), ("active", text_main)],
            expand=[("selected", [1, 1, 1, 0])],
        )

        style.configure("TEntry", fieldbackground=bg_sheet, foreground=text_main, insertcolor=text_main, padding=6)
        style.map("TEntry", fieldbackground=[("readonly", bg_sheet)])

        style.configure(
            "TCombobox",
            fieldbackground=bg_sheet,
            background=bg_sheet,
            foreground=text_main,
            arrowcolor=text_main,
            padding=4,
        )
        style.map("TCombobox", fieldbackground=[("readonly", bg_sheet)])

        style.configure("TSpinbox", fieldbackground=bg_sheet, foreground=text_main, padding=4)

        style.configure("Horizontal.TScale", background=bg_page)

        style.configure("TSeparator", background=border_strong)

        style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background=border,
            troughcolor=bg_page,
            bordercolor=border,
            arrowcolor=text_muted,
        )
        style.map("Vertical.TScrollbar", background=[("active", border_strong)])

        style.configure(
            "Horizontal.TScrollbar",
            gripcount=0,
            background=border,
            troughcolor=bg_page,
            bordercolor=border,
            arrowcolor=text_muted,
        )

        # 画面上部「シェル」ヘッダー（白カード）
        style.configure("ShellHeader.TFrame", background=bg_header)
        style.configure("ShellTitle.TLabel", font=(ui_family, max(sz + 6, 18), "bold"), foreground=text_main, background=bg_header)
        style.configure("ShellSubtitle.TLabel", font=(ui_family, sz), foreground=text_muted, background=bg_header)
        style.configure("ShellHeroCaption.TLabel", font=(ui_family, sz - 1), foreground=text_muted, background=bg_header)
        style.configure("ShellHeroValue.TLabel", font=(ui_family, max(sz + 5, 16), "bold"), foreground=primary, background=bg_header)

        style.configure("ShellInner.TFrame", background=bg_header)

        style.configure(
            "Treeview",
            rowheight=max(28, sz + 14),
            background=bg_sheet,
            fieldbackground=bg_sheet,
            foreground=text_main,
            borderwidth=0,
        )
        style.configure("Treeview.Heading", font=(ui_family, sz, "bold"), foreground=text_main, background=tab_idle)
        style.map("Treeview.Heading", background=[("active", border)])
        style.map(
            "Treeview",
            background=[("selected", tree_sel)],
            foreground=[("selected", text_main)],
        )

        # 白いカードセクション（枠付き）
        try:
            style.configure(
                "Card.TLabelframe",
                padding=14,
                background=bg_card,
                relief="solid",
                borderwidth=1,
                bordercolor=border,
            )
        except tk.TclError:
            style.configure(
                "Card.TLabelframe",
                padding=14,
                background=bg_card,
                relief="solid",
                borderwidth=1,
            )
        style.configure("Card.TLabelframe.Label", background=bg_card, foreground="#3730a3", font=(ui_family, sz, "bold"))

        style.configure("Accent.TButton", background=primary, foreground="#ffffff", padding=(14, 8), font=(ui_family, sz, "bold"))
        style.map(
            "Accent.TButton",
            background=[("active", primary_hover), ("pressed", primary_press), ("disabled", "#a5b4fc")],
            foreground=[("disabled", "#e0e7ff")],
        )

        style.configure("Toolbar.TButton", background="#e2e8f0", foreground=text_main, padding=(10, 6), font=(ui_family, sz))
        style.map(
            "Toolbar.TButton",
            background=[("active", "#cbd5e1"), ("pressed", "#94a3b8")],
        )

        # 互換・他タブ用ラベル
        style.configure("App.TLabel", font=(ui_family, sz), background=bg_page)
        style.configure("AppTitle.TLabel", font=(ui_family, max(sz + 4, 15), "bold"), foreground=text_main, background=bg_page)
        style.configure("AppSubtitle.TLabel", font=(ui_family, sz), foreground=text_muted, background=bg_page)
        style.configure("HeroValue.TLabel", font=(ui_family, max(sz + 5, 17), "bold"), foreground=primary, background=bg_page)
        style.configure("HeroCaption.TLabel", font=(ui_family, sz - 1), foreground=text_muted, background=bg_page)

        _sync_title_strip(root)
        return

    # --- ネイティブ / 非統一 ---
    style.configure(".", font=(ui_family, size))
    style.configure("TFrame", background="")
    style.configure("TLabel", background="")
    style.configure("Treeview", rowheight=max(24, size + 10))
    style.configure("App.TLabel", font=(ui_family, size))
    style.configure("AppTitle.TLabel", font=(ui_family, max(size + 4, 14), "bold"))
    style.configure("AppSubtitle.TLabel", font=(ui_family, size), foreground="#555")
    style.configure("HeroValue.TLabel", font=(ui_family, max(size + 6, 16), "bold"))
    style.configure("HeroCaption.TLabel", font=(ui_family, size - 1), foreground="#666")
    style.configure("Card.TLabelframe", padding=10)
    style.configure("Card.TLabelframe.Label", font=(ui_family, size, "bold"))
    style.configure("Accent.TButton", padding=(12, 6))
    style.configure("Toolbar.TButton", padding=(8, 4))
    style.configure("Treeview.Heading", font=(ui_family, size, "bold"))
    try:
        style.map(
            "Accent.TButton",
            background=[("active", "#2563eb"), ("!disabled", "#1d4ed8")],
            foreground=[("!disabled", "#ffffff")],
        )
    except Exception:
        pass

    _sync_title_strip(root)
