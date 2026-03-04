import pandas as pd

def analyze_dates():
    file_path = '/Users/satoushunsuke/Desktop/antigravityseisaku/slotdata/combined_slot_data.csv'
    print(f"Loading data from {file_path}...")
    df = pd.read_csv(file_path, low_memory=False)
    
    # Handle machine naems
    if '機種名（正式名）' in df.columns and '機種名' in df.columns:
        df['機種名'] = df['機種名（正式名）'].fillna(df['機種名'])
    elif '機種名（正式名）' in df.columns:
        df['機種名'] = df['機種名（正式名）']
        
    df['日付'] = pd.to_datetime(df['日付'])
    df['Month'] = df['日付'].dt.month
    df['Day'] = df['日付'].dt.day
    df['Weekday'] = df['日付'].dt.day_name()
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['Weekday'] = pd.Categorical(df['Weekday'], categories=weekdays, ordered=True)
    df['Win'] = (df['差枚'] > 0).astype(int)

    print("\n==============================================")
    print("1. 日付（1日〜31日）ごとの全体傾向 (トップ10)")
    print("==============================================")
    day_stats = df.groupby('Day').agg(
        Total_Play=('差枚', 'count'),
        Avg_Samaisu=('差枚', 'mean'),
        Total_Samaisu=('差枚', 'sum'),
        Win_Rate=('Win', 'mean')
    ).round(2)
    print(day_stats.sort_values('Avg_Samaisu', ascending=False).head(10).to_string())

    print("\n==============================================")
    print("2. 曜日ごとの全体傾向")
    print("==============================================")
    weekday_stats = df.groupby('Weekday').agg(
        Total_Play=('差枚', 'count'),
        Avg_Samaisu=('差枚', 'mean'),
        Total_Samaisu=('差枚', 'sum'),
        Win_Rate=('Win', 'mean')
    ).round(2)
    print(weekday_stats.to_string())

    print("\n==============================================")
    print("3. 日付の末尾（0〜9）ごとの傾向")
    print("==============================================")
    df['End_Digit'] = df['Day'] % 10
    end_digit_stats = df.groupby('End_Digit').agg(
        Total_Play=('差枚', 'count'),
        Avg_Samaisu=('差枚', 'mean'),
        Total_Samaisu=('差枚', 'sum'),
        Win_Rate=('Win', 'mean')
    ).round(2)
    print(end_digit_stats.sort_values('Avg_Samaisu', ascending=False).to_string())

    print("\n==============================================")
    print("4. 最も強い特定日（平均差枚トップ）における優良機種")
    print("==============================================")
    top_day = day_stats.sort_values('Avg_Samaisu', ascending=False).index[0]
    print(f"--- 毎月 {top_day}日 の機種別データ（サンプル数30以上） ---")
    top_day_df = df[df['Day'] == top_day]
    machine_stats = top_day_df.groupby('機種名').agg(
        Count=('差枚', 'count'),
        Avg_Samaisu=('差枚', 'mean'),
        Win_Rate=('Win', 'mean')
    ).round(2)
    print(machine_stats[machine_stats['Count'] >= 30].sort_values('Avg_Samaisu', ascending=False).head(10).to_string())

if __name__ == "__main__":
    analyze_dates()
