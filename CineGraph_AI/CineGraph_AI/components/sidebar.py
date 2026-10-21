import streamlit as st
from config.settings import settings
from database.neo4j_connection import test_connection
from components.styling import brand

def render_sidebar():
    with st.sidebar:
        brand()
        st.caption('Graph RAG Movie Assistant')
        st.divider()
        ok, msg = test_connection()
        if ok:
            st.markdown('<div class="status"><span class="dot"></span> Neo4j connected</div>', unsafe_allow_html=True)
        else:
            st.warning('Neo4j not connected')
        st.divider()
        st.markdown('**Navigation**')
        st.page_link('app.py', label='Home', icon='🏠')
        st.page_link('pages/1_AI_Companion.py', label='AI Companion', icon='🤖')
        st.page_link('pages/2_Graph_Explorer.py', label='Graph Explorer', icon='🔗')
        st.page_link('pages/4_Recommendations.py', label='Recommendations', icon='⭐')
        st.page_link('pages/5_System_Status.py', label='System Status', icon='⚙️')
        st.divider()
        st.caption(f'LLM: {settings.llm_provider.title()}')
        st.caption('Credentials are never displayed.')
