import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="주요국 원화 환율 대시보드",
    page_icon="💱",
    layout="wide"
)

st.title("💱 주요국 통화 대원화 환율 흐름")
st.markdown("한국은행/통계청 데이터를 기반으로 **주요국 통화의 환율 변동 추이**를 시각화합니다.")

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 함수
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_preprocess_data():
    file_name = "주요국 통화의 대원화환율_16153917.csv"
    
    # 1) 파일 읽기 (인코딩 자동 감지)
    encodings = ['utf-8', 'cp949', 'euc-kr']
    df = None
    
    for enc in encodings:
        try:
            # csv 파일 읽기
            df = pd.read_csv(file_name, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            st.error(f"❌ 파일을 찾을 수 없습니다: {file_name}")
            return None

    if df is None:
        st.error("파일을 읽는 데 실패했습니다. 인코딩을 확인해주세요.")
        return None

    # 2) 데이터 전처리 (Wide -> Long 변환)
    # 데이터 형태를 보니 1행부터 5행까지는 정보이고, 6행(인덱스 5)부터가 날짜 데이터입니다.
    # '계정항목'이 통화명, '측정항목'이 데이터 타입(평균/말일)입니다.
    
    # 고정된 컬럼(식별자)
    id_vars = ['계정항목', '측정항목', '단위', '변환']
    # 날짜 컬럼(값) - 데이터프레임에 실제 존재하는 컬럼만 추려냅니다.
    existing_ids = [col for col in id_vars if col in df.columns]
    date_cols = [col for col in df.columns if col not in existing_ids and col != '통계표']

    # Melt 수행 (가로로 긴 데이터를 세로로 변환)
    df_melted = df.melt(
        id_vars=existing_ids, 
        value_vars=date_cols,
        var_name='날짜', 
        value_name='환율'
    )

    # 3) 데이터 정제
    # 환율 값에서 콤마(,) 제거하고 숫자로 변환
    df_melted['환율'] = df_melted['환율'].astype(str).str.replace(',', '')
    df_melted['환율'] = pd.to_numeric(df_melted['환율'], errors='coerce')
    
    # 날짜 형식 변환 (정렬을 위해)
    # 2024/12 같은 형식을 datetime 객체로 변환
    df_melted['날짜_dt'] = pd.to_datetime(df_melted['날짜'], format='%Y/%m', errors='coerce')
    df_melted = df_melted.sort_values('날짜_dt')

    return df_melted

# -----------------------------------------------------------------------------
# 3. 메인 앱 로직
# -----------------------------------------------------------------------------
df = load_and_preprocess_data()

if df is not None:
    # --- 사이드바 필터 ---
    st.sidebar.header("검색 옵션")
    
    # 1. 통화 선택
    currency_list = df['계정항목'].unique()
    # 기본값으로 '원/미국달러'가 있으면 선택, 없으면 첫 번째 것
    default_currency = [c for c in currency_list if '미국달러' in c]
    if not default_currency:
        default_currency = [currency_list[0]]
        
    selected_currency = st.sidebar.selectbox(
        "통화를 선택하세요:",
        currency_list,
        index=list(currency_list).index(default_currency[0])
    )
    
    # 2. 측정 항목 선택 (평균자료 vs 말일자료)
    measure_list = df['측정항목'].unique()
    selected_measure = st.sidebar.multiselect(
        "측정 기준을 선택하세요:",
        measure_list,
        default=measure_list  # 기본적으로 모두 선택
    )

    # --- 데이터 필터링 ---
    # 선택한 통화와 측정 기준에 맞는 데이터만 추출
    filtered_df = df[
        (df['계정항목'] == selected_currency) & 
        (df['측정항목'].isin(selected_measure))
    ]

    # --- 시각화 ---
    if not filtered_df.empty:
        # 1. 라인 차트
        st.subheader(f"📈 {selected_currency} 환율 추이")
        
        fig = px.line(
            filtered_df,
            x='날짜',
            y='환율',
            color='측정항목',
            markers=True,
            title=f"{selected_currency} 변동 그래프",
            labels={'환율': '환율(원)', '날짜': '기간'},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        # 2. 주요 통계 요약
        col1, col2, col3 = st.columns(3)
        recent_data = filtered_df.iloc[-1] # 가장 최근 데이터
        min_rate = filtered_df['환율'].min()
        max_rate = filtered_df['환율'].max()
        
        with col1:
            st.metric("최근 환율", f"{recent_data['환율']:,.2f} 원", f"기준: {recent_data['날짜']}")
        with col2:
            st.metric("기간 내 최저", f"{min_rate:,.2f} 원")
        with col3:
            st.metric("기간 내 최고", f"{max_rate:,.2f} 원")
            
        # 3. 상세 데이터 표
        with st.expander("📋 상세 데이터 보기"):
            # 보기 좋게 컬럼 정리
            display_cols = ['날짜', '계정항목', '측정항목', '환율', '단위']
            st.dataframe(
                filtered_df[display_cols].sort_values('날짜', ascending=False),
                use_container_width=True
            )
            
    else:
        st.warning("선택한 조건에 맞는 데이터가 없습니다.")

else:
    st.info("데이터를 불러오는 중입니다...")

    