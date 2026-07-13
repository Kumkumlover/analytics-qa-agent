# Analytics Q&A Agent

An intelligent, context-aware Analytics Q&A Agent that translates natural language questions into accurate SQL queries, executes them against an e-commerce database, and returns the results. 

## (1) Architecture and Why We Chose It

**Stack:**
*   **LLM:** Google Gemini 
*   **Core Framework:** Vanna AI (RAG-based Text-to-SQL framework)
*   **Vector Database:** ChromaDB (Local)
*   **Database:** SQLite (`analytics.db` containing 7 e-commerce tables)
*   **Frontend:** Streamlit
*   **Evaluations:** Braintrust

**Why this architecture?**
We chose a **Retrieval-Augmented Generation (RAG)** approach using Vanna AI rather than sending massive static prompts to the LLM. 
1. **Accuracy & Cost:** By storing "Golden SQL" pairs and schema definitions in a local ChromaDB vector store, the agent dynamically retrieves only the exact context relevant to the user's question. This prevents token overflow, significantly reduces hallucination, and keeps API costs near zero.
2. **Performance:** We implemented a lightning-fast custom **Semantic Caching Layer** using `faiss-cpu` and `sentence-transformers`. If a user asks a question with high cosine similarity to a previously answered question (e.g., "Mobile revenue" vs "Revenue from mobile"), the agent bypasses the LLM entirely and serves the cached SQL instantly.

## (2) How We Handle Wrong/Hallucinated SQL

LLMs naturally hallucinate column names or produce invalid SQL syntax. We solve this using a multi-layered defense strategy:

1. **Clarification Guardrail:** We intercept non-data questions or highly ambiguous requests (e.g., "Are we doing well?") *before* generating SQL. The agent will refuse to generate SQL and instead ask the user for clarification, preventing garbage-in-garbage-out.
2. **Self-Correction Verification Loop:** The agent never blindly shows SQL results to the user. We use Vanna's internal validation loop (`validate_and_execute`). If the LLM generates invalid SQL that fails to run on the database, the agent catches the database traceback error, feeds it back to the LLM, and asks it to rewrite the query. It will self-correct up to 3 times to guarantee an executable payload.

## (3) How We Evaluate This

We use **Braintrust** to run automated, code-based evaluations against a gauntlet of 45 highly complex test cases spanning 10 analytical categories (e.g., Cohort analysis, complex joins, intentional ambiguity, date formatting).

Our evaluation loop scores the agent on three strict metrics:
1. **SQL Validity (100%):** Does the generated SQL compile and run without syntax errors?
2. **Result Non-Empty (100%):** Did the SQL return an actual dataset, or did it return an empty table because it hallucinated a filtering condition?
3. **Clarification Guardrail (100%):** Did the agent successfully detect intentional ambiguity and refuse to generate SQL?

By tying this into Braintrust, we can iterate on our system prompts and instantly measure regressions.

## (4) How We'd Scale to a 100+ Table Warehouse

To scale this agent from a local SQLite database to a massive enterprise warehouse (e.g., Snowflake, BigQuery) with 100+ tables, we would make four core architectural shifts:

1. **RAG Schema Retrieval over Full DDL:** At 100+ tables, injecting the entire schema into the LLM context window causes hallucination and extreme cost. Vanna natively scales to this by only retrieving the Top-K relevant schemas (using RAG) based on the user's specific question.
2. **Heavy Reliance on Documentation:** Large warehouses have cryptic column names. We would shift our training pipeline to prioritize thousands of "Golden SQL" examples and plain-english documentation strings mapped to business logic, rather than relying on the LLM to guess what `cust_rev_typ_2` means.
3. **Cloud Infrastructure Swap:** We would swap our local database connectors for enterprise connectors (`vn.connect_to_snowflake()`). 
4. **Centralized Caching & Vector DBs:** We would migrate our local ChromaDB to a managed cloud vector database (like Pinecone or pgvector), and upgrade our local FAISS semantic cache to a centralized Redis Vector cache. This ensures horizontal scalability across multiple frontend instances.
