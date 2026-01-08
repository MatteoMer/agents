"""
Telegram integration for Ralph agent.

Provides monitoring and control of Ralph agents via Telegram bot.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ralph.telegram_config import (
    TelegramConfig,
    get_sessions_path,
    get_config_dir,
)

if TYPE_CHECKING:
    from ralph.agent import RalphAgent


class TelegramHandler:
    """Handles Telegram bot integration for Ralph agent."""

    def __init__(self, config: TelegramConfig):
        """
        Initialize Telegram handler.

        Args:
            config: Telegram configuration with token, chat_id, user_id
        """
        self.config = config
        self.agent: Optional["RalphAgent"] = None
        self.app: Optional[Application] = None
        self._running = False

    def set_agent(self, agent: "RalphAgent"):
        """Set the agent to control."""
        self.agent = agent

    async def start(self):
        """Start the Telegram bot."""
        if not self.config.is_configured:
            raise ValueError(
                "Telegram not configured. Set RALPH_TELEGRAM_TOKEN, "
                "RALPH_TELEGRAM_CHAT_ID, and RALPH_TELEGRAM_USER_ID environment variables."
            )

        self.app = Application.builder().token(self.config.token).build()

        # Register command handlers
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("todo", self._cmd_todo))
        self.app.add_handler(CommandHandler("plan", self._cmd_plan))
        self.app.add_handler(CommandHandler("notes", self._cmd_notes))
        self.app.add_handler(CommandHandler("log", self._cmd_log))
        self.app.add_handler(CommandHandler("screenshot", self._cmd_screenshot))
        self.app.add_handler(CommandHandler("history", self._cmd_history))
        self.app.add_handler(CommandHandler("pause", self._cmd_pause))
        self.app.add_handler(CommandHandler("resume", self._cmd_resume))
        self.app.add_handler(CommandHandler("force", self._cmd_force))
        self.app.add_handler(CommandHandler("stop", self._cmd_stop))
        self.app.add_handler(CommandHandler("hint", self._cmd_hint))
        self.app.add_handler(CommandHandler("help", self._cmd_help))

        # Register callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))

        # Start polling in background
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        self._running = True

    async def stop(self):
        """Stop the Telegram bot."""
        if self.app and self._running:
            self._running = False
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    def _is_authorized(self, update: Update) -> bool:
        """Check if the user is authorized."""
        if not update.effective_user:
            return False
        return update.effective_user.id == self.config.user_id

    async def _send_message(self, text: str, reply_markup=None):
        """Send a message to the configured chat."""
        if self.app and self.config.chat_id:
            await self.app.bot.send_message(
                chat_id=self.config.chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

    async def _send_photo(self, photo_path: str, caption: str = ""):
        """Send a photo to the configured chat."""
        if self.app and self.config.chat_id:
            with open(photo_path, "rb") as photo:
                await self.app.bot.send_photo(
                    chat_id=self.config.chat_id,
                    photo=photo,
                    caption=caption,
                )

    def _get_status_keyboard(self) -> InlineKeyboardMarkup:
        """Get inline keyboard for status message."""
        keyboard = [
            [
                InlineKeyboardButton("Pause", callback_data="pause"),
                InlineKeyboardButton("Resume", callback_data="resume"),
                InlineKeyboardButton("Force", callback_data="force"),
            ],
            [
                InlineKeyboardButton("TODO", callback_data="todo"),
                InlineKeyboardButton("Plan", callback_data="plan"),
                InlineKeyboardButton("Notes", callback_data="notes"),
            ],
            [
                InlineKeyboardButton("Screenshot", callback_data="screenshot"),
                InlineKeyboardButton("Stop", callback_data="stop"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _format_duration(self, start_time: datetime) -> str:
        """Format duration since start time."""
        delta = datetime.now() - start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def _get_agent_state(self) -> str:
        """Get current agent state string."""
        if not self.agent:
            return "No agent"
        if self.agent._should_stop:
            return "Stopping"
        if self.agent._paused:
            return "Paused"
        if self.agent._current_task:
            return "Running"
        return "Idle"

    # --- Command Handlers ---

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not self._is_authorized(update):
            return

        if not self.agent:
            await update.message.reply_text("No agent running.")
            return

        state = self._get_agent_state()
        duration = self._format_duration(self.agent.start_time) if self.agent.start_time else "N/A"

        status_text = f"""<b>{self.agent.name}</b>

<b>State:</b> {state}
<b>Iteration:</b> {self.agent.iterations}
<b>Cost:</b> ${self.agent.total_cost:.4f}
<b>Running:</b> {duration}
<b>Directory:</b> <code>{self.agent.working_dir}</code>"""

        await update.message.reply_html(
            status_text,
            reply_markup=self._get_status_keyboard(),
        )

    async def _cmd_todo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /todo command."""
        if not self._is_authorized(update):
            return

        await self._send_file_content(update, "TODO.md")

    async def _cmd_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /plan command."""
        if not self._is_authorized(update):
            return

        await self._send_file_content(update, "PLAN.md")

    async def _cmd_notes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /notes command."""
        if not self._is_authorized(update):
            return

        await self._send_file_content(update, "NOTES.md")

    async def _send_file_content(self, update: Update, filename: str):
        """Send contents of a scratchpad file."""
        if not self.agent:
            await update.message.reply_text("No agent running.")
            return

        file_path = self.agent.scratchpad_dir / filename
        if not file_path.exists():
            await update.message.reply_text(f"{filename} does not exist yet.")
            return

        content = file_path.read_text()

        # Telegram message limit is 4096 chars
        if len(content) > 4000:
            content = content[:4000] + "\n\n... (truncated)"

        await update.message.reply_text(f"<b>{filename}</b>\n\n<pre>{self._escape_html(content)}</pre>", parse_mode="HTML")

    async def _cmd_log(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /log [N] command."""
        if not self._is_authorized(update):
            return

        if not self.agent:
            await update.message.reply_text("No agent running.")
            return

        # Get number of lines from args
        n_lines = 20
        if context.args:
            try:
                n_lines = int(context.args[0])
            except ValueError:
                pass

        log_path = self.agent.scratchpad_dir / "iterations.log"
        if not log_path.exists():
            await update.message.reply_text("No iteration log yet.")
            return

        content = log_path.read_text()
        lines = content.strip().split("\n")
        last_lines = lines[-n_lines:] if len(lines) > n_lines else lines

        text = "\n".join(last_lines)
        if len(text) > 4000:
            text = text[-4000:]

        await update.message.reply_text(f"<b>Last {n_lines} lines of log:</b>\n\n<pre>{self._escape_html(text)}</pre>", parse_mode="HTML")

    async def _cmd_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /screenshot command."""
        if not self._is_authorized(update):
            return

        if not self.agent:
            await update.message.reply_text("No agent running.")
            return

        screenshots_dir = self.agent.scratchpad_dir / "screenshots"
        if not screenshots_dir.exists():
            await update.message.reply_text("No screenshots directory.")
            return

        # Find most recent screenshot
        screenshots = sorted(screenshots_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not screenshots:
            await update.message.reply_text("No screenshots available.")
            return

        latest = screenshots[0]
        caption = f"Latest screenshot: {latest.name}"

        with open(latest, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=caption)

    async def _cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command."""
        if not self._is_authorized(update):
            return

        sessions_path = get_sessions_path()
        if not sessions_path.exists():
            await update.message.reply_text("No session history yet.")
            return

        try:
            with open(sessions_path) as f:
                sessions = json.load(f)
        except Exception:
            await update.message.reply_text("Error reading session history.")
            return

        if not sessions:
            await update.message.reply_text("No sessions recorded.")
            return

        # Show last 10 sessions
        recent = sessions[-10:]
        recent.reverse()

        lines = ["<b>Session History (last 10)</b>\n"]
        for i, session in enumerate(recent, 1):
            name = session.get("name", "unknown")
            date = session.get("start_time", "")[:16].replace("T", " ")
            iterations = session.get("iterations", 0)
            cost = session.get("cost", 0)
            outcome = session.get("outcome", "unknown")

            icon = {"completed": "\u2705", "interrupted": "\u26a0\ufe0f", "error": "\u274c"}.get(outcome, "\u2753")

            lines.append(f"{i}. <b>{name}</b> ({date})")
            lines.append(f"   {icon} {outcome.title()} | {iterations} iters | ${cost:.2f}\n")

        await update.message.reply_html("\n".join(lines))

    async def _cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command."""
        if not self._is_authorized(update):
            return

        if not self.agent:
            await update.message.reply_text("No agent running.")
            return

        self.agent.pause()
        await update.message.reply_text(f"Pausing {self.agent.name}... (will pause after current iteration)")

    async def _cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command."""
        if not self._is_authorized(update):
            return

        if not self.agent:
            await update.message.reply_text("No agent running.")
            return

        self.agent.resume()
        await update.message.reply_text(f"Resumed {self.agent.name}")

    async def _cmd_force(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /force [hint] command."""
        if not self._is_authorized(update):
            return

        if not self.agent:
            await update.message.reply_text("No agent running.")
            return

        hint = " ".join(context.args) if context.args else None
        self.agent.force_iteration(hint)

        if hint:
            await update.message.reply_text(f"Forcing new iteration with hint: {hint}")
        else:
            await update.message.reply_text("Forcing new iteration...")

    async def _cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command."""
        if not self._is_authorized(update):
            return

        if not self.agent:
            await update.message.reply_text("No agent running.")
            return

        self.agent.stop()
        await update.message.reply_text(f"Stopping {self.agent.name}...")

    async def _cmd_hint(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /hint <type> <text> command."""
        if not self._is_authorized(update):
            return

        if not self.agent:
            await update.message.reply_text("No agent running.")
            return

        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Usage:\n"
                "/hint todo <text> - Add to TODO.md\n"
                "/hint note <text> - Add to NOTES.md\n"
                "/hint prompt <text> - Inject into next iteration"
            )
            return

        hint_type = context.args[0].lower()
        hint_text = " ".join(context.args[1:])

        if hint_type == "todo":
            file_path = self.agent.scratchpad_dir / "TODO.md"
            with open(file_path, "a") as f:
                f.write(f"\n\n## User Hint ({datetime.now().strftime('%H:%M')})\n{hint_text}\n")
            await update.message.reply_text(f"Added to TODO.md")

        elif hint_type == "note":
            file_path = self.agent.scratchpad_dir / "NOTES.md"
            with open(file_path, "a") as f:
                f.write(f"\n\n## User Note ({datetime.now().strftime('%H:%M')})\n{hint_text}\n")
            await update.message.reply_text(f"Added to NOTES.md")

        elif hint_type == "prompt":
            self.agent._prompt_injection = hint_text
            await update.message.reply_text(f"Hint will be injected in next iteration")

        else:
            await update.message.reply_text(f"Unknown hint type: {hint_type}. Use: todo, note, or prompt")

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self._is_authorized(update):
            return

        help_text = """<b>Ralph Telegram Commands</b>

<b>Query:</b>
/status - Agent status overview
/todo - View TODO.md
/plan - View PLAN.md
/notes - View NOTES.md
/log [N] - Last N lines of log (default 20)
/screenshot - Get latest screenshot
/history - View past sessions

<b>Control:</b>
/pause - Pause after current iteration
/resume - Resume paused agent
/force [hint] - Force new iteration
/stop - Stop the agent

<b>Hints:</b>
/hint todo &lt;text&gt; - Add to TODO.md
/hint note &lt;text&gt; - Add to NOTES.md
/hint prompt &lt;text&gt; - Inject into next iteration"""

        await update.message.reply_html(help_text)

    # --- Callback Query Handler ---

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()

        if not self._is_authorized(update):
            return

        action = query.data

        if action == "pause":
            if self.agent:
                self.agent.pause()
                await query.edit_message_text(f"Pausing {self.agent.name}...")
        elif action == "resume":
            if self.agent:
                self.agent.resume()
                await query.edit_message_text(f"Resumed {self.agent.name}")
        elif action == "force":
            if self.agent:
                self.agent.force_iteration()
                await query.edit_message_text("Forcing new iteration...")
        elif action == "stop":
            if self.agent:
                self.agent.stop()
                await query.edit_message_text(f"Stopping {self.agent.name}...")
        elif action == "todo":
            await self._send_callback_file(query, "TODO.md")
        elif action == "plan":
            await self._send_callback_file(query, "PLAN.md")
        elif action == "notes":
            await self._send_callback_file(query, "NOTES.md")
        elif action == "screenshot":
            if self.agent:
                screenshots_dir = self.agent.scratchpad_dir / "screenshots"
                if screenshots_dir.exists():
                    screenshots = sorted(screenshots_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
                    if screenshots:
                        await self._send_photo(str(screenshots[0]), f"Latest: {screenshots[0].name}")
                        return
            await query.edit_message_text("No screenshots available.")

    async def _send_callback_file(self, query, filename: str):
        """Send file content in response to callback."""
        if not self.agent:
            await query.edit_message_text("No agent running.")
            return

        file_path = self.agent.scratchpad_dir / filename
        if not file_path.exists():
            await query.edit_message_text(f"{filename} does not exist yet.")
            return

        content = file_path.read_text()
        if len(content) > 4000:
            content = content[:4000] + "\n\n... (truncated)"

        await query.edit_message_text(
            f"<b>{filename}</b>\n\n<pre>{self._escape_html(content)}</pre>",
            parse_mode="HTML",
        )

    # --- Notification Methods ---

    async def notify_start(self, agent: "RalphAgent"):
        """Notify that agent has started."""
        if not self.config.notifications.on_start:
            return

        text = f"<b>{agent.name}</b> started\n\n"
        text += f"<b>Directory:</b> <code>{agent.working_dir}</code>\n"
        text += f"<b>Max iterations:</b> {agent.max_iterations or 'unlimited'}"

        await self._send_message(text, reply_markup=self._get_status_keyboard())

    async def notify_iteration(self, agent: "RalphAgent", result: dict):
        """Notify about iteration completion (based on config)."""
        config = self.config.notifications

        # Check if we should notify
        should_notify = config.on_iteration
        if config.every_n_iterations > 0 and agent.iterations % config.every_n_iterations == 0:
            should_notify = True
        if result.get("error") and config.on_error:
            should_notify = True

        # Check for BLOCKED.md updates
        if config.on_blocked:
            blocked_path = agent.scratchpad_dir / "BLOCKED.md"
            if blocked_path.exists():
                # Simple check - could be improved with mtime tracking
                should_notify = True

        if not should_notify:
            return

        text = f"<b>{agent.name}</b> - Iteration {result['iteration']}\n"
        text += f"Cost: ${result.get('cost', 0):.4f} (total: ${agent.total_cost:.4f})"

        if result.get("error"):
            text += f"\n\n<b>Error:</b> {result['error']}"

        await self._send_message(text)

    async def notify_complete(self, agent: "RalphAgent"):
        """Notify that task is complete."""
        if not self.config.notifications.on_complete:
            return

        duration = self._format_duration(agent.start_time) if agent.start_time else "N/A"

        text = f"<b>{agent.name}</b> completed!\n\n"
        text += f"<b>Iterations:</b> {agent.iterations}\n"
        text += f"<b>Total cost:</b> ${agent.total_cost:.4f}\n"
        text += f"<b>Duration:</b> {duration}"

        await self._send_message(text)

    async def notify_stop(self, agent: "RalphAgent"):
        """Notify that agent has stopped."""
        duration = self._format_duration(agent.start_time) if agent.start_time else "N/A"

        text = f"<b>{agent.name}</b> stopped\n\n"
        text += f"<b>Iterations:</b> {agent.iterations}\n"
        text += f"<b>Total cost:</b> ${agent.total_cost:.4f}\n"
        text += f"<b>Duration:</b> {duration}"

        await self._send_message(text)

        # Save to session history
        self._save_session(agent, "interrupted" if agent._should_stop else "completed")

    async def notify_error(self, agent: "RalphAgent", error: str):
        """Notify about an error."""
        if not self.config.notifications.on_error:
            return

        text = f"<b>{agent.name}</b> error\n\n"
        text += f"<code>{self._escape_html(error)}</code>"

        await self._send_message(text)

    # --- Utility Methods ---

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _save_session(self, agent: "RalphAgent", outcome: str):
        """Save session to history."""
        sessions_path = get_sessions_path()
        sessions_path.parent.mkdir(parents=True, exist_ok=True)

        sessions = []
        if sessions_path.exists():
            try:
                with open(sessions_path) as f:
                    sessions = json.load(f)
            except Exception:
                pass

        session = {
            "name": agent.name,
            "start_time": agent.start_time.isoformat() if agent.start_time else None,
            "end_time": datetime.now().isoformat(),
            "iterations": agent.iterations,
            "cost": agent.total_cost,
            "outcome": outcome,
            "working_dir": str(agent.working_dir),
        }

        sessions.append(session)

        # Keep only last 100 sessions
        sessions = sessions[-100:]

        with open(sessions_path, "w") as f:
            json.dump(sessions, f, indent=2)


async def test_connection(config: TelegramConfig) -> bool:
    """Test Telegram connection by sending a test message."""
    if not config.is_configured:
        return False

    try:
        app = Application.builder().token(config.token).build()
        await app.initialize()
        await app.bot.send_message(
            chat_id=config.chat_id,
            text="Ralph Telegram connection test successful!",
        )
        await app.shutdown()
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False
