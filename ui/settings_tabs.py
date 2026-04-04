# ui/settings_tabs.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from utils import safe_int, make_backup
from ui.theme import (
    configure_app_styles,
    pick_default_theme,
    pick_native_theme,
    pick_unified_theme,
)
from ui.scrollframe import VerticalScrollFrame


class SettingsTabs(ttk.Frame):
    def __init__(self, parent, store, *, style: ttk.Style, on_settings_changed=None):
        super().__init__(parent)
        self.store = store
        self.style = style
        self.on_settings_changed = on_settings_changed

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        vscroll = VerticalScrollFrame(self)
        vscroll.grid(row=0, column=0, sticky="nsew")

        outer = ttk.Frame(vscroll.body)
        outer.pack(fill="x", expand=False, padx=12, pady=12)

        lf = ttk.LabelFrame(outer, text="表示", style="Card.TLabelframe")
        lf.pack(fill="x", padx=4, pady=8)

        ttk.Label(lf, text="画面の見た目").grid(row=0, column=0, sticky="nw", padx=6, pady=6)
        self.var_ui_mode = tk.StringVar(value=self.store.get_setting("ui_mode", "unified"))
        mode_frm = ttk.Frame(lf)
        mode_frm.grid(row=0, column=1, columnspan=2, sticky="w", padx=6, pady=4)
        ttk.Radiobutton(
            mode_frm,
            text="統一（Windows・Mac でほぼ同じ・推奨）",
            variable=self.var_ui_mode,
            value="unified",
            command=self.save_ui_mode,
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_frm,
            text="OS の標準（Mac は aqua、Windows はネイティブ風など）",
            variable=self.var_ui_mode,
            value="native",
            command=self.save_ui_mode,
        ).pack(anchor="w")

        ttk.Label(lf, text="ttk テーマ").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.var_theme = tk.StringVar(value=self.store.get_setting("theme", "") or self.style.theme_use())
        themes = list(self.style.theme_names())
        self.cb_theme = ttk.Combobox(lf, textvariable=self.var_theme, values=themes, state="readonly", width=32)
        self.cb_theme.grid(row=1, column=1, sticky="w", padx=6, pady=6)
        ttk.Button(lf, text="適用", command=self.apply_theme, style="Accent.TButton").grid(row=1, column=2, sticky="w", padx=10, pady=6)
        ttk.Label(lf, text="※上で「統一」を選ぶと clam 系が使われ、細部の配色も揃います。", foreground="#666").grid(
            row=2, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4)
        )

        ttk.Label(lf, text="金額の表示形式").grid(row=3, column=0, sticky="nw", padx=6, pady=6)
        self.var_price_mode = tk.StringVar(value=self.store.get_setting("price_mode", "int"))
        ttk.Radiobutton(lf, text="整数（例: 1,200）", variable=self.var_price_mode, value="int", command=self.save_price_mode).grid(
            row=3, column=1, sticky="w", padx=6, pady=2
        )
        ttk.Radiobutton(lf, text="小数（例: 1,200.00）", variable=self.var_price_mode, value="float", command=self.save_price_mode).grid(
            row=4, column=1, sticky="w", padx=6, pady=2
        )

        self.var_decimals = tk.StringVar(value=str(self.store.get_setting("price_decimals", 2)))
        ttk.Label(lf, text="小数桁数").grid(row=5, column=0, sticky="w", padx=6, pady=6)
        self.sp_dec = ttk.Spinbox(lf, from_=0, to=6, textvariable=self.var_decimals, width=6, command=self.save_decimals)
        self.sp_dec.grid(row=5, column=1, sticky="w", padx=6, pady=4)
        ttk.Button(lf, text="桁数を保存", command=self.save_decimals, style="Toolbar.TButton").grid(row=5, column=2, sticky="w", padx=6, pady=4)

        lf2 = ttk.LabelFrame(outer, text="安全設定", style="Card.TLabelframe")
        lf2.pack(fill="x", padx=4, pady=8)

        ttk.Label(lf2, text="完全削除時の確認語").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.var_phrase = tk.StringVar(value=self.store.get_setting("danger_confirm_phrase", "DELETE"))
        ttk.Entry(lf2, textvariable=self.var_phrase, width=18).grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Button(lf2, text="保存", command=self.save_phrase, style="Toolbar.TButton").grid(row=0, column=2, sticky="w", padx=10, pady=6)

        self.var_show_deleted_default = tk.BooleanVar(value=bool(self.store.get_setting("show_deleted_by_default", False)))
        ttk.Checkbutton(
            lf2,
            text="履歴画面で「削除済みも表示」を初期ONにする",
            variable=self.var_show_deleted_default,
            command=self.save_show_deleted_default,
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=6, pady=6)

        lf3 = ttk.LabelFrame(outer, text="データファイル", style="Card.TLabelframe")
        lf3.pack(fill="x", padx=4, pady=8)

        ttk.Label(lf3, text="保存場所").grid(row=0, column=0, sticky="nw", padx=6, pady=6)
        path_var = tk.StringVar(value=self.store.path)
        ttk.Entry(lf3, width=72, state="readonly", textvariable=path_var).grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        lf3.columnconfigure(1, weight=1)

        ttk.Button(lf3, text="バックアップを作成", command=self.make_backup, style="Accent.TButton").grid(
            row=1, column=0, sticky="w", padx=6, pady=8
        )
        ttk.Button(lf3, text="表示設定のみ初期化", command=self.reset_settings, style="Toolbar.TButton").grid(
            row=1, column=1, sticky="w", padx=6, pady=8
        )

        self._sync_controls()

    def _sync_controls(self):
        mode = self.var_price_mode.get()
        state = "normal" if mode == "float" else "disabled"
        self.sp_dec.configure(state=state)

    def _notify_changed(self):
        if callable(self.on_settings_changed):
            self.on_settings_changed()

    def save_ui_mode(self):
        mode = self.var_ui_mode.get()
        if mode not in ("unified", "native"):
            mode = "unified"
        self.store.set_setting("ui_mode", mode)
        if mode == "unified":
            chosen = pick_unified_theme(self.style)
        else:
            chosen = pick_native_theme(self.style)
        try:
            self.style.theme_use(chosen)
        except Exception:
            chosen = pick_unified_theme(self.style)
            self.style.theme_use(chosen)
        self.store.set_setting("theme", chosen)
        self.var_theme.set(chosen)
        configure_app_styles(self.winfo_toplevel(), self.style)
        self._notify_changed()

    def apply_theme(self):
        theme = self.var_theme.get()
        if theme and theme in self.style.theme_names():
            try:
                self.style.theme_use(theme)
                self.store.set_setting("theme", theme)
                configure_app_styles(self.winfo_toplevel(), self.style)
                self._notify_changed()
            except Exception as e:
                messagebox.showerror("エラー", str(e), parent=self)

    def save_price_mode(self):
        mode = self.var_price_mode.get()
        if mode not in ("int", "float"):
            mode = "int"
        self.store.set_setting("price_mode", mode)
        self._sync_controls()
        self._notify_changed()

    def save_decimals(self):
        dec = safe_int(self.var_decimals.get(), 2)
        dec = max(0, min(6, dec))
        self.var_decimals.set(str(dec))
        self.store.set_setting("price_decimals", dec)
        self._notify_changed()

    def save_phrase(self):
        phrase = (self.var_phrase.get() or "").strip()
        if not phrase:
            messagebox.showwarning("入力", "確認語を空にはできません", parent=self)
            return
        self.store.set_setting("danger_confirm_phrase", phrase)
        messagebox.showinfo("保存", f"確認語を「{phrase}」にしました", parent=self)

    def save_show_deleted_default(self):
        self.store.set_setting("show_deleted_by_default", bool(self.var_show_deleted_default.get()))
        self._notify_changed()

    def make_backup(self):
        try:
            dst = make_backup(self.store.path)
            messagebox.showinfo("バックアップ", f"作成しました:\n{dst}", parent=self)
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def reset_settings(self):
        if not messagebox.askyesno("確認", "表示・安全に関する設定を初期値に戻します。続行しますか？", parent=self):
            return
        self.store.reset_settings()
        self.var_ui_mode.set(self.store.get_setting("ui_mode", "unified"))
        self.var_price_mode.set(self.store.get_setting("price_mode", "int"))
        self.var_decimals.set(str(self.store.get_setting("price_decimals", 2)))
        self.var_phrase.set(self.store.get_setting("danger_confirm_phrase", "DELETE"))
        self.var_show_deleted_default.set(bool(self.store.get_setting("show_deleted_by_default", False)))
        ui_m = self.store.get_setting("ui_mode", "unified")
        chosen = pick_default_theme(self.style, ui_mode=ui_m)
        try:
            self.style.theme_use(chosen)
        except Exception:
            chosen = pick_unified_theme(self.style)
            self.style.theme_use(chosen)
        self.store.set_setting("theme", chosen)
        self.var_theme.set(chosen)
        configure_app_styles(self.winfo_toplevel(), self.style)
        self._sync_controls()
        self._notify_changed()
