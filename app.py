import streamlit as st
import swisseph as swe
from datetime import datetime, time, timezone, timedelta
import os
import math

# --- 定数 ---
# 天体暦ファイルのパス
EPHE_PATH = 'ephe'
# 都道府県の緯度経度データ
PREFECTURE_DATA = {
    "北海道": {"lat": 43.064, "lon": 141.348}, "青森県": {"lat": 40.825, "lon": 140.741},
    "岩手県": {"lat": 39.704, "lon": 141.153}, "宮城県": {"lat": 38.269, "lon": 140.872},
    "秋田県": {"lat": 39.719, "lon": 140.102}, "山形県": {"lat": 38.240, "lon": 140.364},
    "福島県": {"lat": 37.750, "lon": 140.468}, "茨城県": {"lat": 36.342, "lon": 140.447},
    "栃木県": {"lat": 36.566, "lon": 139.884}, "群馬県": {"lat": 36.391, "lon": 139.060},
    "埼玉県": {"lat": 35.857, "lon": 139.649}, "千葉県": {"lat": 35.605, "lon": 140.123},
    "東京都": {"lat": 35.690, "lon": 139.692}, "神奈川県": {"lat": 35.448, "lon": 139.643},
    "新潟県": {"lat": 37.902, "lon": 139.023}, "富山県": {"lat": 36.695, "lon": 137.211},
    "石川県": {"lat": 36.594, "lon": 136.626}, "福井県": {"lat": 36.065, "lon": 136.222},
    "山梨県": {"lat": 35.664, "lon": 138.568}, "長野県": {"lat": 36.651, "lon": 138.181},
    "岐阜県": {"lat": 35.391, "lon": 136.722}, "静岡県": {"lat": 34.977, "lon": 138.383},
    "愛知県": {"lat": 35.180, "lon": 136.907}, "三重県": {"lat": 34.730, "lon": 136.509},
    "滋賀県": {"lat": 35.005, "lon": 135.869}, "京都府": {"lat": 35.021, "lon": 135.756},
    "大阪府": {"lat": 34.686, "lon": 135.520}, "兵庫県": {"lat": 34.691, "lon": 135.183},
    "奈良県": {"lat": 34.685, "lon": 135.833}, "和歌山県": {"lat": 34.226, "lon": 135.168},
    "鳥取県": {"lat": 35.504, "lon": 134.238}, "島根県": {"lat": 35.472, "lon": 133.051},
    "岡山県": {"lat": 34.662, "lon": 133.934}, "広島県": {"lat": 34.396, "lon": 132.459},
    "山口県": {"lat": 34.186, "lon": 131.471}, "徳島県": {"lat": 34.066, "lon": 134.559},
    "香川県": {"lat": 34.340, "lon": 134.043}, "愛媛県": {"lat": 33.842, "lon": 132.765},
    "高知県": {"lat": 33.560, "lon": 133.531}, "福岡県": {"lat": 33.607, "lon": 130.418},
    "佐賀県": {"lat": 33.249, "lon": 130.299}, "長崎県": {"lat": 32.745, "lon": 129.874},
    "熊本県": {"lat": 32.790, "lon": 130.742}, "大分県": {"lat": 33.238, "lon": 131.613},
    "宮崎県": {"lat": 31.911, "lon": 131.424}, "鹿児島県": {"lat": 31.560, "lon": 130.558},
    "沖縄県": {"lat": 26.212, "lon": 127.681}
}
PLANET_IDS = {
    "太陽": swe.SUN, "月": swe.MOON, "水星": swe.MERCURY, "金星": swe.VENUS, 
    "火星": swe.MARS, "木星": swe.JUPITER, "土星": swe.SATURN, "天王星": swe.URANUS, 
    "海王星": swe.NEPTUNE, "冥王星": swe.PLUTO
}
# イベントカテゴリと関連アングル/天体のマッピング
EVENT_MAPPING = {
    "就職/独立/昇進/退職": {"angle": "MC", "planets": ["太陽", "木星", "土星"]},
    "結婚/離婚/パートナーシップ": {"angle": "DSC", "planets": ["太陽", "月", "金星", "木星"]},
    "引っ越し/家族の変化": {"angle": "IC", "planets": ["月", "天王星", "冥王星"]},
    "事故/病気/人生観の変化": {"angle": "ASC", "planets": ["火星", "土星", "天王星", "冥王星"]}
}
ASPECTS_TO_CHECK = [0, 90, 180] # チェックするアスペクト（合、スクエア、オポジション）
ASPECT_ORB = 1.0 # アスペクトのオーブ（許容度数）

# --- 関数定義 ---

def get_jd(dt_obj):
    """
    タイムゾーンを考慮してdatetimeオブジェクトからユリウス日を計算
    """
    dt_utc = dt_obj.replace(tzinfo=timezone(timedelta(hours=9))).astimezone(timezone.utc)
    return swe.utc_to_jd(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour, dt_utc.minute, dt_utc.second, 1)[1]

def calculate_natal_chart(jd, lat, lon):
    """
    指定されたユリウス日のネイタルチャート（天体とアングル）を計算
    """
    iflag = swe.FLG_SWIEPH | swe.FLG_SPEED
    natal_chart = {"planets": {}, "angles": {}}
    
    # 天体位置
    for name, pid in PLANET_IDS.items():
        pos = swe.calc_ut(jd, pid, iflag)[0][0]
        natal_chart["planets"][name] = pos
        
    # ハウス（アングル）
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    natal_chart["angles"] = {"ASC": ascmc[0], "MC": ascmc[1], "DSC": (ascmc[0] + 180) % 360, "IC": (ascmc[1] + 180) % 360}
    
    return natal_chart

def check_solar_arc(natal_chart, event_date, event_category):
    """
    ソーラーアークとネイタルチャートのアスペクトを検証し、根拠となる文字列を返す
    """
    found_aspects = []
    
    # 1. ソーラーアークの度数を計算
    age = event_date.year - natal_chart["birth_date"].year
    prog_date = natal_chart["birth_date"] + timedelta(days=age)
    jd_prog = get_jd(prog_date)
    
    natal_sun_pos = natal_chart["planets"]["太陽"]
    prog_sun_pos = swe.calc_ut(jd_prog, swe.SUN, swe.FLG_SWIEPH)[0][0]
    solar_arc = (prog_sun_pos - natal_sun_pos + 360) % 360

    # 2. イベントに関連するアングルと天体を取得
    mapping = EVENT_MAPPING.get(event_category)
    if not mapping:
        return []
    
    target_angle_name = mapping["angle"]
    target_planet_names = mapping["planets"]
    
    # 3. アスペクトをチェック
    # (A) ソーラーアークのアングル vs ネイタルの天体
    sa_angle_pos = (natal_chart["angles"][target_angle_name] + solar_arc) % 360
    for planet_name in target_planet_names:
        natal_planet_pos = natal_chart["planets"][planet_name]
        angle_diff = abs(sa_angle_pos - natal_planet_pos)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        for aspect in ASPECTS_TO_CHECK:
            if abs(angle_diff - aspect) < ASPECT_ORB:
                found_aspects.append(f"SA {target_angle_name} が N {planet_name} と {aspect}度")

    # (B) ソーラーアークの天体 vs ネイタルのアングル
    natal_angle_pos = natal_chart["angles"][target_angle_name]
    for planet_name in target_planet_names:
        sa_planet_pos = (natal_chart["planets"][planet_name] + solar_arc) % 360
        angle_diff = abs(sa_planet_pos - natal_angle_pos)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
            
        for aspect in ASPECTS_TO_CHECK:
            if abs(angle_diff - aspect) < ASPECT_ORB:
                found_aspects.append(f"SA {planet_name} が N {target_angle_name} と {aspect}度")
                
    return found_aspects

# --- Streamlit UI ---

st.set_page_config(page_title="レクティフィケーション・アシスタント", page_icon="⏳")
st.title("⏳ レクティフィケーション・アシスタント")
st.write("生年月日と人生の出来事を入力することで、可能性の高い出生時刻を割り出します。")

# --- 1. ユーザー情報入力 ---
st.header("1. あなたの情報を入力してください")
col1, col2 = st.columns(2)
with col1:
    birth_date = st.date_input("📅 生年月日", min_value=datetime(1900, 1, 1), value=datetime(1980, 1, 1))
with col2:
    birth_pref = st.selectbox("📍 出生都道府県", options=list(PREFECTURE_DATA.keys()), index=12) # Default to Tokyo

# --- 2. 出来事入力 ---
st.header("2. 人生の重要な出来事を入力してください")
st.info("出来事が起きた年月を入力してください。日付は1日で構いません。")

if 'events' not in st.session_state:
    st.session_state.events = []

for i, event in enumerate(st.session_state.events):
    with st.container(border=True):
        st.subheader(f"出来事 {i+1}")
        col1, col2, col3 = st.columns([3,3,1])
        event['category'] = col1.selectbox("カテゴリ", options=list(EVENT_MAPPING.keys()), key=f"cat_{i}")
        event['date'] = col2.date_input("発生年月", value=event.get('date', datetime(2010,1,1)), key=f"date_{i}")
        if col3.button("削除", key=f"del_{i}"):
            st.session_state.events.pop(i)
            st.rerun()

if st.button("出来事を追加 ➕"):
    st.session_state.events.append({})
    st.rerun()
    
st.markdown("---")

# --- 3. 計算実行 ---
if st.button("出生時刻を計算する 🚀", type="primary", disabled=(not st.session_state.events)):
    
    if not os.path.exists(EPHE_PATH):
        st.error(f"天体暦ファイルが見つかりません。`{EPHE_PATH}` フォルダを配置してください。")
        st.stop()
    swe.set_ephe_path(EPHE_PATH)

    coords = PREFECTURE_DATA[birth_pref]
    lat, lon = coords["lat"], coords["lon"]
    
    candidate_times = []
    
    progress_text = "出生時刻の候補を検証中... (00:00)"
    bar = st.progress(0, text=progress_text)

    # 4分ごとに時刻を検証 (00:00から23:56まで)
    total_steps = 24 * 15
    for i, minute_of_day in enumerate(range(0, 24 * 60, 4)):
        hour = minute_of_day // 60
        minute = minute_of_day % 60
        candidate_time = time(hour, minute)
        
        # 進捗バーを更新
        progress_val = (i + 1) / total_steps
        bar.progress(progress_val, text=f"出生時刻の候補を検証中... ({candidate_time.strftime('%H:%M')})")
        
        birth_dt = datetime.combine(birth_date, candidate_time)
        jd_natal = get_jd(birth_dt)
        
        # ネイタルチャートを計算
        natal_chart = calculate_natal_chart(jd_natal, lat, lon)
        natal_chart["birth_date"] = birth_dt # 後で年齢計算に使う
        
        score = 0
        evidence = []
        
        # 各イベントについてソーラーアークを検証
        for event in st.session_state.events:
            event_date = datetime.combine(event['date'], time(0,0))
            found_aspects = check_solar_arc(natal_chart, event_date, event['category'])
            if found_aspects:
                score += len(found_aspects)
                for aspect_info in found_aspects:
                    evidence.append(f"[{event['category']}/{event_date.year}年] {aspect_info}")

        if score > 0:
            candidate_times.append({"time": candidate_time, "score": score, "evidence": evidence})

    bar.empty()

    # --- 4. 結果表示 ---
    st.header("📈 計算結果")
    if not candidate_times:
        st.warning("入力された出来事と合致する、有力な出生時刻の候補は見つかりませんでした。出来事の種類や日付を変えて試してみてください。")
    else:
        # スコアの高い順に並び替え
        sorted_candidates = sorted(candidate_times, key=lambda x: x['score'], reverse=True)
        
        st.success(f"**{len(sorted_candidates)}個** の有力な出生時刻の候補が見つかりました。")

        for i, candidate in enumerate(sorted_candidates[:10]): # 上位10件を表示
            with st.container(border=True):
                st.subheader(f"👑 第 {i+1} 位： {candidate['time'].strftime('%H:%M')} ごろ")
                st.metric(label="信頼スコア", value=candidate['score'])
                st.markdown("**占星術的な根拠:**")
                for ev_str in candidate['evidence']:
                    st.text(f"・{ev_str}")
