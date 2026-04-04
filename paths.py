# paths.py — データファイルの保存場所（デスクトップ版・Web版で共通）
from __future__ import annotations

import sys
from pathlib import Path


def get_data_file_path(filename: str = "sales_inventory_tool.json") -> str:
    """
    - PyInstaller exe: exe と同じフォルダ
    - 通常: このパッケージのルート（app.py があるディレクトリ）
    """
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent
    return str(base_dir / filename)
