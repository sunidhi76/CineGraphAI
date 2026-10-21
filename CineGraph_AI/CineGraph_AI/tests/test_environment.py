from config.settings import Settings


def test_missing_environment_is_not_configured():
    settings = Settings(
        neo4j_uri="",
        neo4j_username="",
        neo4j_password="",
        llm_provider="ollama",
        ollama_model="llama3.2:3b",
        ollama_host="http://localhost:11434",
        max_results=20,
        debug_mode=False,
    )
    assert not settings.neo4j_configured
    assert settings.llm_configured  # configured locally; service is checked on use


def test_ollama_configuration():
    settings = Settings(
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="test",
        llm_provider="ollama",
        ollama_model="llama3.2:3b",
        ollama_host="http://localhost:11434",
        max_results=20,
        debug_mode=False,
    )
    assert settings.neo4j_configured
    assert settings.llm_configured
