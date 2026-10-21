from contextlib import contextmanager
from typing import Any
import streamlit as st
from neo4j import GraphDatabase, Driver
from config.settings import settings

@st.cache_resource(show_spinner=False)
def get_driver() -> Driver:
    if not settings.neo4j_configured:
        raise RuntimeError('Neo4j is not configured. Add NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD to .env.')
    try:
        driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password))
        driver.verify_connectivity()
        return driver
    except Exception as exc:
        raise RuntimeError(f'Neo4j connection failed: {type(exc).__name__}. Check the URI and credentials.') from exc

@contextmanager
def session():
    driver = get_driver()
    s = driver.session()
    try:
        yield s
    finally:
        s.close()

def run_query(query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        with session() as s:
            result = s.run(query, parameters or {})
            return [record.data() for record in result]
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f'Neo4j query failed: {type(exc).__name__}.') from exc

def test_connection() -> tuple[bool, str]:
    try:
        driver = get_driver()
        driver.verify_connectivity()
        return True, 'Connected to Neo4j successfully.'
    except Exception as exc:
        return False, str(exc)
