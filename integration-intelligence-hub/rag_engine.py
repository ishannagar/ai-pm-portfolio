"""
rag_engine.py

A simple RAG engine for enterprise integration support data.
It uses:
- LanceDB for vector storage
- Anthropic Claude for answer generation
- Anthropic embeddings if available, otherwise TF-IDF vectors
"""

# Standard library imports for JSON handling, filesystem paths, math, and text processing.
import json
import math
import os
import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

# Third-party imports for vector database and model API.
import anthropic
import lancedb


# Global constants for data paths and index settings.
DATA_DIR = "data"
LANCEDB_DIR = ".lancedb"
TABLE_NAME = "integration_chunks"
EMBEDDING_DIM = 256

# Global state to reuse the same vectorizer and table between function calls.
_VOCAB: Dict[str, int] = {}
_IDF: Dict[str, float] = {}
_TABLE = None
_USING_ANTHROPIC_EMBEDDINGS = False


# This helper tokenizes text into lowercase keywords for TF-IDF and keyword matching.
def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


# This helper builds a compact TF-IDF representation with fixed dimensionality.
def tfidf_vector(text: str, vocab: Dict[str, int], idf: Dict[str, float], dim: int = EMBEDDING_DIM) -> List[float]:
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * dim

    tf_counts = Counter(tokens)
    max_tf = max(tf_counts.values())
    vec = [0.0] * dim

    # Hash each token into one of `dim` buckets so vectors have fixed size for LanceDB.
    for token, count in tf_counts.items():
        tf = count / max_tf
        token_idf = idf.get(token, 1.0)
        weight = tf * token_idf
        bucket = hash(token) % dim
        vec[bucket] += weight

    # L2-normalize to make cosine-like comparisons more stable.
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


# This helper tries Anthropic embeddings first and returns None when not available.
def try_anthropic_embeddings(client: anthropic.Anthropic, texts: List[str]) -> List[List[float]] | None:
    global _USING_ANTHROPIC_EMBEDDINGS
    try:
        # The embeddings endpoint may vary by SDK/version; this call is wrapped safely.
        response = client.embeddings.create(
            model="claude-embedding-1",
            input=texts,
        )
        vectors = [item.embedding for item in response.data]
        _USING_ANTHROPIC_EMBEDDINGS = True
        return vectors
    except Exception:
        _USING_ANTHROPIC_EMBEDDINGS = False
        return None


# This function loads support data files and converts them into text chunks with metadata.
def load_documents() -> List[Dict]:
    chunks: List[Dict] = []
    chunk_id = 1

    # Load and flatten support tickets JSON into one chunk per ticket.
    with open(os.path.join(DATA_DIR, "support_tickets.json"), "r", encoding="utf-8") as f:
        tickets = json.load(f)
    for ticket in tickets:
        text = (
            f"Ticket ID: {ticket.get('id', '')}\n"
            f"Title: {ticket.get('title', '')}\n"
            f"System: {ticket.get('system', '')}\n"
            f"Error Code: {ticket.get('error_code', '')}\n"
            f"Error Message: {ticket.get('error_message', '')}\n"
            f"Root Cause: {ticket.get('root_cause', '')}\n"
            f"Resolution Steps: {'; '.join(ticket.get('resolution_steps', []))}\n"
            f"Severity: {ticket.get('severity', '')}\n"
            f"Resolved: {ticket.get('resolved', False)}"
        )
        chunks.append(
            {
                "chunk_id": f"chunk-{chunk_id}",
                "text": text,
                "source": "support_tickets.json",
                "type": "ticket",
                "system": ticket.get("system", ""),
            }
        )
        chunk_id += 1

    # Load and flatten error code catalog into one chunk per error code record.
    with open(os.path.join(DATA_DIR, "error_codes.json"), "r", encoding="utf-8") as f:
        error_codes = json.load(f)
    for err in error_codes:
        text = (
            f"Code: {err.get('code', '')}\n"
            f"System: {err.get('system', '')}\n"
            f"Description: {err.get('description', '')}\n"
            f"Common Causes: {'; '.join(err.get('common_causes', []))}\n"
            f"Resolution: {err.get('resolution', '')}"
        )
        chunks.append(
            {
                "chunk_id": f"chunk-{chunk_id}",
                "text": text,
                "source": "error_codes.json",
                "type": "error_code",
                "system": err.get("system", ""),
            }
        )
        chunk_id += 1

    # Load integration docs and split into paragraph-style chunks for retrieval.
    with open(os.path.join(DATA_DIR, "integration_docs.txt"), "r", encoding="utf-8") as f:
        docs_text = f.read().strip()

    raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", docs_text) if p.strip()]
    for paragraph in raw_paragraphs:
        chunks.append(
            {
                "chunk_id": f"chunk-{chunk_id}",
                "text": paragraph,
                "source": "integration_docs.txt",
                "type": "doc",
                "system": "",
            }
        )
        chunk_id += 1

    return chunks


# This function builds LanceDB index rows and stores all chunks with vectors + metadata.
def build_index(chunks: List[Dict]) -> None:
    global _VOCAB, _IDF, _TABLE

    # Build corpus statistics for TF-IDF fallback vectors.
    doc_freq = defaultdict(int)
    for ch in chunks:
        unique_tokens = set(tokenize(ch["text"]))
        for token in unique_tokens:
            doc_freq[token] += 1

    num_docs = max(1, len(chunks))
    _VOCAB = {token: i for i, token in enumerate(doc_freq.keys())}
    _IDF = {token: math.log((1 + num_docs) / (1 + df)) + 1.0 for token, df in doc_freq.items()}

    # Initialize Anthropic client for optional embedding generation.
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    texts = [ch["text"] for ch in chunks]
    embedding_vectors = try_anthropic_embeddings(client, texts)

    # If Anthropic embeddings are unavailable, generate TF-IDF vectors locally.
    if embedding_vectors is None:
        embedding_vectors = [tfidf_vector(t, _VOCAB, _IDF) for t in texts]

    # Prepare rows for LanceDB table insertion.
    rows = []
    for ch, vector in zip(chunks, embedding_vectors):
        rows.append(
            {
                "chunk_id": ch["chunk_id"],
                "text": ch["text"],
                "source": ch["source"],
                "type": ch["type"],
                "system": ch["system"],
                "vector": vector,
            }
        )

    # Connect to local LanceDB and recreate table with fresh index data.
    db = lancedb.connect(LANCEDB_DIR)
    if TABLE_NAME in db.table_names():
        db.drop_table(TABLE_NAME)
    _TABLE = db.create_table(TABLE_NAME, data=rows)


# This helper computes a simple keyword-overlap score for hybrid ranking.
def keyword_score(query: str, text: str) -> float:
    q_tokens = set(tokenize(query))
    t_tokens = set(tokenize(text))
    if not q_tokens or not t_tokens:
        return 0.0
    overlap = len(q_tokens.intersection(t_tokens))
    return overlap / max(1, len(q_tokens))


# This function searches relevant chunks using LanceDB vector search + keyword matching.
def search(query: str, top_k: int = 3) -> List[Dict]:
    global _TABLE
    if _TABLE is None:
        raise RuntimeError("Index not built. Call build_index(load_documents()) before search().")

    # Build query vector using the same embedding mode as index build.
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    query_vecs = try_anthropic_embeddings(client, [query]) if _USING_ANTHROPIC_EMBEDDINGS else None
    if query_vecs is None:
        query_vector = tfidf_vector(query, _VOCAB, _IDF)
    else:
        query_vector = query_vecs[0]

    # Retrieve a wider candidate pool from LanceDB, then rerank with keyword overlap.
    candidate_limit = max(10, top_k * 4)
    results_df = _TABLE.search(query_vector).limit(candidate_limit).to_pandas()

    reranked: List[Tuple[float, Dict]] = []
    for _, row in results_df.iterrows():
        base_score = 1.0 / (1.0 + float(row.get("_distance", 0.0)))
        kw_score = keyword_score(query, row["text"])
        hybrid = 0.65 * base_score + 0.35 * kw_score
        reranked.append(
            (
                hybrid,
                {
                    "chunk_id": row["chunk_id"],
                    "text": row["text"],
                    "source": row["source"],
                    "type": row["type"],
                    "system": row["system"],
                    "score": round(hybrid, 4),
                },
            )
        )

    reranked.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in reranked[:top_k]]


# This function answers a query by retrieving context and asking Claude to produce a grounded response.
def answer(query: str) -> str:
    # Retrieve top supporting chunks from the vector + keyword hybrid search.
    retrieved = search(query, top_k=3)

    # Build a compact context block to send into the LLM.
    context_blocks = []
    for i, ch in enumerate(retrieved, start=1):
        context_blocks.append(
            f"[Source {i}] ({ch['source']} | {ch['type']} | score={ch['score']})\n{ch['text']}"
        )
    context_text = "\n\n".join(context_blocks)

    # Ask Claude to answer using only retrieved context and include source references.
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    system_prompt = (
        "You are an enterprise integration support assistant. "
        "Answer using only the provided context. Be concise, actionable, and technically specific. "
        "If context is insufficient, say what is missing."
    )
    user_prompt = (
        f"User query:\n{query}\n\n"
        f"Retrieved context:\n{context_text}\n\n"
        "Return:\n"
        "1) Direct answer\n"
        "2) Recommended next troubleshooting steps\n"
        "3) Sources used (Source 1/2/3)"
    )
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=700,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return resp.content[0].text


# This test block runs the full pipeline with a sample query when executed directly.
if __name__ == "__main__":
    docs = load_documents()
    build_index(docs)
    test_query = "Salesforce OAuth token expired error"
    print(f"Query: {test_query}\n")
    print(answer(test_query))

