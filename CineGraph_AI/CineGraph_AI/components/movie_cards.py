import streamlit as st

def movie_card(movie: dict, key: str):
    title = movie.get('title', 'Untitled')
    year = movie.get('released') or 'Year unavailable'
    st.markdown(f'''<div class="card movie-card"><div class="poster">{title}</div><h3>{title}</h3><div class="muted">{year}</div></div>''', unsafe_allow_html=True)
    return st.button('Explore', key=key, use_container_width=True)
