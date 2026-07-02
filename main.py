import asyncio
import json
import sys

from llm_planner import plan_mission
from validator import validate_mission, MissionValidationError
from executor import execute_mission


def run(prompt: str):
    print(f"\n[1/3] Prompt received:\n  \"{prompt}\"\n")

    print("[2/3] Asking LLM to propose a mission plan...")
    candidate = plan_mission(prompt)
    print("LLM proposed:")
    print(json.dumps(candidate, indent=2))

    print("\n[2/3] Validating candidate plan against schema + safety rules...")
    try:
        validated = validate_mission(candidate)
    except MissionValidationError as e:
        print(f"\nMISSION REJECTED: {e}")
        print("Nothing was sent to the vehicle.")
        sys.exit(1)
    print("Validation passed. Mission is safe to execute.")

    print("\n[3/3] Handing validated JSON to deterministic executor...")
    asyncio.run(execute_mission(validated))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python main.py "<your natural language command>"')
        sys.exit(1)

    user_prompt = " ".join(sys.argv[1:])
    run(user_prompt)
