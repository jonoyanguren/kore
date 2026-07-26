"""Repo-root path helpers (prompts/, skills/, docs/)."""

from __future__ import annotations

from pathlib import Path

# app/paths.py → parents[1] is the project root (local) or /app (Docker).
ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT_DIR / "prompts"
# Companion (Telegram). Dev skills live in skills/dev/ — see skills/README.md
SKILLS_DIR = ROOT_DIR / "skills" / "companion"
DEV_SKILLS_DIR = ROOT_DIR / "skills" / "dev"
DOCS_DIR = ROOT_DIR / "docs"
