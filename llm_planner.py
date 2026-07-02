import json
import os
from groq import Groq

SYSTEM_PROMPT = """You are a mission planner for a single quadcopter drone
operating in a simulator. You translate a natural-language operator command
into a structured mission plan.

You MUST respond with ONLY a single JSON object, no markdown fences, no
prose, matching this exact shape:

{
  "mission_name": "<short descriptive string>",
  "vehicle_type": "drone",
  "command": "patrol_loop" | "point_to_point",
  "altitude_m": <number, 2 to 50>,
  "speed_ms": <number, 1 to 10>,
  "loop_count": <integer, 1 to 5>,
  "path_type": "perimeter_loop" | "custom",
  "waypoints_local_ned": [[north_m, east_m, down_m], ...],
  "return_to_start": true | false
}

Rules for building waypoints_local_ned:
- Coordinates are LOCAL, relative to the drone's home/takeoff position in
  metres, using NED convention: north (+ is north), east (+ is east),
  down (+ is down, so a positive altitude above ground is a NEGATIVE down
  value, e.g. 15m altitude => down = -15).
- Every waypoint in the list must use the SAME down value equal to
  -altitude_m (constant-altitude flight), unless the operator explicitly
  asks for a different altitude at a specific point.
- For "patrol the perimeter" / "patrol loop" type commands with no explicit
  shape given, generate a rectangular loop with 4 corners, roughly 20m x 20m,
  centred so the first waypoint is at [10, -10, down], going
  [10,-10,down] -> [10,10,down] -> [-10,10,down] -> [-10,-10,down].
- If the operator gives an explicit size (e.g. "50 metre square"), use that
  instead of the 20m default, keeping the same corner ordering pattern.
- If the operator says "loop it N times" or "twice" etc, set loop_count
  accordingly. Otherwise default to 1.
- If the operator does not mention altitude, default to 10m. Never exceed 50m.
- If the operator does not mention speed, default to 3 m/s. Never exceed 10 m/s.
- return_to_start should be true unless the operator explicitly says not to
  return.
- Only ever use "patrol_loop" or "point_to_point" as the command value.
- Do not invent extra JSON fields. Do not include comments or explanations.
"""


def plan_mission(prompt: str, model: str = "llama-3.3-70b-versatile") -> dict:
    
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    raw_text = response.choices[0].message.content.strip()

    # Defensive cleanup in case the model wraps output in a code fence anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return json.loads(raw_text)


if __name__ == "__main__":
    import sys

    test_prompt = " ".join(sys.argv[1:]) or "Patrol the perimeter loop twice at 15 metres"
    plan = plan_mission(test_prompt)
    print(json.dumps(plan, indent=2))
