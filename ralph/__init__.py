"""
Ralph: An autonomous coding agent that runs in a loop.

Inspired by Geoff Huntley's technique and the YC Agents hackathon project.
Ralph can port codebases, maintain repositories, and work on long-running tasks
autonomously.
"""

__version__ = "0.1.0"

from ralph.agent import RalphAgent, run_ralph
from ralph.simulator import (
    SimulatorManager,
    SimulatorDevice,
    SimulatorState,
    ScreenshotResult,
    ActionResult,
    SimulatorError,
    NoBootedDeviceError,
    IDBNotFoundError,
    XcodeNotFoundError,
)

__all__ = [
    "RalphAgent",
    "run_ralph",
    "SimulatorManager",
    "SimulatorDevice",
    "SimulatorState",
    "ScreenshotResult",
    "ActionResult",
    "SimulatorError",
    "NoBootedDeviceError",
    "IDBNotFoundError",
    "XcodeNotFoundError",
]
