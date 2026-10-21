from rag.cypher_templates import TEMPLATES

def recommend(title: str, limit: int = 8) -> list[dict]:
    from database.neo4j_connection import run_query
    rows = run_query(TEMPLATES['recommendations'], {'title': title, 'limit': min(limit, 20)})
    for row in rows:
        row['explanation'] = _explain(row)
        row['connection_summary'] = f"{row.get('sharedActors', 0)} shared actor(s) + {row.get('sharedDirectors', 0)} shared director(s)"
    return rows

def _explain(row: dict) -> str:
    actors = row.get('sharedActors', 0)
    directors = row.get('sharedDirectors', 0)
    parts = []
    if actors:
        parts.append(f'{actors} shared actor' + ('s' if actors != 1 else ''))
    if directors:
        parts.append(f'{directors} shared director' + ('s' if directors != 1 else ''))
    return 'Recommended because it shares ' + ' and '.join(parts) + '.' if parts else 'Recommended from the graph relationship baseline.'
