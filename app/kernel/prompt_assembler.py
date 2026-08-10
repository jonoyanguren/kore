"""Assemble the system prompt from prompts/, skills, time, and memory digests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import settings
from app.kernel.skill_registry import Skill, SkillRegistry
from app.project_docs import load_always_inject
from app.storage.memory import MemoryStore
from app.storage.vault import Vault
from app.timeutil import format_now_for_prompt


class PromptAssembler:
    def __init__(
        self,
        prompts_dir: str | Path,
        skills: SkillRegistry,
        memory: MemoryStore,
        vault: Vault | None = None,
        calendar: Any | None = None,
    ) -> None:
        self._prompts_dir = Path(prompts_dir)
        self._skills = skills
        self._memory = memory
        self._vault = vault
        self._calendar = calendar

    def _read_prompt(self, name: str) -> str:
        path = self._prompts_dir / name
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8")
        return (
            text.replace("{{ASSISTANT_NAME}}", settings.assistant_name)
            .replace("{{OPENROUTER_MODEL}}", settings.openrouter_model)
            .strip()
        )

    async def assemble(self, active_skill: Skill | None = None) -> str:
        parts: list[str] = []

        system = self._read_prompt("system.md")
        if system:
            parts.append(system)

        personality = self._read_prompt("personality.md")
        if personality:
            parts.append("## Personality\n" + personality)

        kimay = self._read_prompt("kimay.md")
        if kimay:
            parts.append("## Kimay\n" + kimay)

        slow = self._read_prompt("slow-project.md")
        if slow:
            parts.append("## Slow Project SL\n" + slow)

        investing = self._read_prompt("investing.md")
        if investing:
            parts.append("## Investing\n" + investing)

        # Cursor-like alwaysApply: agent rules + living plan + TODO every turn.
        for rel, content in load_always_inject():
            parts.append(f"## Project file: {rel}\n{content}")

        # Full skill playbooks every turn (not only when /command activates one).
        skill_blocks: list[str] = []
        for skill in self._skills.list_skills():
            cmds = ", ".join(skill.commands) if skill.commands else "—"
            tools = ", ".join(skill.tools) if skill.tools else "—"
            skill_blocks.append(
                f"### {skill.name}\n"
                f"description: {skill.description}\n"
                f"commands: {cmds}\n"
                f"tools: {tools}\n\n"
                f"{skill.body}"
            )
        if skill_blocks:
            parts.append("## Skills playbooks (full)\n" + "\n\n".join(skill_blocks))

        parts.append(f"## Time context\nNow (Europe/Madrid): {format_now_for_prompt()}")

        digests = await self._memory.memory_digests(limit_per_category=8)
        if digests:
            lines = []
            for category, items in digests.items():
                lines.append(f"### {category}")
                for item_id, text in items:
                    lines.append(f"- (id {item_id}) {text}")
            parts.append("## Memory digests\n" + "\n".join(lines))

        diary = await self._memory.list_diary_for_day()
        if diary:
            lines = [f"- (id {item_id}) {text}" for item_id, text in diary]
            parts.append("## Today's diary\n" + "\n".join(lines))

        open_tasks = await self._memory.list_tasks(status="open", limit=12)
        if open_tasks:
            from app.storage.memory import format_task_lines

            parts.append(
                "## Open tasks\n" + "\n".join(format_task_lines(open_tasks, detailed=True))
            )

        if self._vault is not None:
            done_excerpt = self._vault.read_done_tasks_excerpt(max_chars=2200)
            if done_excerpt:
                parts.append(
                    "## Completed tasks archive (cleared from UI; use as context)\n"
                    + done_excerpt
                )

        agenda = await self._memory.list_agenda_upcoming(limit=10)
        if agenda:
            lines = [
                f"- (id {i}) {starts} — {title}"
                for i, starts, title, _st in agenda
            ]
            parts.append("## Agenda local (chat)\n" + "\n".join(lines))

        if self._calendar is not None:
            try:
                from datetime import datetime, timedelta
                from zoneinfo import ZoneInfo

                from app.timeutil import today_madrid

                madrid = ZoneInfo("Europe/Madrid")
                start = datetime.combine(
                    today_madrid(), datetime.min.time(), tzinfo=madrid
                )
                end = start + timedelta(days=4)
                events = await self._calendar.list_events(
                    time_min=start, time_max=end, max_total=15
                )
                if events:
                    lines = [
                        f"- {e.starts_at} — {e.title}"
                        + (f" [{e.calendar_name}]" if e.calendar_name else "")
                        for e in events
                    ]
                    parts.append(
                        "## Google Calendar (próximos días)\n" + "\n".join(lines)
                    )
            except Exception:
                pass

        if active_skill is not None:
            parts.append(
                f"## Active skill (follow this playbook now): {active_skill.name}\n"
                f"{active_skill.description}\n\n{active_skill.body}"
            )

        return "\n\n".join(parts)
