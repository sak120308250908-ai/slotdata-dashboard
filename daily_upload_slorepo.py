"""
毎日0時の自動実行向けスロレポアップロードスクリプト。

slot_data_normalized.csv から、Ppro既存店舗を除外したスロレポ集計行を
Supabase の slot_data テーブルへ登録する。
"""

import json
import math
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "slot_data_normalized.csv"
EXISTING_STORES_FILE = BASE_DIR / "existing_stores.txt"
STORE_MAPPING_FILE = BASE_DIR / "store_mapping.json"
MACHINE_MAPPING_FILE = BASE_DIR / "machine_mapping.json"

SUPABASE_URL = "https://ymqubftkyssluyqiqoci.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InltcXViZnRreXNzbHV5cWlxb2NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2NTQyMDcsImV4cCI6MjA4ODIzMDIwN30"
    ".g_t67t1bzw0sKrvL7pN1xYtRo-Z8ApVcObrsKA5ZHz4"
)
TABLE_NAME = "slot_data"
CHUNK_SIZE = 500
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFKC", str(name)).replace(" ", "").replace("\u3000", "")


def load_lines(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return data


def clean_value(value):
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def is_ppro_store(store_name: str, existing_stores: list[str], store_mapping: dict[str, str]) -> bool:
    mapped_name = store_mapping.get(store_name, store_name)
    normalized_name = normalize_name(mapped_name)
    return any(normalize_name(existing) == normalized_name for existing in existing_stores)


def delete_existing_slorepo_rows(dates: list[str]) -> None:
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"

    for date in dates:
        response = requests.delete(
            endpoint,
            headers=HEADERS,
            params={"台番": "eq.スロレポ", "日付": f"eq.{date}"},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code not in (200, 204):
            raise RuntimeError(
                f"Supabase delete failed for 日付={date}: "
                f"HTTP {response.status_code} {response.text[:200]}"
            )
        print(f"既存削除: {date}")


def build_rows(df: pd.DataFrame, machine_mapping: dict[str, str]) -> list[dict]:
    rows: list[dict] = []

    for _, row in df.iterrows():
        machine_name = clean_value(row.get("機種名"))
        if machine_name is not None:
            machine_name = machine_mapping.get(machine_name, machine_name)

        rows.append(
            {
                "店舗": row["店舗"],
                "日付": str(row["日付"]),
                "機種名": machine_name,
                "台番": "スロレポ",
                "G数": clean_value(row.get("平均G数")),
                "差枚": clean_value(row.get("平均差枚")),
                "台数": clean_value(row.get("台数")),
                "勝ち台数": clean_value(row.get("勝ち台数")),
                "BB": None,
                "RB": None,
                "ART": None,
                "合成確率": None,
            }
        )

    return rows


def upload_rows(rows: list[dict]) -> None:
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    total = len(rows)

    for start in range(0, total, CHUNK_SIZE):
        chunk = rows[start : start + CHUNK_SIZE]
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(
                    endpoint,
                    headers=HEADERS,
                    json=chunk,
                    timeout=REQUEST_TIMEOUT,
                )
                if response.status_code in (200, 201, 204):
                    break
                if attempt == MAX_RETRIES:
                    raise RuntimeError(
                        f"Supabase insert failed: HTTP {response.status_code} {response.text[:200]}"
                    )
                last_error = f"HTTP {response.status_code} {response.text[:200]}"
            except requests.RequestException as exc:
                last_error = str(exc)
                if attempt == MAX_RETRIES:
                    raise RuntimeError(f"Supabase insert request failed: {exc}") from exc

            if attempt < MAX_RETRIES:
                time.sleep(2)
        else:
            raise RuntimeError(f"Supabase insert failed after retries: {last_error}")

        done = min(start + CHUNK_SIZE, total)
        print(f"アップロード進捗: {done:,}/{total:,}")


def main() -> None:
    for required_path in (INPUT_CSV, EXISTING_STORES_FILE, STORE_MAPPING_FILE, MACHINE_MAPPING_FILE):
        if not required_path.exists():
            print(f"エラー: {required_path} が見つかりません。")
            sys.exit(1)

    df = pd.read_csv(INPUT_CSV, encoding="utf-8")
    existing_stores = load_lines(EXISTING_STORES_FILE)
    store_mapping = load_json(STORE_MAPPING_FILE)
    machine_mapping = load_json(MACHINE_MAPPING_FILE)

    df = df.copy()
    df = df[~df["店舗"].apply(lambda store: is_ppro_store(store, existing_stores, store_mapping))]

    if df.empty:
        print("アップロード対象データがありません。")
        return

    df["店舗"] = df["店舗"].apply(lambda store: store_mapping.get(store, store))

    upload_dates = sorted(df["日付"].astype(str).unique().tolist())
    print(f"対象件数: {len(df):,}行")
    print(f"対象店舗数: {df['店舗'].nunique():,}")
    print(f"対象日付: {', '.join(upload_dates)}")

    delete_existing_slorepo_rows(upload_dates)

    rows = build_rows(df, machine_mapping)
    if not rows:
        print("アップロード対象レコードがありません。")
        return

    upload_rows(rows)
    print(f"完了: {len(rows):,}件をアップロードしました。")


if __name__ == "__main__":
    main()
