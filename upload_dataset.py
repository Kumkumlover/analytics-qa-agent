import os
from braintrust import init_dataset
from eval_analytics_agent import DATASET, PROJECT_NAME

os.environ.setdefault("BRAINTRUST_API_KEY", "sk-JgwSMtu8gQB9boSwpFOxhzzf4wlUAMCH0kfnS31O0kY1ozVM")

def upload():
    dataset = init_dataset(PROJECT_NAME, "Analytics_QA_Dataset")
    for case in DATASET:
        dataset.insert(
            input=case["input"],
            expected=case["expected"],
            metadata=case.get("metadata", {})
        )
    print(f"Uploaded {len(DATASET)} cases to Braintrust Dataset 'Analytics_QA_Dataset'.")

if __name__ == "__main__":
    upload()
