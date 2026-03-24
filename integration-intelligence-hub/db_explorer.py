import streamlit as st
import lancedb
import pandas as pd

st.title("LanceDB Explorer")

db = lancedb.connect("./test_db")

# Show all tables
tables = db.table_names()
st.write(f"**Tables in DB:** {tables}")

# Select table
table_name = st.selectbox("Select table", tables)

if table_name:
    table = db.open_table(table_name)
    df = table.to_pandas()
    
    # Show stats
    st.write(f"**Total chunks:** {len(df)}")
    st.write(f"**Columns:** {list(df.columns)}")
    
    # Show data without vector column (too noisy)
    st.subheader("Stored chunks")
    display_cols = [c for c in df.columns if c != 'vector']
    st.dataframe(df[display_cols])
    
    # Search
    st.subheader("Search")
    query = st.text_input("Filter by text (contains)")
    if query:
        mask = df['text'].str.contains(query, case=False)
        st.dataframe(df[mask][display_cols])
