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

# 사이드바 메뉴
menu = st.sidebar.radio("메뉴", ["계산기", "⚙️ 설정"])

if menu == "계산기":
    st.title("🌊 분할 진입(물타기) 전략 계산기")
    
    # 세션 상태로 진입 가격 리스트 관리
    if "entries" not in st.session_state:
        st.session_state.entries = [{"price": 0.0, "reason": "nothing", "custom_reason": ""}]
    
    col_input, col_result = st.columns([1, 1.2])

    with col_input:
        st.subheader("1. 자산 정보")
        seed = st.number_input("총 시드 (USD)", value=None, placeholder="예: 10000.0")
        risk_pct = st.number_input("총 손실 비율 (%)", value=None, placeholder="예: 2.0")
        
        symbol_list = st.session_state.symbol_df["Symbol"].tolist()
        selected_symbol = st.selectbox("종목 선택", symbol_list)
        unit_val = st.session_state.symbol_df.loc[st.session_state.symbol_df["Symbol"] == selected_symbol, "Value"].values[0]

        st.divider()
        st.subheader("2. 진입 및 손절가 설정")
        reasons = ["nothing", "High Bollinger band", "500 EMA", "High 20 EMA", "High 60 EMA", "High 100 EMA", "High UBB", "High LBB", "직접 입력"]
        
        # 진입가 입력 루프
        for i, entry in enumerate(st.session_state.entries):
            c1, c2 = st.columns([1.5, 1])
            with c1:
                st.session_state.entries[i]["price"] = st.number_input(f"{i+1}차 진입 가격", value=None, placeholder="0.0", format="%.5f", key=f"price_{i}")
            with c2:
                st.session_state.entries[i]["reason"] = st.selectbox(f"근거 {i+1}", reasons, key=f"reason_{i}")
                # '직접 입력' 선택 시 텍스트 입력창 등장
                if st.session_state.entries[i]["reason"] == "직접 입력":
                    st.session_state.entries[i]["custom_reason"] = st.text_input(f"직접 입력 {i+1}", key=f"custom_{i}", placeholder="내용 입력")

        # 버튼 배치를 위한 컬럼
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("+ 진입 추가"):
                st.session_state.entries.append({"price": 0.0, "reason": "nothing", "custom_reason": ""})
                st.rerun()
        with bc2:
            if len(st.session_state.entries) > 1 and st.button("- 마지막 제거"):
                st.session_state.entries.pop()
                st.rerun()

        # 진입가 설정이 모두 끝난 뒤 하단에 손절 가격 배치
        st.write("---")
        stop_loss = st.number_input("⛔ 최종 손절 가격", value=None, placeholder="여기에 손절가를 입력하세요", format="%.5f")

    with col_result:
        st.subheader("3. 전략 상세 리스트")
        
        # 유효성 검사 (시드, 비율, 손절가, 모든 진입가가 입력되었는지 확인)
        all_prices_entered = all(e["price"] is not None and e["price"] != 0 for e in st.session_state.entries)
        ready = seed and risk_pct and stop_loss and all_prices_entered
        
        if ready:
            prices = [e["price"] for e in st.session_state.entries]
            
            # 수학적 계산 (랏수 비율 산출)
            lots_ratio = [1.0] 
            if len(prices) > 1:
                lots_ratio.append(1.0) # 1차와 2차 랏수 동일
                # 기준 수익금 (L=1일 때 2차 진입 후 1차 가격 반등 시 수익)
                target_profit_unit = abs(prices[0] - prices[1]) * unit_val
                
                for n in range(2, len(prices)):
                    # n+1차 랏수 계산
                    # 이전 포지션들이 n-1차 가격에 도달했을 때의 합산 손익 계산
                    prev_loss_sum = 0
                    for j in range(n):
                        prev_loss_sum += lots_ratio[j] * (prices[j] - prices[n-1]) * unit_val * (1 if prices[0] > stop_loss else -1)
                    
                    # n차 포지션이 n-1차 가격에서 만들어야 할 수익 = 목표수익 + 이전 손실 복구
                    # (실제 계산 시 방향성에 관계 없이 절댓값으로 처리하기 위해 로직 단순화)
                    needed_lot = (target_profit_unit + abs(prev_loss_sum)) / (abs(prices[n-1] - prices[n]) * unit_val)
                    lots_ratio.append(needed_lot)

            # 전체 손실액 합산 (L=1일 때)
            total_loss_unit = sum(lots_ratio[i] * abs(prices[i] - stop_loss) * unit_val for i in range(len(prices)))
            
            # 최종 1차 랏수 결정
            total_allowed_risk = seed * (risk_pct / 100)
            base_lot = total_allowed_risk / total_loss_unit
            
            # 결과 테이블 데이터 준비
            res_data = []
            for i, e in enumerate(st.session_state.entries):
                actual_lot = base_lot * lots_ratio[i]
                final_reason = e["custom_reason"] if e["reason"] == "직접 입력" else e["reason"]
                res_data.append({
                    "차수": f"{i+1}차",
                    "진입가": f"{e['price']:,.5f}",
                    "진입 랏수": f"**{actual_lot:.3f}**",
                    "근거": final_reason
                })
            
            st.table(pd.DataFrame(res_data))
            
            # 요약 섹션
            st.success(f"✅ **총 리스크(손절 시):** ${total_allowed_risk:,.2f} ({risk_pct}%)")
            st.info(f"💰 **반등 성공 시 목표 수익:** ${base_lot * abs(prices[0]-prices[1]) * unit_val:,.2f}")
            st.markdown(f"**[전략 가이드]**")
            st.write(f"- 가격이 밀려 {len(prices)}차까지 체결된 후, **{prices[-2]:,.5f}**까지 반등하면 모든 포지션을 정리하세요.")
            st.write(f"- 그러면 2차 진입 시 기대했던 수익금인 **${base_lot * abs(prices[0]-prices[1]) * unit_val:,.2f}**을 얻게 됩니다.")
            
        else:
            st.warning("⚠️ 왼쪽의 모든 입력 칸(시드, 리스크, 진입가, 손절가)을 채워주세요.")

elif menu == "⚙️ 설정":
    st.title("⚙️ 종목 가치 설정")
    edited_df = st.data_editor(st.session_state.symbol_df, num_rows="dynamic", use_container_width=True)
    if st.button("설정 저장"):
        st.session_state.symbol_df = edited_df
        st.success("종목 설정이 저장되었습니다.")
