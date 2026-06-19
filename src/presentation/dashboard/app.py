import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from mock_data import get_robots, get_fleet_breakdown, get_missions, get_simulator_status, get_map_graph

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


@st.cache_data(ttl=60, show_spinner=False)
def load_map_graph():
    """맵 노드/엣지를 60초 캐시로 로드한다 (수천 개 데이터를 매 rerun마다 재조회하지 않도록)."""
    return get_map_graph()

# --- 데이터 로드 ---
robots = list(get_robots())

fleet_breakdown = get_fleet_breakdown()
missions = list(get_missions())

sim_status = get_simulator_status()

# 로봇이 하나도 없을 때(DB 연결 실패 등) 화면이 죽지 않도록 방어
if not robots:
    st.warning("⚠️ 로봇 데이터를 불러오지 못했습니다. Supabase 연결 또는 robots 테이블을 확인하세요.")
    st.stop()

# --- 상태 관리 (세션) ---
if 'selected_robot_id' not in st.session_state:
    st.session_state.selected_robot_id = robots[0]['id']

if 'show_left' not in st.session_state:
    st.session_state.show_left = True

if 'show_right' not in st.session_state:
    st.session_state.show_right = True

# --- 상단 배너 (Simulator Status) ---
if not sim_status["is_online"]:
    st.error(f"⚠️ Simulator is OFFLINE. Last Heartbeat: {sim_status['last_heartbeat']}. Map controls are disabled.")
else:
    # 간이 표시 (원하면 뺄 수 있음)
    st.caption(f"🟢 Simulator Online (Last Heartbeat: {sim_status['last_heartbeat']})")

# --- 레이아웃 토글 논리 ---
if st.session_state.show_left and st.session_state.show_right:
    col_left, col_center, col_right = st.columns([1, 2, 1])
elif st.session_state.show_left and not st.session_state.show_right:
    col_left, col_center = st.columns([1, 3])
    col_right = None
elif not st.session_state.show_left and st.session_state.show_right:
    col_center, col_right = st.columns([3, 1])
    col_left = None
else:
    col_center = st.container()
    col_left = None
    col_right = None

# ==========================================
# 1. 좌측 사이드바: 로봇 플릿 목록 (Fleet Status)
# ==========================================
if col_left:
    with col_left:
        st.subheader("Fleet Status")
        
        # 필터 (스크롤되지 않는 영역)
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            plat_filter = st.multiselect("Platform", ["wheeled", "legged"], default=["wheeled", "legged"])
        with f_col2:
            stat_filter = st.multiselect("Status", ["Idle", "Charging", "Delivery", "Exploring", "Returning"], 
                                         default=["Charging", "Delivery", "Exploring", "Returning"])
        
        filtered_robots = [r for r in robots if r['platform'] in plat_filter and r['status'] in stat_filter]
        
        st.markdown("---")
        
        # 로봇 카드 리스트 (스크롤 영역)
        with st.container(height=650):
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
    # --- 헤더 및 토글 버튼 ---
    head_l, head_c, head_r = st.columns([1, 10, 1])
    with head_l:
        if st.button("▶" if not st.session_state.show_left else "◀", key="toggle_left"):
            st.session_state.show_left = not st.session_state.show_left
            st.rerun()
    with head_c:
        selected_robot = next((r for r in robots if r['id'] == st.session_state.selected_robot_id), robots[0])
        st.subheader(f"Telemetry & Map View: {selected_robot['name']}")
    with head_r:
        if st.button("◀" if not st.session_state.show_right else "▶", key="toggle_right"):
            st.session_state.show_right = not st.session_state.show_right
            st.rerun()
    
    # 텔레메트리 (Toolbar)
    t_col1, t_col2, t_col3, t_col4 = st.columns(4)
    with t_col1:
        st.metric("Battery", f"{selected_robot['battery_pct']}%")
    with t_col2:
        st.metric("Speed", f"{selected_robot['current_speed_mps']} m/s")
    
    # 연관 미션 정보 찾기
    cur_mission = next((m for m in missions if m['id'] == selected_robot['current_mission_id']), None)
    if cur_mission:
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

    # --- 맵 컨트롤 바 ---
    st.markdown("<div class='telemetry-row'>", unsafe_allow_html=True)
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    disabled = not sim_status["is_online"]
    with b_col1:
        st.button("Clear Path", disabled=disabled, use_container_width=True)
    with b_col2:
        if st.button("🔄 Refresh Map", use_container_width=True):
            load_map_graph.clear()
            st.rerun()
    with b_col3:
        view_mode = st.selectbox(
            "Map View", ["전체", "발견 영역만", "거점만"], label_visibility="collapsed"
        )
    with b_col4:
        show_edges = st.toggle("경로망", value=False)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 캠퍼스 맵 (실데이터: nodes + map_edges) ---
    st.markdown("##### 📍 캠퍼스 맵 (Supabase 실데이터)")

    graph = load_map_graph()
    g_nodes = graph.get("nodes", [])
    g_edges = graph.get("edges", [])
    g_stations = graph.get("stations", [])

    if not g_nodes:
        st.info("맵 데이터를 불러오지 못했습니다. (nodes 테이블이 비어있거나 DB 연결 실패)")
    else:
        # 지형 태그 → 색상 (config/cost_profiles.json 기준)
        TERRAIN_COLORS = {
            "Terrain_Flat": "#475569",       # 평지 (슬레이트)
            "Terrain_Slope": "#14B8A6",      # 경사 (틸)
            "Path_Ramp": "#22C55E",          # 램프 (그린)
            "Path_Stair": "#F97316",         # 계단 (오렌지)
            "Path_Tunnel": "#8B5CF6",        # 터널 (퍼플)
            "Road_Vehicle": "#DC2626",       # 차도 (레드)
            "Road_Vehicle_Ramp": "#B91C1C",  # 차도 램프 (다크레드)
            "Crosswalk": "#E5E7EB",          # 횡단보도 (화이트)
            "Tile_Hazard": "#FACC15",        # 위험 타일 (옐로)
        }
        DEFAULT_COLOR = "#64748B"

        # 거점 node_id 집합 (base_locations 멤버십)
        station_meta = {s.get("node_id"): s for s in g_stations}

        # 분류: 거점 / 타일(탐색됨 · 미탐색), 타일은 지형색
        st_x, st_y, st_t = [], [], []
        dx_, dy_, dc_, dt_ = [], [], [], []   # 탐색된 타일
        ux_, uy_, uc_ = [], [], []            # 미탐색 타일
        terrain_present = set()

        for n in g_nodes:
            nid = n.get("id")
            x, z = n.get("x"), n.get("z")
            tag = n.get("terrain_tag") or "-"
            if nid in station_meta:
                meta = station_meta[nid]
                usage = meta.get("location_usage") or "station"
                st_x.append(x); st_y.append(z)
                st_t.append(f"🏁 거점 · {usage}<br>{meta.get('name', '')}")
                continue
            color = TERRAIN_COLORS.get(tag, DEFAULT_COLOR)
            terrain_present.add(tag)
            if n.get("is_discovered"):
                dx_.append(x); dy_.append(z); dc_.append(color); dt_.append(f"탐색됨 · {tag}")
            else:
                ux_.append(x); uy_.append(z); uc_.append(color)

        fig = go.Figure()

        # 엣지(선택, 기본 off) — 수십만 개까지 가능해 상한 샘플링
        edge_note = ""
        if show_edges and view_mode != "거점만" and g_edges:
            pos = {n["id"]: (n["x"], n["z"]) for n in g_nodes}
            MAX_EDGES = 20000
            step = max(1, len(g_edges) // MAX_EDGES)
            ex, ey = [], []
            for e in g_edges[::step]:
                a = pos.get(e.get("from_node_id"))
                b = pos.get(e.get("to_node_id"))
                if a and b:
                    ex += [a[0], b[0], None]
                    ey += [a[1], b[1], None]
            if ex:
                fig.add_trace(go.Scattergl(
                    x=ex, y=ey, mode="lines",
                    line=dict(color="#1E293B", width=0.5),
                    hoverinfo="skip", showlegend=False,
                ))
            if step > 1:
                edge_note = f" · 엣지 1/{step} 샘플 표시"

        # 미탐색 타일 (흐릿, Fog) — '전체'에서만
        if view_mode == "전체" and ux_:
            fig.add_trace(go.Scattergl(
                x=ux_, y=uy_, mode="markers",
                marker=dict(size=4, color=uc_, opacity=0.35),
                hoverinfo="skip", showlegend=False,
            ))
        # 탐색된 타일 (선명)
        if view_mode in ("전체", "발견 영역만") and dx_:
            fig.add_trace(go.Scattergl(
                x=dx_, y=dy_, mode="markers",
                marker=dict(size=5, color=dc_, opacity=1.0),
                text=dt_, hovertemplate="%{text}<extra></extra>",
                showlegend=False,
            ))
        # 거점(Station)
        if st_x:
            fig.add_trace(go.Scatter(
                x=st_x, y=st_y, mode="markers",
                marker=dict(size=12, color="#F59E0B", symbol="diamond",
                            line=dict(color="#FDE68A", width=1)),
                text=st_t, hovertemplate="%{text}<extra></extra>",
                showlegend=False,
            ))

        fig.update_layout(
            plot_bgcolor="#0B0F19", paper_bgcolor="#0B0F19",
            margin=dict(l=0, r=0, t=0, b=0), height=560,
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, visible=False,
                       scaleanchor="y", scaleratio=1),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
            dragmode="pan",
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"scrollZoom": True, "displaylogo": False})

        # 지형 색상 범례 (실제 존재하는 태그만)
        chips = []
        for tag, col in TERRAIN_COLORS.items():
            if tag in terrain_present:
                chips.append(
                    f"<span style='color:{col};font-size:1.2em;'>■</span> "
                    f"<span style='color:#CBD5E1;font-size:0.8em;'>{tag}</span>"
                )
        chips.append(
            "<span style='color:#F59E0B;font-size:1.1em;'>◆</span> "
            "<span style='color:#CBD5E1;font-size:0.8em;'>거점</span>"
        )
        st.markdown(
            "&nbsp;&nbsp;".join(chips)
            + "<div style='color:#64748B;font-size:0.75em;margin-top:4px;'>"
              "흐릿=미탐색 · 선명=탐색됨 (Fog of War)</div>",
            unsafe_allow_html=True,
        )

        # 요약 캡션
        total = len(g_nodes)
        disc = len(dx_)
        tiles_total = len(dx_) + len(ux_)
        pct = (disc / tiles_total * 100) if tiles_total else 0
        st.caption(
            f"노드 {total:,}개 · 거점 {len(st_x)}개 · 타일 {tiles_total:,}개 "
            f"(탐색 {disc:,}개, {pct:.1f}%) · 엣지 {len(g_edges):,}개{edge_note}"
        )

# ==========================================
# 3. 우측 사이드바: 분석 및 로그 (Analytics & Logs)
# ==========================================
if col_right:
    with col_right:
        # 🚨 미확인 실패 알림
        failed_count = sum(1 for m in missions if m['status'] == 'Failed')
        st.subheader(f"Analytics & Logs 🚨({failed_count})")
        
        # Fleet Breakdown Donut Chart (고정 영역)
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
        
        # 필터 (고정 영역)
        m_filter = st.selectbox("Status Filter", ["All", "Pending", "Active", "Completed", "Failed"])
        filtered_missions = missions if m_filter == "All" else [m for m in missions if m['status'] == m_filter]
        
        # 로그 리스트 (스크롤 영역)
        with st.container(height=350):
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
