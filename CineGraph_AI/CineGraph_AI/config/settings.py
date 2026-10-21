from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str = os.getenv("NEO4J_URI", "")
    neo4j_username: str = os.getenv("NEO4J_USERNAME", "")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    max_results: int = int(os.getenv("MAX_RESULTS", "20"))
    debug_mode: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"

    @property
    def neo4j_configured(self) -> bool:
        return all((self.neo4j_uri, self.neo4j_username, self.neo4j_password))

    @property
    def llm_configured(self) -> bool:
        # Local configuration is present; live availability is checked at request time.
        return self.llm_provider == "ollama" and bool(self.ollama_model and self.ollama_host)


settings = Settings()
