"""Repo-root path helpers (prompts/, skills/)."""

from __future__ import annotations

from pathlib import Path

# app/paths.py → parents[1] is the project root (local) or /app (Docker).
ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT_DIR / "prompts"
SKILLS_DIR = ROOT_DIR / "skills"
