"""
Telegram notification configuration for Ralph.

Handles loading and managing notification rules from ~/.ralph/notifications.yaml
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class NotificationConfig:
    """Configuration for Telegram notifications."""

    on_start: bool = True
    on_complete: bool = True
    on_error: bool = True
    on_blocked: bool = True
    every_n_iterations: int = 0  # 0 = disabled
    on_iteration: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationConfig":
        """Create config from dictionary."""
        return cls(
            on_start=data.get("on_start", True),
            on_complete=data.get("on_complete", True),
            on_error=data.get("on_error", True),
            on_blocked=data.get("on_blocked", True),
            every_n_iterations=data.get("every_n_iterations", 0),
            on_iteration=data.get("on_iteration", False),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "on_start": self.on_start,
            "on_complete": self.on_complete,
            "on_error": self.on_error,
            "on_blocked": self.on_blocked,
            "every_n_iterations": self.every_n_iterations,
            "on_iteration": self.on_iteration,
        }


@dataclass
class TelegramConfig:
    """Full Telegram configuration."""

    token: Optional[str] = None
    chat_id: Optional[str] = None
    user_id: Optional[int] = None
    notifications: NotificationConfig = field(default_factory=NotificationConfig)

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is fully configured."""
        return bool(self.token and self.chat_id and self.user_id)

    @classmethod
    def load(cls) -> "TelegramConfig":
        """Load configuration from environment and config file."""
        config = cls()

        # Load from environment variables
        config.token = os.environ.get("RALPH_TELEGRAM_TOKEN")
        config.chat_id = os.environ.get("RALPH_TELEGRAM_CHAT_ID")

        user_id_str = os.environ.get("RALPH_TELEGRAM_USER_ID")
        if user_id_str:
            try:
                config.user_id = int(user_id_str)
            except ValueError:
                pass

        # Load notification config from file
        config_path = get_config_path()
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = yaml.safe_load(f) or {}
                    notifications_data = data.get("notifications", {})
                    config.notifications = NotificationConfig.from_dict(notifications_data)
            except Exception:
                pass  # Use defaults on error

        return config

    def save_notifications(self):
        """Save notification config to file."""
        config_path = get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {"notifications": self.notifications.to_dict()}

        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)


def get_config_dir() -> Path:
    """Get the Ralph config directory (~/.ralph/)."""
    return Path.home() / ".ralph"


def get_config_path() -> Path:
    """Get the notifications config file path."""
    return get_config_dir() / "notifications.yaml"


def get_sessions_path() -> Path:
    """Get the sessions history file path."""
    return get_config_dir() / "sessions.json"


def create_default_config():
    """Create default notification config file if it doesn't exist."""
    config_path = get_config_path()

    if config_path.exists():
        return

    config_path.parent.mkdir(parents=True, exist_ok=True)

    default_config = """# Ralph Telegram Notification Configuration
#
# Environment variables required:
#   RALPH_TELEGRAM_TOKEN=<your_bot_token>
#   RALPH_TELEGRAM_CHAT_ID=<your_chat_id>
#   RALPH_TELEGRAM_USER_ID=<your_user_id>

notifications:
  # Notify when Ralph starts a new session
  on_start: true

  # Notify when task completes (TASK COMPLETE detected)
  on_complete: true

  # Notify on errors during iteration
  on_error: true

  # Notify if BLOCKED.md is created/updated
  on_blocked: true

  # Notify every N iterations (0 = disabled)
  every_n_iterations: 0

  # Notify after every single iteration (can be noisy)
  on_iteration: false
"""

    with open(config_path, "w") as f:
        f.write(default_config)
