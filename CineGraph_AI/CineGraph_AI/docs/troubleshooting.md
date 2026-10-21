# Troubleshooting

- **Ollama is not reachable:** Install Ollama, open/run it, then check `ollama list` and `http://localhost:11434`.
- **Model not found:** Run `ollama pull llama3.2:3b` (or pull the model set in `OLLAMA_MODEL`).
- **Ollama generation failed:** Verify `OLLAMA_HOST` is correct and the Ollama service is running. No cloud API key or API credits are required for local inference.
- **Neo4j is not connected:** Check `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD`, and confirm the Movies sample graph is loaded.
- **No graph evidence:** Inspect the selected query category, Cypher query, parameters, and actual labels/relationships in Neo4j.
- **Slow answers:** Smaller models such as `llama3.2:3b` use fewer local resources. Larger models may need more RAM/VRAM.
- Never commit `.env` or expose database credentials.
