"""
app.py

Streamlit web app for the Integration Intelligence Hub.
It uses the RAG engine to search integration support data and answer questions with Claude.
"""

# Streamlit import for building the web UI.
import streamlit as st

# Import RAG functions from the local engine module.
from rag_engine import answer, build_index, load_documents, search


# This function initializes and caches the RAG index in session state so it only builds once.
def initialize_index() -> None:
    # Skip rebuild if initialization has already completed in this user session.
    if st.session_state.get("index_ready", False):
        return

    # Load source documents and build the vector index once.
    chunks = load_documents()
    build_index(chunks)

    # Store lightweight metadata for sidebar display and reuse.
    st.session_state["index_ready"] = True
    st.session_state["total_chunks"] = len(chunks)
    st.session_state["data_sources"] = sorted({chunk["source"] for chunk in chunks})


# This function updates the query input when an example-query button is clicked.
def set_example_query(query_text: str) -> None:
    st.session_state["query_input"] = query_text


# Configure the page for a professional wide layout and meaningful browser title.
st.set_page_config(
    page_title="Integration Intelligence Hub",
    page_icon="🔍",
    layout="wide",
)

# Render app title and subtitle in the main area.
st.title("🔍 Integration Intelligence Hub")
st.caption("AI-powered enterprise integration support")

# Initialize default state keys so interactions are stable across reruns.
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""
if "last_answer" not in st.session_state:
    st.session_state["last_answer"] = ""
if "last_sources" not in st.session_state:
    st.session_state["last_sources"] = []

# Build index with a spinner so users understand startup work is in progress.
try:
    with st.spinner("Loading support data and building search index..."):
        initialize_index()
except Exception as exc:
    st.error("Failed to initialize the Integration Intelligence Hub.")
    st.exception(exc)
    st.stop()

# Populate the sidebar with key metadata and a short "how it works" explainer.
with st.sidebar:
    st.header("Overview")
    st.metric("Total chunks loaded", st.session_state.get("total_chunks", 0))

    st.subheader("Data sources")
    for source_name in st.session_state.get("data_sources", []):
        st.write(f"- `{source_name}`")

    st.subheader("How it works")
    st.write("1. Retrieve relevant chunks from integration data.")
    st.write("2. Combine vector + keyword relevance for better matching.")
    st.write("3. Ask Claude to answer using retrieved evidence.")

# Add quick-start example queries as clickable buttons.
st.markdown("### Example queries")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Salesforce OAuth token expired", use_container_width=True):
        set_example_query("Salesforce OAuth token expired")
with col2:
    if st.button("HubSpot rate limit 429 error", use_container_width=True):
        set_example_query("HubSpot rate limit 429 error")
with col3:
    if st.button("ServiceNow webhook timeout", use_container_width=True):
        set_example_query("ServiceNow webhook timeout")

# Query input and search action live in the main content area.
st.markdown("### Ask a support question")
query = st.text_input(
    "Enter your query",
    key="query_input",
    placeholder="e.g., Salesforce OAuth token expired error during nightly sync",
)

# The search button triggers retrieval + answer generation.
if st.button("Search", type="primary"):
    if not query.strip():
        st.warning("Please enter a query before searching.")
    else:
        try:
            # Show a loading spinner while retrieval and answer generation run.
            with st.spinner("Searching knowledge base and generating answer..."):
                retrieved_sources = search(query, top_k=3)
                generated_answer = answer(query)

            # Persist latest results in session state so they remain visible on reruns.
            st.session_state["last_sources"] = retrieved_sources
            st.session_state["last_answer"] = generated_answer
        except Exception as exc:
            st.error("Something went wrong while processing your request.")
            st.exception(exc)

# Render answer and sources if we have a successful prior result.
if st.session_state.get("last_answer"):
    st.markdown("### Claude answer")
    st.info(st.session_state["last_answer"])

    st.markdown("### Sources used")
    sources = st.session_state.get("last_sources", [])
    if not sources:
        st.write("No sources available.")
    else:
        for idx, source in enumerate(sources, start=1):
            title = (
                f"Source {idx} — {source.get('source', 'unknown')} | "
                f"type: {source.get('type', 'n/a')} | "
                f"score: {source.get('score', 'n/a')}"
            )
            with st.expander(title):
                st.write(source.get("text", ""))

