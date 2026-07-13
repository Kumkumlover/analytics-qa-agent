from agent import setup_agent

vn = setup_agent("analytics.db")

context_prompt = """Previous Chat History:
User: Who are our highest paying customers?
Assistant: Could you clarify how you define 'highest paying'? Do you mean customers with the highest total spend across all orders, or those with the highest average spend per order? Also, how many top customers would you like to see?
User: both highest total and higheast avg spend
Assistant: Would you like to see two separate lists of top customers (one ranked by total spend and another by average spend), or a single list? Also, how many top customers should we display?

Current Request: make 2 lists, 10 customers each
(Please answer the current request using the context of the chat history if needed)"""

raw_response = vn.generate_sql(context_prompt)
print(f"RAW RESPONSE:\n{raw_response}")
print(f"CONTAINS SELECT: {'SELECT' in raw_response.upper()}")
