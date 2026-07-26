"""Route Telegram slash commands to skills or built-in handlers."""

from __future__ import annotations

from dataclasses import dataclass

from app.kernel.skill_registry import Skill, SkillRegistry


@dataclass(frozen=True)
class CommandMatch:
    command: str
    args: str
    skill: Skill | None = None
    builtin: str | None = None  # "skills" | "start" | ...


class CommandRouter:
    """Match leading /command; unknown slash commands fall through as chat."""

    BUILTINS = {"/skills", "/start", "/diario"}

    def __init__(self, skills: SkillRegistry) -> None:
        self._skills = skills

    def match(self, text: str) -> CommandMatch | None:
        stripped = text.strip()
        if not stripped.startswith("/"):
            return None

        first, _, rest = stripped.partition(" ")
        # Telegram may send /hora@BotName
        command = first.split("@", 1)[0].lower()
        args = rest.strip()

        if command in self.BUILTINS:
            return CommandMatch(command=command, args=args, builtin=command.lstrip("/"))

        skill = self._skills.by_command(command)
        if skill is None:
            return None
        return CommandMatch(command=command, args=args, skill=skill)
