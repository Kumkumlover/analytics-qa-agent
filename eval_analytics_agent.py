"""
Braintrust LLM Evals for Analytics Q&A Agent
=============================================
Covers 5 query categories with 3 targeted scorers:
  - sql_validity:            Is the output a valid SELECT statement?
  - result_non_empty:        Does the SQL return at least 1 row of actual data?
  - clarification_guardrail: For ambiguous queries, did the agent ask rather than guess?
"""

import os
import sqlite3

import sqlglot
from braintrust import Eval

# ── Environment ──────────────────────────────────────────────────────────────
os.environ.setdefault("BRAINTRUST_API_KEY", "sk-JgwSMtu8gQB9boSwpFOxhzzf4wlUAMCH0kfnS31O0kY1ozVM")
os.environ.setdefault("GEMINI_API_KEY",     "")

DB_PATH = "analytics.db"
PROJECT_NAME = "Analytics Q&A Agent"  # matches your Braintrust project

# ── Dataset ───────────────────────────────────────────────────────────────────
# Each case:
#   input    – the natural-language question sent to the agent
#   expected – "sql"  → agent should produce a SELECT + non-empty rows
#              "clarification" → agent should ask a question, NOT produce SQL
#   category – for labelling in the UI
# Note: Braintrust passes input directly as a string to the task function.
# We embed expected and category into metadata for scorers to access.
DATASET = [
    # ── Category 1: Simple Aggregates ────────────────────────────────────────
    {"input": "What was our MAU last month?",
     "expected": "sql", "metadata": {"category": "simple_aggregate", "expected": "sql"}},

    {"input": "How many total orders were placed?",
     "expected": "sql", "metadata": {"category": "simple_aggregate", "expected": "sql"}},

    {"input": "What is our total revenue?",
     "expected": "sql", "metadata": {"category": "simple_aggregate", "expected": "sql"}},

    # ── Category 2: Filtered Aggregates ──────────────────────────────────────
    {"input": "What was our DAU for UK users last week?",
     "expected": "sql", "metadata": {"category": "filtered_aggregate", "expected": "sql",
                                      "note": "Must use country='GB', not 'UK'"}},

    {"input": "How many orders were paid by credit card?",
     "expected": "sql", "metadata": {"category": "filtered_aggregate", "expected": "sql",
                                      "note": "Must use payment_method='card'"}},

    {"input": "What is the total revenue from mobile users?",
     "expected": "sql", "metadata": {"category": "filtered_aggregate", "expected": "sql",
                                      "note": "Must use device='mobile' (lowercase)"}},

    # ── Category 3: Cohort & Complex ─────────────────────────────────────────
    {"input": "What is our D7 retention?",
     "expected": "sql", "metadata": {"category": "cohort", "expected": "sql"}},

    {"input": "What is the average order value for users aged 18-24?",
     "expected": "sql", "metadata": {"category": "cohort", "expected": "sql"}},

    {"input": "How many customers signed up in October 2025?",
     "expected": "sql", "metadata": {"category": "cohort", "expected": "sql"}},

    # ── Category 4: Comparisons ───────────────────────────────────────────────
    {"input": "Compare revenue this week vs last week",
     "expected": "sql", "metadata": {"category": "comparison", "expected": "sql"}},

    {"input": "Compare DAU on mobile vs desktop",
     "expected": "sql", "metadata": {"category": "comparison", "expected": "sql"}},

    {"input": "Compare total orders for US vs UK",
     "expected": "sql", "metadata": {"category": "comparison", "expected": "sql",
                                      "note": "UK must resolve to GB"}},

    # ── Category 5: Ambiguous / Edge-Case ────────────────────────────────────
    {"input": "Who are our top customers?",
     "expected": "clarification", "metadata": {"category": "ambiguous", "expected": "clarification"}},

    {"input": "What are our worst selling products?",
     "expected": "clarification", "metadata": {"category": "ambiguous", "expected": "clarification"}},

    {"input": "Show me the top 5 countries and top 5 products",
     "expected": "clarification", "metadata": {"category": "edge_case", "expected": "clarification",
                                                 "note": "Multi-dataset refusal"}},

    # ── Category 6: Advanced Joins & Math ─────────────────────────────────────
    {"input": "What is the average rating for products in the Electronics category?", "expected": "sql", "metadata": {"category": "joins", "expected": "sql"}},
    {"input": "Which customers have placed more than 5 orders?", "expected": "sql", "metadata": {"category": "aggregation", "expected": "sql"}},
    {"input": "Top 3 categories by total revenue", "expected": "sql", "metadata": {"category": "aggregation", "expected": "sql"}},
    {"input": "What is the average cart size for desktop users?", "expected": "sql", "metadata": {"category": "filtered_aggregate", "expected": "sql"}},
    {"input": "Customers who signed up but never placed an order", "expected": "sql", "metadata": {"category": "joins", "expected": "sql"}},
    
    # ── Category 7: Date Rules ──────────────────────────────────────────────
    {"input": "Revenue last week", "expected": "sql", "metadata": {"category": "date_rule", "expected": "sql"}},
    {"input": "How many users signed up in 2024?", "expected": "sql", "metadata": {"category": "date_rule", "expected": "sql"}},
    {"input": "Sales in the last 30 days", "expected": "sql", "metadata": {"category": "date_rule", "expected": "sql"}},
    {"input": "Number of sessions yesterday", "expected": "sql", "metadata": {"category": "date_rule", "expected": "sql"}},
    {"input": "Compare revenue from October vs September", "expected": "sql", "metadata": {"category": "comparison", "expected": "sql"}},

    # ── Category 8: Geographic & Device Rules ────────────────────────────────
    {"input": "Sales in the United Kingdom", "expected": "sql", "metadata": {"category": "geo_rule", "expected": "sql", "note": "Must use country='GB'"}},
    {"input": "Mobile sessions in the UK", "expected": "sql", "metadata": {"category": "geo_rule", "expected": "sql", "note": "device='mobile' and country='GB'"}},
    {"input": "Compare desktop and tablet revenue in the US", "expected": "sql", "metadata": {"category": "comparison", "expected": "sql"}},
    {"input": "Number of users from Great Britain", "expected": "sql", "metadata": {"category": "geo_rule", "expected": "sql", "note": "Must use country='GB'"}},
    {"input": "Tablet orders using paypal", "expected": "sql", "metadata": {"category": "filtered_aggregate", "expected": "sql", "note": "device='tablet', payment_method='paypal'"}},

    # ── Category 9: Payment Methods ─────────────────────────────────────────
    {"input": "How many orders used paypal?", "expected": "sql", "metadata": {"category": "payment_rule", "expected": "sql", "note": "payment_method='paypal'"}},
    {"input": "Revenue from wallet payments", "expected": "sql", "metadata": {"category": "payment_rule", "expected": "sql", "note": "payment_method='wallet'"}},
    {"input": "Cash on delivery orders vs credit card", "expected": "sql", "metadata": {"category": "payment_rule", "expected": "sql", "note": "'cod' and 'card'"}},
    {"input": "Total discount given on card purchases", "expected": "sql", "metadata": {"category": "payment_rule", "expected": "sql"}},
    {"input": "Average order value for paypal", "expected": "sql", "metadata": {"category": "payment_rule", "expected": "sql"}},

    # ── Category 10: Specific Edge Cases & Ambiguity ────────────────────────
    {"input": "Who are our best users?", "expected": "clarification", "metadata": {"category": "ambiguous", "expected": "clarification"}},
    {"input": "What is the best product?", "expected": "clarification", "metadata": {"category": "ambiguous", "expected": "clarification"}},
    {"input": "Are we doing well?", "expected": "clarification", "metadata": {"category": "ambiguous", "expected": "clarification"}},
    {"input": "Show me the worst categories and best countries", "expected": "clarification", "metadata": {"category": "edge_case", "expected": "clarification"}},
    {"input": "What was the highest single transaction?", "expected": "sql", "metadata": {"category": "aggregation", "expected": "sql"}},
    {"input": "Which product has the highest margin?", "expected": "sql", "metadata": {"category": "aggregation", "expected": "sql"}},
    {"input": "Total events logged in the system", "expected": "sql", "metadata": {"category": "simple_aggregate", "expected": "sql"}},
    {"input": "Compare average rating of 5-star reviews to 1-star reviews", "expected": "clarification", "metadata": {"category": "ambiguous", "expected": "clarification"}},
    {"input": "Number of users who opted in to marketing", "expected": "sql", "metadata": {"category": "filtered_aggregate", "expected": "sql"}},
    {"input": "What is the email of the person who spent the most?", "expected": "sql", "metadata": {"category": "joins", "expected": "sql"}},
]

# ── Agent Singleton ──────────────────────────────────────────────────────────
# Initialize once so parallel Braintrust threads share the same instance
# and don't race to create a fresh ChromaDB from scratch simultaneously.
import threading
_agent_lock = threading.Lock()
_vn = None

def get_agent():
    global _vn
    with _agent_lock:
        if _vn is None:
            from agent import setup_agent
            _vn = setup_agent(DB_PATH)
    return _vn

import time

def task(input_data):
    """
    Braintrust calls task(input) where input is the raw string from the dataset.
    Returns a dict with sql, response, and row_count.

    IMPORTANT: We intentionally use generate_sql + run_sql directly rather than
    validate_and_execute(), because validate_and_execute() calls generate_sql()
    internally a second time, producing a potentially different SQL than what we
    already checked for clarification. This avoids a double-LLM-call bug.
    """
    # Throttle strictly to avoid Gemini free-tier 15 RPM limit (1 request every 4 seconds)
    time.sleep(4.5)

    # Braintrust passes input directly as a string
    question = input_data if isinstance(input_data, str) else input_data["input"]
    vn = get_agent()

    # Single LLM call — check for clarification vs SQL
    sql = vn.generate_sql(question)

    if "SELECT" not in sql.upper():
        return {
            "sql": None,
            "response": sql,
            "row_count": -1,
        }

    # Execute the SQL we already have — no second LLM call
    try:
        df = vn.run_sql(sql)
        return {
            "sql": sql,
            "response": f"Found {len(df)} results.",
            "row_count": len(df),
        }
    except Exception as e:
        return {
            "sql": sql,
            "response": f"SQL Error: {e}",
            "row_count": -1,
        }


# ── Scorers ───────────────────────────────────────────────────────────────────
def sql_validity(output, expected, **kwargs):
    """
    Applies only when expected == 'sql'.
    Returns 1.0 if output SQL is a valid SELECT, else 0.0.
    """
    if expected != "sql":
        return None   # skip scorer for clarification cases
    sql = output.get("sql")
    if not sql:
        return 0.0
    try:
        parsed = sqlglot.parse_one(sql, read="sqlite")
        return 1.0 if isinstance(parsed, sqlglot.exp.Select) else 0.0
    except Exception:
        return 0.0


def result_non_empty(output, expected, **kwargs):
    """
    Applies only when expected == 'sql'.
    Returns 1.0 if the query returned ≥1 row (actual data accuracy check).
    Returns 0.0 if it returned 0 rows (string hallucination / wrong filter).
    """
    if expected != "sql":
        return None
    row_count = output.get("row_count", -1)
    if row_count < 0:
        return 0.0   # SQL errored or wasn't generated
    return 1.0 if row_count > 0 else 0.0


def clarification_guardrail(output, expected, **kwargs):
    """
    Applies only when expected == 'clarification'.
    Returns 1.0 if the agent asked a question (no SELECT in response).
    Returns 0.0 if the agent ran SQL anyway.
    """
    if expected != "clarification":
        return None
    response = output.get("response", "")
    return 1.0 if "SELECT" not in response.upper() else 0.0


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Eval(
        PROJECT_NAME,
        experiment_name="Analytics Agent – Full Gauntlet v1",
        data=[
            {
                "input":    case["input"],
                "expected": case["expected"],
                "metadata": case.get("metadata", {}),
            }
            for case in DATASET
        ],
        task=task,
        scores=[sql_validity, result_non_empty, clarification_guardrail],
        max_concurrency=1, # Critical for free-tier APIs
    )
