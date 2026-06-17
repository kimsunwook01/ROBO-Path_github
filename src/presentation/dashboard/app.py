import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from mock_data import get_robots, get_fleet_breakdown, get_missions, get_simulator_status

# --- 설정 및 전역 스타일 ---
st.set_page_config(page_title="ROBO-Path Dashboard", page_icon="🤖", layout="wide")

# CSS 주입: 배경, 카드 텍스트, 상태 배지 스타일 (Config.toml 테마 보완용)
st.markdown("""
<style>
    /* Card Container */
    .robot-card {
        background-color: #1A2235;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        border: 1px solid #334155;
    }
    .robot-title {
        font-size: 1.1em;
        font-weight: 600;
        color: #F8FAFC;
        margin-bottom: 8px;
        font-family: monospace;
    }
    /* Status Badges */
    .badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 600;
        display: inline-block;
        color: #FFFFFF;
    }
    .badge-idle { background-color: #9CA3AF; }
    .badge-charging { background-color: #10B981; }
    .badge-delivery { background-color: #F59E0B; }
    .badge-exploring { background-color: #0EA5E9; }
    .badge-returning { background-color: #8B5CF6; }
    
    .badge-failed { background-color: #EF4444; }
    .badge-completed { background-color: #10B981; }
    .badge-active { background-color: #38BDF8; }
    .badge-pending { background-color: #9CA3AF; }

    /* Telemetry Panel */
    .telemetry-row { margin-top: 10px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

def get_badge_class(status):
    return f"badge-{status.lower()}"

# --- 데이터 로드 ---
robots = get_robots()
fleet_breakdown = get_fleet_breakdown()
missions = get_missions()
sim_status = get_simulator_status()

# --- 상태 관리 (세션) ---
if 'selected_robot_id' not in st.session_state:
    st.session_state.selected_robot_id = robots[0]['id']

# --- 상단 배너 (Simulator Status) ---
if not sim_status["is_online"]:
    st.error(f"⚠️ Simulator is OFFLINE. Last Heartbeat: {sim_status['last_heartbeat']}. Map controls are disabled.")
else:
    # 간이 표시 (원하면 뺄 수 있음)
    st.caption(f"🟢 Simulator Online (Last Heartbeat: {sim_status['last_heartbeat']})")

# --- 3분할 레이아웃 ---
col_left, col_center, col_right = st.columns([1, 2, 1])

# ==========================================
# 1. 좌측 사이드바: 로봇 플릿 목록 (Fleet Status)
# ==========================================
with col_left:
    st.subheader("Fleet Status")
    
    # 필터
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        plat_filter = st.multiselect("Platform", ["wheeled", "legged"], default=["wheeled", "legged"])
    with f_col2:
        stat_filter = st.multiselect("Status", ["Idle", "Charging", "Delivery", "Exploring", "Returning"], 
                                     default=["Idle", "Charging", "Delivery", "Exploring", "Returning"])
    
    filtered_robots = [r for r in robots if r['platform'] in plat_filter and r['status'] in stat_filter]
    
    st.markdown("---")
    for r in filtered_robots:
        # 배터리 바 색상 조정
        bat_color = "normal"
        if r['battery_pct'] < 20: bat_color = "error"
        elif r['battery_pct'] < 50: bat_color = "warning"
        
        # 선택 버튼 (State 업데이트용)
        is_selected = "🔵 " if st.session_state.selected_robot_id == r['id'] else ""
        
        # HTML 카드
        badge_html = f'<span class="badge {get_badge_class(r["status"])}">{r["status"]}</span>'
        icon = "🚗" if r['platform'] == "wheeled" else "🐕"
        
        st.markdown(f"""
        <div class="robot-card">
            <div class="robot-title">{is_selected}{icon} {r['name']}</div>
            <div style="margin-bottom: 5px;">{badge_html}</div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(int(r['battery_pct']), text=f"Battery: {r['battery_pct']}%")
        
        if st.button(f"Select {r['name']}", key=f"btn_{r['id']}"):
            st.session_state.selected_robot_id = r['id']
            st.rerun()

# ==========================================
# 2. 중앙 메인: 맵 및 텔레메트리
# ==========================================
with col_center:
    selected_robot = next((r for r in robots if r['id'] == st.session_state.selected_robot_id), robots[0])
    st.subheader(f"Telemetry & Map View: {selected_robot['name']}")
    
    # 텔레메트리 (Toolbar)
    t_col1, t_col2, t_col3, t_col4 = st.columns(4)
    with t_col1:
        st.metric("Battery", f"{selected_robot['battery_pct']}%")
    with t_col2:
        st.metric("Speed", f"{selected_robot['current_speed_mps']} m/s")
    
    # 연관 미션 정보 찾기
    cur_mission = next((m for m in missions if m['id'] == selected_robot['current_mission_id']), None)
    if cur_mission:
        # 경과 시간 계산 (가짜)
        st_time = datetime.fromisoformat(cur_mission['started_at'].replace('Z', '+00:00'))
        elapsed = "15m 30s" # 목업 고정값
        cost = cur_mission['accumulated_cost']
    else:
        elapsed = "N/A"
        cost = 0.0

    with t_col3:
        st.metric("Mission Elapsed", elapsed)
    with t_col4:
        st.metric("Mission Cost", f"{cost:.1f}")

    # Map Control Buttons
    st.markdown("<div class='telemetry-row'>", unsafe_allow_html=True)
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    disabled = not sim_status["is_online"]
    with b_col1: st.button("Clear Path", disabled=disabled, use_container_width=True)
    with b_col2: st.button("Zoom Fit", disabled=disabled, use_container_width=True)
    with b_col3: st.selectbox("Map Visibility", ["All", "Path Only", "Obstacles"], disabled=disabled, label_visibility="collapsed")
    with b_col4: st.button("Refresh Voxels", disabled=disabled, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Mock 3D / 2D Map Placeholder (Plotly)
    st.markdown("##### 📍 Grid Map (Mock Visualization)")
    
    # 2D Heatmap (Grid) 생성 - 탐색 구역(Fog of war)과 경로(path) 표현용 가짜 데이터
    import numpy as np
    grid_size = 20
    z_data = np.random.choice([0, 1, 2], size=(grid_size, grid_size), p=[0.7, 0.2, 0.1])
    # 0: Unexplored/Empty, 1: Explored Flat, 2: Obstacle/Stair
    
    # 로봇 위치(가짜)
    rx, ry = 10, 10
    z_data[rx, ry] = 3 # Robot Position
    
    fig = px.imshow(z_data, color_continuous_scale=["#0B0F19", "#1A2235", "#8B5CF6", "#38BDF8"], origin='lower')
    fig.update_layout(
        plot_bgcolor="#0B0F19",
        paper_bgcolor="#0B0F19",
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_showscale=False,
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False)
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 3. 우측 사이드바: 분석 및 로그 (Analytics & Logs)
# ==========================================
with col_right:
    # 🚨 미확인 실패 알림
    failed_count = sum(1 for m in missions if m['status'] == 'Failed')
    st.subheader(f"Analytics & Logs 🚨({failed_count})")
    
    # Fleet Breakdown Donut Chart
    st.markdown("**Fleet Task Breakdown**")
    labels = list(fleet_breakdown.keys())
    values = list(fleet_breakdown.values())
    
    # 색상 매핑
    color_map = {
        "Idle": "#9CA3AF",
        "Charging": "#10B981",
        "Delivery": "#F59E0B",
        "Exploring": "#0EA5E9",
        "Returning": "#8B5CF6"
    }
    pie_colors = [color_map.get(l, "#FFFFFF") for l in labels]
    
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5, marker=dict(colors=pie_colors))])
    fig_pie.update_layout(
        paper_bgcolor="#0B0F19",
        plot_bgcolor="#0B0F19",
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(color="#F8FAFC"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    st.markdown("---")
    st.markdown("**Mission Logs**")
    
    m_filter = st.selectbox("Status Filter", ["All", "Pending", "Active", "Completed", "Failed"])
    filtered_missions = missions if m_filter == "All" else [m for m in missions if m['status'] == m_filter]
    
    for m in filtered_missions:
        badge_html = f'<span class="badge {get_badge_class(m["status"])}">{m["status"]}</span>'
        st.markdown(f"""
        <div style="background-color: #1A2235; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 4px solid {color_map.get(m['status'], '#38BDF8') if m['status'] in color_map else ('#EF4444' if m['status']=='Failed' else '#10B981')};">
            <div style="font-size:0.9em; margin-bottom:4px;"><b>{m['robot_name']}</b> ({m['mission_type']})</div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                {badge_html}
                <span style="font-size:0.8em; color:#94A3B8;">Cost: {m['accumulated_cost']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
