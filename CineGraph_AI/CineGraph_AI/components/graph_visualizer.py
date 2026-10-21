import streamlit.components.v1 as components
from pyvis.network import Network


def render_graph(records: list[dict]):
    """Render returned Neo4j nodes and relationship edges as an interactive graph."""
    net = Network(height="600px", width="100%", bgcolor="#0b0d10", font_color="#f4f1eb", directed=True)
    net.set_options('''{
      "nodes": {"font": {"size": 16, "face": "DM Sans", "color": "#f4f1eb"}, "borderWidth": 1},
      "edges": {"font": {"size": 11, "face": "DM Sans", "color": "#b9c1ce", "strokeWidth": 1},
                 "color": {"color": "#52c7bd", "highlight": "#b98cff"}, "arrows": {"to": {"enabled": true, "scaleFactor": 0.55}}, "smooth": {"type": "dynamic"}},
      "physics": {"enabled": true, "stabilization": {"iterations": 150}, "barnesHut": {"gravitationalConstant": -5000, "springLength": 150, "springConstant": 0.035}}
    }''')
    seen = set()
    edges = set()
    for row in records:
        # Each edge is drawn between the relationship's real startNode/endNode IDs.
        source_id = str(row.get('source_id') or '')
        target_id = str(row.get('target_id') or '')
        source_label = row.get('source_label')
        target_label = row.get('target_label')
        source_labels = row.get('source_labels') or []
        target_labels = row.get('target_labels') or []
        rel = str(row.get('relationship') or 'RELATED')
        for node_id, label, labels_ in (
            (source_id, source_label, source_labels),
            (target_id, target_label, target_labels),
        ):
            if node_id and label and node_id not in seen:
                is_movie = 'Movie' in labels_
                net.add_node(
                    node_id,
                    label=str(label),
                    title=f"{', '.join(labels_) or 'Entity'}: {label}",
                    color='#e7b86b' if is_movie else '#52c7bd',
                    shape='box' if is_movie else 'dot',
                )
                seen.add(node_id)
        edge_key = (source_id, target_id, rel)
        if source_id and target_id and source_id != target_id and edge_key not in edges:
            net.add_edge(source_id, target_id, label=rel, title=rel)
            edges.add(edge_key)
    if not seen:
        return
    html = net.generate_html()
    components.html(html, height=630, scrolling=False)
