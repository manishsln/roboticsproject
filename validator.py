import json
import math
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).parent / "mission_schema.json"

# Extra safety rules that go beyond plain JSON-schema typing/ranges.
MAX_DISTANCE_FROM_HOME_M = 60.0   # simple geofence
MAX_TOTAL_LOOP_PERIMETER_M = 400.0


class MissionValidationError(Exception):
    pass


def _load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def validate_mission(candidate: dict) -> dict:
   
    schema = _load_schema()

    # 1. Structural / type / range validation via JSON schema
    try:
        jsonschema.validate(instance=candidate, schema=schema)
    except jsonschema.ValidationError as e:
        raise MissionValidationError(f"Schema validation failed: {e.message}")

    waypoints = candidate["waypoints_local_ned"]
    altitude_m = candidate["altitude_m"]

    # 2. Known-command check (belt-and-suspenders on top of schema enum)
    allowed_commands = {"patrol_loop", "point_to_point"}
    if candidate["command"] not in allowed_commands:
        raise MissionValidationError(f"Unknown command '{candidate['command']}'")

    # 3. Altitude consistency: every waypoint's 'down' value must match
    #    -altitude_m (we only support constant-altitude flight in v1).
    expected_down = -altitude_m
    for i, (n, e, d) in enumerate(waypoints):
        if abs(d - expected_down) > 0.5:
            raise MissionValidationError(
                f"Waypoint {i} altitude ({-d}m) does not match mission "
                f"altitude ({altitude_m}m). Constant-altitude flight only."
            )

    # 4. Geofence: no waypoint may be further than MAX_DISTANCE_FROM_HOME_M
    #    from the home position (0, 0), in the horizontal plane.
    for i, (n, e, d) in enumerate(waypoints):
        dist = math.hypot(n, e)
        if dist > MAX_DISTANCE_FROM_HOME_M:
            raise MissionValidationError(
                f"Waypoint {i} is {dist:.1f}m from home, exceeds geofence "
                f"limit of {MAX_DISTANCE_FROM_HOME_M}m."
            )

    # 5. Sanity check on total path length so a pathological plan
    #    (e.g. LLM hallucinating huge loop_count * huge perimeter) can't
    #    slip through.
    perimeter = 0.0
    for i in range(len(waypoints)):
        n1, e1, _ = waypoints[i]
        n2, e2, _ = waypoints[(i + 1) % len(waypoints)]
        perimeter += math.hypot(n2 - n1, e2 - e1)

    total_distance = perimeter * candidate["loop_count"]
    if total_distance > MAX_TOTAL_LOOP_PERIMETER_M * candidate["loop_count"]:
        raise MissionValidationError(
            f"Total planned flight distance ({total_distance:.1f}m) exceeds "
            f"safety limit."
        )

    # 6. Altitude hard ceiling (redundant with schema, but explicit here
    #    since this is a safety-critical bound, not just a type constraint).
    if altitude_m > 50:
        raise MissionValidationError("Altitude exceeds absolute ceiling of 50m.")

    return candidate


if __name__ == "__main__":
    # Quick self-test with a known-good and a known-bad mission
    good = {
        "mission_name": "test loop",
        "vehicle_type": "drone",
        "command": "patrol_loop",
        "altitude_m": 15,
        "speed_ms": 3,
        "loop_count": 2,
        "path_type": "perimeter_loop",
        "waypoints_local_ned": [
            [10, -10, -15], [10, 10, -15], [-10, 10, -15], [-10, -10, -15]
        ],
        "return_to_start": True,
    }
    print("Valid mission accepted:", validate_mission(good)["mission_name"])

    bad = dict(good)
    bad["altitude_m"] = 500  # violates schema max
    try:
        validate_mission(bad)
        print("ERROR: bad mission was NOT rejected")
    except MissionValidationError as e:
        print("Correctly rejected bad mission:", e)
