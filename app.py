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
    
    # 1) 파일 읽기
    encodings = ['utf-8', 'cp949', 'euc-kr']
    df = None
    
    for enc in encodings:
        try:
            df = pd.read_csv(file_name, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            return None

    if df is None:
        st.error(f"❌ 파일을 찾을 수 없습니다: {file_name}")
        st.warning("같은 폴더에 csv 파일이 있는지 확인해주세요.")
        return None

    # 2) 데이터 전처리 (Wide -> Long 변환)
    possible_ids = ['통계표', '계정항목', '측정항목', '단위', '변환']
    id_vars = [col for col in possible_ids if col in df.columns]
    date_cols = [col for col in df.columns if col not in id_vars]

    df_melted = df.melt(
        id_vars=id_vars, 
        value_vars=date_cols,
        var_name='날짜', 
        value_name='환율'
    )

    # 3) 데이터 정제
    # 콤마 제거
    df_melted['환율'] = df_melted['환율'].astype(str).str.replace(',', '')
    
    # 숫자로 변환 (에러나 빈 값은 NaN으로 변환)
    df_melted['환율'] = pd.to_numeric(df_melted['환율'], errors='coerce')
    
    # [추가된 부분] 환율 값이 없는 행(NaN)은 아예 삭제
    # 이렇게 하면 데이터가 비어있는 '독일마르크', '프랑스프랑'은 목록에서 자동으로 사라집니다.
    df_melted = df_melted.dropna(subset=['환율'])
    
    # 날짜 변환 및 정렬
    df_melted['날짜_dt'] = pd.to_datetime(df_melted['날짜'], format='%Y/%m', errors='coerce')
    df_melted = df_melted.dropna(subset=['날짜_dt'])
    df_melted = df_melted.sort_values('날짜_dt')

    return df_melted

# -----------------------------------------------------------------------------
# 3. 메인 앱 로직
# -----------------------------------------------------------------------------
df = load_and_preprocess_data()

if df is not None and not df.empty:
    # --- 사이드바 필터 ---
    st.sidebar.header("검색 옵션")
    
    # 1. 통화 선택 (데이터가 있는 통화만 자동으로 뜹니다)
    if '계정항목' in df.columns:
        currency_list = df['계정항목'].unique()
        
        # 기본값 설정: '미국달러' 우선
        default_currency = [c for c in currency_list if '미국달러' in str(c)]
        default_index = list(currency_list).index(default_currency[0]) if default_currency else 0

        selected_currency = st.sidebar.selectbox(
            "통화를 선택하세요:",
            currency_list,
            index=default_index
        )
    
    # 2. 측정 항목 선택
    if '측정항목' in df.columns:
        measure_list = df['측정항목'].unique()
        selected_measure = st.sidebar.multiselect(
            "측정 기준을 선택하세요:",
            measure_list,
            default=measure_list
        )
    else:
        selected_measure = []

    # --- 데이터 필터링 ---
    mask = (df['계정항목'] == selected_currency)
    if selected_measure:
        mask = mask & (df['측정항목'].isin(selected_measure))
        
    filtered_df = df[mask]

    # --- 시각화 ---
    if not filtered_df.empty:
        st.subheader(f"📈 {selected_currency} 환율 추이")
        
        fig = px.line(
            filtered_df,
            x='날짜',
            y='환율',
            color='측정항목' if '측정항목' in df.columns else None,
            markers=True,
            title=f"{selected_currency} 변동 그래프",
            labels={'환율': '환율(원)', '날짜': '기간'},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        recent_row = filtered_df.iloc[-1] 
        
        try:
            with col1:
                st.metric("최근 환율", f"{recent_row['환율']:,.2f} 원", f"기준: {recent_row['날짜']}")
            with col2:
                st.metric("기간 내 최저", f"{filtered_df['환율'].min():,.2f} 원")
            with col3:
                st.metric("기간 내 최고", f"{filtered_df['환율'].max():,.2f} 원")
        except:
             st.info("통계 값을 계산할 수 없습니다.")
            
        with st.expander("📋 상세 데이터 보기"):
            cols_to_show = ['날짜', '계정항목', '측정항목', '환율', '단위']
            final_cols = [c for c in cols_to_show if c in filtered_df.columns]
            st.dataframe(
                filtered_df[final_cols].sort_values('날짜', ascending=False),
                use_container_width=True
            )
    else:
        st.warning("선택한 조건에 맞는 데이터가 없습니다.")

else:
    # 데이터가 아예 없거나 로드 실패 시
    if df is not None: 
        st.warning("표시할 데이터가 없습니다.")
