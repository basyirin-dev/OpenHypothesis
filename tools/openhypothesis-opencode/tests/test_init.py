"""Tests for the openhypothesis-opencode CLI init command."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from openhypothesis_opencode.cli import app

runner = CliRunner()


def _check_agent_file(agents_dir: Path) -> None:
    """Verify the agent file has valid frontmatter."""
    agent_file = agents_dir / "scientific-researcher.md"
    assert agent_file.exists(), f"Missing agent file: {agent_file}"
    content = agent_file.read_text()
    assert content.startswith("---"), "Agent file missing YAML frontmatter"
    assert "mode: primary" in content
    assert "temperature: 0.7" in content


def _check_skill_files(skills_dir: Path) -> None:
    """Verify all three skill SKILL.md files exist."""
    expected = [
        "hypothesis-generation",
        "wet-lab-feasibility",
        "literature-review",
    ]
    for name in expected:
        skill_file = skills_dir / name / "SKILL.md"
        assert skill_file.exists(), f"Missing skill: {skill_file}"
        content = skill_file.read_text()
        assert content.startswith("---"), f"Skill {name} missing frontmatter"
        assert "name: " in content


def _check_plugin_file(plugins_dir: Path) -> None:
    """Verify the plugin JS file exists and has the hook exports."""
    plugin_file = plugins_dir / "openhypothesis.js"
    assert plugin_file.exists(), f"Missing plugin: {plugin_file}"
    content = plugin_file.read_text()
    assert "tool.execute.before" in content
    assert "tool.execute.after" in content
    assert "config:" in content


def _check_opencode_json(project_dir: Path) -> None:
    """Verify opencode.json has all required keys."""
    config_file = project_dir / "opencode.json"
    assert config_file.exists(), "Missing opencode.json"
    cfg: dict[str, Any] = json.loads(config_file.read_text())
    assert "agent" in cfg
    assert "scientific-researcher" in cfg["agent"]
    assert "mcp" in cfg
    assert "command" in cfg
    assert "discover" in cfg["command"]
    assert "ground" in cfg["command"]
    assert "feasibility" in cfg["command"]
    assert "graveyard" in cfg["command"]
    assert "audit" in cfg["command"]
    assert "dashboard" in cfg["command"]


def test_init_creates_all_files() -> None:
    """Running ``init`` in an empty directory creates all expected files."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        result = runner.invoke(app, ["init", str(project_dir)])
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        dot_opencode = project_dir / ".opencode"
        assert dot_opencode.is_dir()

        _check_agent_file(dot_opencode / "agents")
        _check_skill_files(dot_opencode / "skills")
        _check_plugin_file(dot_opencode / "plugins")
        _check_opencode_json(project_dir)


def test_init_target_directory_works() -> None:
    """Running ``init`` with an explicit target directory writes files there."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        result = runner.invoke(app, ["init", str(project_dir)])
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        assert (project_dir / "opencode.json").exists()
        assert (project_dir / ".opencode" / "agents" / "scientific-researcher.md").exists()


def test_init_idempotent() -> None:
    """Running ``init`` twice does not error."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        result1 = runner.invoke(app, ["init", str(project_dir)])
        assert result1.exit_code == 0

        result2 = runner.invoke(app, ["init", str(project_dir)])
        assert result2.exit_code == 0
        _check_opencode_json(project_dir)
