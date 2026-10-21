import streamlit as st
from components.styling import inject_css
from components.sidebar import render_sidebar
from components.chat_interface import render_chat
from rag.conversation import init_state, clear

st.set_page_config(page_title='AI Companion · CineGraph AI', page_icon='🤖', layout='wide')
inject_css(); render_sidebar(); init_state(st)

st.markdown('<div class="eyebrow">AI Movie Companion</div><h1>Ask the movie graph.</h1><p class="muted">Questions are routed to safe, predefined Cypher retrieval strategies before the local Ollama model sees the evidence.</p>', unsafe_allow_html=True)
if st.button('Clear conversation'):
    clear(st); st.rerun()
render_chat()
