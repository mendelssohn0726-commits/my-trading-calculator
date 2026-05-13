import streamlit as st

# 페이지 제목
st.set_page_config(page_title="해외선물 포지션 계산기", layout="centered")
st.title("📈 해외선물 진입 랏수 계산기")

# 입력 섹션
st.header("1. 정보 입력")
col1, col2 = st.columns(2)

with col1:
    seed = st.number_input("총 시드 (USD)", min_value=0.0, value=10000.0, step=100.0)
    risk_pct = st.number_input("손실 비율 (%)", min_value=0.0, max_value=100.0, value=1.0, step=0.1)

with col2:
    entry_price = st.number_input("진입 가격", min_value=0.0, value=18000.0, step=0.25)
    stop_loss = st.number_input("손절 가격", min_value=0.0, value=17950.0, step=0.25)

# 종목 설정 (나스닥 기본값)
st.sidebar.header("⚙️ 종목별 틱 설정")
tick_value = st.sidebar.number_input("틱 가치 (USD)", value=5.0) # 나스닥(NQ) 마이크로 기준은 0.5, 미니는 5.0
tick_size = st.sidebar.number_input("틱 사이즈 (최소 변동폭)", value=0.25)

# 계산 로직
if st.button("진입 랏수 계산하기"):
    price_diff = abs(entry_price - stop_loss)
    
    if price_diff == 0:
        st.error("진입가와 손절가가 같을 수 없습니다.")
    else:
        # 손실 허용 금액 계산
        risk_amount = seed * (risk_pct / 100)
        # 손절폭을 틱 단위로 변환
        ticks_at_risk = price_diff / tick_size
        # 랏수 계산 (손실액 / (틱수 * 틱가치))
        lot_size = risk_amount / (ticks_at_risk * tick_value)
        
        # 결과 출력
        st.divider()
        st.header("2. 계산 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("허용 손실 ($)", f"$ {risk_amount:,.2f}")
        c2.metric("손절 폭 (틱)", f"{ticks_at_risk:,.0f} 틱")
        c3.metric("추천 진입 랏수", f"{lot_size:.2f} 랏")
        
        st.info(f"💡 {lot_size:.2f} 랏 이하로 진입하면 원금의 {risk_pct}%를 넘지 않게 손절할 수 있습니다.")