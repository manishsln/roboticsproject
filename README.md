# Omokai Robotics Take-Home Task
 
## Overview
 
This project implements a natural language mission planning pipeline for a PX4 simulated drone.
 
Pipeline:
 
Natural Language Prompt
        ↓
Groq LLM
        ↓
Mission JSON
        ↓
JSON Validator
        ↓
Deterministic Executor
        ↓
PX4 SITL + Gazebo
 
---
 
## Features
 
- Natural language mission planning
- Structured JSON mission generation
- Mission validation with safety constraints
- Deterministic execution using MAVSDK
- PX4 SITL and Gazebo simulation
 
---
 
## Project Structure
 
```
main.py              # Entry point
llm_planner.py       # Prompt → Mission JSON
validator.py         # Safety validation
executor.py          # Mission execution
mission_schema.json  # Mission schema
requirements.txt     # Python dependencies
SETUP.md             # Installation guide
WRITEUP.md           # Design and implementation details
```
 
---
 
## Installation
 
Follow the instructions in **SETUP.md**.
 
---
 
## Running
 
Example commands:
 
```bash
python3 main.py "Patrol the perimeter loop twice at 15 metres"
 
python3 main.py "Fly a 40 metre square loop once at 20 metres altitude"
 
python3 main.py "Fly straight up to 500 metres"
```
 
The final command is expected to be rejected by the validator because it exceeds the allowed altitude.
 
---
 
## Documentation
 
- SETUP.md
- WRITEUP.md
 
---
 
## Demo

Demonstration Video (Google Drive):

[Watch the demo video](https://drive.google.com/drive/folders/1fZnbKZwd8BMMAimdIYRn3Q2dxrBfaKAK?usp=drive_link)
