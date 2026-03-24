"""
explore_lancedb.py
See exactly what gets stored in a vector database.
"""

import lancedb
import json
import os

# Step 1 — Connect to LanceDB (creates a folder called 'test_db')
print("Connecting to LanceDB...")
db = lancedb.connect("./test_db")

# Step 2 — Create some sample data
# In real RAG, these would be your document chunks
# Each chunk has: text, source, and a vector (embedding)
# We'll use fake simple vectors for now just to see the structure

sample_data = [
    {
        "id": "1",
        "text": "Salesforce OAuth token expired after 2 hours. Re-authenticate to fix.",
        "source": "support_tickets.json",
        "type": "ticket",
        # Fake vector — in real RAG this would be 384 numbers from embedding model
        # We use 4 numbers just to show the concept
        "vector": [0.2, 0.8, 0.1, 0.9]
    },
    {
        "id": "2", 
        "text": "HubSpot rate limit exceeded. 429 error. Wait 10 seconds and retry.",
        "source": "error_codes.json",
        "type": "error_code",
        "vector": [0.1, 0.3, 0.9, 0.2]
    },
    {
        "id": "3",
        "text": "OAuth2 authentication errors occur when session tokens expire silently.",
        "source": "integration_docs.txt",
        "type": "documentation",
        "vector": [0.2, 0.7, 0.1, 0.8]
    },
    {
        "id": "4",
        "text": "ServiceNow webhook timeout. Increase timeout threshold in connector settings.",
        "source": "support_tickets.json",
        "type": "ticket",
        "vector": [0.9, 0.1, 0.3, 0.4]
    },
    {
        "id": "5",
        "text": "SAP SSL certificate expired. Renew certificate and restart connector.",
        "source": "error_codes.json",
        "type": "error_code",
        "vector": [0.5, 0.2, 0.8, 0.3]
    }
]

# Step 3 — Create a table and store the data
print("\nCreating table and storing chunks...")
table = db.create_table("integration_chunks", data=sample_data, mode="overwrite")
print(f"Stored {len(sample_data)} chunks in LanceDB")

# Step 4 — SEE what's stored (like SELECT * FROM table)
print("\n" + "="*60)
print("ALL DATA STORED IN VECTOR DB:")
print("="*60)
df = table.to_pandas()
for _, row in df.iterrows():
    print(f"\nID: {row['id']}")
    print(f"Text: {row['text']}")
    print(f"Source: {row['source']}")
    print(f"Type: {row['type']}")
    print(f"Vector: {row['vector']}")
    print("-"*40)

# Step 5 — SQL-style filter query
print("\n" + "="*60)
print("SQL-STYLE QUERY: Show only 'ticket' type chunks")
print("(Like: SELECT * FROM chunks WHERE type = 'ticket')")
print("="*60)
tickets_only = table.search().where("type = 'ticket'").to_pandas()
for _, row in tickets_only.iterrows():
    print(f"\n{row['id']}: {row['text']}")

# Step 6 — Vector similarity search
print("\n" + "="*60)
print("VECTOR SEARCH: Find chunks similar to 'OAuth authentication error'")
print("(No SQL — finds by meaning similarity)")
print("="*60)
# Search using a vector close to our OAuth chunks
query_vector = [0.2, 0.75, 0.1, 0.85]  # Similar to chunks 1 and 3
results = table.search(query_vector).limit(3).to_pandas()
print("\nTop 3 most similar chunks:")
for i, (_, row) in enumerate(results.iterrows()):
    print(f"\nRank {i+1}: {row['text']}")
    print(f"Source: {row['source']}")
    if '_distance' in row:
        print(f"Distance: {row['_distance']:.4f} (lower = more similar)")

print("\n" + "="*60)
print("KEY INSIGHT:")
print("="*60)
print("Chunk 1 (OAuth Salesforce) and Chunk 3 (OAuth2 docs)")
print("have similar vectors [0.2, 0.8, 0.1, 0.9] and [0.2, 0.7, 0.1, 0.8]")
print("So they appear as TOP results for an OAuth query")
print("\nChunk 4 (ServiceNow webhook) has very different vector [0.9, 0.1, 0.3, 0.4]")
print("So it appears LAST — even though it's also a support ticket")
print("\nThis is semantic search — finding by MEANING not by words!")