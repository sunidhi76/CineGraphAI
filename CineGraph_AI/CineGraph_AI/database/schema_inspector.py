from database.neo4j_connection import run_query

def get_schema() -> dict:
    labels = run_query('CALL db.labels() YIELD label RETURN label ORDER BY label')
    rels = run_query('CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType')
    props = run_query('MATCH (n) UNWIND keys(n) AS key RETURN DISTINCT labels(n)[0] AS label, key ORDER BY label, key')
    return {
        'labels': [r['label'] for r in labels],
        'relationships': [r['relationshipType'] for r in rels],
        'properties': props,
    }

def get_counts() -> dict[str, int]:
    movies = run_query('MATCH (m:Movie) RETURN count(m) AS count')
    people = run_query('MATCH (p:Person) RETURN count(p) AS count')
    return {'movies': movies[0]['count'] if movies else 0, 'people': people[0]['count'] if people else 0}
