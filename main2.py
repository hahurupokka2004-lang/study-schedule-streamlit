# streamlit_app.py
# =========================================
# テストスケジュール提案アプリ（タイマー削除版）
# =========================================

import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime

# -----------------------------
# 初期設定
# -----------------------------
st.set_page_config(page_title="テストスケジュール提案", layout="wide")

# セッション状態の初期化
if "subjects" not in st.session_state:
    st.session_state.subjects = []
if "schedule" not in st.session_state:
    st.session_state.schedule = None

st.title("📘 テストスケジュール提案アプリ")
st.caption("科目・難易度・テスト日から、学習マイルストーンを作成します")

# -----------------------------
# サイドバー：学習時間設定
# -----------------------------
st.sidebar.header("⏱ 1日の学習時間設定")

weekday_minutes = st.sidebar.number_input(
    "平日の学習時間（分）", 0, 600, 120, step=10
)
weekend_minutes = st.sidebar.number_input(
    "休日の学習時間（分）", 0, 900, 240, step=10
)

weekday_hours = weekday_minutes / 60
weekend_hours = weekend_minutes / 60

# -----------------------------
# 科目入力（削除機能付き）
# -----------------------------
st.header("① 科目登録")

c1, c2, c3 = st.columns(3)
with c1:
    subject_name = st.text_input("科目名")
with c2:
    difficulty = st.slider("難易度", 1, 5, 3)
with c3:
    exam_date = st.date_input("テスト日", date.today())

col1, col2 = st.columns(2)
with col1:
    if st.button("➕ 科目を追加", use_container_width=True):
        if subject_name:
            st.session_state.subjects.append({
                "科目": subject_name,
                "難易度": difficulty,
                "テスト日": exam_date
            })
            st.success(f"科目「{subject_name}」を追加しました")
            st.rerun()

with col2:
    if st.button("🗑️ 全科目クリア", use_container_width=True):
        st.session_state.subjects = []
        st.session_state.schedule = None  # スケジュールも削除
        st.success("全ての科目とスケジュールを削除しました")
        st.rerun()

if st.session_state.subjects:
    st.subheader("登録済み科目")
    
    # 科目一覧を表示し、削除ボタンを追加
    for i, subject in enumerate(st.session_state.subjects):
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        with col1:
            st.write(f"**{subject['科目']}**")
        with col2:
            st.write(f"難易度: {subject['難易度']}/5")
        with col3:
            st.write(f"テスト日: {subject['テスト日'].strftime('%Y-%m-%d')}")
        with col4:
            if st.button("削除", key=f"delete_{i}", type="secondary"):
                # 科目を削除
                subject_to_delete = st.session_state.subjects[i]['科目']
                del st.session_state.subjects[i]
                
                # 該当科目のスケジュールも削除
                if st.session_state.schedule is not None:
                    # スケジュールから該当科目の行を削除
                    schedule_df = st.session_state.schedule.copy()
                    schedule_df = schedule_df[schedule_df['科目'] != subject_to_delete]
                    
                    # スケジュールが空になったらNoneに設定
                    if schedule_df.empty:
                        st.session_state.schedule = None
                    else:
                        st.session_state.schedule = schedule_df
                
                st.success(f"科目「{subject_to_delete}」と関連スケジュールを削除しました")
                st.rerun()
    
    # データフレームでも表示（列の表示をオフ）
    st.dataframe(pd.DataFrame(st.session_state.subjects), use_container_width=True, hide_index=True)

# -----------------------------
# スケジュール生成
# -----------------------------
st.header("② スケジュール生成")
start_date = st.date_input("学習開始日", date.today())


def generate_schedule(subjects, start, wd_h, we_h):
    records = []
    
    # すべての日付に対して処理
    all_days = []
    for subj in subjects:
        days = (subj["テスト日"] - start).days + 1
        if days <= 0:
            continue
        for i in range(days):
            d = start + timedelta(days=i)
            if d not in all_days:
                all_days.append(d)
    
    # 各日付ごとに処理
    for current_date in sorted(all_days):
        is_weekend = current_date.weekday() >= 5
        max_study_hours = we_h if is_weekend else wd_h
        
        # その日に学習すべき科目を特定
        day_subjects = []
        for subj in subjects:
            if start <= current_date <= subj["テスト日"]:
                days_left = (subj["テスト日"] - current_date).days
                
                # 強度計算
                if days_left <= 3:
                    intensity = 1.5
                elif days_left <= 7:
                    intensity = 1.2
                else:
                    intensity = 1.0
                
                day_subjects.append({
                    "科目": subj["科目"],
                    "難易度": subj["難易度"],
                    "強度": intensity,
                    "テスト日": subj["テスト日"],
                    "相対重み": subj["難易度"] * intensity
                })
        
        if not day_subjects:
            continue
        
        # 総重みを計算
        total_weight = sum([subj["相対重み"] for subj in day_subjects])
        
        # 各科目に学習時間を割り当て（合計がmax_study_hours以内になるように）
        assigned_hours = {}
        
        # 各科目に基本時間を割り当て
        for subj in day_subjects:
            weight_ratio = subj["相対重み"] / total_weight
            assigned = round(weight_ratio * max_study_hours, 2)
            # 最低0.1時間は確保
            assigned = max(0.1, assigned)
            assigned_hours[subj["科目"]] = assigned
        
        # 合計がmax_study_hoursを超える場合は調整
        total_assigned = sum(assigned_hours.values())
        if total_assigned > max_study_hours:
            # 比例配分で調整
            adjustment_factor = max_study_hours / total_assigned
            for subject in assigned_hours:
                assigned_hours[subject] = round(assigned_hours[subject] * adjustment_factor, 2)
        
        # レコード作成（時間から分に変換し、四捨五入）
        for subj in day_subjects:
            study_time_hours = assigned_hours.get(subj["科目"], 0)
            if study_time_hours > 0:
                # 時間から分に変換し、四捨五入
                study_time_minutes = round(study_time_hours * 60)
                records.append({
                    "日付": current_date,
                    "科目": subj["科目"],
                    "予定時間(分)": study_time_minutes,
                    "強度": subj["強度"],
                    "イベント": "テスト" if current_date == subj["テスト日"] else "学習"
                })
    
    return pd.DataFrame(records)


col1, col2 = st.columns(2)
with col1:
    if st.button("📅 スケジュール作成", use_container_width=True) and st.session_state.subjects:
        st.session_state.schedule = generate_schedule(
            st.session_state.subjects, start_date, weekday_hours, weekend_hours
        )
        st.success("スケジュールを作成しました")


# -----------------------------
# 学習スケジュール表
# -----------------------------
if st.session_state.schedule is not None:
    st.header("③ 学習スケジュール表")
    
    df = st.session_state.schedule.copy()
    
    # 日付列をdatetime型に変換
    df["日付"] = pd.to_datetime(df["日付"])
    
    # 強度レベルを表示用に変換
    def intensity_label(x):
        if x < 1.1:
            return "🟢 低"
        elif x < 1.4:
            return "🟠 中"
        else:
            return "🔴 高"
    
    df["強度レベル"] = df["強度"].apply(intensity_label)
    
    # 科目ごとの詳細表
    for subject in df["科目"].unique():
        st.subheader(f"📘 {subject}")
        sdf = df[df["科目"] == subject].copy()
        
        # 日付順にソート
        sdf = sdf.sort_values("日付")
        
        # 日付を文字列に変換して表示
        sdf_display = sdf.copy()
        if pd.api.types.is_datetime64_any_dtype(sdf_display["日付"]):
            sdf_display["日付"] = sdf_display["日付"].dt.strftime("%Y-%m-%d")
        else:
            sdf_display["日付"] = sdf_display["日付"].astype(str)
        
        # テスト日の強調表示
        def highlight_test_day(row):
            if row["イベント"] == "テスト":
                return ["background-color: #FFCCCC"] * len(row)
            return [""] * len(row)
        
        # データフレームを表示（列の表示をオフ）
        st.dataframe(
            sdf_display[["日付", "予定時間(分)", "強度レベル", "イベント"]].style.apply(
                highlight_test_day, axis=1
            ),
            use_container_width=True,
            hide_index=True
        )
        
        # 合計学習時間の表示（分単位）
        total_study_minutes = sdf[sdf["イベント"] == "学習"]["予定時間(分)"].sum()
        # 分から時間と分に変換（120分以上なら時間表示も）
        if total_study_minutes >= 60:
            hours = total_study_minutes // 60
            minutes = total_study_minutes % 60
            if minutes == 0:
                st.info(f"**{subject}の合計学習時間:** {hours}時間 ({total_study_minutes}分)")
            else:
                st.info(f"**{subject}の合計学習時間:** {hours}時間{minutes}分 ({total_study_minutes}分)")
        else:
            st.info(f"**{subject}の合計学習時間:** {total_study_minutes}分")

# -----------------------------
# 今日の学習目標
# -----------------------------
st.header("④ 今日の学習目標")

if st.session_state.schedule is not None:
    today = date.today()
    
    df = st.session_state.schedule.copy()
    df["日付"] = pd.to_datetime(df["日付"])
    
    today_study = df[df["日付"].dt.date == today]
    
    if not today_study.empty:
        total_today_minutes = today_study["予定時間(分)"].sum()
        subjects_today = today_study["科目"].unique()
        
        # 分から時間と分に変換（表示用）
        if total_today_minutes >= 60:
            hours = total_today_minutes // 60
            minutes = total_today_minutes % 60
            if minutes == 0:
                display_time = f"{hours}時間"
            else:
                display_time = f"{hours}時間{minutes}分"
        else:
            display_time = f"{total_today_minutes}分"
        
        st.info(f"**今日の学習目標:** {display_time} ({total_today_minutes}分)")
        
        for subject in subjects_today:
            subject_minutes = today_study[today_study["科目"] == subject]["予定時間(分)"].sum()
            if subject_minutes >= 60:
                hours = subject_minutes // 60
                minutes = subject_minutes % 60
                if minutes == 0:
                    subject_display = f"{hours}時間"
                else:
                    subject_display = f"{hours}時間{minutes}分"
            else:
                subject_display = f"{subject_minutes}分"
            st.write(f"- {subject}: {subject_display}")
    else:
        st.info("今日は学習計画がありません")
else:
    st.info("スケジュールを作成すると、今日の学習目標が表示されます")

# -----------------------------
# 注意事項
# -----------------------------
st.sidebar.header("📝 注意事項")
st.sidebar.info("""
1. 学習計画は目安です。体調に合わせて調整してください。
2. 強度はテストまでの残り日数に応じて自動調整されます。
3. 科目を削除すると、関連するスケジュールも自動的に削除されます。
4. 予定時間は分単位で表示されます。
5. 「全科目クリア」ボタンで全ての科目とスケジュールを削除できます。
""")