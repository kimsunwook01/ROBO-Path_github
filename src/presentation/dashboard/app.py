import sys
import os
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가하여 src 모듈을 임포트할 수 있도록 함
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# .env 명시적 로드
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path)

from src.infrastructure.database.client import get_supabase_client

# 기본 페이지 설정 (웹 디자인 지침에 따라 모던한 레이아웃 권장)
st.set_page_config(
    page_title="ROBO-Path Dashboard (POC)",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 ROBO-Path Database Explorer")
st.markdown("Supabase 데이터베이스와 Streamlit 간의 연동 상태를 확인하기 위한 대시보드입니다.")

@st.cache_data(ttl=60)
def fetch_table_data(table_name: str):
    """
    Supabase 테이블에서 전체 데이터를 가져옵니다.
    """
    try:
        client = get_supabase_client()
        response = client.table(table_name).select("*").execute()
        return response.data, None
    except Exception as e:
        return None, str(e)

st.header("1. Nodes Table")
with st.spinner("Loading nodes data..."):
    nodes_data, error = fetch_table_data("nodes")
    
    if error:
        st.error(f"Failed to fetch nodes: {error}")
    elif nodes_data:
        st.success(f"Successfully loaded {len(nodes_data)} nodes.")
        df_nodes = pd.DataFrame(nodes_data)
        st.dataframe(df_nodes, use_container_width=True)
    else:
        st.warning("No nodes found or table is empty.")

st.markdown("---")

st.header("2. Map Edges Table")
with st.spinner("Loading edges data..."):
    edges_data, error = fetch_table_data("map_edges")
    
    if error:
        st.error(f"Failed to fetch map_edges: {error}")
    elif edges_data:
        st.success(f"Successfully loaded {len(edges_data)} edges.")
        df_edges = pd.DataFrame(edges_data)
        st.dataframe(df_edges, use_container_width=True)
    else:
        st.warning("No map_edges found or table is empty.")
