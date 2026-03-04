import pandas as pd
import glob
import warnings
import os

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

files = glob.glob('/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/*.xlsx')
files.sort()
df_list = []
# ファイル名の店舗部分を日本語に統一するための辞書
shop_name_mapping = {
    "castleokane": "キャッスル大金",
    "playlandcastle takahama": "プレイランドキャッスル高浜"
}

for f in files:
    filename = os.path.basename(f)
    # Filename format: YYYYMM_storename_style.xlsx e.g., 202501_castleokane_20S.xlsx
    parts = filename.split('_')
    raw_store_name = parts[1] if len(parts) >= 2 else "Unknown"
    
    # 英語名であれば日本語名に変換、既に日本語であればそのまま使用
    store_name = shop_name_mapping.get(raw_store_name, raw_store_name)
    
    df = pd.read_excel(f)
    df['店舗'] = store_name
    print(f'Reading {filename} - {len(df)} rows, Shop: {store_name} (from: {raw_store_name})')
    df_list.append(df)

combined_df = pd.concat(df_list, ignore_index=True)

# Also create cleaned_slot_data.csv to match app expectations
out_path = '/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cleaned_slot_data.csv'
combined_df.to_csv(out_path, index=False)

print('-'*20)
print(f'Success! Combined {len(files)} files.')
print(f'Total Rows: {len(combined_df)}')
print(f'Saved to: {out_path}')
