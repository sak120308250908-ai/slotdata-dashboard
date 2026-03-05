import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

st.set_page_config(page_title="Slot Data Dashboard", page_icon="🎰", layout="wide")

# Chromeなどの自動翻訳によるDOM破壊（Reactエラー）を防ぐため、HTMLタグを強制的に日本語指定する
components.html(
    """
    <script>
    // Streamlitのデフォルトである lang="en" を "ja" に変更
    window.parent.document.documentElement.lang = 'ja';
    // 念のためGoogle翻訳ツールを無効化する属性を追加
    window.parent.document.documentElement.setAttribute('translate', 'no');
    // メタタグ（google: notranslate）もheadに動的追加
    var meta = window.parent.document.createElement('meta');
    meta.name = 'google';
    meta.content = 'notranslate';
    window.parent.document.getElementsByTagName('head')[0].appendChild(meta);
    </script>
    """,
    width=0, height=0
)

import requests
import io
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

@st.cache_data(ttl=3600)
def fetch_store_data(store_name):
    all_data = []
    limit = 1000
    offset = 0
    
    # Supabaseから指定店舗の全データをページネーションで取得
    while True:
        response = supabase.table('slot_data').select('*').eq('店舗', store_name).range(offset, offset + limit - 1).execute()
        data = response.data
        if not data:
            break
        all_data.extend(data)
        if len(data) < limit:
            break
        offset += limit
        
    if not all_data:
        # データがない場合は空のDataFrameを返す（後続のエラー防止）
        df = pd.DataFrame(columns=['店舗', '日付', '機種名', '台番', 'G数', '差枚', 'BB', 'RB', 'ART', '合成確率'])
    else:
        df = pd.DataFrame(all_data)
        
    # 前処理（既存ロジック）
    df['日付'] = pd.to_datetime(df['日付'])
    df['Month'] = df['日付'].dt.month
    df['Day'] = df['日付'].dt.day
    df['End_Digit'] = df['Day'] % 10
    
    weekday_map = {
        'Monday': '月曜日', 'Tuesday': '火曜日', 'Wednesday': '水曜日',
        'Thursday': '木曜日', 'Friday': '金曜日', 'Saturday': '土曜日', 'Sunday': '日曜日'
    }
    df['Weekday_EN'] = df['日付'].dt.day_name()
    df['Weekday'] = df['Weekday_EN'].map(weekday_map)
    weekdays = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
    df['Weekday'] = pd.Categorical(df['Weekday'], categories=weekdays, ordered=True)
    
    # 差枚列のクレンジング（文字混入等を考慮）
    df['差枚'] = pd.to_numeric(df['差枚'], errors='coerce').fillna(0)
    df['Win'] = (df['差枚'] > 0).astype(int)
    return df

# --- サイドバー ---
st.sidebar.title("🎰 解析メニュー")

# 固定の店舗リスト（データベースへの毎回のDistinctクエリ負荷を避けるためハードコード）
shops = sorted(['プレイランドキャッスル知多にしの台', 'プレイランドキャッスル東郷', 'キング観光サウザンド生桑', 'JP888', 'キング観光尾鷲', 'メガコンコルド大口41号通り', 'プレイランドキャッスル高浜', 'A-FLAG津', 'KYORAKU妙音通', 'プレイランドキャッスル知多東海', 'メガコンコルド名古屋みなと23号通り', 'プレイランドキャッスル天白', 'タイキ豊橋藤沢', 'ラッキー1番日進竹の山', 'リブレ遊援館', 'プレイランドキャッスルワンダー', '玉越中川', 'キング観光サウザンド津', 'キャッスル大金', 'パーラーワールド小牧', 'ZENT岡崎インター', 'ZENT刈谷', 'キング観光サウザンド桑名本店', 'コスモジャパン三谷', 'キング観光サウザンド松阪', 'キング観光サウザンド栄若宮大通', 'メガコンコルド豊川インター', 'がちゃぽん南', 'KEIZ港', 'キクヤ長良', 'ZENT住吉', 'キング観光笠寺', 'キング観光サウザンド栄東新町', 'サンシャインKYORAKU平針', 'プレイランドキャッスル尾頭橋', 'プレイランドキャッスル記念橋南', 'タイキ四日市泊小柳', 'ラッキープラザ弥富', 'ラッキープラザ津島', 'キング観光サウザンド近鉄四日市', 'KYORAKU西', 'メガコンコルド春日井', 'ラッキープラザ可児', 'メガコンコルドみなと木場インター', 'オーギヤタウン半田', 'メガコンコルドBLAZE', 'コスモジャパン大府', 'マルシン777', 'コンコルド愛西日比野駅前', 'ZENT扶桑', 'ZENT各務原', 'キャッスル岩倉', 'キング観光鈴鹿インター', 'プレイランドキャッスル上社', 'サンパレス', 'オーギヤ安城', 'キング観光名張', 'プレイランドキャッスル小牧', 'メガコンコルド刈谷知立', 'プレイランド第一平和', 'キング観光いなべ', 'キング観光サウザンド今池2号', 'コスモジャパン蒲郡', 'ZENT豊橋藤沢店', 'ZENT木曽川', 'メガガイア一宮', 'メガコンコルド稲沢', 'プレイランドキャッスル知多', 'プレイランドキャッスル大垣', 'キング666飛騨高山', 'M&K岡崎', 'MGM四日市', 'ゴー港', 'キクヤ島', 'グランドオータ鳴海', 'ZENT長久手', 'キング観光熊野', 'オータ岡崎', 'KEIZ中川運河', 'メガコンコルド岡崎インター', 'M&K道光寺', 'M&K本店', 'ラッキー1番江南', 'プレイランドキャッスル大曽根', 'ラッキープラザ関', 'A-FLAG瀬戸', 'キクヤ春日井', 'キング666一宮', 'ZENT稲沢', 'キング観光サウザンド桑名サンシパーク', 'メガコンコルド西尾', 'ZENT名古屋北', 'キング観光新瑞', 'キング666半田', 'プレイランドキャッスル春日井', 'プレイランドキャッスル熱田', 'コンコルド岐阜羽島駅前', 'グランワールドカップ本巣', '大丸桜山', 'ZENT市ノ坪', 'コスモジャパン西尾', 'パチンコ立岩', 'ラッキープラザ名古屋西インター七宝', 'ZENT可児', 'メガコンコルド岡崎北', 'キクヤ穂積', 'KYORAKU東海', 'ZENT梅坪', 'ZENT555', 'コンコルド一宮尾西インター', 'G&L一宮', 'ABC豊川', 'メガコンコルド大垣インター南', 'キング666東海', 'ミカド観光半田', 'キング観光サウザンド鈴鹿', 'メガコンコルド豊田インター', 'ZENT豊田本店', 'メガスロットコンコルド吉浜', 'キクヤ本店'])

# キャッスル大金を初期表示にする
if "キャッスル大金" in shops:
    shops.insert(0, shops.pop(shops.index("キャッスル大金")))

selected_shop = st.sidebar.selectbox("🏠 分析対象の店舗", shops)

# 選択された店舗のデータのみをSupabaseから取得してDataFrame化
try:
    df = fetch_store_data(selected_shop)
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    st.stop()

menu = st.sidebar.radio(
    "分析モードを選択してください",
    ("1. 全体サマリー＆特定日分析", "2. カレンダー・曜日分析", "3. 機種別詳細分析", "4. 強力なクロス分析 (曜日×特定日)", "5. 新台の初日・強弱分析", "6. AI・チャット風検索")
)

# --- ヘッダー ---
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)
st.title("🎰 スロットデータ分析ダッシュボード")
st.markdown(f"**対象店舗**: {selected_shop}")
if len(df) > 0:
    st.markdown(f"**データ件数**: {len(df):,}件 (期間: {df['日付'].min().strftime('%Y-%m-%d')} 〜 {df['日付'].max().strftime('%Y-%m-%d')})")
else:
    st.markdown(f"**データ件数**: 0件 (現在データベースへアップロード処理中です。しばらくお待ちください...)")


# --- 1. 全体サマリー＆特定日分析 ---
if menu == "1. 全体サマリー＆特定日分析":
    st.header("🎯 1. 特定日の傾向（末尾・日付別）")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 末尾（0〜9）ごとの平均差枚数")
        end_digit_stats = df.groupby('End_Digit').agg(
            Avg_Samaisu=('差枚', 'mean'), Win_Rate=('Win', 'mean')
        ).reset_index()
        end_digit_stats['End_Digit'] = end_digit_stats['End_Digit'].astype(str) + "の付く日"
        
        fig = px.bar(end_digit_stats, x='End_Digit', y='Avg_Samaisu', 
                     title="末尾別の平均差枚数",
                     color='Avg_Samaisu', color_continuous_scale='RdYlGn',
                     labels={'Avg_Samaisu': '平均差枚数', 'End_Digit': '日付の末尾'})
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("🏅 日付別 平均差枚トップ10")
        day_stats = df.groupby('Day').agg(
            Avg_Samaisu=('差枚', 'mean'), Win_Rate=('Win', 'mean'), Count=('差枚', 'count')
        ).sort_values('Avg_Samaisu', ascending=False).head(10).reset_index()
        day_stats['Day'] = day_stats['Day'].astype(str) + "日"
        day_stats['Win_Rate'] = (day_stats['Win_Rate'] * 100).round(1).astype(str) + "%"
        day_stats['Avg_Samaisu'] = day_stats['Avg_Samaisu'].round().astype(int)
        day_stats.columns = ['日付', '平均差枚数', '勝率', 'サンプル数']
        st.dataframe(day_stats, use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 特定日の「強い機種」ランキング")
    target_day = st.slider("日付（1〜31）を選択", 1, 31, 6)
    min_count = st.number_input("最低サンプル数", min_value=1, value=30)
    
    target_df = df[df['Day'] == target_day]
    machine_stats = target_df.groupby('機種名').agg(
        Count=('差枚', 'count'), Avg_Samaisu=('差枚', 'mean'), Win_Rate=('Win', 'mean')
    ).reset_index()
    
    filtered_stats = machine_stats[machine_stats['Count'] >= min_count].sort_values('Avg_Samaisu', ascending=False).head(15)
    filtered_stats['Win_Rate'] = (filtered_stats['Win_Rate'] * 100).round(1).astype(str) + "%"
    filtered_stats['Avg_Samaisu'] = filtered_stats['Avg_Samaisu'].round().astype(int)
    filtered_stats.columns = ['機種名', 'サンプル数', '平均差枚数', '勝率']
    
    st.write(f"毎月 **{target_day}日** の優良機種トップ15 (サンプル数{min_count}以上)")
    st.dataframe(filtered_stats, use_container_width=True)


# --- 2. カレンダー・曜日分析 ---
elif menu == "2. カレンダー・曜日分析":
    st.header("📅 2. 曜日ごとの全体傾向")
    
    weekday_stats = df.groupby('Weekday').agg(
        Avg_Samaisu=('差枚', 'mean'), Win_Rate=('Win', 'mean')
    ).reset_index()
    
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.bar(weekday_stats, x='Weekday', y='Avg_Samaisu', 
                      title="曜日別の平均差枚数",
                      color='Avg_Samaisu', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = px.line(weekday_stats, x='Weekday', y='Win_Rate', 
                       title="曜日別の勝率", markers=True)
        fig2.update_layout(yaxis=dict(tickformat=".0%"))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 曜日別の「強い機種」ランキング")
    target_weekday = st.selectbox("分析したい曜日を選択", ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日'], index=5)
    min_count_w = st.number_input("最低サンプル数", min_value=1, value=30, key="min_count_weekday")
    
    w_df = df[df['Weekday'] == target_weekday]
    w_machine_stats = w_df.groupby('機種名').agg(
        Count=('差枚', 'count'), Avg_Samaisu=('差枚', 'mean'), Win_Rate=('Win', 'mean')
    ).reset_index()
    
    w_filtered_stats = w_machine_stats[w_machine_stats['Count'] >= min_count_w].sort_values('Avg_Samaisu', ascending=False).head(15)
    w_filtered_stats['Win_Rate'] = (w_filtered_stats['Win_Rate'] * 100).round(1).astype(str) + "%"
    w_filtered_stats['Avg_Samaisu'] = w_filtered_stats['Avg_Samaisu'].round().astype(int)
    w_filtered_stats.columns = ['機種名', 'サンプル数', '平均差枚数', '勝率']
    
    st.write(f"**{target_weekday}** の優良機種トップ15 (サンプル数{min_count_w}以上)")
    st.dataframe(w_filtered_stats, use_container_width=True)


# --- 3. 機種別詳細分析 ---
elif menu == "3. 機種別詳細分析":
    st.header("🎰 3. 機種別の詳細・グラフ")
    
    # 選択できる機種名（全体で100件以上のデータがあるものに絞る）
    machine_counts = df['機種名'].value_counts()
    valid_machines = machine_counts[machine_counts >= 100].index.tolist()
    
    st.write("▼ 機種を選択し、更新ボタンを押してください")
    with st.form("machine_selection_form"):
        selected_machine = st.selectbox(
            "分析したい機種（データ数が多い順）", 
            valid_machines
        )
        submitted = st.form_submit_button("🔄 データを更新する")
        
    if "form_selected_machine" not in st.session_state:
        st.session_state["form_selected_machine"] = valid_machines[0]
        
    if submitted:
        st.session_state["form_selected_machine"] = selected_machine
        
    display_machine = st.session_state["form_selected_machine"]
    m_df = df[df['機種名'] == display_machine]
    
    st.markdown("---")
    st.subheader(f"「{display_machine}」の基本データ")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("総稼働数", f"{len(m_df):,}回")
    c2.metric("平均差枚数", f"{m_df['差枚'].mean():.1f}枚")
    c3.metric("勝率", f"{m_df['Win'].mean() * 100:.1f}%")
    c4.metric("最高差枚", f"{m_df['差枚'].max():,}枚")
    
    st.markdown("---")
    st.subheader("📊 特定日・曜日・差枚数の傾向")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("▼ 特定日の傾向（末尾別の平均差枚）")
        e_stats = m_df.groupby('End_Digit')['差枚'].mean().reset_index()
        e_stats['End_Digit'] = e_stats['End_Digit'].astype(str) + "の付く日"
        fig_e = px.bar(e_stats, x='End_Digit', y='差枚', color='差枚', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_e, use_container_width=True)
        
    with col2:
        st.write("▼ 曜日別の平均差枚")
        w_stats = m_df.groupby('Weekday')['差枚'].mean().reset_index()
        fig_w = px.bar(w_stats, x='Weekday', y='差枚', color='差枚', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_w, use_container_width=True)
        
    with col3:
        st.write("▼ 差枚数の分布（ヒストグラム）")
        fig_hist = px.histogram(m_df, x='差枚', nbins=50)
        st.plotly_chart(fig_hist, use_container_width=True)

# --- 5. 新台の初日・強弱分析 ---
elif menu == "5. 新台の初日・強弱分析":
    st.header("✨ 5. 新台強弱判断データ")
    st.write("対象店舗における「初めて稼働した日」の機種別平均結果を表示します。（データ集計開始時点から存在する機種は除外されます）")
    
    if st.button("新台の初日データを抽出する"):
        with st.spinner("新台のデータを抽出中..."):
            min_date = df['日付'].min()
            first_appearance = df.groupby('機種名')['日付'].min().reset_index()
            new_machines_df = first_appearance[first_appearance['日付'] > min_date]
            new_machines = new_machines_df['機種名'].tolist()
            
            if not new_machines:
                st.warning("この店舗に新台と判定できるデータがありませんでした。")
            else:
                results = []
                for machine in new_machines:
                    m_df = df[df['機種名'] == machine].sort_values('日付')
                    # G数が0より大きいレコード（実際に稼働した日）
                    active_m_df = m_df[m_df['G数'] > 0]
                    
                    if len(active_m_df) > 0:
                        first_active_date = active_m_df['日付'].iloc[0]
                        target_df = m_df[m_df['日付'] == first_active_date]
                        
                        avg_g = target_df['G数'].mean()
                        avg_bb = target_df['BB'].mean() if 'BB' in target_df.columns else 0
                        avg_rb = target_df['RB'].mean() if 'RB' in target_df.columns else 0
                        avg_art = target_df['ART'].mean() if 'ART' in target_df.columns else 0
                        avg_diff = target_df['差枚'].mean()
                        win_rate = (target_df['差枚'] > 0).mean() * 100
                        
                        results.append({
                            '機種名': machine,
                            '導入/初稼働日': first_active_date.strftime('%Y-%m-%d'),
                            '台数': len(target_df),
                            '平均回転数': int(round(avg_g)),    # 小数点なし
                            '平均BB': round(avg_bb, 1),
                            '平均RB': round(avg_rb, 1),
                            '平均ART': round(avg_art, 1),
                            '平均差枚数': int(round(avg_diff)), # 小数点なし
                            '勝率': f"{win_rate:.1f}%"
                        })
                
                res_df = pd.DataFrame(results).sort_values('導入/初稼働日', ascending=False)
                st.success(f"🤖 {len(res_df)}機種の新台データが見つかりました！")
                
                # 見やすくするためのフォーマット＆色分け関数 (共通利用)
                def format_diff(val):
                    try:
                        num = int(round(float(val)))
                        if num > 0:
                            return f"+{num:,}"
                        return f"{num:,}"
                    except:
                        return str(val)
                    
                def color_negative_red(val):
                    try:
                        num = float(str(val).replace(',', '').replace('+', ''))
                        return 'color: red' if num < 0 else 'color: black'
                    except:
                        return ''
                        
                # -------------------------------------------------------------
                # ▼ 新台 全体の・台数別 サマリー分析
                # -------------------------------------------------------------
                st.markdown("---")
                st.subheader("📊 新台入替分析（全体サマリー）")
                
                # 集計用に「勝った台数」と「総差枚」を逆算して求める
                res_df['総差枚'] = res_df['台数'] * res_df['平均差枚数']
                
                # 全体サマリー計算
                total_machines = res_df['台数'].sum()
                overall_avg_g = (res_df['台数'] * res_df['平均回転数']).sum() / total_machines if total_machines > 0 else 0
                total_diff = res_df['総差枚'].sum()
                overall_avg_diff = total_diff / total_machines if total_machines > 0 else 0
                
                # 全体の勝率は「勝った機種数÷全機種」ではなく「各機種の勝率×台数を合計して全体台数で割る」
                # 今回は簡略化のため元データdfから直接新台の全件を再抽出して勝率を出す
                all_new_active_records = []
                for machine in new_machines:
                    m_df = df[df['機種名'] == machine].sort_values('日付')
                    active_m_df = m_df[m_df['G数'] > 0]
                    if len(active_m_df) > 0:
                        first_active_date = active_m_df['日付'].iloc[0]
                        all_new_active_records.append(m_df[m_df['日付'] == first_active_date])
                
                if all_new_active_records:
                    all_new_df = pd.concat(all_new_active_records)
                    overall_win_rate = (all_new_df['差枚'] > 0).mean() * 100
                else:
                    overall_win_rate = 0
                
                overall_summary = pd.DataFrame([{
                    '総集計台数': total_machines,
                    '平均回転数': int(round(overall_avg_g)),
                    '総差枚': int(round(total_diff)),
                    '平均差枚数': int(round(overall_avg_diff)),
                    '勝率': f"{overall_win_rate:.1f}%"
                }])
                
                overall_style_formats = {
                    '総差枚': format_diff,
                    '平均差枚数': format_diff,
                    '平均回転数': '{:,.0f}'
                }
                
                st.table(overall_summary.style.format(overall_style_formats)
                                              .applymap(color_negative_red, subset=['総差枚', '平均差枚数'])
                                              .set_properties(**{'text-align': 'right'})
                                              .hide(axis="index"))
                
                # --- 導入台数別分析 ---
                st.subheader("📊 導入台数別分析")
                
                def get_tier(count):
                    if count == 1: return "1台機種"
                    elif 2 <= count <= 4: return "2-4台機種"
                    elif 5 <= count <= 9: return "5-9台機種"
                    elif 10 <= count <= 19: return "10-19台機種"
                    else: return "20台以上機種"
                
                all_new_df['Tier'] = all_new_df.groupby('機種名')['台番'].transform('count').apply(get_tier)
                
                tier_order = ["1台機種", "2-4台機種", "5-9台機種", "10-19台機種", "20台以上機種"]
                tier_results = []
                
                for tier in tier_order:
                    t_df = all_new_df[all_new_df['Tier'] == tier]
                    if len(t_df) > 0:
                        t_machines = len(t_df)
                        t_avg_g = t_df['G数'].mean()
                        t_total_diff = t_df['差枚'].sum()
                        t_avg_diff = t_df['差枚'].mean()
                        t_win_rate = (t_df['差枚'] > 0).mean() * 100
                        
                        tier_results.append({
                            '導入規模': tier,
                            '総集計台数': t_machines,
                            '平均回転数': int(round(t_avg_g)),
                            '総差枚': int(round(t_total_diff)),
                            '平均差枚数': int(round(t_avg_diff)),
                            '勝率': f"{t_win_rate:.1f}%"
                        })
                    else:
                        tier_results.append({
                            '導入規模': tier,
                            '総集計台数': 0,
                            '平均回転数': 0,
                            '総差枚': 0,
                            '平均差枚数': 0,
                            '勝率': "0.0%"
                        })
                        
                tier_summary_df = pd.DataFrame(tier_results)
                st.table(tier_summary_df.style.format(overall_style_formats)
                                              .applymap(color_negative_red, subset=['総差枚', '平均差枚数'])
                                              .set_properties(subset=['総集計台数', '平均回転数', '総差枚', '平均差枚数', '勝率'], **{'text-align': 'right'})
                                              .hide(axis="index"))
                
                st.markdown("---")
                
                # -------------------------------------------------------------
                # 日付ごとにグループ化して表示
                unique_dates = res_df['導入/初稼働日'].unique()
                
                # 見やすくするためのフォーマット＆色分け関数
                def format_diff(val):
                    try:
                        num = int(round(float(val)))
                        if num > 0:
                            return f"+{num:,}"
                        return f"{num:,}"
                    except:
                        return str(val)
                    
                def color_negative_red(val):
                    try:
                        num = float(str(val).replace(',', '').replace('+', ''))
                        return 'color: red' if num < 0 else 'color: black'
                    except:
                        return ''
                
                # 表示する列の順番を指定（平均差枚数が先）
                display_cols = ['機種名', '台数', '平均差枚数', '平均回転数', '平均BB', '平均RB', '平均ART', '勝率']
                
                # Pandas Stylerのフォーマット設定（全表で共通使用）
                style_formats = {
                    '平均差枚数': format_diff,
                    '平均回転数': '{:,.0f}',
                    '平均BB': '{:.1f}',
                    '平均RB': '{:.1f}',
                    '平均ART': '{:.1f}'
                }
                
                for date in unique_dates:
                    st.markdown(f"### 📅 {date}")
                    date_df = res_df[res_df['導入/初稼働日'] == date][display_cols].copy()
                    
                    # スタイルとフォーマットを適用（CSSで右寄せ指定）
                    styled_df = date_df.style.format(style_formats) \
                                       .applymap(color_negative_red, subset=['平均差枚数']) \
                                       .set_properties(subset=['台数', '平均差枚数', '平均回転数', '平均BB', '平均RB', '平均ART', '勝率'], 
                                                       **{'text-align': 'right'}) \
                                       .hide(axis="index")
                    
                    # HTMLの表として描画（st.tableを使うことで確実な右寄せと文字色反映が可能）
                    st.table(styled_df)
                
                st.markdown("---")
                st.write("▼ 全件まとめデータ（ソート・検索用）")
                
                # 全件テーブルもフォーマットして描画
                formatted_res_df = res_df[display_cols + ['導入/初稼働日']].copy()
                styled_all_df = formatted_res_df.style.format(style_formats) \
                                                .applymap(color_negative_red, subset=['平均差枚数']) \
                                                .set_properties(subset=['台数', '平均差枚数', '平均回転数', '平均BB', '平均RB', '平均ART', '勝率'], 
                                                                **{'text-align': 'right'})
                st.dataframe(styled_all_df, use_container_width=True, hide_index=True)

# --- 6. AI・チャット風検索 ---
elif menu == "6. AI・チャット風検索":
    import re
    st.header("💬 6. AI・チャット風検索")
    st.write("質問を入力してください。（例：「ハナハナで最も差枚数が出ている台番は？」「からくりサーカスの勝率は？」など）")
    
    query = st.text_input("質問を入力：", placeholder="ハナハナで最も差枚数が出ている台番は？")
    
    if query:
        # パターン0: 特定の日付検索 (例: 2/28, 2月28日, 2026/2/28)
        match_specific_date = re.fullmatch(r'(?:(20\d{2})[年/])?([0-1]?[0-9])[月/]([0-3]?[0-9])日?\s*(のデータ)?', query.strip())
        
        # パターン1: 「[機種名]で最も差枚数が出ている台番は？」
        match_top_machine = re.search(r'(.*?)で(最も|一番)(差枚|差枚数)が出ている(台番|台)は[？?]?', query)
        
        # パターン2: 「[機種名]の勝率は？」
        match_win_rate = re.search(r'(.*?)の勝率は[？?]?', query)
        
        # パターン3: 「[数字]のつく日(または[数字]日)に(台)平均差枚が多い(高い)機種は？」
        match_date_machine = re.search(r'([0-9]+)(のつく日|日)に[台\s]*平均差枚が(多い|高い|一番|トップ)機種は[？?]?', query)
        
        if match_specific_date:
            y_str = match_specific_date.group(1)
            m_str = match_specific_date.group(2)
            d_str = match_specific_date.group(3)
            
            m_num = int(m_str)
            d_num = int(d_str)
            
            if y_str:
                y_num = int(y_str)
                res = df[(df['日付'].dt.year == y_num) & (df['Month'] == m_num) & (df['Day'] == d_num)]
                years_to_display = [y_num]
            else:
                res = df[(df['Month'] == m_num) & (df['Day'] == d_num)]
                # 存在する年を新しい順（降順）リストとして取得
                years_to_display = sorted(res['日付'].dt.year.unique().tolist(), reverse=True)
                
            if len(res) == 0:
                if y_str:
                    st.warning(f"「{y_num}年{m_num}月{d_num}日」のデータは見つかりませんでした。")
                else:
                    st.warning(f"「{m_num}月{d_num}日」のデータは見つかりませんでした。")
            else:
                st.success(f"🤖 回答: {m_num}月{d_num}日 のデータが見つかりました！（合計 {len(res)}件）")
                
                # 年ごとにデータを分割して表示
                for y in years_to_display:
                    year_res = res[res['日付'].dt.year == y]
                    if len(year_res) == 0:
                        continue
                        
                    title_str = f"📅 {y}年{m_num}月{d_num}日のデータ"
                    st.subheader(title_str)
                    
                    # サマリー情報
                    col1, col2, col3 = st.columns(3)
                    col1.metric("稼働台数", f"{len(year_res):,}台")
                    col2.metric("平均差枚数", f"{year_res['差枚'].mean():+,.0f}枚")
                    col3.metric("勝率", f"{year_res['Win'].mean() * 100:.1f}%")
                    
                    st.write(f"▼ {y}年{m_num}月{d_num}日の優秀台ランキング（差枚数順 トップ20）")
                    top_machines = year_res.sort_values('差枚', ascending=False).head(20).copy()
                    
                    # 日付列が見やすいように文字列にフォーマット
                    top_machines['日付'] = top_machines['日付'].dt.strftime('%Y-%m-%d')
                    
                    display_cols = ['日付', '店舗', '機種名', '台番', '差枚', 'G数']
                    display_cols = [c for c in display_cols if c in year_res.columns]
                    
                    st.dataframe(top_machines[display_cols], use_container_width=True)
                    
                    with st.expander(f"{y}年{m_num}月{d_num}日の全データを見る"):
                        all_res = year_res.sort_values('差枚', ascending=False).copy()
                        all_res['日付'] = all_res['日付'].dt.strftime('%Y-%m-%d')
                        st.dataframe(all_res, use_container_width=True)
                    
                    st.markdown("---")

        elif match_date_machine:
            target_num = int(match_date_machine.group(1))
            date_type = match_date_machine.group(2)
            
            if date_type == "のつく日":
                res = df[df['End_Digit'] == target_num]
                title_str = f"{target_num}のつく日"
            else:
                res = df[df['Day'] == target_num]
                title_str = f"毎月{target_num}日"
                
            if len(res) == 0:
                st.warning(f"「{title_str}」のデータが見つかりませんでした。")
            else:
                st.success(f"🤖 回答: {title_str} に台平均差枚数が多い機種のランキングです！（サンプル数10以上の機種を表示）")
                
                # 機種名ごとの集計
                machine_stats = res.groupby('機種名').agg(
                    累計差枚数=('差枚', 'sum'),
                    稼働日数=('差枚', 'count'),      # 何回稼働したか
                    稼働台数=('台番', 'nunique')   # 何台の異なる台番が稼働したか
                ).reset_index()
                
                machine_stats['1日平均差枚数'] = (machine_stats['累計差枚数'] / machine_stats['稼働日数']).round(1)
                
                # サンプル数10以上に絞り、平均差枚の降順でソート
                filtered_stats = machine_stats[machine_stats['稼働日数'] >= 10].sort_values('1日平均差枚数', ascending=False)
                
                # 列の並び替え
                display_df = filtered_stats[['機種名', '累計差枚数', '稼働日数', '稼働台数', '1日平均差枚数']]
                st.dataframe(display_df.head(20), use_container_width=True)

        elif match_top_machine:
            target_machine = match_top_machine.group(1).strip()
            target_clean = target_machine.replace(" ", "").replace("　", "")
            normalized_machines = df['機種名'].astype(str).str.replace(" ", "").str.replace("　", "")
            
            res = df[normalized_machines.str.contains(target_clean, na=False)]
            
            if len(res) == 0:
                st.warning(f"「{target_machine}」という機種は見つかりませんでした。別の名前でお試しください。")
            else:
                # 台番と機種名ごとの合計・平均差枚を計算
                daiban_stats = res.groupby(['台番', '機種名']).agg(
                    差枚=('差枚', 'sum'),
                    稼働日数=('差枚', 'count')
                ).reset_index()
                daiban_stats['1日平均差枚'] = (daiban_stats['差枚'] / daiban_stats['稼働日数']).round(1)
                
                best_daiban = daiban_stats.loc[daiban_stats['差枚'].idxmax()]
                total_machines = res['台番'].nunique()
                
                st.success(f"🤖 回答: 「{target_machine}」を含む機種の中で、過去最も累計差枚数が出ている台番は **{int(best_daiban['台番'])}番台（{best_daiban['機種名']}）** です！（累計差枚: +{int(best_daiban['差枚']):,}枚 / 1日平均: +{best_daiban['1日平均差枚']:,}枚）")
                st.info(f"📊 対象となる機種の **総台数は {total_machines}台** です。")
                
                st.write(f"▼ {target_machine} を含む台番別ランキング TOP10")
                # 表示用に見やすく列名を整理
                display_df = daiban_stats.sort_values('差枚', ascending=False).head(10)
                display_df = display_df[['台番', '機種名', '差枚', '稼働日数', '1日平均差枚']]
                display_df.columns = ['台番', '機種名', '累計差枚数', '稼働日数', '1日平均差枚数']
                st.dataframe(display_df, use_container_width=True)
                
        elif match_win_rate:
            target_machine = match_win_rate.group(1).strip()
            res = df[df['機種名'].str.fullmatch(target_machine, na=False)]
            if len(res) == 0:
                res = df[df['機種名'].str.contains(target_machine, na=False)]
                
            if len(res) == 0:
                st.warning(f"「{target_machine}」という機種は見つかりませんでした。")
            else:
                summary = res.groupby('機種名').agg(
                    Count=('差枚', 'count'), Win_Rate=('Win', 'mean')
                ).reset_index()
                st.success(f"🤖 回答: 結果は以下の通りです！")
                for _, row in summary.iterrows():
                    st.write(f"- **{row['機種名']}**: 勝率 **{row['Win_Rate']*100:.1f}%** ({row['Count']}回稼働)")
                    
        else:
            # 通常のキーワード検索フォールバック
            if query.isdigit():
                res = df[df['台番'] == int(query)]
                st.info(f"台番 {query} の稼働履歴（{len(res)}件）を表示します：")
                st.dataframe(res.sort_values("日付", ascending=False).head(50), use_container_width=True)
            else:
                res = df[df['機種名'].str.contains(query, na=False)]
                if len(res) > 0:
                    st.info(f"「{query}」を含む機種のデータが見つかりました（{len(res)}件）。機種別サマリーを表示します：")
                    summary = res.groupby('機種名').agg(
                        Count=('差枚', 'count'), Avg_Samaisu=('差枚', 'mean'), Win_Rate=('Win', 'mean')
                    ).sort_values('Avg_Samaisu', ascending=False)
                    summary['Win_Rate'] = (summary['Win_Rate'] * 100).round(1).astype(str) + "%"
                    st.dataframe(summary, use_container_width=True)
                else:
                    st.warning("該当するデータが見つかりませんでした。「ハナハナで一番差枚数が出ている台番は？」のように質問するか、機種名を入力してください。")

# --- 4. 強力なクロス分析 (曜日×特定日) ---
elif menu == "4. 強力なクロス分析 (曜日×特定日)":
    st.header("🔍 4. 強力なクロス分析 (曜日 × 特定日)")
    st.write("「曜日」と「特定日（日付または末尾）」を組み合わせて、ピンポイントな状況を分析できます。")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        target_weekdays = st.multiselect("曜日を選択（複数可）", 
                                        ['曜日すべて', '月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日'],
                                        default=['曜日すべて'])
        if not target_weekdays or '曜日すべて' in target_weekdays:
            target_weekdays = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
            
    with col2:
        filter_type = st.radio("特定日条件の種類", ["日付指定 (1〜31日)", "末尾指定 (0〜9の付く日)"])
        
    with col3:
        if filter_type == "日付指定 (1〜31日)":
            target_val = st.number_input("日付を入力", 1, 31, 6)
        else:
            target_val = st.number_input("末尾番号を入力", 0, 9, 6)
            
    # データフィルタリング
    cross_df = df[df['Weekday'].isin(target_weekdays)]
    if filter_type == "日付指定 (1〜31日)":
        cross_df = cross_df[cross_df['Day'] == target_val]
        cond_str = f"{target_val}日"
    else:
        cross_df = cross_df[cross_df['End_Digit'] == target_val]
        cond_str = f"末尾{target_val}の日"
        
    st.markdown("---")
    if len(cross_df) == 0:
        st.warning("選択された条件に合致するデータが見つかりませんでした。条件を変えてお試しください。")
    else:
        st.subheader(f"📊 分析結果: 【{', '.join(target_weekdays)}】 × 【{cond_str}】")
        
        # 基本データの表示
        c1, c2, c3 = st.columns(3)
        c1.metric("対象データ件数", f"{len(cross_df):,}件")
        c2.metric("平均差枚数", f"{cross_df['差枚'].mean():.1f}枚")
        c3.metric("平均勝率", f"{cross_df['Win'].mean() * 100:.1f}%")
        
        st.write("▼ この条件下での優良機種ランキング")
        min_count_c = st.number_input("最低サンプル数", min_value=1, value=5, key="min_count_cross")
        
        c_machine_stats = cross_df.groupby('機種名').agg(
            Count=('差枚', 'count'), Avg_Samaisu=('差枚', 'mean'), Win_Rate=('Win', 'mean')
        ).reset_index()
        
        c_filtered_stats = c_machine_stats[c_machine_stats['Count'] >= min_count_c].sort_values('Avg_Samaisu', ascending=False).head(20)
        c_filtered_stats['Win_Rate'] = (c_filtered_stats['Win_Rate'] * 100).round(1).astype(str) + "%"
        c_filtered_stats['Avg_Samaisu'] = c_filtered_stats['Avg_Samaisu'].round().astype(int)
        c_filtered_stats.columns = ['機種名', 'サンプル数', '平均差枚数', '勝率']
        st.dataframe(c_filtered_stats, use_container_width=True)

