import streamlit as st
from components.styling import inject_css, brand
from components.sidebar import render_sidebar
from config.settings import settings
from database.neo4j_connection import test_connection
from database.schema_inspector import get_counts

st.set_page_config(page_title='CineGraph AI', page_icon='🎬', layout='wide', initial_sidebar_state='expanded')
inject_css(); render_sidebar()

st.markdown('<div class="hero"><div class="eyebrow">✦ Graph RAG · Neo4j · Ollama</div><h1>Every story leaves<br>a <span>trace.</span></h1><p>Discover films through the people, performances and connections behind them. Ask your graph a question, follow a relationship, or find your next movie — with evidence, not guesses.</p></div>', unsafe_allow_html=True)

ok, _ = test_connection()
cols = st.columns([1.3,1,1,1])
with cols[0]:
    st.markdown(f'<div class="card"><div class="smallcaps">Database</div><h3>{"Connected" if ok else "Needs setup"}</h3><div class="muted">Neo4j graph status</div></div>', unsafe_allow_html=True)
if ok:
    try: counts = get_counts()
    except Exception: counts = {'movies': 0, 'people': 0}
else: counts = {'movies': 0, 'people': 0}
with cols[1]: st.metric('Movies', counts['movies'])
with cols[2]: st.metric('People', counts['people'])
with cols[3]: st.metric('LLM', 'Ready' if settings.llm_configured else 'Optional')

st.markdown('### Start with a question')
prompts = ['Who directed The Matrix?', 'Which movies did Tom Hanks act in?', 'Recommend movies related to The Matrix.']
for i, p in enumerate(prompts):
    if st.button(p, key=f'home_prompt_{i}', use_container_width=True):
        st.session_state['pending_question'] = p
        st.switch_page('pages/1_AI_Companion.py')

st.markdown('### Explore the product')
a,b = st.columns(2)
with a:
    st.markdown('<div class="card"><div class="eyebrow">01 · Companion</div><h3>Ask the graph</h3><p class="muted">Conversational answers grounded in retrieved Neo4j facts, with transparent evidence.</p></div>', unsafe_allow_html=True)
    if st.button('Open AI Companion', key='home_chat'): st.switch_page('pages/1_AI_Companion.py')
with b:
    st.markdown('<div class="card"><div class="eyebrow">02 · Explorer</div><h3>Trace connections</h3><p class="muted">Visualize real movie-person relationships and inspect the graph around an entity.</p></div>', unsafe_allow_html=True)
    if st.button('Open Graph Explorer', key='home_graph'): st.switch_page('pages/2_Graph_Explorer.py')
