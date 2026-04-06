import pandas as pd
import os
import numpy as np
from supabase import create_client

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
    ('メガコンコルド岡崎北',        '2026-01-15', '800'),  # 差枚+1664万枚の異常値
    ('キング観光サウザンド今池2号',  '2025-08-13', '815'),  # 差枚-418万枚の異常値
]
for store, date, daiban in BAD_ROW_FILTER:
    mask = (df['店舗'] == store) & (df['日付'] == pd.Timestamp(date)) & (df['台番'].astype(str) == str(daiban))
    n = mask.sum()
    if n > 0:
        print(f"[BAD ROW] {store} {date} 台番{daiban} を除外: {n}行")
    df = df[~mask]

# ===== Supabaseからスロレポデータを取得 =====
SUPABASE_URL = "https://ymqubftkyssluyqiqoci.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InltcXViZnRreXNzbHV5cWlxb2NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2NTQyMDcsImV4cCI6MjA4ODIzMDIwN30.g_t67t1bzw0sKrvL7pN1xYtRo-Z8ApVcObrsKA5ZHz4"
PPRO_STORES = set(df['店舗'].unique())

print("Fetching スロレポ data from Supabase...")
_sb = create_client(SUPABASE_URL, SUPABASE_KEY)
_all_slorepo = []
_limit = 1000
_fetch_start = pd.Timestamp("2025-11-15")
_fetch_end = max(df['日付'].max().normalize(), pd.Timestamp.today().normalize())
_fallback_store_candidates = set(PPRO_STORES)
_legacy_slorepo_path = "/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/slot_data_normalized.csv"
if os.path.exists(_legacy_slorepo_path):
    try:
        _fallback_store_candidates.update(
            pd.read_csv(_legacy_slorepo_path, usecols=['店舗'], low_memory=False)['店舗'].dropna().unique()
        )
    except Exception as e:
        print(f"Fallback store list load error: {e}")
_day = _fetch_start
while _day <= _fetch_end:
    _next_day = _day + pd.Timedelta(days=1)
    _offset = 0
    _day_rows = []
    _day_failed = False
    while True:
        try:
            _r = (_sb.table('slot_data')
                  .select('店舗,日付,機種名,G数,差枚,台数,勝ち台数')
                  .eq('台番', 'スロレポ')
                  .gte('日付', _day.strftime('%Y-%m-%d'))
                  .lt('日付', _next_day.strftime('%Y-%m-%d'))
                  .range(_offset, _offset + _limit - 1)
                  .execute())
            _chunk = _r.data
            if not _chunk:
                break
            _day_rows.extend(_chunk)
            if len(_chunk) < _limit:
                break
            _offset += _limit
        except Exception as e:
            print(f"Supabase fetch error on {_day.strftime('%Y-%m-%d')} offset {_offset}: {e}")
            _day_failed = True
            break

    if _day_failed:
        _day_rows = []
        _stores_for_day = sorted(_fallback_store_candidates)
        print(f"  fallback store-sliced fetch for {_day.strftime('%Y-%m-%d')} ({len(_stores_for_day)} stores)")
        for _store in _stores_for_day:
            _store_offset = 0
            while True:
                try:
                    _r = (_sb.table('slot_data')
                          .select('店舗,日付,機種名,G数,差枚,台数,勝ち台数')
                          .eq('台番', 'スロレポ')
                          .eq('店舗', _store)
                          .gte('日付', _day.strftime('%Y-%m-%d'))
                          .lt('日付', _next_day.strftime('%Y-%m-%d'))
                          .range(_store_offset, _store_offset + _limit - 1)
                          .execute())
                    _chunk = _r.data
                    if not _chunk:
                        break
                    _day_rows.extend(_chunk)
                    if len(_chunk) < _limit:
                        break
                    _store_offset += _limit
                except Exception as e:
                    print(f"  store-sliced fetch error on {_day.strftime('%Y-%m-%d')} store {_store} offset {_store_offset}: {e}")
                    break

    if _day_rows:
        _all_slorepo.extend(_day_rows)
        _fallback_store_candidates.update(
            row.get('店舗') for row in _day_rows if row.get('店舗')
        )

    if len(_all_slorepo) > 0 and len(_all_slorepo) % 10000 < _limit:
        print(f"  fetched {len(_all_slorepo)} rows...")
    _day = _next_day

slorepo_df_raw = None
if _all_slorepo:
    slorepo_df_raw = pd.DataFrame(_all_slorepo)
    slorepo_df_raw['日付'] = pd.to_datetime(slorepo_df_raw['日付'])
    # Pproデータが存在する店舗は除外（二重集計防止）
    slorepo_df_raw = slorepo_df_raw[~slorepo_df_raw['店舗'].isin(PPRO_STORES)]
    # 機種名不明を除外
    slorepo_df_raw = slorepo_df_raw[
        slorepo_df_raw['機種名'].notna() &
        (slorepo_df_raw['機種名'] != '不明') &
        (slorepo_df_raw['機種名'].str.strip() != '')
    ]
    # 数値型変換
    # 台数 = 勝率の分母（例: 勝率1/3 → 台数=3）= 総導入台数
    slorepo_df_raw['台数'] = pd.to_numeric(slorepo_df_raw['台数'], errors='coerce').fillna(1)
    slorepo_df_raw['勝ち台数'] = pd.to_numeric(slorepo_df_raw['勝ち台数'], errors='coerce').fillna(0)
    # 差枚・G数はSupabaseでは「平均値」として格納されている
    slorepo_df_raw['差枚'] = pd.to_numeric(slorepo_df_raw['差枚'], errors='coerce')
    slorepo_df_raw['G数'] = pd.to_numeric(slorepo_df_raw['G数'], errors='coerce').fillna(0)
    # カラム名を内部処理用に統一（平均値であることを明示）
    slorepo_df_raw = slorepo_df_raw.rename(columns={'差枚': '平均差枚', 'G数': '平均G数'})
    print(f"スロレポデータ取得完了: {len(slorepo_df_raw)} 行, {slorepo_df_raw['店舗'].nunique()} 店舗 (Ppro除外後)")

# 1. 特定機種分析 (Cross Machine Stats)
print("Computing cross_machine_stats...")
machine_stats = df.groupby(['店舗', '機種名']).agg(
    総導入台数=('台番', 'nunique'),
    稼働日数=('日付', 'nunique'),
    平均差枚数=('差枚', 'mean'),
    平均回転数=('G数', 'mean'),
    勝率=('Win', 'mean'),
    集計数=('差枚', 'count')
).reset_index()

machine_stats = machine_stats[machine_stats['集計数'] >= 5]
machine_stats = machine_stats.sort_values(['機種名', '平均差枚数'], ascending=[True, False])
# 集計数は勝率X/Y表示のためCSVに残す
machine_stats.to_csv("/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cross_machine_stats.csv", index=False)

# 1b. 末尾別統計 (Cross Machine Digit Stats)
print("Computing cross_machine_digit_stats...")
df['End_Digit'] = df['日付'].dt.day % 10
digit_stats = df.groupby(['店舗', '機種名', 'End_Digit']).agg(
    稼働日数=('日付', 'nunique'),
    集計数=('差枚', 'count'),
    平均差枚数=('差枚', 'mean'),
    平均回転数=('G数', 'mean'),
    勝率=('Win', 'mean')
).reset_index()
digit_stats = digit_stats[digit_stats['集計数'] >= 3]
digit_stats.to_csv("/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cross_machine_digit_stats.csv", index=False)

# 1c. 日付別統計 (Cross Machine Day Stats)
print("Computing cross_machine_day_stats...")
df['Day'] = df['日付'].dt.day
day_stats = df.groupby(['店舗', '機種名', 'Day']).agg(
    稼働日数=('日付', 'nunique'),
    集計数=('差枚', 'count'),
    平均差枚数=('差枚', 'mean'),
    平均回転数=('G数', 'mean'),
    勝率=('Win', 'mean')
).reset_index()
day_stats = day_stats[day_stats['集計数'] >= 3]
day_stats.to_csv("/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cross_machine_day_stats.csv", index=False)

# 1d. 曜日別統計 (Cross Machine Weekday Stats)
print("Computing cross_machine_weekday_stats...")
_wday_map = {0: '月曜日', 1: '火曜日', 2: '水曜日', 3: '木曜日', 4: '金曜日', 5: '土曜日', 6: '日曜日'}
df['Weekday'] = df['日付'].dt.weekday.map(_wday_map)
weekday_stats = df.groupby(['店舗', '機種名', 'Weekday']).agg(
    稼働日数=('日付', 'nunique'),
    集計数=('差枚', 'count'),
    平均差枚数=('差枚', 'mean'),
    平均回転数=('G数', 'mean'),
    勝率=('Win', 'mean')
).reset_index()
weekday_stats = weekday_stats[weekday_stats['集計数'] >= 3]
weekday_stats.to_csv("/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cross_machine_weekday_stats.csv", index=False)


# 2. 新台分析 (Cross New Machine Stats)
# ---- 新台の定義 ----
# (1) 各(店舗, 機種名)の初登場日（G数問わず）を取得
# (2) 各店舗のデータ開始日と同日に初登場した機種は既存機種として除外
# (3) 残った新台について、G数>0 の最初の日を「新台初日（導入日）」とする
# (4) 新台初日の全レコード（G数=0 の台も含む）で差枚・勝率を集計
# ---- スロレポデータ対応 ----
# Pproにない店舗のスロレポデータも上記と同じ条件で新台判定し、マージして集計する
print("Computing cross_new_machine_stats...")

# ===== Ppro新台集計 =====
first_appearance = df.groupby(['店舗', '機種名'])['日付'].min().reset_index()
first_appearance.rename(columns={'日付': '初登場日'}, inplace=True)

store_min_dates = df.groupby('店舗')['日付'].min().reset_index()
store_min_dates.rename(columns={'日付': '店舗最古日'}, inplace=True)

first_appearance = pd.merge(first_appearance, store_min_dates, on='店舗')
new_machines = first_appearance[first_appearance['初登場日'] > first_appearance['店舗最古日']][['店舗', '機種名']]

active_df = df[df['G数'] > 0][['店舗', '機種名', '日付']]
new_machines_active = pd.merge(new_machines, active_df, on=['店舗', '機種名'])
first_active_days = new_machines_active.groupby(['店舗', '機種名'])['日付'].min().reset_index()
first_active_days.rename(columns={'日付': '導入日'}, inplace=True)

new_machine_df = pd.merge(df, first_active_days,
                          left_on=['店舗', '機種名', '日付'],
                          right_on=['店舗', '機種名', '導入日'])

# Ppro: 1行=1台番 → _台数=1, _差枚=差枚, _勝ち台数=Win
new_machine_df['_台数'] = 1
new_machine_df['_差枚'] = new_machine_df['差枚']
new_machine_df['_勝ち台数'] = new_machine_df['Win']

# ===== スロレポ新台集計 =====
slorepo_new_machine_df = None
if slorepo_df_raw is not None and len(slorepo_df_raw) > 0:
    sr = slorepo_df_raw.copy()

    sr_first = sr.groupby(['店舗', '機種名'])['日付'].min().reset_index()
    sr_first.rename(columns={'日付': '初登場日'}, inplace=True)

    sr_store_min = sr.groupby('店舗')['日付'].min().reset_index()
    sr_store_min.rename(columns={'日付': '店舗最古日'}, inplace=True)

    sr_first = pd.merge(sr_first, sr_store_min, on='店舗')
    sr_new_machines = sr_first[sr_first['初登場日'] > sr_first['店舗最古日']][['店舗', '機種名']]

    sr_active = sr[sr['平均G数'] > 0][['店舗', '機種名', '日付']]
    sr_new_active = pd.merge(sr_new_machines, sr_active, on=['店舗', '機種名'])
    sr_first_active = sr_new_active.groupby(['店舗', '機種名'])['日付'].min().reset_index()
    sr_first_active.rename(columns={'日付': '導入日'}, inplace=True)

    slorepo_new_machine_df = pd.merge(sr, sr_first_active,
                                      left_on=['店舗', '機種名', '日付'],
                                      right_on=['店舗', '機種名', '導入日'])

    # スロレポ: 台数=勝率の分母（総導入台数）、差枚=平均差枚、勝ち台数=勝ち台数
    # 平均差枚の加重計算: Σ(平均差枚×台数) / Σ台数
    slorepo_new_machine_df['_台数'] = slorepo_new_machine_df['台数']
    slorepo_new_machine_df['_差枚'] = slorepo_new_machine_df['平均差枚']
    slorepo_new_machine_df['_勝ち台数'] = slorepo_new_machine_df['勝ち台数']
    slorepo_new_machine_df['G数'] = slorepo_new_machine_df['平均G数']
    # Win列: 台数加重の勝率（後のcompute_store_new_statsでは _勝ち台数/_台数 で計算するため不要だが念のため）
    slorepo_new_machine_df['Win'] = slorepo_new_machine_df['勝ち台数'] / slorepo_new_machine_df['台数'].clip(lower=1)
    print(f"スロレポ新台レコード: {len(slorepo_new_machine_df)} 行")

# ===== Ppro + スロレポの統合集計 =====
common_cols = ['店舗', '機種名', '導入日', '_台数', '_差枚', '_勝ち台数', 'Win', 'G数']
ppro_for_agg = new_machine_df[[c for c in common_cols if c in new_machine_df.columns]].copy()

if slorepo_new_machine_df is not None and len(slorepo_new_machine_df) > 0:
    sr_for_agg = slorepo_new_machine_df[[c for c in common_cols if c in slorepo_new_machine_df.columns]].copy()
    combined_new_df = pd.concat([ppro_for_agg, sr_for_agg], ignore_index=True)
else:
    combined_new_df = ppro_for_agg


def compute_store_new_stats(g):
    """
    新台初日データを集計する関数。
    差枚・G数・勝率はすべて台数加重平均で算出する。

    スロレポ: 1行 = (店舗, 機種名, 日付) の集計済みデータ
      - _台数 = 台数（勝率の分母 = 総導入台数）
      - _差枚 = 平均差枚（1台あたり）
      - _勝ち台数 = 勝ち台数
    Ppro: 1行 = 1台番
      - _台数 = 1
      - _差枚 = 差枚（その台の差枚）
      - _勝ち台数 = Win（0 or 1）

    複数新台入替日の平均差枚 = Σ(平均差枚×台数) / Σ台数
    例: A(5台×500枚)＋B(10台×1000枚) → 12500÷15 = 833枚
    """
    num_events = g['導入日'].nunique()        # 新台入替イベント数（導入日のユニーク数）
    total_units = g['_台数'].sum()            # 総導入台数（台数加重合計）

    if total_units <= 0:
        return pd.Series({
            '新台入替回数': num_events,
            '総導入台数': 0,
            '平均差枚数': 0.0,
            '平均回転数': 0.0,
            '勝率': 0.0,
            'Count': 0
        })

    # 台数加重平均差枚: Σ(差枚×台数) / Σ台数
    avg_samaisu = (g['_差枚'] * g['_台数']).sum() / total_units

    # 台数加重平均G数
    avg_g = (g['G数'] * g['_台数']).sum() / total_units

    # 台数加重勝率: Σ勝ち台数 / Σ台数
    win_rate = g['_勝ち台数'].sum() / total_units

    return pd.Series({
        '新台入替回数': num_events,
        '総導入台数': int(round(total_units)),
        '平均差枚数': avg_samaisu,
        '平均回転数': avg_g,
        '勝率': win_rate,
        'Count': total_units
    })


store_new_stats = combined_new_df.groupby('店舗').apply(compute_store_new_stats, include_groups=False).reset_index()
store_new_stats = store_new_stats[store_new_stats['Count'] >= 5]
store_new_stats = store_new_stats.sort_values('平均差枚数', ascending=False)
store_new_stats.drop('Count', axis=1, inplace=True)
store_new_stats.to_csv("/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/cross_new_machine_stats.csv", index=False)

print("Done computing cross_stats. Checking output sizes:")
print(f"machine_stats: {len(machine_stats)} rows")
print(f"store_new_stats: {len(store_new_stats)} rows")
