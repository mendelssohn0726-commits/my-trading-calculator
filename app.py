import streamlit as st
import pandas as pd

import streamlit as st
import pandas as pd
from PIL import Image  # 이 줄을 맨 위에 추가하세요

# 아이콘 이미지 불러오기
try:
    img = Image.open("icon.png")
except:
    img = "💰" # 이미지가 없을 때를 대비한 비상용 이모지

st.set_page_config(
    page_title="Trading Calculator",
    page_icon=img,            # 이제 이모지 대신 이미지를 아이콘으로 씁니다
    layout="centered",
    initial_sidebar_state="collapsed"
)
# 사이드바 설정 (선택지 대신 버튼 하나로 관리)
if "page" not in st.session_state:
    st.session_state.page = "main"

with st.sidebar:
    st.write("---")
    if st.button("⚙️ 종목 가치 설정"):
        st.session_state.page = "settings"
    if st.button("🏠 계산기로 돌아가기"):
        st.session_state.page = "main"

# 숫자를 깔끔하게 포맷팅하는 함수
def format_num(n):
    if n is None: return ""
    return f"{n:g}"

# --- 메인 계산기 화면 ---
if st.session_state.page == "main":
    st.title("🧮 랏수 계산기")
    
    if "entries" not in st.session_state:
        st.session_state.entries = [{"price": 0.0, "reason": "⚪ nothing", "custom_reason": ""}]
    
    col_input, col_result = st.columns([1, 1.4])

    with col_input:
        st.subheader("💰 투자금")
        seed = st.number_input("내 시드 (USD)", value=None, placeholder="예: 10000", format="%g")
        risk_pct = st.number_input("손실 비중 (%)", value=None, placeholder="예: 2.0", format="%g")
        
        symbol_list = st.session_state.symbol_df["Symbol"].tolist()
        selected_symbol = st.selectbox("거래 종목", symbol_list)
        unit_val = st.session_state.symbol_df.loc[st.session_state.symbol_df["Symbol"] == selected_symbol, "Value"].values[0]

        st.divider()
        st.subheader("📍 진입 계획")
        reasons_list = ["⚪ nothing", "🟡 500 EMA", "🟢 High 20 EMA", "🔵 High 60 EMA", "🟣 High 100 EMA", "🔴 High UBB", "🔴 High LBB", "📝 직접 입력"]
        
        for i, entry in enumerate(st.session_state.entries):
            c1, c2 = st.columns([1.5, 1])
            with c1:
                st.session_state.entries[i]["price"] = st.number_input(
                    f"{i+1}차 진입가", value=None, placeholder="가격 입력", format="%g", key=f"price_{i}"
                )
            with c2:
                st.session_state.entries[i]["reason"] = st.selectbox(
                    f"진입 근거 {i+1}", reasons_list, key=f"reason_{i}"
                )
                if "직접 입력" in st.session_state.entries[i]["reason"]:
                    st.session_state.entries[i]["custom_reason"] = st.text_input(f"내용 입력 {i+1}", key=f"custom_{i}")

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("+ 진입 추가"):
                st.session_state.entries.append({"price": 0.0, "reason": "⚪ nothing", "custom_reason": ""})
                st.rerun()
        with bc2:
            if len(st.session_state.entries) > 1 and st.button("- 마지막 제거"):
                st.session_state.entries.pop()
                st.rerun()

        st.write("---")
        stop_loss = st.number_input("⛔ 손절가 (최종)", value=None, placeholder="손절 가격 입력", format="%g")

    with col_result:
        st.subheader("📑 계산 결과 및 탈출 전략")
        
        all_prices = [e["price"] for e in st.session_state.entries]
        ready = seed and risk_pct and stop_loss and all(p is not None and p != 0 for p in all_prices)
        
        if ready:
            lots_ratio = [1.0] 
            if len(all_prices) > 1:
                lots_ratio.append(1.0) 
                target_profit_unit = abs(all_prices[0] - all_prices[1]) * unit_val
                for n in range(2, len(all_prices)):
                    prev_loss_sum = sum(lots_ratio[j] * abs(all_prices[j] - all_prices[n-1]) * unit_val for j in range(n))
                    needed_lot = (target_profit_unit + prev_loss_sum) / (abs(all_prices[n-1] - all_prices[n]) * unit_val)
                    lots_ratio.append(needed_lot)

            total_loss_unit = sum(lots_ratio[i] * abs(all_prices[i] - stop_loss) * unit_val for i in range(len(all_prices)))
            base_lot = (seed * (risk_pct / 100)) / total_loss_unit
            
            for i, e in enumerate(st.session_state.entries):
                current_lot = base_lot * lots_ratio[i]
                display_reason = e["custom_reason"] if "직접 입력" in e["reason"] else e["reason"]
                
                with st.expander(f"📌 {i+1}차 진입: {format_num(round(current_lot, 3))} 랏", expanded=True):
                    c1, c2 = st.columns([1, 2])
                    c1.metric("가격", format_num(e['price']))
                    c2.write(f"**근거:** {display_reason}")
                    
                    if i >= 1:
                        st.markdown("**반등 시 목표 수익**")
                        scenario_cols = st.columns(min(i, 4))
                        for k in range(i):
                            target_p = all_prices[k]
                            total_profit = sum((base_lot * lots_ratio[j]) * ((target_p - all_prices[j]) if all_prices[0] > stop_loss else (all_prices[j] - target_p)) * unit_val for j in range(i + 1))
                            with scenario_cols[k % len(scenario_cols)]:
                                st.caption(f"To {k+1}차")
                                st.write(f"**${format_num(round(total_profit, 2))}**")

            st.divider()
            st.success(f"**최대 손실:** ${format_num(round(seed*(risk_pct/100), 2))} | **목표 수익:** ${format_num(round(base_lot*abs(all_prices[0]-all_prices[1])*unit_val, 2))}")
        else:
            st.info("시드, 비중, 가격들을 입력하면 계산 결과가 여기에 표시됩니다.")

# --- 설정 화면 ---
elif st.session_state.page == "settings":
    st.title("⚙️ 종목별 1단위 가치 설정")
    st.write("사용하시는 증권사에 맞게 1랏당 1포인트 가치를 수정하세요.")
    
    # column_config를 사용하여 Value 열을 왼쪽 정렬(left)로 설정
    st.session_state.symbol_df = st.data_editor(
        st.session_state.symbol_df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Value": st.column_config.NumberColumn(
                "Value",
                alignment="left"  # 이 부분이 핵심입니다!
            )
        }
    )
    
    if st.button("설정 저장"):
        st.success("저장되었습니다.")
