import streamlit as st
from components.styling import inject_css
from components.sidebar import render_sidebar
from config.settings import settings
from database.neo4j_connection import test_connection, run_query
from database.schema_inspector import get_schema, get_counts

st.set_page_config(page_title='System Status · CineGraph AI', page_icon='⚙️', layout='wide')
inject_css(); render_sidebar()
st.markdown('<div class="eyebrow">Database & System Status</div><h1>Know what is connected.</h1>', unsafe_allow_html=True)
ok,msg=test_connection()
c1,c2=st.columns(2)
with c1: st.metric('Neo4j', 'Connected' if ok else 'Not connected')
with c2: st.metric('Ollama', 'Configured' if settings.llm_configured else 'Not configured')
st.caption(f'Model: {settings.ollama_model} · Host: {settings.ollama_host}')
if ok:
    try:
        counts=get_counts(); schema=get_schema()
        st.write('**Movies:**', counts['movies']); st.write('**People:**', counts['people'])
        st.write('**Relationship types:**', ', '.join(schema['relationships']) or 'None reported')
        with st.expander('Available labels and properties'):
            st.json(schema)
    except Exception as exc: st.error(str(exc))
else:
    st.warning(msg)
    st.markdown('1. Create a Neo4j AuraDB or local instance.\n2. Load the Movies sample graph.\n3. Put credentials in `.env`.\n4. Restart Streamlit and test again.')
if st.button('Test database connection'): st.rerun()
