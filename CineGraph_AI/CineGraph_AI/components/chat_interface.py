import streamlit as st

from config.settings import settings
from rag.conversation import add_message
from rag.query_router import route_question_with_llm
from rag.graph_retriever import GraphRetriever
from rag.answer_generator import AnswerGenerator


def _fallback_answer(question: str, records: list[dict]) -> str:
    """Present graph facts readably if Ollama is unavailable."""
    if not records:
        return "I couldn't find relevant information in the connected Neo4j graph."

    if all("movie" in row and "director" in row for row in records):
        grouped: dict[str, list[str]] = {}
        for row in records:
            movie = str(row["movie"])
            director = str(row["director"])
            grouped.setdefault(movie, [])
            if director not in grouped[movie]:
                grouped[movie].append(director)
        return "\n\n".join(
            f"**{movie}** was directed by {', '.join(directors)}."
            for movie, directors in grouped.items()
        )

    if all("person" in row and "movies" in row for row in records):
        answers = []
        for row in records:
            movies = row.get("movies") or []
            if movies:
                answers.append(f"**{row['person']}** appeared in: {', '.join(map(str, movies))}.")
            else:
                answers.append(f"No movies were found for **{row['person']}**.")
        return "\n\n".join(answers)

    if all("movie" in row and "cast_size" in row for row in records) and not any("movies" in row for row in records):
        return "\n\n".join(f"**{row['movie']}** has {row['cast_size']} credited actor(s)." for row in records)

    facts = "\n".join(
        "- " + "; ".join(f"{key}: {value}" for key, value in row.items())
        for row in records[:10]
    )
    return "I retrieved these facts from the connected Neo4j graph:\n\n" + facts


SUPPORTED_HELP = (
    "I can't map that question to a graph query yet. Try asking things like:\n\n"
    "- **Cast & crew:** \"List the actors of The Matrix\", \"Who directed Cloud Atlas?\", \"Who worked on Apollo 13?\"\n"
    "- **People's movies:** \"Tom Hanks movies\", \"Which movies did Lana Wachowski direct?\"\n"
    "- **Connections:** \"Who has Tom Hanks worked with?\", \"Movies with both Tom Hanks and Meg Ryan\"\n"
    "- **Filters & rankings:** \"Movies from the 90s\", \"Which actor appeared in the most movies?\", \"How many movies are in the database?\"\n"
    "- **Reviews:** \"What rating did Jessica Thompson give Cloud Atlas?\", \"Highest rated movies\"\n"
    "- **Recommendations:** \"Recommend movies like The Matrix\""
)


def handle_question(question: str):
    route = route_question_with_llm(question, settings.ollama_model, settings.ollama_host)
    if route.category == "unsupported":
        add_message(st, "assistant", SUPPORTED_HELP)
        return
    retriever = GraphRetriever(settings.max_results)

    try:
        result = retriever.retrieve(route)
    except Exception as exc:
        message = f"I couldn't retrieve graph data: {type(exc).__name__}: {exc}"
        add_message(st, "assistant", message)
        return

    records = result.get("records", [])
    if not records:
        answer = "I couldn't find relevant evidence in the connected Neo4j graph for that question."
    elif settings.llm_provider != "ollama":
        answer = (
            f"The configured provider is '{settings.llm_provider}', but this project build uses Ollama. "
            "Set LLM_PROVIDER=ollama in .env.\n\n" + _fallback_answer(question, records)
        )
    else:
        try:
            generator = AnswerGenerator(
                model=settings.ollama_model,
                host=settings.ollama_host,
            )
            history = st.session_state.get("messages", [])[-6:]
            answer = generator.answer(question, records, history)
        except Exception as exc:
            print(f"Ollama generation error: {type(exc).__name__}: {exc}")
            answer = (
                f"Ollama could not generate the answer ({type(exc).__name__}: {exc}).\n\n"
                + _fallback_answer(question, records)
            )

    add_message(st, "assistant", answer, result)


def render_chat():
    # Home-page suggestion buttons submit the selected prompt once we arrive here.
    pending_question = st.session_state.pop("pending_question", None)
    if pending_question:
        add_message(st, "user", pending_question)
        try:
            with st.spinner("Tracing the movie graph and generating your answer…"):
                handle_question(pending_question)
        except Exception as exc:
            add_message(st, "assistant", f"I couldn't complete that question: {type(exc).__name__}: {exc}")
        st.rerun()

    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            evidence = msg.get("evidence")
            if evidence:
                with st.expander("Graph evidence & retrieval details"):
                    st.write("**Category:**", evidence.get("category"))
                    st.write("**Records:**")
                    st.json(evidence.get("records", []))
                    if evidence.get("query"):
                        st.code(evidence["query"], language="cypher")
                    st.write("**Parameters:**", evidence.get("parameters"))

    question = st.chat_input("Ask about movies, actors, directors, connections, or recommendations…")
    if question:
        add_message(st, "user", question)
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Tracing the movie graph and generating your answer…"):
                handle_question(question)
        st.rerun()
