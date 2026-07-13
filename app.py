import streamlit as st
import pandas as pd
import plotly.express as px
from agent import setup_agent
from cache import SemanticCache

st.set_page_config(page_title="Analytics Q&A Agent", layout="wide")

# Initialize agent and cache
@st.cache_resource
def get_backend():
    agent = setup_agent("analytics.db")
    cache = SemanticCache(threshold=0.25)
    return agent, cache

try:
    vn, semantic_cache = get_backend()
except Exception as e:
    st.error(f"Error initializing agent: {e}")
    st.stop()

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
        if msg.get("chart") is not None:
            st.plotly_chart(msg["chart"], use_container_width=True)

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
            fig = None
            
            try:
                # 1. Check Cache
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
                            semantic_cache.put(prompt, sql) # Cache using the short prompt

                        except Exception as e:
                            st.error(f"Error processing query: {e}")
                            st.stop()
                
                # 3. Generate Chart (if not a clarification)
                if not is_clarification and df is not None and not df.empty:
                    # Basic auto-charting logic if the LLM doesn't generate one
                    if len(df.columns) >= 2:
                        x_col = df.columns[0]
                        # try to find a numeric y column
                        numeric_cols = df.select_dtypes(include='number').columns
                        if len(numeric_cols) > 0:
                            y_col = numeric_cols[0] if numeric_cols[0] != x_col else (numeric_cols[1] if len(numeric_cols)>1 else numeric_cols[0])
                            try:
                                # Simple heuristic for bar vs line
                                if df[x_col].nunique() < 20:
                                    fig = px.bar(df, x=x_col, y=y_col)
                                else:
                                    fig = px.line(df, x=x_col, y=y_col)
                            except:
                                pass

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
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
            
        # Save to history
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_text,
            "sql": sql,
            "dataframe": df,
            "chart": fig
        })
