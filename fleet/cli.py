"""fleet CLI — typer-based surface for the fleet supervisor (FR-32)."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Annotated

import typer

from fleet.adapters import get_adapter
from fleet.config import load as load_config
from fleet.config import write_atomic
from fleet.queue import BeadsError, BeadsQueue
from fleet.supervisor import Supervisor

app = typer.Typer(no_args_is_help=True)
config_app = typer.Typer(no_args_is_help=True)
app.add_typer(config_app, name="config", help="Manage runtime configuration.")


def _repo_root() -> Path:
    return Path.cwd()


def _queue() -> BeadsQueue:
    return BeadsQueue(_repo_root())


# ---------------------------------------------------------------------------
# Task management commands
# ---------------------------------------------------------------------------


@app.command()
def create(
    title: Annotated[str, typer.Argument(help="Task title.")],
    description: Annotated[str | None, typer.Option("--description", "-d", help="Task description.")] = None,
    depends_on: Annotated[list[str] | None, typer.Option("--depends-on", help="Task IDs this task depends on.")] = None,
    label: Annotated[list[str] | None, typer.Option("--label", help="Labels to attach.")] = None,
) -> None:
    """Create a new task in beads."""
    q = _queue()
    try:
        task = q.create_task(title, description=description, depends_on=depends_on, labels=label)
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
        typer.echo(f"{t.id:<{width}}{t.title}")


@app.command()
def show(
    task_id: Annotated[str, typer.Argument(help="Task ID.")],
    json_output: Annotated[bool, typer.Option("--json", help="Emit raw bd show JSON envelope.")] = False,
) -> None:
    """Show one task."""
    root = _repo_root()
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

    import structlog

    root = _repo_root()
    q = BeadsQueue(root)
    runtime_toml = root / ".fleet" / "runtime.toml"
    log = structlog.get_logger()
    supervisor = Supervisor(
        adapter=adapter_cls(),
        queue=q,
        runtime_toml_path=runtime_toml,
        project_root=root,
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
# Config sub-commands
# ---------------------------------------------------------------------------


@config_app.command("show")
def config_show(
    raw: Annotated[bool, typer.Option("--raw", help="Print raw TOML bytes.")] = False,
) -> None:
    """Show the current runtime configuration."""
    path = _repo_root() / ".fleet" / "runtime.toml"
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

    path = _repo_root() / ".fleet" / "runtime.toml"
    try:
        new_cfg = write_atomic(path, updates)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"{'key':<38} value")
    typer.echo("-" * 55)
    for f in dc_fields(new_cfg):
        typer.echo(f"{f.name:<38} {getattr(new_cfg, f.name)!s}")
