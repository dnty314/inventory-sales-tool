# app.py
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from store import StoreJSON
from ui.inventory_tabs import InventoryTabs
from ui.sales_tabs import SalesTabs
from ui.settings_tabs import SettingsTabs

APP_TITLE = "在庫・売上管理ツール"

def get_data_file_path(filename: str = "sales_inventory_tool.json") -> str:
    """
    保存先を決定する。
    - exe化（PyInstaller）: exe と同じフォルダ
    - 通常実行: app.py と同じフォルダ
    """
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent
    return str(base_dir / filename)

DATA_FILE = get_data_file_path()



def apply_theme(style: ttk.Style, theme_name: str) -> None:
    names = style.theme_names()
    if theme_name and theme_name in names:
        style.theme_use(theme_name)


def main():
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("1200x800")

    try:
        store = StoreJSON(DATA_FILE)
    except Exception as e:
        messagebox.showerror("起動エラー", f"データファイルの読み込みに失敗しました。\n\n{e}")
        return

    style = ttk.Style(root)
    apply_theme(style, store.get_setting("theme", ""))

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    inv = InventoryTabs(notebook, store)
    sales = SalesTabs(notebook, store)

    def refresh_all():
        inv.refresh_all()
        sales.refresh_all()

    settings = SettingsTabs(
        notebook,
        store,
        style=style,
        on_settings_changed=refresh_all,
    )

    notebook.add(inv, text="在庫")
    notebook.add(sales, text="売上")
    notebook.add(settings, text="設定")

    root.mainloop()


if __name__ == "__main__":
    main()
