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

st.set_page_config(page_title="분할 진입 계산기", layout="wide")

# 입력 편의를 위한 커스텀 숫자 입력 함수 (클릭 시 0 초기화)
def auto_clean_number_input(label, value=0.0, step=0.01, format="%.2f", key=None):
    return st.number_input(label, value=None, placeholder=str(value), step=step, format=format, key=key)

# 사이드바 메뉴
menu = st.sidebar.radio("메뉴", ["계산기", "⚙️ 설정"])

if menu == "계산기":
    st.title("🌊 분할 진입(물타기) 전략 계산기")
    
    # 세션 상태로 진입 가격 리스트 관리
    if "entries" not in st.session_state:
        st.session_state.entries = [{"price": 0.0, "reason": "nothing"}]
    
    col_input, col_result = st.columns([1, 1.2])

    with col_input:
        st.subheader("1. 기본 정보")
        seed = st.number_input("총 시드 (USD)", value=None, placeholder="10000.0")
        risk_pct = st.number_input("총 손실 비율 (%)", value=None, placeholder="2.0")
        stop_loss = st.number_input("최종 손절 가격", value=None, placeholder="0.0", format="%.5f")
        
        symbol_list = st.session_state.symbol_df["Symbol"].tolist()
        selected_symbol = st.selectbox("종목 선택", symbol_list)
        unit_val = st.session_state.symbol_df.loc[st.session_state.symbol_df["Symbol"] == selected_symbol, "Value"].values[0]

        st.divider()
        st.subheader("2. 차수별 진입가")
        reasons = ["nothing", "High Bollinger band", "500 EMA", "High 20 EMA", "High 60 EMA", "High 100 EMA", "High UBB", "High LBB", "직접 입력"]
        
        for i, entry in enumerate(st.session_state.entries):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.session_state.entries[i]["price"] = st.number_input(f"{i+1}차 진입 가격", value=None, placeholder="0.0", format="%.5f", key=f"price_{i}")
            with c2:
                st.session_state.entries[i]["reason"] = st.selectbox(f"근거 {i+1}", reasons, key=f"reason_{i}")

        if st.button("+ 진입 차수 추가"):
            st.session_state.entries.append({"price": 0.0, "reason": "nothing"})
            st.rerun()
        if len(st.session_state.entries) > 1 and st.button("- 마지막 차수 제거"):
            st.session_state.entries.pop()
            st.rerun()

    with col_result:
        st.subheader("3. 전략 상세 리스트")
        
        # 유효성 검사
        ready = seed and risk_pct and stop_loss and all(e["price"] for e in st.session_state.entries)
        
        if ready:
            prices = [e["price"] for e in st.session_state.entries]
            is_long = prices[0] > stop_loss
            
            # 수학적 계산 시작
            # 1. 1차와 2차의 랏수는 같음 (L1 = L2)
            # 2. n차 반등 수익: (Sum of Lots up to n) * (P_{n-1} - P_n) * UnitVal - (Total Loss of previous lots) = TargetProfit
            # 3. 최종 손절 시 총 손실 = Seed * Risk%
            
            # 여기서 1차 랏수(L)를 변수로 두고 모든 관계를 L에 대한 식으로 정리하여 역산
            # 최종 손실액 = sum(Lot_i * abs(Price_i - StopLoss) * UnitVal)
            
            # 간단한 선형 방정식 풀이
            # L_1 = L, L_2 = L
            # L_3 * (P2 - P3) * UnitVal - L1*(P1-P2)*UnitVal - L2*(P2-P2)*UnitVal = L1*(P1-P2)*UnitVal (목표수익)
            # 이런 식으로 각 랏수는 L의 배수가 됨.
            
            lots_ratio = [1.0] # 1차 랏수를 1이라고 가정했을 때의 비율
            if len(prices) > 1:
                lots_ratio.append(1.0) # 2차는 1차와 동일
                target_profit_unit = abs(prices[0] - prices[1]) * unit_val # 2차가 반등했을 때의 기준 수익(L=1일때)
                
                for n in range(2, len(prices)):
                    # n+1차 랏수 계산 (인덱스로는 n)
                    # 이전 차수들의 손실 합 (n-1차 가격 기준)
                    prev_loss_sum = 0
                    for j in range(n):
                        prev_loss_sum += lots_ratio[j] * (abs(prices[j] - prices[n-1])) * unit_val
                    
                    # n차 랏수가 만들어야 할 수익 = 목표수익 + 이전 손실 복구
                    needed_lot = (target_profit_unit + prev_loss_sum) / (abs(prices[n-1] - prices[n]) * unit_val)
                    lots_ratio.append(needed_lot)

            # 전체 손실 합산 (L=1일 때)
            total_loss_unit = sum(lots_ratio[i] * abs(prices[i] - stop_loss) * unit_val for i in range(len(prices)))
            
            # 실제 1차 랏수(base_lot) 결정
            total_allowed_risk = seed * (risk_pct / 100)
            base_lot = total_allowed_risk / total_loss_unit
            
            # 결과 테이블 데이터 준비
            res_data = []
            for i, (p, r) in enumerate(zip(prices, [e["reason"] for e in st.session_state.entries])):
                actual_lot = base_lot * lots_ratio[i]
                res_data.append({
                    "차수": f"{i+1}차",
                    "진입가": f"{p:,.5f}",
                    "진입 랏수": f"{actual_lot:.3f}",
                    "근거": r
                })
            
            st.table(pd.DataFrame(res_data))
            
            # 요약 정보
            st.success(f"✅ **총 리스크 금액:** ${total_allowed_risk:,.2f}")
            st.info(f"💡 **탈출 성공 시 목표 수익:** ${base_lot * abs(prices[0]-prices[1]) * unit_val:,.2f}")
            st.warning(f"⚠️ **주의:** 모든 차수가 체결된 후 {stop_loss:,.5f} 도달 시 위 리스크 금액만큼 손실이 확정됩니다.")
        else:
            st.write("모든 필드(시드, 비율, 손절가, 진입가)를 입력하면 자동으로 계산됩니다.")

elif menu == "⚙️ 설정":
    st.title("⚙️ 종목 가치 설정")
    edited_df = st.data_editor(st.session_state.symbol_df, num_rows="dynamic", use_container_width=True)
    if st.button("설정 저장"):
        st.session_state.symbol_df = edited_df
        st.success("저장되었습니다.")
