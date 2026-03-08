import pandas as pd
import warnings
import os
from pathlib import Path

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# 対象となる拡張子
extensions = ['.xlsx', '.xls']
base_dir = Path('/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata')
files = []

# ディレクトリ以下の全ファイルから拡張子が一致するものを抽出（再帰的検索）
for ext in extensions:
    files.extend([str(p) for p in base_dir.rglob(f"*{ext}") if not p.name.startswith("~$")])

files.sort()
df_list = []
import unicodedata

# ファイル名の店舗部分を日本語に統一するための辞書
# 表記ゆれ（半角・全角の違い、スペースの有無など）を吸収
shop_name_mapping = {
    "castleokane": "キャッスル大金",
    "playlandcastle takahama": "プレイランドキャッスル高浜",
    "プレイランドキャッスル高浜": "プレイランドキャッスル高浜"
}

for f in files:
    filename = os.path.basename(f)
    # Filename format: YYYYMM_storename_style.xlsx e.g., 202501_castleokane_20S.xlsx
    parts = filename.split('_')
    raw_store_name = parts[1] if len(parts) >= 2 else "Unknown"
    
    # Unicode正規化（全角英数字を半角に、濁点を結合）して小文字化、前後の空白削除
    normalized_name = unicodedata.normalize('NFKC', raw_store_name).strip().lower()
    
    # 辞書に一致すれば日本語に、一致しなければNFKC正規化後の名前を使用（decomposed Unicodeを防ぐ）
    nfkc_store_name = unicodedata.normalize('NFKC', raw_store_name).strip()
    store_name = shop_name_mapping.get(normalized_name, nfkc_store_name)
    
    # さらに、もし「プレイランドキャッスル高浜」が含まれていたら強制統一
    if "プレイランドキャッスル高浜" in normalized_name or "playland" in normalized_name:
        store_name = "プレイランドキャッスル高浜"
    elif "大金" in normalized_name or "okane" in normalized_name:
         store_name = "キャッスル大金"
    
    df = pd.read_excel(f)
    df['店舗'] = store_name
    
    if '日付' not in df.columns:
        date_str = parts[0] # 例: '20260303'
        try:
            # 8桁の数字（YYYYMMDD）を日付型に変換して全行にセット
            df['日付'] = pd.to_datetime(date_str, format='%Y%m%d')
        except Exception as e:
            print(f"  [Warn] Failed to parse date from filename '{date_str}': {e}")
            
    # 機種名のカラム名揺れを吸収する
    possible_machine_cols = ['機種名（正式名）', '機種名（データサイト 表記）', '機種', '台名称']
    if '機種名' not in df.columns:
        for col in possible_machine_cols:
            if col in df.columns:
                df.rename(columns={col: '機種名'}, inplace=True)
                break
                
    print(f'Reading {filename} - {len(df)} rows, Shop: {store_name} (from: {raw_store_name})')
    df_list.append(df)

combined_df = pd.concat(df_list, ignore_index=True)

# 異常データの除外（バグのある日付・店舗の組み合わせ）
BAD_DATA_FILTER = [
    ('プレイランドキャッスル大曽根', '2025-12-26'),
]
combined_df['日付'] = pd.to_datetime(combined_df['日付'])
for store, date in BAD_DATA_FILTER:
    mask = (combined_df['店舗'] == store) & (combined_df['日付'] == pd.Timestamp(date))
    n = mask.sum()
    if n > 0:
        print(f"[BAD DATA] {store} {date} を除外: {n}行")
    combined_df = combined_df[~mask]

BAD_ROW_FILTER = [
    ('メガコンコルド岡崎北',        '2026-01-15', '800'),  # 差枚+1664万枚の異常値
    ('キング観光サウザンド今池2号',  '2025-08-13', '815'),  # 差枚-418万枚の異常値
]
for store, date, daiban in BAD_ROW_FILTER:
    mask = (combined_df['店舗'] == store) & (combined_df['日付'] == pd.Timestamp(date)) & (combined_df['台番'].astype(str) == str(daiban))
    n = mask.sum()
    if n > 0:
        print(f"[BAD ROW] {store} {date} 台番{daiban} を除外: {n}行")
    combined_df = combined_df[~mask]

# 重複排除: 店舗、日付、台番が完全に一致するデータが複数ある場合は、古いものを消して1つにする
before_dedup = len(combined_df)
# '日付'列がdatetime型でない場合は変換（念のため）
combined_df['日付'] = pd.to_datetime(combined_df['日付'])
combined_df.drop_duplicates(subset=['店舗', '日付', '台番'], keep='last', inplace=True)
after_dedup = len(combined_df)
dedup_count = before_dedup - after_dedup
if dedup_count > 0:
    print(f"Removed {dedup_count} duplicate rows from overlapping files.")

# Also create cleaned_slot_data.csv to match app expectations
out_path = '/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cleaned_slot_data.csv'
combined_df.to_csv(out_path, index=False)

print('-'*20)
print(f'Success! Combined {len(files)} files.')
print(f'Total Rows: {len(combined_df)}')
print(f'Saved to: {out_path}')
