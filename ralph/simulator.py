"""
iOS Simulator helper module for Ralph.

Provides IDB + simctl wrapper functions for:
- Taking screenshots
- Tapping/swiping UI elements
- Typing text
- Listing and managing simulator devices

Usage as CLI:
    python -m ralph.simulator screenshot --context "login screen" --json
    python -m ralph.simulator tap --x 200 --y 400
    python -m ralph.simulator swipe --from 200,800 --to 200,200
    python -m ralph.simulator type "hello@example.com"
    python -m ralph.simulator status --json
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class SimulatorState(Enum):
    """Possible states of a simulator device."""
    BOOTED = "Booted"
    SHUTDOWN = "Shutdown"
    UNAVAILABLE = "Unavailable"
    UNKNOWN = "Unknown"


@dataclass
class SimulatorDevice:
    """Represents an iOS Simulator device."""
    udid: str
    name: str
    state: SimulatorState
    runtime: str
    is_available: bool

    @classmethod
    def from_json(cls, data: dict, runtime: str) -> "SimulatorDevice":
        """Create a SimulatorDevice from simctl JSON output."""
        state_str = data.get("state", "Unknown")
        try:
            state = SimulatorState(state_str)
        except ValueError:
            state = SimulatorState.UNKNOWN

        return cls(
            udid=data.get("udid", ""),
            name=data.get("name", ""),
            state=state,
            runtime=runtime,
            is_available=data.get("isAvailable", False),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "udid": self.udid,
            "name": self.name,
            "state": self.state.value,
            "runtime": self.runtime,
            "is_available": self.is_available,
        }


@dataclass
class ScreenshotResult:
    """Result of a screenshot operation."""
    success: bool
    path: Optional[str]
    device_name: Optional[str]
    device_udid: Optional[str]
    timestamp: str
    context: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "screenshot_path": self.path,
            "device_name": self.device_name,
            "device_udid": self.device_udid,
            "timestamp": self.timestamp,
            "context": self.context,
            "error": self.error,
        }


@dataclass
class ActionResult:
    """Result of a UI action (tap, swipe, type)."""
    success: bool
    action: str
    details: dict
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "action": self.action,
            "details": self.details,
            "error": self.error,
        }


class SimulatorError(Exception):
    """Base exception for simulator operations."""
    pass


class NoBootedDeviceError(SimulatorError):
    """Raised when no simulator is booted."""
    pass


class IDBNotFoundError(SimulatorError):
    """Raised when IDB is not installed."""
    pass


class XcodeNotFoundError(SimulatorError):
    """Raised when Xcode/simctl is not available."""
    pass


class SimulatorManager:
    """
    Manages iOS Simulator interactions via IDB and simctl.

    IDB (iOS Development Bridge) is used for UI automation (tap, swipe, type).
    simctl is used for device management and as a screenshot fallback.

    Example:
        manager = SimulatorManager()

        # Take screenshot
        result = manager.take_screenshot(context="home screen")

        # Navigate
        manager.tap(200, 400)
        manager.swipe(200, 800, 200, 200)
        manager.type_text("hello@example.com")
    """

    def __init__(self, screenshot_dir: Optional[Path] = None):
        """
        Initialize the simulator manager.

        Args:
            screenshot_dir: Directory for screenshots. Defaults to .agent/screenshots/
        """
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else Path(".agent/screenshots")
        self._idb_available: Optional[bool] = None
        self._simctl_available: Optional[bool] = None

    def _run_command(
        self,
        cmd: list[str],
        check: bool = True,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=check,
            )
            return result
        except subprocess.CalledProcessError as e:
            raise SimulatorError(f"Command failed: {' '.join(cmd)}\n{e.stderr}")
        except FileNotFoundError:
            raise SimulatorError(f"Command not found: {cmd[0]}")

    def _check_idb_available(self) -> bool:
        """Check if IDB is installed and available."""
        if self._idb_available is not None:
            return self._idb_available

        try:
            result = self._run_command(["idb", "--help"], check=False)
            self._idb_available = result.returncode == 0
        except SimulatorError:
            self._idb_available = False

        return self._idb_available

    def _check_simctl_available(self) -> bool:
        """Check if simctl is available."""
        if self._simctl_available is not None:
            return self._simctl_available

        try:
            result = self._run_command(["xcrun", "simctl", "help"], check=False)
            self._simctl_available = result.returncode == 0
        except SimulatorError:
            self._simctl_available = False

        return self._simctl_available

    def check_prerequisites(self) -> dict:
        """
        Check if required tools are installed.

        Returns:
            Dict with availability status and install instructions.
        """
        idb_available = self._check_idb_available()
        simctl_available = self._check_simctl_available()

        return {
            "idb_available": idb_available,
            "simctl_available": simctl_available,
            "ready": idb_available and simctl_available,
            "install_instructions": None if (idb_available and simctl_available) else {
                "idb": "brew install idb-companion && pip install fb-idb" if not idb_available else None,
                "simctl": "Install Xcode from the App Store" if not simctl_available else None,
            },
        }

    def _get_booted_udid(self) -> Optional[str]:
        """Get the UDID of a booted simulator."""
        devices = self.list_devices(booted_only=True)
        if devices:
            return devices[0].udid
        return None

    def _ensure_idb(self) -> None:
        """Ensure IDB is available and connected, raise error if not."""
        if not self._check_idb_available():
            raise IDBNotFoundError(
                "IDB is not installed. Install with:\n"
                "  brew install idb-companion\n"
                "  pip install fb-idb"
            )
        # Auto-connect to booted simulator if not already connected
        self._connect_idb()

    def _connect_idb(self) -> None:
        """Connect IDB to the booted simulator."""
        udid = self._get_booted_udid()
        if udid:
            self._run_command(["idb", "connect", udid], check=False)

    def _ensure_booted(self) -> str:
        """Ensure a simulator is booted and return its UDID."""
        udid = self._get_booted_udid()
        if not udid:
            raise NoBootedDeviceError(
                "No iOS Simulator is currently booted.\n"
                "Boot one with: xcrun simctl boot <device-name>\n"
                "Or open Simulator.app and start a device."
            )
        return udid

    # =========================================================================
    # Device Management
    # =========================================================================

    def list_devices(self, booted_only: bool = False) -> list[SimulatorDevice]:
        """
        List available simulator devices.

        Args:
            booted_only: If True, only return booted devices.

        Returns:
            List of SimulatorDevice objects.
        """
        if not self._check_simctl_available():
            raise XcodeNotFoundError("simctl not available. Install Xcode.")

        result = self._run_command(["xcrun", "simctl", "list", "devices", "-j"])
        data = json.loads(result.stdout)

        devices = []
        for runtime, device_list in data.get("devices", {}).items():
            # Extract iOS version from runtime string
            # e.g., "com.apple.CoreSimulator.SimRuntime.iOS-17-0" -> "iOS 17.0"
            runtime_name = runtime.split(".")[-1].replace("-", " ").replace("iOS ", "iOS ")

            for device_data in device_list:
                device = SimulatorDevice.from_json(device_data, runtime_name)
                if booted_only and device.state != SimulatorState.BOOTED:
                    continue
                if device.is_available:
                    devices.append(device)

        return devices

    def is_simulator_booted(self) -> bool:
        """Check if any simulator is currently booted."""
        return bool(self.list_devices(booted_only=True))

    def boot_device(self, udid_or_name: str) -> bool:
        """
        Boot a simulator device.

        Args:
            udid_or_name: Device UDID or name (e.g., "iPhone 17 Pro").

        Returns:
            True if successful.
        """
        if not self._check_simctl_available():
            raise XcodeNotFoundError("simctl not available. Install Xcode.")

        # Check if it's a name and find the UDID
        target = udid_or_name
        if not re.match(r"^[A-F0-9-]{36}$", udid_or_name, re.IGNORECASE):
            # It's a name, find the UDID
            devices = self.list_devices()
            for device in devices:
                if device.name.lower() == udid_or_name.lower():
                    target = device.udid
                    break

        result = self._run_command(
            ["xcrun", "simctl", "boot", target],
            check=False,
        )

        return result.returncode == 0

    def get_screen_size(self) -> tuple[int, int]:
        """
        Get the screen size of the booted simulator.

        Returns:
            Tuple of (width, height) in points.
        """
        # Take a screenshot to determine size
        # This is a simple approach; could also parse device info
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name

        try:
            self._take_screenshot_simctl(temp_path)
            # Read image dimensions
            from PIL import Image
            with Image.open(temp_path) as img:
                return img.size
        except ImportError:
            # PIL not available, return common iPhone size
            return (390, 844)  # iPhone 14 Pro logical size
        finally:
            Path(temp_path).unlink(missing_ok=True)

    # =========================================================================
    # Screenshots
    # =========================================================================

    def _take_screenshot_idb(self, output_path: str) -> bool:
        """Take screenshot using IDB."""
        result = self._run_command(
            ["idb", "screenshot", output_path],
            check=False,
        )
        return result.returncode == 0

    def _take_screenshot_simctl(self, output_path: str) -> bool:
        """Take screenshot using simctl (fallback)."""
        result = self._run_command(
            ["xcrun", "simctl", "io", "booted", "screenshot", output_path],
            check=False,
        )
        return result.returncode == 0

    def take_screenshot(
        self,
        output_path: Optional[Path] = None,
        context: str = "",
    ) -> ScreenshotResult:
        """
        Take a screenshot of the simulator.

        Args:
            output_path: Where to save the screenshot. Auto-generates if None.
            context: Description of what this screenshot shows (for logging).

        Returns:
            ScreenshotResult with path and metadata.
        """
        # Ensure a simulator is booted
        try:
            udid = self._ensure_booted()
        except NoBootedDeviceError as e:
            return ScreenshotResult(
                success=False,
                path=None,
                device_name=None,
                device_udid=None,
                timestamp=datetime.now().isoformat(),
                context=context,
                error=str(e),
            )

        # Get device info
        devices = self.list_devices(booted_only=True)
        device = devices[0] if devices else None

        # Generate output path if not provided
        if output_path is None:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            context_slug = re.sub(r"[^a-z0-9]+", "-", context.lower())[:30] if context else "screen"
            filename = f"{timestamp}_{context_slug}.png"
            output_path = self.screenshot_dir / filename
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try IDB first, fall back to simctl
        success = False
        if self._check_idb_available():
            success = self._take_screenshot_idb(str(output_path))

        if not success:
            success = self._take_screenshot_simctl(str(output_path))

        if success and output_path.exists():
            return ScreenshotResult(
                success=True,
                path=str(output_path),
                device_name=device.name if device else None,
                device_udid=device.udid if device else udid,
                timestamp=datetime.now().isoformat(),
                context=context,
            )
        else:
            return ScreenshotResult(
                success=False,
                path=None,
                device_name=device.name if device else None,
                device_udid=device.udid if device else udid,
                timestamp=datetime.now().isoformat(),
                context=context,
                error="Screenshot command failed",
            )

    # =========================================================================
    # UI Automation (via IDB)
    # =========================================================================

    def tap(self, x: int, y: int) -> ActionResult:
        """
        Tap at the specified coordinates.

        Args:
            x: X coordinate (points from left).
            y: Y coordinate (points from top).

        Returns:
            ActionResult indicating success/failure.
        """
        self._ensure_idb()
        self._ensure_booted()

        result = self._run_command(
            ["idb", "ui", "tap", str(x), str(y)],
            check=False,
        )

        return ActionResult(
            success=result.returncode == 0,
            action="tap",
            details={"x": x, "y": y},
            error=result.stderr if result.returncode != 0 else None,
        )

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> ActionResult:
        """
        Swipe from one point to another.

        Args:
            x1, y1: Start coordinates.
            x2, y2: End coordinates.
            duration: Swipe duration in seconds.

        Returns:
            ActionResult indicating success/failure.
        """
        self._ensure_idb()
        self._ensure_booted()

        result = self._run_command(
            ["idb", "ui", "swipe", str(x1), str(y1), str(x2), str(y2)],
            check=False,
        )

        return ActionResult(
            success=result.returncode == 0,
            action="swipe",
            details={"from": [x1, y1], "to": [x2, y2], "duration": duration},
            error=result.stderr if result.returncode != 0 else None,
        )

    def type_text(self, text: str) -> ActionResult:
        """
        Type text into the focused field.

        Args:
            text: Text to type.

        Returns:
            ActionResult indicating success/failure.
        """
        self._ensure_idb()
        self._ensure_booted()

        result = self._run_command(
            ["idb", "ui", "text", text],
            check=False,
        )

        return ActionResult(
            success=result.returncode == 0,
            action="type",
            details={"text": text},
            error=result.stderr if result.returncode != 0 else None,
        )

    def press_button(self, button: str) -> ActionResult:
        """
        Press a hardware button.

        Args:
            button: Button name. Options:
                - "home" (key code 4)
                - "lock" / "power" (key code 26)
                - "volume_up" (key code 24)
                - "volume_down" (key code 25)

        Returns:
            ActionResult indicating success/failure.
        """
        self._ensure_idb()
        self._ensure_booted()

        # Map button names to key codes
        button_map = {
            "home": "4",
            "lock": "26",
            "power": "26",
            "volume_up": "24",
            "volume_down": "25",
        }

        key_code = button_map.get(button.lower(), button)

        result = self._run_command(
            ["idb", "ui", "key", key_code],
            check=False,
        )

        return ActionResult(
            success=result.returncode == 0,
            action="press_button",
            details={"button": button, "key_code": key_code},
            error=result.stderr if result.returncode != 0 else None,
        )

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def scroll_up(self, amount: int = 300) -> ActionResult:
        """Scroll up by swiping down."""
        return self.swipe(200, 400, 200, 400 + amount)

    def scroll_down(self, amount: int = 300) -> ActionResult:
        """Scroll down by swiping up."""
        return self.swipe(200, 600, 200, 600 - amount)

    def status(self) -> dict:
        """
        Get comprehensive status of simulator environment.

        Returns:
            Dict with tool availability, booted device, etc.
        """
        prereqs = self.check_prerequisites()
        booted_devices = self.list_devices(booted_only=True) if prereqs["simctl_available"] else []

        return {
            "simulator_available": prereqs["simctl_available"],
            "idb_available": prereqs["idb_available"],
            "ready": prereqs["ready"],
            "booted_device": booted_devices[0].to_dict() if booted_devices else None,
            "install_instructions": prereqs["install_instructions"],
        }


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI entry point for simulator operations."""
    parser = argparse.ArgumentParser(
        description="iOS Simulator helper for Ralph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s screenshot --context "login screen" --json
  %(prog)s tap --x 200 --y 400
  %(prog)s swipe --from 200,800 --to 200,200
  %(prog)s type "hello@example.com"
  %(prog)s status --json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # screenshot command
    screenshot_parser = subparsers.add_parser(
        "screenshot",
        help="Take a simulator screenshot",
    )
    screenshot_parser.add_argument(
        "--output", "-o",
        help="Output path (auto-generated if not specified)",
    )
    screenshot_parser.add_argument(
        "--context", "-c",
        default="",
        help="Context about what this screenshot shows",
    )
    screenshot_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    # tap command
    tap_parser = subparsers.add_parser(
        "tap",
        help="Tap at coordinates",
    )
    tap_parser.add_argument(
        "--x",
        type=int,
        required=True,
        help="X coordinate",
    )
    tap_parser.add_argument(
        "--y",
        type=int,
        required=True,
        help="Y coordinate",
    )
    tap_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    # swipe command
    swipe_parser = subparsers.add_parser(
        "swipe",
        help="Swipe between two points",
    )
    swipe_parser.add_argument(
        "--from",
        dest="from_coords",
        required=True,
        help="Start coordinates as x,y (e.g., 200,800)",
    )
    swipe_parser.add_argument(
        "--to",
        dest="to_coords",
        required=True,
        help="End coordinates as x,y (e.g., 200,200)",
    )
    swipe_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    # type command
    type_parser = subparsers.add_parser(
        "type",
        help="Type text",
    )
    type_parser.add_argument(
        "text",
        help="Text to type",
    )
    type_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    # button command
    button_parser = subparsers.add_parser(
        "button",
        help="Press a hardware button",
    )
    button_parser.add_argument(
        "name",
        choices=["home", "lock", "power", "volume_up", "volume_down"],
        help="Button to press",
    )
    button_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    # status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show simulator status",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # list-devices command
    list_parser = subparsers.add_parser(
        "list-devices",
        help="List simulator devices",
    )
    list_parser.add_argument(
        "--booted-only",
        action="store_true",
        help="Only show booted devices",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # boot command
    boot_parser = subparsers.add_parser(
        "boot",
        help="Boot a simulator device",
    )
    boot_parser.add_argument(
        "device",
        help="Device name or UDID",
    )

    args = parser.parse_args()
    manager = SimulatorManager()

    def output(data: dict, as_json: bool):
        """Output data as JSON or human-readable."""
        if as_json:
            print(json.dumps(data, indent=2))
        else:
            for key, value in data.items():
                print(f"{key}: {value}")

    try:
        if args.command == "screenshot":
            result = manager.take_screenshot(
                output_path=Path(args.output) if args.output else None,
                context=args.context,
            )
            output(result.to_dict(), args.json)
            sys.exit(0 if result.success else 1)

        elif args.command == "tap":
            result = manager.tap(args.x, args.y)
            output(result.to_dict(), args.json)
            sys.exit(0 if result.success else 1)

        elif args.command == "swipe":
            from_parts = args.from_coords.split(",")
            to_parts = args.to_coords.split(",")
            x1, y1 = int(from_parts[0]), int(from_parts[1])
            x2, y2 = int(to_parts[0]), int(to_parts[1])
            result = manager.swipe(x1, y1, x2, y2)
            output(result.to_dict(), args.json)
            sys.exit(0 if result.success else 1)

        elif args.command == "type":
            result = manager.type_text(args.text)
            output(result.to_dict(), args.json)
            sys.exit(0 if result.success else 1)

        elif args.command == "button":
            result = manager.press_button(args.name)
            output(result.to_dict(), args.json)
            sys.exit(0 if result.success else 1)

        elif args.command == "status":
            status = manager.status()
            output(status, args.json)

        elif args.command == "list-devices":
            devices = manager.list_devices(booted_only=args.booted_only)
            if args.json:
                print(json.dumps([d.to_dict() for d in devices], indent=2))
            else:
                for device in devices:
                    status_icon = "[Booted]" if device.state == SimulatorState.BOOTED else ""
                    print(f"{device.name} ({device.udid}) {status_icon}")
                    print(f"  Runtime: {device.runtime}")

        elif args.command == "boot":
            success = manager.boot_device(args.device)
            if success:
                print(f"Successfully booted {args.device}")
            else:
                print(f"Failed to boot {args.device}")
                sys.exit(1)

    except SimulatorError as e:
        if hasattr(args, "json") and args.json:
            print(json.dumps({"success": False, "error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
