#!/usr/bin/env python3
"""Watch a Codex thread and resume it with a keep-going prompt after shutdown."""

import argparse
import atexit
import json
import logging
import os
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)


SHUTDOWN_TARGET = "codex_core::codex::handlers"
SHUTDOWN_MESSAGE = "Shutting down Codex instance"


class WatchdogError(RuntimeError):
    """Raised when watchdog setup or resume launch fails."""


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--thread-id",
        default=os.environ.get("CODEX_THREAD_ID", ""),
        help="Codex thread id to watch. Defaults to CODEX_THREAD_ID.",
    )
    parser.add_argument(
        "--cwd",
        default=os.getcwd(),
        help="Working directory to reopen when resuming the thread.",
    )
    parser.add_argument(
        "--state-dir",
        required=True,
        help="Directory for PID, state, and stop files.",
    )
    parser.add_argument(
        "--resume-prompt",
        required=True,
        help="Prompt to send when the watcher revives the thread.",
    )
    parser.add_argument(
        "--log-db",
        default="",
        help="Optional path to Codex state SQLite database. Auto-detected by default.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=15.0,
        help="Polling interval for checking thread shutdown logs.",
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=float,
        default=45.0,
        help="Minimum delay between automatic resume attempts.",
    )
    parser.add_argument(
        "--launch-mode",
        choices=("auto", "direct", "terminal"),
        default="auto",
        help="How to launch codex resume after shutdown.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll iteration and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log the resume action instead of launching it.",
    )
    return parser.parse_args()


def _default_log_db() -> Path:
    codex_home = Path.home() / ".codex"
    candidates = sorted(codex_home.glob("state_*.sqlite"))
    if not candidates:
        raise WatchdogError("Could not find a Codex state_*.sqlite database in ~/.codex.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _load_state(state_path: Path, last_shutdown_log_id: int) -> "dict[str, int | float]":
    if not state_path.exists():
        return {
            "last_shutdown_log_id": last_shutdown_log_id,
            "resume_count": 0,
            "last_resume_at": 0.0,
        }
    with state_path.open(encoding="utf-8") as handle:
        raw_state = json.load(handle)
    return {
        "last_shutdown_log_id": int(raw_state.get("last_shutdown_log_id", last_shutdown_log_id)),
        "resume_count": int(raw_state.get("resume_count", 0)),
        "last_resume_at": float(raw_state.get("last_resume_at", 0.0)),
    }


def _save_state(state_path: Path, state: "dict[str, int | float]") -> None:
    with state_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _write_pid_file(pid_path: Path) -> None:
    pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")

    def _cleanup_pid_file() -> None:
        try:
            if pid_path.exists():
                current = pid_path.read_text(encoding="utf-8").strip()
                if current == str(os.getpid()):
                    pid_path.unlink()
        except OSError:
            logger.warning("Failed to clean up PID file %s", pid_path)

    atexit.register(_cleanup_pid_file)


def _ensure_single_watcher(pid_path: Path) -> bool:
    if not pid_path.exists():
        _write_pid_file(pid_path)
        return True

    current_text = pid_path.read_text(encoding="utf-8").strip()
    if current_text.isdigit() and _pid_is_running(int(current_text)):
        logger.info("Watcher already running with pid %s; exiting.", current_text)
        return False

    logger.info("Replacing stale watcher pid file at %s.", pid_path)
    _write_pid_file(pid_path)
    return True


def _connect_db(log_db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{log_db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _latest_shutdown_log_id(connection: sqlite3.Connection, thread_id: str) -> int:
    row = connection.execute(
        """
        SELECT COALESCE(MAX(id), 0) AS max_id
        FROM logs
        WHERE thread_id = ?
          AND target = ?
          AND message = ?
        """,
        (thread_id, SHUTDOWN_TARGET, SHUTDOWN_MESSAGE),
    ).fetchone()
    return int(row["max_id"]) if row is not None else 0


def _choose_launch_mode(mode: str) -> str:
    if mode != "auto":
        return mode
    return "terminal" if sys.platform == "darwin" else "direct"


def _launch_in_terminal(cwd: Path, command: list[str]) -> None:
    if shutil.which("osascript") is None:
        raise WatchdogError("osascript is unavailable; cannot launch Terminal resume flow.")
    shell_command = f"cd {shlex.quote(str(cwd))} && {shlex.join(command)}"
    terminal_command = f"zsh -lc {shlex.quote(shell_command)}"
    apple_script = (
        'tell application "Terminal"\n'
        f"  do script {json.dumps(terminal_command)}\n"
        "  activate\n"
        "end tell"
    )
    subprocess.run(["osascript", "-e", apple_script], check=True)


def _launch_direct(cwd: Path, command: list[str], state_dir: Path) -> None:
    resume_log_path = state_dir / "resume-invocations.log"
    with resume_log_path.open("a", encoding="utf-8") as handle:
        subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def _launch_resume(
    thread_id: str,
    cwd: Path,
    resume_prompt: str,
    launch_mode: str,
    state_dir: Path,
    dry_run: bool,
) -> None:
    codex_binary = shutil.which("codex")
    if codex_binary is None:
        raise WatchdogError("Could not find the codex CLI in PATH.")

    command = [
        codex_binary,
        "resume",
        thread_id,
        resume_prompt,
        "--no-alt-screen",
        "-C",
        str(cwd),
    ]
    selected_mode = _choose_launch_mode(launch_mode)
    if dry_run:
        logger.info("Dry run: would launch %s via %s.", shlex.join(command), selected_mode)
        return

    logger.info("Launching codex resume for thread %s via %s.", thread_id, selected_mode)
    if selected_mode == "terminal":
        _launch_in_terminal(cwd, command)
        return
    _launch_direct(cwd, command, state_dir)


def _watch_loop(args: argparse.Namespace) -> None:
    if not args.thread_id:
        raise WatchdogError("Missing --thread-id and CODEX_THREAD_ID is not set.")

    state_dir = Path(args.state_dir).expanduser().resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    pid_path = state_dir / "watchdog.pid"
    state_path = state_dir / "watchdog.state.json"
    stop_path = state_dir / "STOP"

    if not _ensure_single_watcher(pid_path):
        return

    log_db_path = Path(args.log_db).expanduser().resolve() if args.log_db else _default_log_db()
    cwd = Path(args.cwd).expanduser().resolve()
    logger.info("Watching Codex thread %s using log db %s.", args.thread_id, log_db_path)

    with _connect_db(log_db_path) as connection:
        initial_shutdown_log_id = _latest_shutdown_log_id(connection, args.thread_id)
        state = _load_state(state_path, initial_shutdown_log_id)
        _save_state(state_path, state)

        while True:
            if stop_path.exists():
                logger.info("Stop file %s found; exiting watcher.", stop_path)
                return

            latest_shutdown_log_id = _latest_shutdown_log_id(connection, args.thread_id)
            last_shutdown_log_id = int(state["last_shutdown_log_id"])
            if latest_shutdown_log_id > last_shutdown_log_id:
                last_resume_at = float(state["last_resume_at"])
                now = time.time()
                if now - last_resume_at >= args.cooldown_seconds:
                    _launch_resume(
                        thread_id=args.thread_id,
                        cwd=cwd,
                        resume_prompt=args.resume_prompt,
                        launch_mode=args.launch_mode,
                        state_dir=state_dir,
                        dry_run=args.dry_run,
                    )
                    state["last_shutdown_log_id"] = latest_shutdown_log_id
                    state["last_resume_at"] = now
                    state["resume_count"] = int(state["resume_count"]) + 1
                    _save_state(state_path, state)
                else:
                    logger.info(
                        "Observed shutdown log %s but cooldown is active for %.1f more seconds.",
                        latest_shutdown_log_id,
                        args.cooldown_seconds - (now - last_resume_at),
                    )

            if args.once:
                return
            time.sleep(args.poll_seconds)


def main() -> None:
    _configure_logging()
    args = _parse_args()
    try:
        _watch_loop(args)
    except WatchdogError as error:
        logger.error("%s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
