import streamlit as st
import pandas as pd

# 1. 초기 종목 데이터 설정
DEFAULT_SYMBOLS = [
    {"Symbol": "US100", "Value": 20.0},
    {"Symbol": "JPN225", "Value": 0.63},
    {"Symbol": "UK100", "Value": 1.361},
    {"Symbol": "DAX40", "Value": 1.177},
    {"Symbol": "XAUUSD", "Value": 100.0},
    {"Symbol": "XAGUSD", "Value": 5000.0},
    {"Symbol": "WTI", "Value": 1000.0},
    {"Symbol": "EURUSD", "Value": 100000.0},
    {"Symbol": "USDJPY", "Value": 635.596},
    {"Symbol": "BTCUSD", "Value": 1.0}
]

# 세션 상태에 종목 리스트 저장 (수정 가능하도록)
if "symbol_df" not in st.session_state:
    st.session_state.symbol_df = pd.DataFrame(DEFAULT_SYMBOLS)

st.set_page_config(page_title="트레이딩 포지션 사이징", layout="wide")

# 사이드바 메뉴
menu = st.sidebar.radio("메뉴", ["계산기", "⚙️ 종목 및 증권사 설정"])

# --- 메뉴 1: 계산기 ---
if menu == "계산기":
    st.title("📈 포지션 진입 랏수 계산기")
    
    col_input, col_result = st.columns([1, 1])

    with col_input:
        st.subheader("1. 정보 입력")
        
        # 종목 선택 (설정에서 저장된 리스트 불러오기)
        symbol_list = st.session_state.symbol_df["Symbol"].tolist()
        selected_symbol = st.selectbox("종목 선택", symbol_list)
        
        # 선택된 종목의 1단위 가치 가져오기
        unit_value = st.session_state.symbol_df.loc[
            st.session_state.symbol_df["Symbol"] == selected_symbol, "Value"
        ].values[0]
        
        st.caption(f"ℹ️ 선택된 종목의 1랏당 1포인트 가치: ${unit_value:,.4f}")

        seed = st.number_input("총 시드 (USD)", min_value=0.0, value=10000.0, step=100.0)
        risk_pct = st.number_input("리스크 비율 (%)", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
        entry_price = st.number_input("진입 가격", min_value=0.0, value=0.0, format="%.5f")
        stop_loss = st.number_input("손절 가격", min_value=0.0, value=0.0, format="%.5f")

    with col_result:
        st.subheader("2. 계산 결과")
        
        if st.button("진입 랏수 계산하기"):
            price_diff = abs(entry_price - stop_loss)
            
            if price_diff == 0:
                st.error("진입가와 손절가가 동일할 수 없습니다.")
            elif entry_price == 0 or stop_loss == 0:
                st.warning("진입가와 손절가를 입력해주세요.")
            else:
                # 손실 허용 금액
                risk_amount = seed * (risk_pct / 100)
                
                # 랏수 계산 공식: 손실액 / (가격차이 * 포인트가치)
                lot_size = risk_amount / (price_diff * unit_value)
                
                # 시각적 결과 표시
                st.info(f"선택 종목: **{selected_symbol}**")
                
                c1, c2 = st.columns(2)
                c1.metric("허용 손실 ($)", f"$ {risk_amount:,.2f}")
                c2.metric("가격 변동폭", f"{price_diff:,.5f}")
                
                st.success(f"🔥 추천 진입 랏수: **{lot_size:.3f} 랏**")
                st.write(f"---")
                st.markdown(f"""
                - **원리:** {lot_size:.3f} 랏으로 진입 시, 가격이 {price_diff:,.5f} 만큼 반대로 움직여 손절가에 도달하면 정확히 시드의 {risk_pct}%인 **${risk_amount:,.2f}**가 손실됩니다.
                """)

# --- 메뉴 2: 설정 ---
elif menu == "⚙️ 종목 및 증권사 설정":
    st.title("⚙️ 종목 및 가치 설정")
    st.write("브로커(증권사)에 따라 1랏당 1단위 변동 시 손익이 다를 경우 여기서 수정하세요.")
    
    # 데이터 에디터 (표 형식으로 바로 수정 가능)
    edited_df = st.data_editor(
        st.session_state.symbol_df, 
        num_rows="dynamic",  # 행 추가/삭제 가능
        use_container_width=True,
        column_config={
            "Symbol": st.column_config.TextColumn("종목명 (예: US100)"),
            "Value": st.column_config.NumberColumn("1랏/1단위 변동 가치 ($)", format="$ %.4f")
        }
    )
    
    if st.button("설정 저장하기"):
        st.session_state.symbol_df = edited_df
        st.success("설정이 저장되었습니다! 이제 '계산기' 메뉴에서 확인하세요.")
        st.balloons()

    with st.expander("❓ 설정 방법 도움말"):
        st.write("""
        1. **수정:** 표의 숫자를 클릭해서 직접 수정하세요.
        2. **추가:** 표 하단의 '+' 버튼을 눌러 새 종목을 만드세요.
        3. **삭제:** 행 왼쪽의 체크박스를 누르고 'Delete' 키를 누르세요.
        4. **저장:** 반드시 아래 '설정 저장하기' 버튼을 눌러야 반영됩니다.
        """)
