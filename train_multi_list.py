from agent import setup_agent

vn = setup_agent("analytics.db")

# Provide an example to handle requests for multiple lists/datasets
vn.train(question="make 2 lists, 10 customers each", sql="I can only generate and display one dataset at a time. Would you like to see the top 10 customers by total spend first, or the top 10 by average spend?")
vn.train(question="show me top 5 products and top 5 customers", sql="I can only run one query at a time. Would you like to see the top products first, or the top customers?")

print("Multi-list examples injected successfully.")
