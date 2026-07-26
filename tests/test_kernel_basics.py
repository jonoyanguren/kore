"""Unit tests for skills, dates, and command routing."""

from __future__ import annotations

from datetime import date

from app.kernel.command_router import CommandRouter
from app.kernel.skill_registry import SkillRegistry
from app.paths import SKILLS_DIR
from app.timeutil import (
    format_date_spoken,
    format_madrid_clock,
    resolve_relative_date,
)


def test_skills_load_and_catalog():
    registry = SkillRegistry(SKILLS_DIR)
    registry.load()
    names = {s.name for s in registry.list_skills()}
    assert names == {
        "brainstorm",
        "capture",
        "dream",
        "execute",
        "plan",
        "project-status",
        "tasks",
        "time-madrid",
    }
    assert "get_madrid_time" in (registry.get("time-madrid").tools or [])
    assert "resolve_madrid_date" in (registry.get("time-madrid").tools or [])
    catalog = registry.catalog_text()
    assert "capture" in catalog
    assert "time-madrid" in catalog


def test_command_router_builtins_and_skills():
    registry = SkillRegistry(SKILLS_DIR)
    registry.load()
    router = CommandRouter(registry)

    assert router.match("hola") is None
    assert router.match("/skills").builtin == "skills"
    assert router.match("/diario").builtin == "diario"
    assert router.match("/hora").skill.name == "time-madrid"
    assert router.match("/hora@SomeBot").skill.name == "time-madrid"
    assert router.match("/captura esto").skill.name == "capture"
    assert router.match("/captura esto").args == "esto"


def test_resolve_relative_dates():
    ref = date(2026, 7, 22)  # Wednesday
    assert resolve_relative_date("mañana", ref=ref) == date(2026, 7, 23)
    assert resolve_relative_date("el lunes que viene", ref=ref) == date(2026, 7, 27)
    assert resolve_relative_date("el siguiente lunes", ref=ref) == date(2026, 7, 27)
    assert resolve_relative_date("este viernes", ref=ref) == date(2026, 7, 24)
    assert resolve_relative_date("hoy", ref=ref) == ref


def test_project_docs_whitelist_and_always_inject():
    from app.project_docs import allowed_docs, load_always_inject, read_doc, resolve_allowed

    assert resolve_allowed("docs/PLAN.md") is not None
    assert "Next steps" in read_doc("docs/PLAN.md")
    assert resolve_allowed("/etc/passwd") is None
    docs = allowed_docs()
    assert "prompts/system.md" in docs
    assert "prompts/personality.md" in docs
    assert "skills/capture.md" in docs
    assert "skills/project-status.md" in docs
    injected = dict(load_always_inject())
    assert "docs/PLAN.md" in injected
    assert "docs/TODO.md" in injected
    assert "docs/agent-rules.md" in injected


def test_assembler_includes_all_skill_playbooks():
    import asyncio
    from unittest.mock import AsyncMock

    from app.kernel.prompt_assembler import PromptAssembler
    from app.paths import PROMPTS_DIR

    registry = SkillRegistry(SKILLS_DIR)
    registry.load()
    memory = AsyncMock()
    memory.memory_digests = AsyncMock(return_value={})
    memory.list_diary_for_day = AsyncMock(return_value=[])
    memory.list_tasks = AsyncMock(return_value=[])
    memory.list_agenda_upcoming = AsyncMock(return_value=[])
    assembler = PromptAssembler(PROMPTS_DIR, registry, memory)
    text = asyncio.run(assembler.assemble())
    assert "## Skills playbooks (full)" in text
    for name in ("capture", "project-status", "time-madrid", "brainstorm", "plan", "execute"):
        assert f"### {name}" in text
    assert "## Personality" in text
    assert "## Kimay" in text


def test_spoken_dates_and_clock_format():
    ref = date(2026, 7, 22)
    assert format_date_spoken(ref, ref=ref) == "hoy"
    assert format_date_spoken(date(2026, 7, 23), ref=ref) == "mañana"
    assert format_date_spoken(date(2026, 7, 27), ref=ref) == "el lunes que viene"

    clock = format_madrid_clock()
    assert "Europe/Madrid" not in clock
    assert "CEST" not in clock
    assert "de" in clock  # "día de mes de año"
