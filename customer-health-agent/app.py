"""
app.py

Streamlit app for Customer Health Finder using functions from agent.py.
"""

# Import Streamlit for the web application UI.
import streamlit as st

# Import the required agent functions for loading, indexing, retrieval, and answer generation.
from agent import answer, build_index, load_documents, search


# This function initializes the in-memory index once per user session.
def initialize_index() -> None:
    # If the index is already ready, skip rebuilding.
    if st.session_state.get("index_ready", False):
        return

    # Load customer health chunks and build the retrieval index.
    chunks = load_documents()
    build_index(chunks)

    # Persist basic metadata for sidebar display.
    st.session_state["index_ready"] = True
    st.session_state["chunks"] = chunks
    st.session_state["total_chunks"] = len(chunks)
    st.session_state["data_sources"] = sorted({chunk["source"] for chunk in chunks})


# This callback sets a sample query when an example button is clicked.
def set_example_query(text: str) -> None:
    st.session_state["query_input"] = text


# Configure page metadata and layout.
st.set_page_config(page_title="Customer Health Finder", page_icon="🔍", layout="wide")

# Render title and subtitle.
st.title("🔍 Customer Health Finder")
st.caption("AI-powered enterprise Customer Health Finder")

# Initialize persistent state keys for stable reruns.
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""
if "last_answer" not in st.session_state:
    st.session_state["last_answer"] = ""
if "last_sources" not in st.session_state:
    st.session_state["last_sources"] = []

# Build/cached index with startup spinner and graceful error handling.
try:
    with st.spinner("Loading customer data and preparing search index..."):
        initialize_index()
except Exception as exc:
    st.error("Failed to initialize Customer Health Finder.")
    st.exception(exc)
    st.stop()

# Populate sidebar metadata and workflow guidance.
with st.sidebar:
    st.header("Overview")
    st.metric("Total chunks loaded", st.session_state.get("total_chunks", 0))

    st.subheader("Data sources")
    for source in st.session_state.get("data_sources", []):
        st.write(f"- `{source}`")

    st.subheader("How it works")
    st.write("1. Load and index account + signals context.")
    st.write("2. Retrieve top matching accounts by query intent.")
    st.write("3. Use Claude to synthesize actions and insights.")

# Show example query buttons for quick testing.
st.markdown("### Example queries")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Give me health of <Account>", use_container_width=True):
        set_example_query("Give me health of ACC-1004")
with col2:
    if st.button("Give me list of At Risk Accounts", use_container_width=True):
        set_example_query("Give me list of At Risk Accounts")
with col3:
    if st.button("What can i do to improve account health", use_container_width=True):
        set_example_query("What can i do to improve account health")

# Main query input and search button.
st.markdown("### Ask a question")
query = st.text_input(
    "Enter your question",
    key="query_input",
    placeholder="e.g., Which accounts are at risk in the next 60 days?",
)

if st.button("Search", type="primary"):
    if not query.strip():
        st.warning("Please enter a query before searching.")
    else:
        try:
            # Show spinner while running retrieval and Claude generation.
            with st.spinner("Analyzing customer portfolio..."):
                top_sources = search(query, top_k=3)
                llm_answer = answer(query)

            # Persist results in session state for visibility after reruns.
            st.session_state["last_sources"] = top_sources
            st.session_state["last_answer"] = llm_answer
        except Exception as exc:
            st.error("Something went wrong while running the analysis.")
            st.exception(exc)

# Render answer box and source details once results exist.
if st.session_state.get("last_answer"):
    st.markdown("### Claude answer")
    st.info(st.session_state["last_answer"])

    st.markdown("### Sources used")
    sources = st.session_state.get("last_sources", [])
    if not sources:
        st.write("No sources available.")
    else:
        for i, source in enumerate(sources, start=1):
            expander_title = (
                f"Source {i} — account: {source.get('id', 'n/a')} | "
                f"type: {source.get('type', 'n/a')} | score: {source.get('score', 'n/a')}"
            )
            with st.expander(expander_title):
                st.write(source.get("text", ""))

