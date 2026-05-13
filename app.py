import streamlit as st
import pandas as pd

# 1. 초기 종목 데이터 설정
if "symbol_df" not in st.session_state:
    st.session_state.symbol_df = pd.DataFrame([
        {"Symbol": "US100", "Value": 20.0}, {"Symbol": "JPN225", "Value": 0.63},
        {"Symbol": "UK100", "Value": 1.361}, {"Symbol": "DAX40", "Value": 1.177},
        {"Symbol": "XAUUSD", "Value": 100.0}, {"Symbol": "XAGUSD", "Value": 5000.0},
        {"Symbol": "WTI", "Value": 1000.0}, {"Symbol": "EURUSD", "Value": 100000.0},
        {"Symbol": "USDJPY", "Value": 635.596}, {"Symbol": "BTCUSD", "Value": 1.0}
    ])

st.set_page_config(page_title="분할 진입 계산기 Pro", layout="wide")

# 숫자를 깔끔하게 포맷팅하는 함수
def format_num(n):
    if n is None: return ""
    return f"{n:g}" # 불필요한 0 제거 포맷

if menu := st.sidebar.radio("메뉴", ["계산기", "⚙️ 설정"]):

    if menu == "계산기":
        st.title("🌊 전략적 분할 진입 시뮬레이터")
        
        if "entries" not in st.session_state:
            st.session_state.entries = [{"price": 0.0, "reason": "⚪ nothing", "custom_reason": ""}]
        
        col_input, col_result = st.columns([1, 1.4])

        with col_input:
            st.subheader("1. 기본 자산 정보")
            seed = st.number_input("총 시드 (USD)", value=None, placeholder="예: 10000")
            risk_pct = st.number_input("총 손실 비율 (%)", value=None, placeholder="예: 2.0")
            
            symbol_list = st.session_state.symbol_df["Symbol"].tolist()
            selected_symbol = st.selectbox("종목 선택", symbol_list)
            unit_val = st.session_state.symbol_df.loc[st.session_state.symbol_df["Symbol"] == selected_symbol, "Value"].values[0]

            st.divider()
            st.subheader("2. 진입/근거 설정")
            # 항목 선택 시 색상 구분을 위한 이모지 추가
            reasons_map = {
                "⚪ nothing": "grey",
                "🟡 500 EMA": "orange",
                "🟢 High 20 EMA": "green",
                "🔵 High 60 EMA": "blue",
                "🟣 High 100 EMA": "purple",
                "🔴 High UBB": "red",
                "🔴 High LBB": "red",
                "📝 직접 입력": "white"
            }
            reasons_list = list(reasons_map.keys())
            
            for i, entry in enumerate(st.session_state.entries):
                c1, c2 = st.columns([1.5, 1])
                with c1:
                    # step을 0으로 설정하여 자동 소수점 생성을 방지하고, format을 %g로 지정
                    st.session_state.entries[i]["price"] = st.number_input(
                        f"{i+1}차 가격", value=None, placeholder="입력하세요", format="%g", key=f"price_{i}"
                    )
                with c2:
                    st.session_state.entries[i]["reason"] = st.selectbox(
                        f"근거 {i+1}", reasons_list, key=f"reason_{i}"
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
            stop_loss = st.number_input("⛔ 최종 손절 가격", value=None, placeholder="최종 데드라인", format="%g")

        with col_result:
            st.subheader("3. 실행 리스트 및 반등 수익 시나리오")
            
            all_prices = [e["price"] for e in st.session_state.entries]
            ready = seed and risk_pct and stop_loss and all(p is not None and p != 0 for p in all_prices)
            
            if ready:
                # 랏수 계산 로직
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
                        c1.metric("진입가", format_num(e['price']))
                        c2.write(f"**근거:** {display_reason}")
                        
                        if i >= 1:
                            st.markdown("**반등 시 예상 수익 (Exit Scenarios)**")
                            scenario_cols = st.columns(min(i, 4))
                            for k in range(i):
                                target_p = all_prices[k]
                                total_profit = sum((base_lot * lots_ratio[j]) * ((target_p - all_prices[j]) if all_prices[0] > stop_loss else (all_prices[j] - target_p)) * unit_val for j in range(i + 1))
                                
                                with scenario_cols[k % len(scenario_cols)]:
                                    st.caption(f"Target: {k+1}차")
                                    st.write(f"**${format_num(round(total_profit, 2))}**")

                st.divider()
                st.success(f"**총 리스크:** ${format_num(round(seed*(risk_pct/100), 2))} | **기준 수익:** ${format_num(round(base_lot*abs(all_prices[0]-all_prices[1])*unit_val, 2))}")
            else:
                st.info("시드, 리스크, 가격들을 모두 입력하면 상세 전략이 계산됩니다.")

    elif menu == "⚙️ 설정":
        st.title("⚙️ 종목 가치 설정")
        st.session_state.symbol_df = st.data_editor(st.session_state.symbol_df, num_rows="dynamic", use_container_width=True)
        st.button("설정 저장")
