# utils.py
from __future__ import annotations

import os
import json
import uuid
import shutil
from datetime import datetime, date
from typing import Any, Dict, Optional


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_date_yyyy_mm_dd(s: str) -> date:
    # "2026-01-11"
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def safe_int(s: str, default: int = 0) -> int:
    try:
        return int(str(s).strip())
    except Exception:
        return default


def safe_float(s: str, default: float = 0.0) -> float:
    try:
        return float(str(s).strip())
    except Exception:
        return default


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_json_or_default(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def auto_foreground_for_bg(hex_color: str) -> str:
    # hex "#RRGGBB"
    c = hex_color.lstrip("#")
    if len(c) != 6:
        return "black"
    r = int(c[0:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)
    y = (r * 299 + g * 587 + b * 114) / 1000
    return "black" if y > 140 else "white"


def format_money(value: float, *, mode: str = "int", decimals: int = 2) -> str:
    """
    mode:
      - "int": 整数表示（四捨五入）
      - "float": 小数表示（decimals桁）
    すべての金額表示はカンマ区切りにする。
    """
    if mode == "float":
        try:
            return f"{float(value):,.{int(decimals)}f}"
        except Exception:
            return str(value)

    # int
    try:
        return f"{int(round(float(value))):,}"
    except Exception:
        return str(value)



def make_backup(src_path: str, backup_dir: Optional[str] = None) -> str:
    """
    JSON等のバックアップを同一ディレクトリ（または指定dir）に作成して、作成先パスを返す。
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError("バックアップ対象ファイルが存在しません")

    base_dir = backup_dir or os.path.dirname(src_path) or "."
    os.makedirs(base_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.basename(src_path)
    dst = os.path.join(base_dir, f"{base}.backup_{ts}")
    shutil.copy2(src_path, dst)
    return dst
