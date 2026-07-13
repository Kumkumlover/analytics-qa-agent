import os
from agent import setup_agent

def mimic_app_logic(vn, prompt):
    print(f"\n--- QUERY: {prompt} ---")
    try:
        raw_response = vn.generate_sql(prompt)
        if "SELECT" not in raw_response.upper():
            print(f"CLARIFICATION DETECTED:\n{raw_response}")
            return "CLARIFICATION", raw_response
        else:
            sql, df = vn.validate_and_execute(prompt)
            print(f"SQL GENERATED:\n{sql}")
            print(f"DATAFRAME (shape {df.shape}):")
            print(df.head())
            return "SUCCESS", df
    except Exception as e:
        print(f"ERROR: {e}")
        return "ERROR", str(e)

def main():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    os.environ['GEMINI_API_KEY'] = api_key
    vn = setup_agent("analytics.db")
    
    queries = [
        "Compare DAU on mobile vs desktop",
        "Compare total orders for US vs UK",
        "Who are our top customers?",
        "What are our worst selling products?",
        "Show me the top 5 countries and top 5 products"
    ]
    
    for q in queries:
        mimic_app_logic(vn, q)

if __name__ == "__main__":
    main()
