# Setup & Run — Prompt-to-Drone Pipeline (Core Task)

Stack: **PX4 SITL (jMAVSim, headless) + MAVSDK-Python + Claude API**

This uses jMAVSim instead of Gazebo because it is dramatically faster to
install and needs no GPU/rendering, while still being a real PX4 SITL
instance running the actual flight stack — satisfying the core task's
"PX4 SITL" requirement.

## 1. Install PX4 SITL

```bash
# Ubuntu 22.04/24.04 recommended
git clone https://github.com/PX4/PX4-Autopilot.git --recursive
cd PX4-Autopilot
bash ./Tools/setup/ubuntu.sh    # installs toolchain + jMAVSim deps
```

Reboot or re-source your shell after this if prompted.

## 2. Start PX4 SITL with jMAVSim (headless)

```bash
cd PX4-Autopilot
HEADLESS=1 make px4_sitl jmavsim
```

Leave this running in its own terminal. PX4 exposes a MAVSDK-compatible
UDP port at `udp://:14540` by default — this is what `executor.py` connects
to.

## 3. Set up the pipeline

```bash
cd omokai_pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."   # your key
```

## 4. Run the full pipeline

With PX4 SITL running in another terminal:

```bash
python3 main.py "Patrol the perimeter loop twice at 15 metres"
```

Expected behaviour:
1. The LLM stage prints the raw JSON plan it proposed.
2. The validator stage prints whether the plan passed schema + safety
   checks (rejects with a clear reason if not — try an unsafe prompt like
   "fly to 500 metres" to see this).
3. The executor connects to PX4 SITL, arms, takes off, flies the
   rectangular perimeter loop the requested number of times at constant
   altitude, returns to start, and lands.

You can watch telemetry / vehicle state via `QGroundControl` connected to
the same SITL instance if you want a visual, or just watch the console
logs from `executor.py` (each waypoint and loop is logged).

## 5. Testing each stage in isolation

```bash
# Test LLM planning only (no simulator needed):
python3 llm_planner.py "Drive... err, fly a 30 metre square loop 3 times at 20m"

# Test validator only (no LLM or simulator needed):
python3 validator.py

# Test executor only, against a hardcoded mission (needs SITL running):
python3 executor.py
```

## Troubleshooting

- **"Waiting for global position + home lock..." hangs forever** — jMAVSim
  needs a few seconds after startup to get a GPS fix in SITL. Wait ~10s
  after `make px4_sitl jmavsim` before running `main.py`.
- **Offboard start fails** — PX4 requires a valid setpoint to already be
  streaming before `offboard.start()` is called; this is handled in
  `executor.py` (`set_position_ned` is called once before `start()`), but
  if you edit the executor, keep that ordering.
- **Port conflicts** — if you already have a MAVSDK/MAVLink consumer
  connected to udp:14540 (e.g. QGroundControl in exclusive mode), the
  executor's connection may not attach. Close other consumers or use
  PX4's secondary MAVLink stream for QGC instead.
