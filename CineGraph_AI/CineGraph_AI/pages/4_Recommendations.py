import streamlit as st
from components.styling import inject_css
from components.sidebar import render_sidebar
from rag.recommendation_engine import recommend

st.set_page_config(page_title='Recommendations · CineGraph AI', page_icon='⭐', layout='wide')
inject_css(); render_sidebar()
st.markdown('<div class="eyebrow">Smart Recommendations</div><h1>Connections, not guesses.</h1><p class="muted">The baseline ranks movies using shared actors and shared directors. Every score is explainable.</p>', unsafe_allow_html=True)
title = st.text_input('Start from a movie', placeholder='The Matrix')
limit = st.slider('Number of recommendations', 3, 12, 6)
if st.button('Generate recommendations', type='primary') and title:
    try:
        rows = recommend(title, limit)
        if not rows: st.info('No connected recommendations were found in the graph.')
        for row in rows:
            st.markdown(f'''<div class="card"><div class="eyebrow">Score {row.get('score',0)}</div><h3>{row.get('title','Untitled')}</h3><div class="muted">{row.get('released') or 'Year unavailable'}</div><p>{row.get('explanation')}</p><div class="smallcaps">{row.get('connection_summary')}</div></div>''', unsafe_allow_html=True)
            st.write('')
    except Exception as exc: st.error(str(exc))
