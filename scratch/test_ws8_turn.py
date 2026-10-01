import os
os.environ["ENVIRONMENT"] = "test"
os.environ["MONGODB_URL"] = "mongodb://localhost:27017"
os.environ["MONGODB_DATABASE"] = "test_ai_legal_assistance"
os.environ["JWT_SECRET"] = "test_jwt_secret_must_be_at_least_32_chars_long"

import asyncio
import json
import sys
sys.path.insert(0, r"D:\112\backend")

from evals.runner import run_scenario_evaluation

async def main():
    scenarios = json.load(open(r"D:\112\backend\evals\dataset.json", encoding="utf-8"))
    ws8 = [s for s in scenarios if s["id"] == "womens_safety_008"][0]
    res = await run_scenario_evaluation(ws8)
    for k, v in res.items():
        print(f"{k}: {v}")

asyncio.run(main())
