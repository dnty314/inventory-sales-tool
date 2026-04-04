# app.py
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from paths import get_data_file_path
from store import StoreJSON
from ui.theme import configure_app_styles, pick_default_theme, rich_ui_active
from ui.inventory_tabs import InventoryTabs
from ui.sales_tabs import SalesTabs
from ui.settings_tabs import SettingsTabs

APP_TITLE = "在庫・売上管理ツール"

DATA_FILE = get_data_file_path()


def main():
    root = tk.Tk()
    root.title(APP_TITLE)
    root.minsize(1000, 600)
    root.geometry("1280x840")

    root._title_chrome = tk.Frame(root, highlightthickness=0, borderwidth=0)
    root._title_chrome.pack(side="top", fill="x")
    root._title_chrome.pack_propagate(False)

    try:
        store = StoreJSON(DATA_FILE)
    except Exception as e:
        messagebox.showerror("起動エラー", f"データファイルの読み込みに失敗しました。\n\n{e}")
        return

    style = ttk.Style(root)
    ui_mode = store.get_setting("ui_mode", "unified")
    saved_theme = store.get_setting("theme", "")
    names = style.theme_names()
    if saved_theme and saved_theme in names:
        try:
            style.theme_use(saved_theme)
        except Exception:
            style.theme_use(pick_default_theme(style, ui_mode=ui_mode))
    else:
        style.theme_use(pick_default_theme(style, ui_mode=ui_mode))

    configure_app_styles(root, style)

    rich = rich_ui_active()
    # --- ヘッダー（ダッシュボード） ---
    hdr_style = "ShellHeader.TFrame" if rich else "TFrame"
    hdr_pad = (22, 16) if rich else (16, 10)
    title_st = "ShellTitle.TLabel" if rich else "AppTitle.TLabel"
    sub_st = "ShellSubtitle.TLabel" if rich else "AppSubtitle.TLabel"
    cap_st = "ShellHeroCaption.TLabel" if rich else "HeroCaption.TLabel"
    val_st = "ShellHeroValue.TLabel" if rich else "HeroValue.TLabel"
    inner_st = "ShellInner.TFrame" if rich else "TFrame"

    header = ttk.Frame(root, style=hdr_style, padding=hdr_pad)
    header.pack(fill="x", padx=(12, 12) if rich else (0, 0), pady=(10, 0) if rich else (0, 0))

    left = ttk.Frame(header, style=inner_st)
    left.pack(side="left", fill="y")
    ttk.Label(left, text=APP_TITLE, style=title_st).pack(anchor="w")
    ttk.Label(
        left,
        text="在庫・売上を1つのJSONで管理（売上は在庫に自動連動しません）",
        style=sub_st,
    ).pack(anchor="w", pady=(2, 0))

    dash = ttk.Frame(header, style=inner_st)
    dash.pack(side="right", fill="y", padx=(16, 0))

    def dash_cell(parent, caption: str, var: tk.StringVar, row: int, col: int) -> None:
        f = ttk.Frame(parent, style=inner_st)
        f.grid(row=0, column=col, padx=12, pady=2, sticky="ne")
        ttk.Label(f, text=caption, style=cap_st).pack(anchor="e")
        ttk.Label(f, textvariable=var, style=val_st).pack(anchor="e")

    var_items = tk.StringVar(value="—")
    var_cust = tk.StringVar(value="—")
    var_invval = tk.StringVar(value="—")
    var_sales_today = tk.StringVar(value="—")
    var_moves = tk.StringVar(value="—")

    dash_cell(dash, "有効商品数", var_items, 0, 0)
    dash_cell(dash, "有効顧客数", var_cust, 0, 1)
    dash_cell(dash, "在庫評価額", var_invval, 0, 2)
    dash_cell(dash, "本日売上", var_sales_today, 0, 3)
    dash_cell(dash, "本日入出庫件数", var_moves, 0, 4)
    dash.grid_columnconfigure((0, 1, 2, 3, 4), weight=0)

    def update_dashboard() -> None:
        snap = store.dashboard_snapshot()
        var_items.set(str(snap["active_items"]))
        var_cust.set(str(snap["active_customers"]))
        var_invval.set(store.money_str(snap["inventory_value"]))
        var_sales_today.set(store.money_str(snap["sales_today"]))
        var_moves.set(str(snap["moves_today"]))

    sep = ttk.Separator(root, orient="horizontal")
    sep.pack(fill="x", padx=(12, 12) if rich else (0, 0), pady=(0, 4) if rich else (0, 0))

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=(14, 14) if rich else (8, 8), pady=(8, 14) if rich else (8, 8))

    inv = InventoryTabs(notebook, store)
    sales = SalesTabs(notebook, store)

    def refresh_all():
        inv.refresh_all()
        sales.refresh_all()
        update_dashboard()

    settings = SettingsTabs(
        notebook,
        store,
        style=style,
        on_settings_changed=refresh_all,
    )

    notebook.add(inv, text="在庫")
    notebook.add(sales, text="売上")
    notebook.add(settings, text="設定")

    update_dashboard()
    root.mainloop()


if __name__ == "__main__":
    main()
