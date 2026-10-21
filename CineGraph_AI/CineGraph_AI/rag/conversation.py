def init_state(st):
    if 'messages' not in st.session_state:
        st.session_state.messages = []

def add_message(st, role: str, content: str, evidence: dict | None = None):
    st.session_state.messages.append({'role': role, 'content': content, 'evidence': evidence})

def clear(st):
    st.session_state.messages = []
