import asyncio
import logging

from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw

logging.basicConfig(level=logging.INFO, format="%(asctime)s [executor] %(message)s")
log = logging.getLogger("executor")


async def execute_mission(mission: dict, connection_url: str = "udp://:14540"):
    """
    Executes an already-validated mission dict against PX4 SITL.

    This function assumes `mission` has ALREADY passed validator.validate_mission.
    It does not re-interpret intent; it only maps JSON fields to MAVSDK calls.
    """
    drone = System()
    await drone.connect(system_address=connection_url)

    log.info("Waiting for drone connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            log.info("Connected to vehicle.")
            break

    log.info("Waiting for global position + home lock...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            log.info("Position lock OK.")
            break

    log.info(f"Arming for mission: {mission['mission_name']}")
    await drone.action.arm()

    altitude_m = mission["altitude_m"]
    log.info(f"Taking off to {altitude_m}m")
    await drone.action.set_takeoff_altitude(altitude_m)
    await drone.action.takeoff()
    await asyncio.sleep(8)  # deterministic fixed settle time for takeoff in SITL

    # Start offboard mode at current position before commanding setpoints
    # (required by PX4 offboard safety rules).
    await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, -altitude_m, 0.0))
    try:
        await drone.offboard.start()
    except OffboardError as e:
        log.error(f"Offboard start failed: {e}")
        await drone.action.land()
        return

    waypoints = mission["waypoints_local_ned"]
    loop_count = mission["loop_count"]

    for loop_num in range(1, loop_count + 1):
        log.info(f"Starting loop {loop_num}/{loop_count}")
        for i, (n, e, d) in enumerate(waypoints):
            log.info(f"  -> waypoint {i}: N={n} E={e} D={d}")
            await drone.offboard.set_position_ned(PositionNedYaw(n, e, d, 0.0))
            await asyncio.sleep(6)  # fixed dwell/travel time per leg (deterministic)

    if mission.get("return_to_start", True):
        log.info("Returning to start position")
        await drone.offboard.set_position_ned(
            PositionNedYaw(0.0, 0.0, -altitude_m, 0.0)
        )
        await asyncio.sleep(6)

    log.info("Stopping offboard mode, landing.")
    try:
        await drone.offboard.stop()
    except OffboardError as e:
        log.warning(f"Offboard stop reported: {e}")

    await drone.action.land()
    log.info("Mission complete.")


if __name__ == "__main__":
    # Standalone smoke test using a hardcoded mission (bypasses LLM+validator
    # on purpose, to prove the executor works against SITL in isolation).
    demo_mission = {
        "mission_name": "manual smoke test loop",
        "vehicle_type": "drone",
        "command": "patrol_loop",
        "altitude_m": 10,
        "speed_ms": 3,
        "loop_count": 1,
        "path_type": "perimeter_loop",
        "waypoints_local_ned": [
            [10, -10, -10], [10, 10, -10], [-10, 10, -10], [-10, -10, -10]
        ],
        "return_to_start": True,
    }
    asyncio.run(execute_mission(demo_mission))
