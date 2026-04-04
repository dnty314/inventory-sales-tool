# TECHNICAL.md

## 1. 概要

本リポジトリは、Python による **在庫管理・売上管理**ツールである。

* **デスクトップ版**: Tkinter GUI（`app.py`）
* **ブラウザ版**: FastAPI + 静的 UI（`web/`、`python -m web`）
* DB は使用せず、**JSON ファイル**で永続化（`paths.get_data_file_path()` でパス統一）
* 個人利用・小規模業務を想定
* Windows / macOS / Linux で動作（Python 3.10 以上）

Windows 向けに **`setup.bat`（仮想環境・依存関係）** と **`run.bat`（起動メニュー）** の 2 本だけを同梱（利用手順は `README.md`）。

本ドキュメントは **技術者・開発者向け**に、設計方針・構成・拡張方法を説明する。

### Windows: 配布用 .exe のビルド（任意）

`README.md` の手順 A 向け。リポジトリ直下で **`setup.bat`** を済ませたあと、同じフォルダでコマンドプロンプトを開き:

```bat
.venv\Scripts\activate.bat
python -m pip install -U pyinstaller
pyinstaller --noconfirm --clean --name inventory-sales-tool --noconsole --onefile app.py
```

生成物は `dist\inventory-sales-tool.exe`。配布用に `_dist\inventory-sales-tool\` のようなフォルダへコピーし、**`sales_inventory_tool.json`** を同じフォルダに置く（無ければ空の `{}` でよい）と、`paths.py` の exe 実行時のデータパスと整合します。デスクトップ用 `.lnk` は手作りするか、`create_shortcut.ps1` 等で作成してください。

---

## 2. 全体構成

```
inventory-sales-tool/
├─ app.py                     # デスクトップ版エントリ
├─ paths.py                   # データ JSON パス（exe / 通常実行）
├─ store.py                   # データ管理・永続化（JSON）
├─ models.py
├─ utils.py
├─ requirements.txt
├─ setup.bat                  # Windows: venv + pip（初回）
├─ run.bat                    # Windows: 起動メニュー（デスクトップ / Web / ショートカット）
├─ sales_inventory_tool.json  # 実行時データ（※Git管理外）
├─ web/                       # ブラウザ版（FastAPI）
│  ├─ server.py
│  ├─ deps.py
│  ├─ __main__.py
│  └─ static/index.html
└─ ui/                        # Tkinter UI
   ├─ inventory_tabs.py
   ├─ sales_tabs.py
   ├─ settings_tabs.py
   ├─ theme.py
   ├─ scrollframe.py
   └─ common.py
```

設計上の原則:

* **UI / ロジック / 永続化の分離**
* Tkinter によるシンプルで追跡しやすい実装
* JSON を人手で編集可能な構造に保つ

---

## 3. データ設計（JSON）

### 3.1 ルート構造

```json
{
  "items": {},
  "customers": {},
  "inventory_history": [],
  "sales": [],
  "category_colors": {},
  "settings": {}
}
```

### 3.2 商品マスタ（items）

```json
"SKU001": {
  "name": "商品A",
  "unit_price": 1200,
  "category": "食品",
  "stock": 10,
  "disabled": false
}
```

* **削除は禁止**（論理削除 `disabled` のみ）
* 履歴との参照整合性を最優先

---

### 3.3 在庫履歴（inventory_history）

```json
{
  "id": "IH_xxxxx",
  "ts": "2026-01-11 10:32:01",
  "action": "IN",
  "sku": "SKU001",
  "qty": 5,
  "stock_after": 15,
  "deleted": false
}
```

* **追記型ログ**
* 誤操作時は削除 or 復元が可能

---

### 3.4 売上履歴（sales）

```json
{
  "id": "S_xxxxx",
  "ts": "2026-01-11 11:00:00",
  "cid": "C001",
  "sku": "SKU001",
  "qty": 2,
  "unit_price": 1200,
  "line_total": 2400,
  "deleted": false
}
```

* 在庫とは **非連動**
* 顧客別・期間別集計に使用

---

## 4. UI 設計

### 4.1 タブ構成

* 在庫

  * 商品マスタ
  * 単発入出庫
  * 一括入出庫
  * 在庫履歴（一覧）
  * 在庫履歴（グラフ）

* 売上

  * 顧客リスト
  * 売上入力
  * 売上履歴
  * 売上集計

* 設定

  * テーマ選択
  * 金額表示形式
  * フォント
  * データファイル情報

---

## 5. 削除ポリシー（重要）

| 対象   | 方法          | 理由     |
| ---- | ----------- | ------ |
| 商品   | 論理削除のみ      | 履歴参照保持 |
| 顧客   | 論理削除のみ      | 売上整合性  |
| 在庫履歴 | 論理削除 + 完全削除 | 誤入力対策  |
| 売上履歴 | 論理削除 + 完全削除 | 修正対応   |

完全削除は **DELETE 入力必須**。

---

## 6. 設定（settings）

```json
"settings": {
  "theme": "default",
  "price_format": "int",   // int | float
  "decimal_places": 2
}
```

* UI 起動時に反映
* すべて JSON に保存

---

## 7. グラフ表示

* matplotlib + TkAgg
* 横軸: 時間
* 縦軸: 在庫数
* SKU 単位で描画
* カテゴリ色を反映

注意:

* Treeview はセル単位着色不可 → 行単位色付け

---

## 8. フォントと多言語

* 日本語表示は OS 依存
* Windows: Yu Gothic / Meiryo
* macOS: Hiragino

matplotlib 側は rcParams で制御

---

## 9. 拡張ポイント

* SQLite / DuckDB への移行
* CSV import / export
* ロール（管理者 / 入力者）
* ネットワーク同期
* exe / dmg 配布

---

## 10. 開発ルール

* UI は ttk を優先
* store.py は UI から直接 JSON を触らせない
* 破壊的操作は必ず確認ダイアログ

---

## 11. 注意事項

* `sales_inventory_tool.json` は **Git 管理外**
* 実運用前に必ずバックアップを取ること

---

## 12. ライセンス

MIT License（予定）

---

このドキュメントは、将来的な引き継ぎ・改修を想定して記載している。
