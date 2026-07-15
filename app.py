import streamlit as st
import pandas as pd
from agent import setup_agent

st.set_page_config(page_title="Analytics Q&A Agent", layout="wide")

# Initialize agent (core — must succeed)
@st.cache_resource
def get_agent():
    return setup_agent("analytics.db")

# Initialize semantic cache (optional — gracefully degrade if model download hangs)
@st.cache_resource
def get_cache():
    try:
        from cache import SemanticCache
        return SemanticCache(threshold=0.25)
    except Exception as e:
        print(f"WARNING: Semantic cache failed to load: {e}. Running without cache.")
        return None

try:
    vn = get_agent()
except Exception as e:
    st.error(f"Error initializing agent: {e}")
    st.stop()

semantic_cache = get_cache()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
st.sidebar.title("Analytics Q&A Agent")
st.sidebar.markdown("Ask natural language questions about your e-commerce data.")
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sql"):
            with st.expander("📋 View SQL Query"):
                st.code(msg["sql"], language="sql")
        if msg.get("dataframe") is not None:
            st.dataframe(msg["dataframe"])

# Handle new user input
if prompt := st.chat_input("Ask a question about your data..."):
    # Add user message to state and display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            is_clarification = False
            response_text = ""
            sql = None
            df = None
            try:
                # 1. Check Cache (only if cache loaded successfully)
                cached_sql = None
                if semantic_cache is not None:
                    cached_sql = semantic_cache.get(prompt)
                
                if cached_sql:
                    sql = cached_sql
                    df = vn.run_sql(sql)
                    response_text = f"Found {len(df)} results (from cache)."
                else:
                    # 2. Ask LLM (generate SQL + validation loop)
                    # Build context-aware prompt so the LLM remembers previous clarifications
                    context_prompt = prompt
                    if len(st.session_state.messages) > 1:
                        history = "\\n".join([f"{m['role'].capitalize()}: {m['content'][:200]}" for m in st.session_state.messages[-5:-1]])
                        context_prompt = f"Previous Chat History:\\n{history}\\n\\nCurrent Request: {prompt}\\n(Please answer the current request using the context of the chat history if needed)"
                        
                    # For clarification, we check the raw response first to avoid throwing Vanna into a 10x max-retries loop
                    raw_response = vn.generate_sql(context_prompt)
                    
                    if "SELECT" not in raw_response.upper():
                        is_clarification = True
                        response_text = raw_response
                    else:
                        try:
                            sql, df = vn.validate_and_execute(context_prompt)
                            response_text = f"Found {len(df)} results."
                            # Cache using the short prompt (only if cache loaded)
                            if semantic_cache is not None:
                                semantic_cache.put(prompt, sql)

                        except Exception as e:
                            st.error(f"Error processing query: {e}")
                            st.stop()

            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.stop()
                
        # Display response
        st.markdown(response_text)
        if sql:
            with st.expander("📋 View SQL Query"):
                st.code(sql, language="sql")
        if df is not None:
            st.dataframe(df)
            
        # Save to history
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_text,
            "sql": sql,
            "dataframe": df
        })
