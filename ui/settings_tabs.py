# ui/settings_tabs.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from utils import safe_int, make_backup


class SettingsTabs(ttk.Frame):
    def __init__(self, parent, store, *, style: ttk.Style, on_settings_changed=None):
        super().__init__(parent)
        self.store = store
        self.style = style
        self.on_settings_changed = on_settings_changed

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        # ---- Appearance ----
        lf = ttk.LabelFrame(outer, text="表示（テーマ / 値段表示）")
        lf.pack(fill="x", padx=6, pady=6)

        # Theme
        ttk.Label(lf, text="テーマ").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.var_theme = tk.StringVar(value=self.store.get_setting("theme", ""))
        themes = list(self.style.theme_names())
        self.cb_theme = ttk.Combobox(lf, textvariable=self.var_theme, values=themes, state="readonly", width=30)
        self.cb_theme.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Button(lf, text="適用", command=self.apply_theme).grid(row=0, column=2, sticky="w", padx=6, pady=4)

        # Price mode
        ttk.Label(lf, text="値段の表示").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.var_price_mode = tk.StringVar(value=self.store.get_setting("price_mode", "int"))
        ttk.Radiobutton(lf, text="整数（例: 1200）", variable=self.var_price_mode, value="int", command=self.save_price_mode).grid(row=1, column=1, sticky="w", padx=4, pady=2)
        ttk.Radiobutton(lf, text="小数（例: 1200.00）", variable=self.var_price_mode, value="float", command=self.save_price_mode).grid(row=2, column=1, sticky="w", padx=4, pady=2)

        self.var_decimals = tk.StringVar(value=str(self.store.get_setting("price_decimals", 2)))
        ttk.Label(lf, text="小数点桁数").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.sp_dec = ttk.Spinbox(lf, from_=0, to=6, textvariable=self.var_decimals, width=6, command=self.save_decimals)
        self.sp_dec.grid(row=2, column=2, sticky="w", padx=6, pady=2)
        ttk.Button(lf, text="保存", command=self.save_decimals).grid(row=2, column=3, sticky="w", padx=6, pady=2)

        # ---- Safety ----
        lf2 = ttk.LabelFrame(outer, text="安全（削除確認など）")
        lf2.pack(fill="x", padx=6, pady=6)

        ttk.Label(lf2, text="完全削除の確認語").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.var_phrase = tk.StringVar(value=self.store.get_setting("danger_confirm_phrase", "DELETE"))
        ttk.Entry(lf2, textvariable=self.var_phrase, width=16).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Button(lf2, text="保存", command=self.save_phrase).grid(row=0, column=2, sticky="w", padx=6, pady=4)

        self.var_show_deleted_default = tk.BooleanVar(value=bool(self.store.get_setting("show_deleted_by_default", False)))
        ttk.Checkbutton(
            lf2,
            text="履歴画面で「削除済みも表示」を最初からONにする",
            variable=self.var_show_deleted_default,
            command=self.save_show_deleted_default
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=4, pady=4)

        # ---- Data ----
        lf3 = ttk.LabelFrame(outer, text="データ（バックアップ / 場所）")
        lf3.pack(fill="x", padx=6, pady=6)

        ttk.Label(lf3, text="データファイル").grid(row=0, column=0, sticky="w", padx=4, pady=4)

        path_var = tk.StringVar(value=self.store.path)
        
        ttk.Entry(
            lf3,
            width=80,
            state="readonly",
            textvariable=path_var
        ).grid(row=0, column=1, sticky="w", padx=4, pady=4)


        ttk.Button(lf3, text="今すぐバックアップ作成", command=self.make_backup).grid(row=1, column=0, sticky="w", padx=4, pady=6)
        ttk.Button(lf3, text="設定を初期化", command=self.reset_settings).grid(row=1, column=1, sticky="w", padx=4, pady=6)

        self._sync_controls()

    def _sync_controls(self):
        # Disable decimals controls when int mode
        mode = self.var_price_mode.get()
        state = "normal" if mode == "float" else "disabled"
        self.sp_dec.configure(state=state)

    def _notify_changed(self):
        if callable(self.on_settings_changed):
            self.on_settings_changed()

    def apply_theme(self):
        theme = self.var_theme.get()
        if theme and theme in self.style.theme_names():
            try:
                self.style.theme_use(theme)
                self.store.set_setting("theme", theme)
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
            messagebox.showwarning("入力", "確認語が空です", parent=self)
            return
        self.store.set_setting("danger_confirm_phrase", phrase)
        messagebox.showinfo("保存", f"確認語を {phrase} にしました", parent=self)

    def save_show_deleted_default(self):
        self.store.set_setting("show_deleted_by_default", bool(self.var_show_deleted_default.get()))
        self._notify_changed()

    def make_backup(self):
        try:
            dst = make_backup(self.store.path)
            messagebox.showinfo("バックアップ作成", f"バックアップを作成しました:\n{dst}", parent=self)
        except Exception as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def reset_settings(self):
        if not messagebox.askyesno("確認", "設定を初期化します。続行しますか？", parent=self):
            return
        self.store.reset_settings()
        # reload vars
        self.var_theme.set(self.store.get_setting("theme", ""))
        self.var_price_mode.set(self.store.get_setting("price_mode", "int"))
        self.var_decimals.set(str(self.store.get_setting("price_decimals", 2)))
        self.var_phrase.set(self.store.get_setting("danger_confirm_phrase", "DELETE"))
        self.var_show_deleted_default.set(bool(self.store.get_setting("show_deleted_by_default", False)))
        self._sync_controls()
        self._notify_changed()
