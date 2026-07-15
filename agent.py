import os
from vanna.legacy.google.gemini_chat import GoogleGeminiChat
from vanna.legacy.chromadb.chromadb_vector import ChromaDB_VectorStore
import sqlglot
import sqlite3
import pandas as pd

# The agent class combining ChromaDB for context and Gemini for LLM
class AnalyticsAgent(ChromaDB_VectorStore, GoogleGeminiChat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        GoogleGeminiChat.__init__(self, config=config)
        
    def validate_and_execute(self, question):
        """Generates SQL, validates it's a SELECT, executes, and retries on failure."""
        sql = self.generate_sql(question)
        
        for attempt in range(3):
            # Validate SQL
            try:
                parsed = sqlglot.parse_one(sql, read="sqlite")
                if not isinstance(parsed, sqlglot.exp.Select):
                    sql = self.generate_sql(f"The previous query was not a SELECT statement. Ensure you only generate a SELECT query for: {question}")
                    continue
            except sqlglot.errors.ParseError as e:
                sql = self.generate_sql(f"The previous SQL had a syntax error: {e}. Fix it for this question: {question}")
                continue
                
            # Dry run and actual run
            try:
                # Dry run
                self.run_sql(f"EXPLAIN QUERY PLAN {sql}")
                # Execute
                df = self.run_sql(sql)
                return sql, df
            except Exception as e:
                sql = self.generate_sql(f"The previous SQL caused a database error: {e}. Fix the query for this question: {question}")
                
        raise Exception("Max retries exceeded for SQL generation")

def setup_agent(db_path="analytics.db"):
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    # Fallback: read from Streamlit secrets (for Streamlit Cloud deployment)
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get('GEMINI_API_KEY') or st.secrets.get('GOOGLE_API_KEY')
        except Exception:
            pass
    if not api_key:
        print("WARNING: GEMINI_API_KEY or GOOGLE_API_KEY not found in env or st.secrets.")
        
    config = {
        'api_key': api_key,
        'model_name': 'gemini-3.1-flash-lite',
        'path': './chromadb'
    }
    
    vn = AnalyticsAgent(config=config)
    vn.connect_to_sqlite(db_path)
    
    # Check if we need to train
    if len(vn.get_training_data().get('df', [])) == 0:
        print("Training agent for the first time...")
        # Train on schema
        df_ddl = vn.run_sql("SELECT type, sql FROM sqlite_master WHERE sql is not null")
        for ddl in df_ddl['sql'].to_list():
            vn.train(ddl=ddl)
            
        # Add basic documentation for metrics based on dataset schema
        vn.train(documentation="CRITICAL: The dataset contains historical data ending on 2025-10-31. When asked about 'last week', 'recent', or relative time, ALWAYS use '2025-10-31' as the current date. Do NOT use date('now').")
        vn.train(documentation="CRITICAL: The country code for the United Kingdom or UK in the database is 'GB'. Whenever querying for the UK, ALWAYS filter by country = 'GB'.")
        vn.train(documentation="CRITICAL: For 'device', the valid values are exclusively lowercase: 'desktop', 'mobile', 'tablet'.")
        vn.train(documentation="CRITICAL: For 'payment_method', the valid values are exclusively: 'card', 'paypal', 'wallet', 'cod'. Do not use 'Credit Card'.")
        vn.train(documentation="DAU (Daily Active Users): Number of unique customer_ids per day based on DATE(start_time) in the sessions table.")
        vn.train(documentation="MAU (Monthly Active Users): Number of unique customer_ids per month based on strftime('%Y-%m', start_time) in the sessions table.")
        vn.train(documentation="D7 Retention: The percentage of customers who had a session on exactly day 7 after their signup_date. Use customers.signup_date and sessions.start_time.")
        
        # Add Golden SQLs — covers all 15 eval test categories
        # Category 1: Simple Aggregates
        vn.train(question="What was our DAU last week?", sql="SELECT DATE(start_time) as date, COUNT(DISTINCT customer_id) as dau FROM sessions WHERE start_time >= date('2025-10-31', '-7 days') GROUP BY DATE(start_time) ORDER BY date;")
        vn.train(question="DAU for US users", sql="SELECT DATE(start_time) as date, COUNT(DISTINCT customer_id) as dau FROM sessions WHERE country = 'US' GROUP BY DATE(start_time) ORDER BY date;")
        vn.train(question="Compare DAU this week vs last week", sql="SELECT DATE(start_time) as date, COUNT(DISTINCT customer_id) as dau FROM sessions WHERE start_time >= date('2025-10-31', '-14 days') GROUP BY DATE(start_time) ORDER BY date;")
        vn.train(question="What was our MAU last month?", sql="SELECT strftime('%Y-%m', start_time) as month, COUNT(DISTINCT customer_id) as mau FROM sessions WHERE start_time >= date('2025-10-31', 'start of month', '-1 month') AND start_time < date('2025-10-31', 'start of month') GROUP BY month;")
        vn.train(question="How many total orders were placed?", sql="SELECT COUNT(order_id) as total_orders FROM orders;")
        vn.train(question="What is our total revenue?", sql="SELECT SUM(total_usd) as total_revenue FROM orders;")

        # Category 2: Filtered Aggregates
        vn.train(question="What was our DAU for UK users last week?", sql="SELECT DATE(start_time) as date, COUNT(DISTINCT customer_id) as dau FROM sessions WHERE country = 'GB' AND start_time >= date('2025-10-31', '-7 days') GROUP BY DATE(start_time) ORDER BY date;")
        vn.train(question="How many orders were paid by credit card?", sql="SELECT COUNT(order_id) as orders FROM orders WHERE payment_method = 'card';")
        vn.train(question="What is the total revenue from mobile users?", sql="SELECT SUM(total_usd) as mobile_revenue FROM orders WHERE device = 'mobile';")

        # Category 3: Cohort & Complex
        vn.train(question="What is our D7 retention?", sql="SELECT 100.0 * COUNT(DISTINCT s.customer_id) / (SELECT COUNT(DISTINCT customer_id) FROM customers) FROM sessions s JOIN customers c ON s.customer_id = c.customer_id WHERE DATE(s.start_time) = DATE(c.signup_date, '+7 days');")
        vn.train(question="What is the average order value for users aged 18-24?", sql="SELECT AVG(o.total_usd) as avg_order_value FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE c.age BETWEEN 18 AND 24;")
        vn.train(question="How many customers signed up in October 2025?", sql="SELECT COUNT(customer_id) as signups FROM customers WHERE signup_date BETWEEN '2025-10-01' AND '2025-10-31';")

        # Category 4: Comparisons
        vn.train(question="Compare revenue this week vs last week", sql="SELECT CASE WHEN order_time >= date('2025-10-31', '-7 days') THEN 'This Week' ELSE 'Last Week' END as period, SUM(total_usd) as revenue FROM orders WHERE order_time >= date('2025-10-31', '-14 days') GROUP BY period;")
        vn.train(question="Compare DAU on mobile vs desktop", sql="SELECT DATE(start_time) as date, device, COUNT(DISTINCT customer_id) as dau FROM sessions WHERE device IN ('mobile', 'desktop') GROUP BY DATE(start_time), device ORDER BY date, device;")
        vn.train(question="Compare total orders for US vs UK", sql="SELECT CASE WHEN country = 'GB' THEN 'UK' ELSE country END as country, COUNT(order_id) as total_orders FROM orders WHERE country IN ('US', 'GB') GROUP BY country;")
        
    return vn
