import pandas as pd
import numpy as np

csv_path = "/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cleaned_slot_data.csv"
print("Loading CSV...")
df = pd.read_csv(csv_path, low_memory=False)

df['日付'] = pd.to_datetime(df['日付'])
df['差枚'] = pd.to_numeric(df['差枚'], errors='coerce')
df['G数'] = pd.to_numeric(df['G数'], errors='coerce').fillna(0)
df['Win'] = (df['差枚'] > 0).astype(int)
df['機種名'] = df['機種名'].fillna('不明')

# 異常データの除外（店舗+日付）
BAD_DATA_FILTER = [
    ('プレイランドキャッスル大曽根', '2025-12-26'),
]
for store, date in BAD_DATA_FILTER:
    mask = (df['店舗'] == store) & (df['日付'] == pd.Timestamp(date))
    n = mask.sum()
    if n > 0:
        print(f"[BAD DATA] {store} {date} を除外: {n}行")
    df = df[~mask]

# 異常データの除外（店舗+日付+台番）
BAD_ROW_FILTER = [
    ('メガコンコルド岡崎北', '2026-01-15', '800'),  # 差枚1664万枚の異常値
]
for store, date, daiban in BAD_ROW_FILTER:
    mask = (df['店舗'] == store) & (df['日付'] == pd.Timestamp(date)) & (df['台番'].astype(str) == str(daiban))
    n = mask.sum()
    if n > 0:
        print(f"[BAD ROW] {store} {date} 台番{daiban} を除外: {n}行")
    df = df[~mask]

# 1. 特定機種分析 (Cross Machine Stats)
print("Computing cross_machine_stats...")
machine_stats = df.groupby(['店舗', '機種名']).agg(
    総導入台数=('台番', 'nunique'),
    稼働日数=('日付', 'nunique'),
    平均差枚数=('差枚', 'mean'),
    勝率=('Win', 'mean'),
    集計数=('差枚', 'count')
).reset_index()

machine_stats = machine_stats[machine_stats['集計数'] >= 5]
machine_stats = machine_stats.sort_values(['機種名', '平均差枚数'], ascending=[True, False])
# 集計数は勝率X/Y表示のためCSVに残す
machine_stats.to_csv("/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cross_machine_stats.csv", index=False)


# 2. 新台分析 (Cross New Machine Stats)
# ---- 新台の定義（app.py mode 5 と統一）----
# (1) 各(店舗, 機種名)の初登場日（G数問わず）を取得
# (2) 各店舗のデータ開始日と同日に初登場した機種は既存機種として除外
# (3) 残った新台について、G数>0 の最初の日を「新台初日」とする
# (4) 新台初日の全レコード（G数=0 の台も含む）で差枚・勝率を集計
print("Computing cross_new_machine_stats...")

# (1) 初登場日（G数問わず）
first_appearance = df.groupby(['店舗', '機種名'])['日付'].min().reset_index()
first_appearance.rename(columns={'日付': '初登場日'}, inplace=True)

# (2) 各店舗のデータ開始日を取得 → 開始日と同日初登場の機種は既存機種として除外
store_min_dates = df.groupby('店舗')['日付'].min().reset_index()
store_min_dates.rename(columns={'日付': '店舗最古日'}, inplace=True)

first_appearance = pd.merge(first_appearance, store_min_dates, on='店舗')
new_machines = first_appearance[first_appearance['初登場日'] > first_appearance['店舗最古日']][['店舗', '機種名']]

# (3) 新台のみG数>0の最初の日（新台初日）を特定
active_df = df[df['G数'] > 0][['店舗', '機種名', '日付']]
new_machines_active = pd.merge(new_machines, active_df, on=['店舗', '機種名'])
first_active_days = new_machines_active.groupby(['店舗', '機種名'])['日付'].min().reset_index()
first_active_days.rename(columns={'日付': '導入日'}, inplace=True)

# (4) 新台初日の全レコードを取得（G数=0 の台も含む）
new_machine_df = pd.merge(df, first_active_days,
                          left_on=['店舗', '機種名', '日付'],
                          right_on=['店舗', '機種名', '導入日'])


def compute_store_new_stats(g):
    num_events = g['導入日'].nunique()   # 新台入替イベント数（導入日のユニーク数）
    total_units = len(g)                 # 新台初日の総台数
    avg_samaisu = g['差枚'].mean()
    win_rate = g['Win'].mean()
    count = len(g)
    return pd.Series({
        '新台入替回数': num_events,
        '総導入台数': total_units,
        '平均差枚数': avg_samaisu,
        '勝率': win_rate,
        'Count': count
    })

store_new_stats = new_machine_df.groupby('店舗').apply(compute_store_new_stats, include_groups=False).reset_index()
store_new_stats = store_new_stats[store_new_stats['Count'] >= 5]
store_new_stats = store_new_stats.sort_values('平均差枚数', ascending=False)
store_new_stats.drop('Count', axis=1, inplace=True)
store_new_stats.to_csv("/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cross_new_machine_stats.csv", index=False)

print("Done computing cross_stats. Checking output sizes:")
print(f"machine_stats: {len(machine_stats)} rows")
print(f"store_new_stats: {len(store_new_stats)} rows")
