from agent import setup_agent

vn = setup_agent("analytics.db")

# Provide concrete examples of ambiguous questions and the EXACT text response expected (no SQL)
vn.train(question="How many users did we have?", sql="Do you mean total registered customers across all time, or active users within a specific timeframe (like last week or last month)?")
vn.train(question="What is our best product?", sql="Could you clarify how you define 'best'? For example, do you mean best by total revenue, highest quantity sold, or best profit margin?")
vn.train(question="Show me the revenue.", sql="Over what timeframe would you like to see the revenue? (e.g., today, last week, last month, or all time?)")

print("Ambiguous examples injected successfully.")
