from agent import setup_agent

vn = setup_agent("analytics.db")
prompt = "Who are our highest paying costumers?"
raw_response = vn.generate_sql(prompt)
print(f"RAW RESPONSE: {raw_response}")
print(f"CONTAINS SELECT: {'SELECT' in raw_response.upper()}")
