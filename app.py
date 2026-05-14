import streamlit as st
import pandas as pd
from PIL import Image

# 1. 초기 종목 데이터 설정
if "symbol_df" not in st.session_state:
    st.session_state.symbol_df = pd.DataFrame([
        {"Symbol": "US100", "Value": 20.0}, {"Symbol": "JPN225", "Value": 0.63},
        {"Symbol": "UK100", "Value": 1.361}, {"Symbol": "DAX40", "Value": 1.177},
        {"Symbol": "XAUUSD", "Value": 100.0}, {"Symbol": "XAGUSD", "Value": 5000.0},
        {"Symbol": "WTI", "Value": 1000.0}, {"Symbol": "EURUSD", "Value": 100000.0},
        {"Symbol": "USDJPY", "Value": 635.596}, {"Symbol": "BTCUSD", "Value": 1.0}
    ])

# 2. 아이콘 설정
try:
    img = Image.open("icon.png")
except:
    img = "💰"

# 3. 페이지 기본 설정 (이름 변경)
st.set_page_config(
    page_title="Trading Calculator",
    page_icon=img,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 4. 숫자를 깔끔하게 포맷팅하는 함수
def format_num(n):
    if n is None: return ""
    return f"{n:g}"

# 5. 사이드바 설정 (화면 이동)
if "page" not in st.session_state:
    st.session_state.page = "main"

with st.sidebar:
    st.write("---")
    if st.button("⚙️ 종목 가치 설정"):
        st.session_state.page = "settings"
    if st.button("🏠 계산기로 돌아가기"):
        st.session_state.page = "main"

# ==========================================
# --- 메인 계산기 화면 ---
# ==========================================
if st.session_state.page == "main":
    st.title("🧮 Trading Calculator")
    
    if "entries" not in st.session_state:
        st.session_state.entries = [{"price": 0.0, "reason": "⚪ nothing", "custom_reason": ""}]
    
    col_input, col_result = st.columns([1, 1])

    with col_input:
        # --- 폼(Form) 내부: 깜빡임 없이 입력하는 구역 ---
        with st.form("calc_form"):
            st.subheader("💰 투자금")
            seed = st.number_input("내 시드 (USD)", value=None, placeholder="예: 10000", format="%g", step=100.0)
            risk_pct = st.number_input("손실 비중 (%)", value=None, placeholder="예: 2.0", format="%g", step=1.0)
            
            symbol_list = st.session_state.symbol_df["Symbol"].tolist()
            selected_symbol = st.selectbox("거래 종목", symbol_list)

            st.divider()
            st.subheader("📍 진입 계획")
            reasons_list = ["⚪ nothing", "🟡 500 EMA", "🟢 High 20 EMA", "🔵 High 60 EMA", "🟣 High 100 EMA", "🔴 High UBB", "🔴 High LBB", "📝 직접 입력"]
            
            prices = []
            reasons = []
            custom_reasons = []
            
            for i in range(len(st.session_state.entries)):
                c1, c2 = st.columns([1, 1.3]) 
                with c1:
                    p = st.number_input(f"{i+1}차 진입가", value=None, placeholder="가격 입력", format="%g", key=f"price_{i}", step=10.0)
                    prices.append(p)
                with c2:
                    r = st.selectbox(f"진입 근거 {i+1}", reasons_list, key=f"reason_{i}")
                    reasons.append(r)
                    if "직접 입력" in r:
                        cr = st.text_input(f"내용 입력 {i+1}", key=f"custom_{i}")
                        custom_reasons.append(cr)
                    else:
                        custom_reasons.append("")

            st.write("---")
            stop_loss = st.number_input("⛔ 손절가 (최종)", value=None, placeholder="손절 가격 입력", format="%g", step=10.0)
            
            # 제출(계산) 버튼
            submitted = st.form_submit_button("🚀 계산하기", type="primary", use_container_width=True)

        # --- 폼(Form) 외부: 차수 조절 버튼을 입력칸 아래로 이동 ---
        st.write(" ") # 약간의 여백
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("➕ 진입 횟수 늘리기", use_container_width=True):
                st.session_state.entries.append({"price": 0.0, "reason": "⚪ nothing", "custom_reason": ""})
                st.rerun()
        with bc2:
            if len(st.session_state.entries) > 1 and st.button("➖ 마지막 제거", use_container_width=True):
                st.session_state.entries.pop()
                st.rerun()

    with col_result:
        st.subheader("📑 계산 결과 및 탈출 전략")
        
        ready = seed and risk_pct and stop_loss and all(p is not None and p != 0 for p in prices)
        
        if ready:
            unit_val = st.session_state.symbol_df.loc[st.session_state.symbol_df["Symbol"] == selected_symbol, "Value"].values[0]
            
            lots_ratio = [1.0] 
            if len(prices) > 1:
                lots_ratio.append(1.0) 
                target_profit_unit = abs(prices[0] - prices[1]) * unit_val
                for n in range(2, len(prices)):
                    prev_loss_sum = sum(lots_ratio[j] * abs(prices[j] - prices[n-1]) * unit_val for j in range(n))
                    needed_lot = (target_profit_unit + prev_loss_sum) / (abs(prices[n-1] - prices[n]) * unit_val)
                    lots_ratio.append(needed_lot)

            total_loss_unit = sum(lots_ratio[i] * abs(prices[i] - stop_loss) * unit_val for i in range(len(prices)))
            base_lot = (seed * (risk_pct / 100)) / total_loss_unit
            
            for i in range(len(prices)):
                current_lot = base_lot * lots_ratio[i]
                display_reason = custom_reasons[i] if "직접 입력" in reasons[i] else reasons[i]
                
                with st.expander(f"📌 {i+1}차 진입: {format_num(round(current_lot, 3))} 랏", expanded=True):
                    c1, c2 = st.columns([1, 2])
                    c1.metric("가격", format_num(prices[i]))
                    c2.write(f"**근거:** {display_reason}")
                    
                    if i >= 1:
                        st.markdown("**반등 시 목표 수익**")
                        scenario_cols = st.columns(min(i, 4))
                        for k in range(i):
                            target_p = prices[k]
                            total_profit = sum((base_lot * lots_ratio[j]) * ((target_p - prices[j]) if prices[0] > stop_loss else (prices[j] - target_p)) * unit_val for j in range(i + 1))
                            with scenario_cols[k % len(scenario_cols)]:
                                st.caption(f"To {k+1}차")
                                st.write(f"**${format_num(round(total_profit, 2))}**")

            st.divider()
            st.success(f"**최대 손실:** ${format_num(round(seed*(risk_pct/100), 2))} | **목표 수익:** ${format_num(round(base_lot*abs(prices[0]-prices[1])*unit_val, 2))}")
        else:
            st.info("입력을 마친 후 [🚀 계산하기] 버튼을 누르면 결과가 표시됩니다.")

# ==========================================
# --- 설정 화면 ---
# ==========================================
elif st.session_state.page == "settings":
    st.title("⚙️ 종목별 1단위 가치 설정")
    st.write("사용하시는 증권사에 맞게 1랏당 1포인트 가치를 수정하세요.")
    
    st.session_state.symbol_df = st.data_editor(
        st.session_state.symbol_df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Value": st.column_config.NumberColumn(
                "Value",
                alignment="left"
            )
        }
    )
    
    if st.button("설정 저장"):
        st.success("저장되었습니다.")
