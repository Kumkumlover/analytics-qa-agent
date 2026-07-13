from agent import setup_agent

vn = setup_agent("analytics.db")
vn.train(documentation="CRITICAL INSTRUCTION: If a user's question is ambiguous or underspecified (e.g., 'How many users did we have?' without specifying timeframe or metric), DO NOT guess the SQL. Instead, output a direct conversational question asking for clarification (e.g. 'Do you mean total registered customers, or active users in a specific timeframe?'). Ensure this response does NOT contain the word SELECT.")
print("Training data injected successfully.")
