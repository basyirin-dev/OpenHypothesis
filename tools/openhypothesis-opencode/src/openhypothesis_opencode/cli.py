"""CLI commands for setting up OpenHypothesis OpenCode integration.

Usage::

    openhypothesis-opencode init
    openhypothesis-opencode setup-mcp
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(
    name="openhypothesis-opencode",
    help="OpenCode integration for OpenHypothesis.",
)


def _template_dir() -> Path:
    """Return the path to the bundled templates directory."""

    try:
        # Python 3.12+
        from importlib.resources import files as _files

        return _files("openhypothesis_opencode.templates")  # type: ignore[return-value]
    except (ImportError, TypeError):
        # Fallback for older Python or frozen packages
        pkg_dir = Path(__file__).resolve().parent / "templates"
        if pkg_dir.is_dir():
            return pkg_dir
        raise RuntimeError("Cannot locate templates directory.") from None


def _copy_template(src_name: str, dst: Path) -> None:
    """Copy a single template file from the package to a destination path."""
    src = _template_dir() / src_name
    if not src.exists():
        typer.echo(f"Warning: template {src_name} not found, skipping.", err=True)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))
    typer.echo(f"  Created {dst}")


def _copy_skill_templates(skills_dir: Path) -> None:
    """Copy all skill templates recursively to the target skills directory."""
    tmpl = _template_dir() / "skills"
    if not tmpl.is_dir():
        typer.echo("Warning: skills templates directory not found, skipping.", err=True)
        return
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
    shutil.copytree(str(tmpl), str(skills_dir), dirs_exist_ok=True)
    for p in skills_dir.rglob("SKILL.md"):
        typer.echo(f"  Created {p}")


def _read_global_config() -> dict[str, Any]:
    """Read the user's global OpenCode config, returning an empty dict if absent."""
    global_path = Path.home() / ".config" / "opencode" / "opencode.json"
    if global_path.exists():
        raw = global_path.read_text()
        return dict(json.loads(raw))
    return {}


def _write_global_config(cfg: dict[str, Any]) -> None:
    """Write the user's global OpenCode config."""
    global_path = Path.home() / ".config" / "opencode" / "opencode.json"
    global_path.parent.mkdir(parents=True, exist_ok=True)
    global_path.write_text(json.dumps(cfg, indent=2) + "\n")
    typer.echo(f"  Updated {global_path}")


_DEFAULT_TARGET = typer.Argument(
    ".", help="Target project directory (default: current directory).", exists=True, file_okay=False, dir_okay=True,
)

@app.command()
def init(
    target: Path = _DEFAULT_TARGET,  # noqa: B008
) -> None:
    """Initialise OpenHypothesis OpenCode tooling in a project.

    Creates .opencode/agents/, .opencode/skills/, .opencode/plugins/,
    and opencode.json with all agent, command, MCP, and skill registrations.
    """
    target = target.resolve()
    typer.echo(f"Initialising OpenHypothesis OpenCode tooling in {target}...")
    typer.echo("")

    dot_opencode = target / ".opencode"
    agents_dir = dot_opencode / "agents"
    skills_dir = dot_opencode / "skills"
    plugins_dir = dot_opencode / "plugins"

    # Agent
    _copy_template("scientific-researcher.md", agents_dir / "scientific-researcher.md")

    # Skills
    _copy_skill_templates(skills_dir)

    # Plugin (lifecycle hooks)
    _copy_template("openhypothesis.js", plugins_dir / "openhypothesis.js")

    # opencode.json
    _copy_template("opencode.json", target / "opencode.json")

    typer.echo("")
    typer.echo("Done! OpenHypothesis OpenCode tooling is ready.")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("  1. Restart OpenCode to pick up the new config.")
    typer.echo("  2. Run /discover to execute the discovery pipeline.")
    typer.echo("  3. Run /dashboard to launch the web UI.")


@app.command()
def setup_mcp() -> None:
    """Register the OpenHypothesis MCP server in the user's global OpenCode config.

    This makes the MCP tools available to all OpenCode sessions.
    """
    cfg = _read_global_config()
    mcp_block: dict[str, Any] = {
        "openhypothesis-mcp": {
            "type": "local",
            "command": ["uv", "run", "openhypothesis-mcp"],
            "enabled": True,
        },
        "openhypothesis-mcp-restricted": {
            "type": "local",
            "command": [
                "uv",
                "run",
                "openhypothesis-mcp",
                "--allow-tools",
                "search_papers,search_negative_results,check_citation",
            ],
            "enabled": True,
        },
    }

    existing = cfg.get("mcp", {})
    # Merge: existing entries take precedence so user overrides are preserved.
    merged = {**mcp_block, **existing}
    cfg["mcp"] = merged

    _write_global_config(cfg)
    typer.echo("OpenHypothesis MCP servers registered in global config.")
    typer.echo("Restart OpenCode for the changes to take effect.")


if __name__ == "__main__":
    app()
