from dataclasses import asdict
from typing import Any
from database.neo4j_connection import run_query
from rag.cypher_templates import TEMPLATES
from rag.query_router import Route

class GraphRetriever:
    def __init__(self, max_results: int = 20):
        self.max_results = max_results

    def retrieve(self, route: Route) -> dict[str, Any]:
        if route.category not in TEMPLATES:
            return {'category': route.category, 'records': [], 'query': None, 'parameters': route.parameters, 'route': asdict(route)}
        params = dict(route.parameters)
        params['limit'] = min(self.max_results, max(1, int(params.get('limit', self.max_results))))
        records = run_query(TEMPLATES[route.category], params)
        normalized = [self._normalize(r) for r in records]
        return {'category': route.category, 'records': normalized, 'query': TEMPLATES[route.category], 'parameters': {k: v for k, v in params.items() if k != 'limit' or True}, 'route': asdict(route)}

    @staticmethod
    def _normalize(record: dict[str, Any]) -> dict[str, Any]:
        out = {}
        for k, v in record.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                out[k] = v
            elif isinstance(v, list):
                out[k] = [GraphRetriever._normalize(x) if isinstance(x, dict) else x for x in v]
            else:
                out[k] = str(v)
        return out
