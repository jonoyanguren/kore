"""Markdown vault under /data/vault (or local data/vault) — readable export of SQLite truth."""

from __future__ import annotations

from pathlib import Path


class Vault:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def ensure(self) -> None:
        for name in ("memory", "diary", "agenda", "dreams", "tasks"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def append_memory(self, category: str, item_id: int, text: str) -> Path:
        self.ensure()
        category = (category or "general").strip().lower() or "general"
        path = self.root / "memory" / f"{category}.md"
        line = f"- (id {item_id}) {text.strip()}\n"
        if not path.exists():
            path.write_text(f"# memory / {category}\n\n{line}", encoding="utf-8")
        else:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        return path

    def append_diary(self, day: str, entry_id: int, text: str) -> Path:
        self.ensure()
        path = self.root / "diary" / f"{day}.md"
        line = f"- (id {entry_id}) {text.strip()}\n"
        if not path.exists():
            path.write_text(f"# diary / {day}\n\n{line}", encoding="utf-8")
        else:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        return path

    def rewrite_memory_category(
        self, category: str, items: list[tuple[int, str]]
    ) -> Path:
        """Rewrite category file from SQLite rows (id, text), oldest→newest."""
        self.ensure()
        category = (category or "general").strip().lower() or "general"
        path = self.root / "memory" / f"{category}.md"
        lines = [f"# memory / {category}", ""]
        for item_id, text in items:
            lines.append(f"- (id {item_id}) {text.strip()}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def rewrite_diary_day(self, day: str, entries: list[tuple[int, str]]) -> Path:
        self.ensure()
        path = self.root / "diary" / f"{day}.md"
        lines = [f"# diary / {day}", ""]
        for entry_id, text in entries:
            lines.append(f"- (id {entry_id}) {text.strip()}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def write_agenda_month(self, month: str, lines_body: list[str]) -> Path:
        """month = YYYY-MM."""
        self.ensure()
        path = self.root / "agenda" / f"{month}.md"
        body = "\n".join(lines_body)
        path.write_text(f"# agenda / {month}\n\n{body}\n", encoding="utf-8")
        return path

    def write_dream(self, day: str, content: str) -> Path:
        self.ensure()
        path = self.root / "dreams" / f"{day}.md"
        path.write_text(content.strip() + "\n", encoding="utf-8")
        return path

    def read_dream(self, day: str) -> str | None:
        path = self.root / "dreams" / f"{day}.md"
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8").strip()
        return text or None

    def write_tasks(self, lines_body: list[str]) -> Path:
        self.ensure()
        path = self.root / "tasks" / "open.md"
        body = "\n".join(lines_body)
        path.write_text(f"# tasks / open\n\n{body}\n", encoding="utf-8")
        return path
