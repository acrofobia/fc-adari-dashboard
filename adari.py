import streamlit as st
import pandas as pd
import datetime
import altair as alt
import subprocess  # 대시보드 안에서 scraper.py를 실행하기 위한 도구

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="FC 온라인 아다리 민심 대시보드", layout="wide")

st.title("📊 FC 온라인 '아다리/굴절' 감성 지수 대시보드")
st.caption("실제 커뮤니티(인벤, 펨코, 디시, 공홈) 수집 데이터 기반 민심 추적기")
st.markdown("---")

# 2. [기능 추가] 새로고침 버튼 작동 로직
# 버튼을 누르면 대시보드가 직접 터미널 명령어를 내려서 scraper.py를 실행합니다.
if st.button("🔄 실시간 민심 데이터 새로고침 (수집기 실행)", use_container_width=True):
    with st.spinner("🚀 4대 커뮤니티에서 최신 아다리 민심을 긁어오는 중입니다... 잠시만 기다려주세요."):
        try:
            # 터미널에서 python scraper.py를 실행하는 것과 똑같은 명령을 내립니다.
            result = subprocess.run(["python", "scraper.py"], capture_output=True, text=True, check=True)
            st.success("🎯 최신 데이터 수집 완료! 대시보드가 자동으로 갱신됩니다.")
            # 캐시를 날려서 새 데이터를 강제로 읽게 만듭니다.
            st.cache_data.clear()
        except Exception as e:
            st.error(f"❌ 수집기 실행 중 오류 발생: {e}")

st.write("") # 한 줄 띄우기

# 3. 데이터 불러오기 함수 (버그 수정: 캐싱 구조 최적화)
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("adari_data.csv")
        # 날짜 형식 안전하게 변환
        df["날짜"] = pd.to_datetime(df["날짜"]).dt.date
        return df
    except FileNotFoundError:
        return None

df = load_data()

if df is not None:
    # 4. ⭐ [요청 반영] 그래프 상단에 필터 배치하기 (3개의 칸으로 구획 나눔)
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        site = st.selectbox(
            "📡 분석할 커뮤니티", 
            ["전체", "인벤", "에펨코리아", "디시인사이드", "공식홈페이지"]
        )
        
    with filter_col2:
        start_date = st.date_input("📅 조회 시작일", datetime.date(2026, 5, 1))
        
    with filter_col3:
        end_date = st.date_input("📅 조회 종료일", datetime.date(2026, 5, 25))

    # 5. ⭐ [버그 수정] 사용자가 고른 날짜와 사이트대로 데이터를 실시간 필터링
    filtered_df = df[(df["날짜"] >= start_date) & (df["날짜"] <= end_date)]
    if site != "전체":
        filtered_df = filtered_df[filtered_df["사이트"] == site]

    st.markdown(f"📊 현재 조건 만족 데이터: **{len(filtered_df)}건**")
    st.markdown("---")

    # 6. ⭐ [요청 반영] 차트를 중간에 큼직하게 배치
    st.subheader(f"📈 {site} 일별 감성 지수 추이 (1~5점)")
    
    if not filtered_df.empty:
        # 날짜별 평균 점수 계산
        daily_avg = filtered_df.groupby("날짜")["감성점수"].mean().reset_index()
        daily_avg["날짜_표시"] = daily_avg["날짜"].apply(lambda x: x.strftime("%m/%d"))
        
        # 선 그래프 및 포인트 시각화
        chart = alt.Chart(daily_avg).mark_line(point=True, color="#FF4B4B").encode(
            x=alt.X('날짜_표시:N', sort=None, axis=alt.Axis(labelAngle=0), title="날짜"),
            y=alt.Y('감성점수:Q', scale=alt.Scale(domain=[0, 5]), title="평균 감성 점수"),
            tooltip=['날짜_표시', '감성점수']
        ).properties(
            width='container',
            height=350
        )
        st.altair_chart(chart, use_container_width=True)
        
        st.markdown("---")
        
        # 7. 하단에 상세 게시글 목록 배치
        st.subheader("📋 실시간 언급 게시글 리스트 (최신순)")
        st.dataframe(
            filtered_df[["날짜", "사이트", "제목", "감성점수"]].sort_values(by="날짜", ascending=False), 
            use_container_width=True
        )
        
    else:
        st.warning("선택한 기간 및 커뮤니티에 해당하는 데이터가 없습니다. 상단의 날짜나 사이트를 변경해 보세요!")
else:
    st.error("🚨 'adari_data.csv' 파일이 없습니다. 상단의 새로고침 버튼을 눌러 데이터를 먼저 생성해 주세요!")