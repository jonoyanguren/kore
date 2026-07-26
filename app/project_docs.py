"""Read whitelisted project docs shipped with the app (PLAN, TODO, prompts, skills…)."""

from __future__ import annotations

from pathlib import Path

from app.paths import ROOT_DIR

# Fixed docs whitelist (prompts/ and skills/ are discovered from disk).
STATIC_DOCS: dict[str, str] = {
    "docs/PLAN.md": "Plan vivo (fase, next steps, decisiones)",
    "docs/TODO.md": "Backlog de tareas sueltas",
    "docs/QA.md": "Plan de pruebas",
    "docs/companion-plan.md": "Diseño detallado del companion",
    "docs/agent-rules.md": "Reglas de comportamiento del agente (estilo Cursor rules)",
}

# Always folded into the system prompt each turn (Cursor-like alwaysApply).
ALWAYS_INJECT = (
    "docs/agent-rules.md",
    "docs/PLAN.md",
    "docs/TODO.md",
)

MAX_CHARS = 60_000


def _discovered_md(subdir: str, label: str, *, recursive: bool = False) -> dict[str, str]:
    folder = ROOT_DIR / subdir
    out: dict[str, str] = {}
    if not folder.is_dir():
        return out
    paths = folder.rglob("*.md") if recursive else folder.glob("*.md")
    for path in sorted(paths):
        if path.name.lower() == "readme.md":
            continue
        rel = str(path.relative_to(ROOT_DIR))
        out[rel] = f"{label}: {path.stem}"
    return out


def allowed_docs() -> dict[str, str]:
    """Whitelist: static docs + prompts/*.md + skills/**/*.md."""
    return {
        **STATIC_DOCS,
        **_discovered_md("prompts", "Prompt"),
        **_discovered_md("skills", "Skill", recursive=True),
    }


def resolve_allowed(path: str) -> Path | None:
    docs = allowed_docs()
    key = path.strip().lstrip("./")
    if key not in docs:
        alt = f"docs/{key}" if not key.startswith(("docs/", "prompts/", "skills/")) else key
        if alt not in docs:
            return None
        key = alt
    full = (ROOT_DIR / key).resolve()
    try:
        full.relative_to(ROOT_DIR.resolve())
    except ValueError:
        return None
    if not full.is_file():
        return None
    return full


def read_doc(path: str) -> str:
    full = resolve_allowed(path)
    if full is None:
        allowed = ", ".join(sorted(allowed_docs()))
        return f"No puedo leer '{path}'. Permitidos: {allowed}"
    text = full.read_text(encoding="utf-8")
    if len(text) > MAX_CHARS:
        return text[:MAX_CHARS] + "\n\n…[truncated]"
    return text


def list_allowed() -> str:
    lines = [f"- {path}: {desc}" for path, desc in sorted(allowed_docs().items())]
    return "\n".join(lines)


def load_always_inject() -> list[tuple[str, str]]:
    """Return (path, content) for docs that always go into the system prompt."""
    out: list[tuple[str, str]] = []
    for rel in ALWAYS_INJECT:
        full = ROOT_DIR / rel
        if full.is_file():
            out.append((rel, full.read_text(encoding="utf-8").strip()))
    return out
