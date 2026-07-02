# Write-up — Core Task

## Architecture

```
Operator prompt (natural language)
        |
        v
  llm_planner.py    -- Claude API, system-prompted to ONLY output JSON
        |               matching mission_schema.json. Proposes, never
        |               executes. No connection to the vehicle exists
        |               in this module.
        v
  candidate mission JSON (untrusted)
        |
        v
  validator.py       -- Hard gate. Two layers:
        |                1. JSON-schema check (types, ranges, enums,
        |                   required fields, no extra fields).
        |                2. Explicit safety/sanity rules: altitude
        |                   ceiling, constant-altitude consistency,
        |                   geofence distance from home, max total
        |                   flight distance, known-command whitelist.
        |               Raises MissionValidationError with a specific
        |               reason if anything fails; nothing downstream
        |               ever sees an unvalidated plan.
        v
  validated mission JSON (trusted)
        |
        v
  executor.py         -- Deterministic. Zero LLM calls, zero NL
        |                interpretation. Maps JSON fields 1:1 to a
        |                fixed sequence of MAVSDK calls (arm, takeoff,
        |                offboard position setpoints per waypoint,
        |                repeated loop_count times, return-to-start,
        |                land). Same JSON in -> same MAVSDK call
        |                sequence out, every time. This is what makes
        |                it auditable: you can read the JSON and know
        |                exactly what the vehicle will do before it
        |                flies.
        v
  MAVSDK -> PX4 SITL (jMAVSim) -- runs the real PX4 flight stack
```

The key design decision is that **the LLM's output is data, not code**.
`llm_planner.py` has no import of `mavsdk` at all — it is structurally
incapable of touching the vehicle. The only path from "LLM said something"
to "vehicle moves" runs through `validator.py`, which is plain
deterministic Python with no model calls, so its behavior is fully
predictable and testable in isolation (see `validator.py`'s own
`__main__` self-test).

## Mission representation

Missions use **local NED coordinates relative to the home/takeoff point**
rather than GPS lat/lon. This was a deliberate simplification for the core
task: it keeps the LLM's job (and the validator's safety math) simple
geometry instead of geodesy, while still exercising the full
prompt -> JSON -> executor -> SITL loop faithfully. Swapping to global
lat/lon waypoints later is a small, contained change (only `executor.py`
would need to convert local offsets to global coordinates via the
vehicle's home position, using PX4's own home-position telemetry).

## Path / loop requirement

The executor flies a rectangular perimeter loop (4 corners, constant
altitude) and repeats it `loop_count` times before returning to the start
point and landing — satisfying "the drone must follow a pre-determined
path or loop." The shape and size are still operator-configurable through
the prompt (e.g. "fly a 40 metre square loop three times"), but once the
JSON is validated, the flight path is fixed and deterministic.

## Which challenges attempted

Only the core task was completed today under time pressure. For the
senior/mid-level challenges (multi-agent formations, SLAM/autonomous nav,
vision AI target detection + follow), see the separate challenge-approach
notes — not yet implemented in this submission, but each has a sketched
approach for how it would build on this same three-layer architecture
(e.g., vision-follow would add a fourth stage — a perception node feeding
detections back into a re-planning loop that still passes through the same
validator before any new setpoints are issued).

## Scaling to real-world problems

The three-layer separation (propose / validate / execute) is exactly the
pattern that would need to harden for real deployment:
- The validator's safety rules would need to grow substantially — real
  geofences (via mapped no-fly zones), battery/return-to-launch reasoning,
  weather/wind limits, and regulatory airspace checks (e.g. UTM/USS
  integration) — but the *shape* of the gate (schema + explicit rule
  checks, hard reject on failure) scales directly.
- The executor would need to handle failure/recovery mid-mission (lost
  link, GPS degradation, obstacle avoidance) rather than assuming a clean
  run, likely via a proper state machine instead of straight-line MAVSDK
  calls with fixed sleeps.
- Fixed `asyncio.sleep()` dwell times in the current executor are a
  simplification for the demo; a real system would wait on
  position-reached telemetry events instead of fixed timers.

## Sources cited

- **PX4-Autopilot** — github.com/PX4/PX4-Autopilot — BSD-3-Clause license.
  Used as the SITL flight stack itself (unmodified, run via its own
  `make px4_sitl jmavsim` target).
- **MAVSDK-Python** — github.com/mavlink/MAVSDK-Python — BSD-3-Clause
  license. Used for the executor's connection, arm/takeoff/offboard/land
  calls; API usage patterns (offboard start sequence, `PositionNedYaw`)
  follow the official MAVSDK-Python offboard example in that repo's docs.
- **Anthropic Python SDK** — github.com/anthropics/anthropic-sdk-python —
  MIT license. Used for the LLM planning call.
- **jsonschema** (Python package) — github.com/python-jsonschema/jsonschema
  — MIT license. Used for the schema-validation layer.
- Architecture pattern (prompt -> LLM -> validated JSON -> deterministic
  executor -> sim) follows the structure specified directly in the task
  document; no external repo's pipeline code was copied — this
  implementation was written from scratch against that spec.
