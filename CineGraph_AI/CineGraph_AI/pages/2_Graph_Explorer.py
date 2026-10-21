import streamlit as st
from components.styling import inject_css
from components.sidebar import render_sidebar
from components.graph_visualizer import render_graph
from database.neo4j_connection import run_query

st.set_page_config(page_title='Graph Explorer · CineGraph AI', page_icon='🔗', layout='wide')
inject_css(); render_sidebar()
st.markdown('<div class="eyebrow">Knowledge Graph Explorer</div><h1>Trace a movie universe.</h1><p class="muted">Search a real Movie or Person node and visualize the relationships stored in Neo4j.</p>', unsafe_allow_html=True)
query = st.text_input('Movie or person', placeholder='e.g. The Matrix or Tom Hanks')
depth = st.slider('Relationship depth', 1, 2, 1)
limit = st.slider('Node/edge limit', 10, 80, 35)
if st.button('Explore graph', type='primary') and query:
    cypher = '''
    MATCH (start)
    WHERE (start:Movie OR start:Person)
      AND (toLower(coalesce(start.name, '')) CONTAINS toLower($q)
           OR toLower(coalesce(start.title, '')) CONTAINS toLower($q))
    MATCH p=(start)-[*1..2]-(n)
    UNWIND relationships(p) AS r
    WITH DISTINCT r, startNode(r) AS source, endNode(r) AS target
    RETURN elementId(source) AS source_id,
           coalesce(source.title, source.name, elementId(source)) AS source_label,
           labels(source) AS source_labels,
           elementId(target) AS target_id,
           coalesce(target.title, target.name, elementId(target)) AS target_label,
           labels(target) AS target_labels,
           type(r) AS relationship,
           CASE WHEN startNode(r) = source THEN 'outgoing' ELSE 'incoming' END AS direction
    LIMIT $limit
    '''
    try:
        rows = run_query(cypher, {'q': query, 'limit': limit})
        if rows:
            render_graph(rows)
            with st.expander('Raw graph records'): st.json(rows)
        else: st.info('No matching graph entities were found.')
    except Exception as exc: st.error(str(exc))
