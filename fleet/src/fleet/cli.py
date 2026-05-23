"""fleet CLI — typer-based surface for the fleet supervisor (FR-32)."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from dataclasses import fields as dc_fields
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from fleet.adapters import get_adapter
from fleet.config import load as load_config
from fleet.config import write_atomic
from fleet.logging_setup import setup_supervisor_logger
from fleet.queue import BeadsError, BeadsQueue
from fleet.supervisor import Supervisor

app = typer.Typer(no_args_is_help=True)
config_app = typer.Typer(no_args_is_help=True)
app.add_typer(config_app, name="config", help="Manage runtime configuration.")
prompt_app = typer.Typer(no_args_is_help=True)
app.add_typer(prompt_app, name="prompt", help="Install bundled agent prompt templates into the current directory.")

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _fleet_home() -> Path:
    """Return the centralized fleet home directory.

    Resolution order:
      1. $FLEET_HOME env var (absolute path).
      2. ~/.fleet
    """
    env = os.environ.get("FLEET_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".fleet"


def _runtime_toml_path() -> Path:
    return _fleet_home() / "runtime.toml"


def _queue() -> BeadsQueue:
    return BeadsQueue(_fleet_home())


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@app.command()
def init(
    force: Annotated[bool, typer.Option("--force", help="Re-init even if .beads already exists.")] = False,
) -> None:
    """Initialize the fleet home directory (git + beads + defaults)."""
    home = _fleet_home()
    home.mkdir(parents=True, exist_ok=True)

    if not (home / ".git").exists():
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=home,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-c", "user.email=fleet@local", "-c", "user.name=fleet",
             "commit", "--allow-empty", "-m", "fleet init"],
            cwd=home,
            check=True,
            capture_output=True,
        )

    beads_dir = home / ".beads"
    if force or not beads_dir.exists():
        result = subprocess.run(
            ["bd", "init"],
            cwd=home,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 and "already" not in result.stderr.lower():
            typer.echo(f"bd init failed: {result.stderr.strip()}", err=True)
            raise typer.Exit(1)

    load_config(_runtime_toml_path())  # writes defaults if missing
    (home / "tasks").mkdir(exist_ok=True)
    typer.echo(f"Fleet home initialized at {home}")


# ---------------------------------------------------------------------------
# Task management commands
# ---------------------------------------------------------------------------


@app.command()
def create(
    title: Annotated[str, typer.Argument(help="Task title.")],
    description: Annotated[str | None, typer.Option("--description", "-d", help="Task description.")] = None,
    depends_on: Annotated[list[str] | None, typer.Option("--depends-on", help="Task IDs this task depends on.")] = None,
    label: Annotated[list[str] | None, typer.Option("--label", help="Labels to attach.")] = None,
    cwd: Annotated[
        str | None,
        typer.Option(
            "--cwd",
            help="Working directory to run the task in. Defaults to the current pwd.",
        ),
    ] = None,
) -> None:
    """Create a new task and capture the working directory."""
    q = _queue()
    resolved_cwd = str(Path(cwd).expanduser().resolve()) if cwd else str(Path.cwd().resolve())
    try:
        task = q.create_task(
            title,
            description=description,
            depends_on=depends_on,
            labels=label,
            cwd=resolved_cwd,
        )
    except BeadsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    typer.echo(task.id)


@app.command()
def ready(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum tasks to list.")] = 50,
) -> None:
    """List ready tasks."""
    q = _queue()
    try:
        tasks = q.list_ready(limit=limit)
    except BeadsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    if not tasks:
        typer.echo("No ready tasks.")
        return
    width = max(len(t.id) for t in tasks) + 2
    for t in tasks:
        cwd_suffix = f"  [{t.cwd}]" if t.cwd else ""
        typer.echo(f"{t.id:<{width}}{t.title}{cwd_suffix}")


@app.command()
def show(
    task_id: Annotated[str, typer.Argument(help="Task ID.")],
    json_output: Annotated[bool, typer.Option("--json", help="Emit raw bd show JSON envelope.")] = False,
) -> None:
    """Show one task."""
    root = _fleet_home()
    if json_output:
        result = subprocess.run(
            ["bd", "show", task_id, "--json"],
            capture_output=True,
            text=True,
            cwd=root,
        )
        if result.returncode != 0:
            typer.echo(result.stderr.strip(), err=True)
            raise typer.Exit(result.returncode)
        typer.echo(result.stdout, nl=False)
        return
    q = BeadsQueue(root)
    try:
        task = q.get(task_id)
    except BeadsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    typer.echo(f"id:     {task.id}")
    typer.echo(f"title:  {task.title}")
    typer.echo(f"status: {task.status}")
    if task.cwd:
        typer.echo(f"cwd:    {task.cwd}")
    if task.description:
        typer.echo(f"desc:   {task.description}")


@app.command()
def release(
    task_id: Annotated[str, typer.Argument(help="Task ID.")],
    reason: Annotated[str, typer.Option("--reason", help="Release reason.")] = "",
) -> None:
    """Release a task back to open."""
    q = _queue()
    try:
        q.release(task_id, reason=reason)
    except BeadsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)


@app.command()
def close(
    task_id: Annotated[str, typer.Argument(help="Task ID.")],
    reason: Annotated[str, typer.Option("--reason", help="Close reason.")] = "completed",
) -> None:
    """Close a task (terminal)."""
    q = _queue()
    try:
        q.close(task_id, reason=reason)
    except BeadsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# bd passthrough
# ---------------------------------------------------------------------------


@app.command(
    "bd",
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    },
    help="Run a `bd` command against the centralized fleet database in $FLEET_HOME.",
)
def bd_passthrough(ctx: typer.Context) -> None:
    """Forward all trailing args verbatim to `bd`, with cwd=$FLEET_HOME."""
    home = _fleet_home()
    result = subprocess.run(["bd", *ctx.args], cwd=home)
    raise typer.Exit(result.returncode)


# ---------------------------------------------------------------------------
# Supervisor command
# ---------------------------------------------------------------------------


@app.command()
def run(
    adapter: Annotated[str, typer.Option("--adapter", help="Coder adapter name (e.g. claude).")],
    once: Annotated[bool, typer.Option("--once", help="Exit after in-flight count reaches 0.")] = False,
) -> None:
    """Start the fleet supervisor."""
    try:
        adapter_cls = get_adapter(adapter)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    home = _fleet_home()
    q = BeadsQueue(home)
    runtime_toml = _runtime_toml_path()
    cfg = load_config(runtime_toml)
    log_root = Path(cfg.log_root)
    if not log_root.is_absolute():
        log_root = home / log_root
    log = setup_supervisor_logger(log_root)
    supervisor = Supervisor(
        adapter=adapter_cls(),
        queue=q,
        runtime_toml_path=runtime_toml,
        project_root=home,
        log=log,
        once=once,
    )
    try:
        rc = asyncio.run(supervisor.run())
    except NotImplementedError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    raise typer.Exit(rc)


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------


def _resolve_log_dir() -> Path:
    cfg = load_config(_runtime_toml_path())
    log_root = Path(cfg.log_root)
    if not log_root.is_absolute():
        log_root = _fleet_home() / log_root
    return log_root


@app.command("log")
def log_cmd(
    lines: Annotated[
        int | None,
        typer.Argument(
            help="If given, print only the last N lines (tail).",
            show_default=False,
        ),
    ] = None,
) -> None:
    """Print the supervisor log from FLEET_HOME/logging.

    With no argument, prints the most recently modified `fleet-*.jsonl` file
    in full. With a positive integer N, prints only the last N lines.
    """
    log_dir = _resolve_log_dir()
    if not log_dir.exists():
        typer.echo(f"No log directory at {log_dir}", err=True)
        raise typer.Exit(1)

    candidates = sorted(
        log_dir.glob("fleet-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        typer.echo(f"No log files in {log_dir}", err=True)
        raise typer.Exit(1)

    latest = candidates[-1]
    if lines is None:
        sys.stdout.write(latest.read_text(encoding="utf-8"))
        return

    if lines <= 0:
        typer.echo("Error: lines must be a positive integer.", err=True)
        raise typer.Exit(1)

    with latest.open("r", encoding="utf-8") as fh:
        tail = fh.readlines()[-lines:]
    sys.stdout.write("".join(tail))


# ---------------------------------------------------------------------------
# tasks / task
# ---------------------------------------------------------------------------


class TaskAction(str, Enum):
    log = "log"
    plan = "plan"
    knowledge = "knowledge"


def _task_dir(task_id: str) -> Path:
    return _fleet_home() / "tasks" / task_id


def _print_file_or_exit(path: Path, missing_msg: str) -> None:
    if not path.exists():
        typer.echo(missing_msg, err=True)
        raise typer.Exit(1)
    sys.stdout.write(path.read_text(encoding="utf-8"))


@app.command("tasks")
def tasks_cmd(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum tasks to list.")] = 50,
) -> None:
    """List currently running tasks (status=in_progress)."""
    q = _queue()
    try:
        tasks = q.list_in_progress(limit=limit)
    except BeadsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    if not tasks:
        typer.echo("No running tasks.")
        return
    width = max(len(t.id) for t in tasks) + 2
    for t in tasks:
        cwd_suffix = f"  [{t.cwd}]" if t.cwd else ""
        typer.echo(f"{t.id:<{width}}{t.title}{cwd_suffix}")


@app.command("task")
def task_cmd(
    task_id: Annotated[str, typer.Argument(help="Task ID.")],
    action: Annotated[
        TaskAction,
        typer.Argument(help="What to print: log | plan | knowledge."),
    ],
) -> None:
    """Print a task's log, PLAN_AND_STATUS, or KNOWLEDGE artifact."""
    task_dir = _task_dir(task_id)
    if not task_dir.exists():
        typer.echo(f"No task directory at {task_dir}", err=True)
        raise typer.Exit(1)

    if action is TaskAction.plan:
        _print_file_or_exit(
            task_dir / "artifacts" / "PLAN_AND_STATUS.md",
            f"No PLAN_AND_STATUS.md for task {task_id}",
        )
        return

    if action is TaskAction.knowledge:
        _print_file_or_exit(
            task_dir / "artifacts" / "KNOWLEDGE.md",
            f"No KNOWLEDGE.md for task {task_id}",
        )
        return

    # action == TaskAction.log
    attempts_dir = task_dir / "attempts"
    if not attempts_dir.exists():
        typer.echo(f"No attempts directory for task {task_id}", err=True)
        raise typer.Exit(1)
    candidates = sorted(
        attempts_dir.glob("attempt-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        typer.echo(f"No attempt logs for task {task_id}", err=True)
        raise typer.Exit(1)
    sys.stdout.write(candidates[-1].read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Config sub-commands
# ---------------------------------------------------------------------------


@config_app.command("show")
def config_show(
    raw: Annotated[bool, typer.Option("--raw", help="Print raw TOML bytes.")] = False,
) -> None:
    """Show the current runtime configuration."""
    path = _runtime_toml_path()
    if raw:
        if path.exists():
            typer.echo(path.read_text(encoding="utf-8"), nl=False)
        else:
            typer.echo("# No config file found (using defaults)")
        return
    cfg = load_config(path)
    typer.echo(f"{'key':<38} value")
    typer.echo("-" * 55)
    for f in dc_fields(cfg):
        typer.echo(f"{f.name:<38} {getattr(cfg, f.name)!s}")


@config_app.command("set")
def config_set(
    pairs: Annotated[list[str], typer.Argument(metavar="key=value", help="One or more key=value pairs.")],
) -> None:
    """Update one or more runtime config keys atomically."""
    updates: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            typer.echo(f"Error: invalid argument {pair!r} — expected key=value format.", err=True)
            raise typer.Exit(1)
        k, _, v = pair.partition("=")
        updates[k.strip()] = v.strip()

    path = _runtime_toml_path()
    try:
        new_cfg = write_atomic(path, updates)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"{'key':<38} value")
    typer.echo("-" * 55)
    for f in dc_fields(new_cfg):
        typer.echo(f"{f.name:<38} {getattr(new_cfg, f.name)!s}")


# ---------------------------------------------------------------------------
# Prompt template installer
# ---------------------------------------------------------------------------


def _install_prompt(src_name: str, default_rel_dest: str, dest_override: str | None, force: bool) -> None:
    src = _PROMPTS_DIR / src_name
    if not src.exists():
        typer.echo(f"Error: bundled template {src_name} not found at {src}", err=True)
        raise typer.Exit(1)

    if dest_override:
        dest = Path(dest_override).expanduser().resolve()
    else:
        dest = (Path.cwd() / default_rel_dest).resolve()

    if dest.exists() and not force:
        typer.echo(
            f"Error: {dest} already exists. Re-run with --force to overwrite, "
            f"or merge the bundled template into the existing file by hand.",
            err=True,
        )
        raise typer.Exit(1)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    typer.echo(f"Installed {src.name} → {dest}")


@prompt_app.command("claude")
def prompt_claude(
    dest: Annotated[str | None, typer.Option("--dest", help="Override destination (default: .claude/CLAUDE.md in pwd).")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite if destination exists.")] = False,
) -> None:
    """Install the bundled Claude prompt template to .claude/CLAUDE.md."""
    _install_prompt("CLAUDE.md", ".claude/CLAUDE.md", dest, force)


@prompt_app.command("agents")
def prompt_agents(
    dest: Annotated[str | None, typer.Option("--dest", help="Override destination (default: AGENTS.md in pwd).")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite if destination exists.")] = False,
) -> None:
    """Install the bundled AGENTS.md prompt template to the current directory."""
    _install_prompt("AGENTS.md", "AGENTS.md", dest, force)
