"""Load skills from markdown files with YAML-like frontmatter."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    commands: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    body: str = ""
    path: str = ""


def _parse_scalar_list(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("'\"") for part in inner.split(",") if part.strip()]
    return [raw.strip().strip("'\"")]


def _parse_frontmatter(block: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def parse_skill_markdown(text: str, path: str = "") -> Skill | None:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        logger.warning("Skill missing frontmatter: %s", path or "<inline>")
        return None
    meta = _parse_frontmatter(match.group(1))
    name = meta.get("name", "").strip()
    if not name:
        logger.warning("Skill missing name: %s", path or "<inline>")
        return None
    return Skill(
        name=name,
        description=meta.get("description", "").strip(),
        commands=_parse_scalar_list(meta.get("commands", "")),
        tools=_parse_scalar_list(meta.get("tools", "")),
        body=match.group(2).strip(),
        path=path,
    )


class SkillRegistry:
    def __init__(self, *skills_dirs: str | Path) -> None:
        self._skills_dirs = [Path(d) for d in skills_dirs]
        self._by_name: dict[str, Skill] = {}
        self._by_command: dict[str, Skill] = {}

    def load(self) -> None:
        self._by_name.clear()
        self._by_command.clear()
        loaded_from: list[str] = []
        for skills_dir in self._skills_dirs:
            if not skills_dir.is_dir():
                logger.warning("Skills directory missing: %s", skills_dir)
                continue
            count_before = len(self._by_name)
            for path in sorted(skills_dir.glob("*.md")):
                if path.name.lower() == "readme.md":
                    continue
                skill = parse_skill_markdown(
                    path.read_text(encoding="utf-8"), str(path)
                )
                if skill is None:
                    continue
                if skill.name in self._by_name:
                    logger.warning(
                        "Duplicate skill name %s from %s (keeping first)",
                        skill.name,
                        path,
                    )
                    continue
                self._by_name[skill.name] = skill
                for command in skill.commands:
                    cmd = command if command.startswith("/") else f"/{command}"
                    self._by_command[cmd.lower()] = skill
            added = len(self._by_name) - count_before
            loaded_from.append(f"{skills_dir}(+{added})")
        logger.info(
            "Loaded %d skills from %s",
            len(self._by_name),
            ", ".join(loaded_from) or "(none)",
        )

    def list_skills(self) -> list[Skill]:
        return sorted(self._by_name.values(), key=lambda s: s.name)

    def get(self, name: str) -> Skill | None:
        return self._by_name.get(name)

    def by_command(self, command: str) -> Skill | None:
        return self._by_command.get(command.lower())

    def catalog_text(self) -> str:
        skills = self.list_skills()
        if not skills:
            return "(no skills loaded)"
        lines = []
        for skill in skills:
            cmds = ", ".join(skill.commands) if skill.commands else "—"
            lines.append(f"- {skill.name}: {skill.description} (commands: {cmds})")
        return "\n".join(lines)
