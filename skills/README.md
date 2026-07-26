# Skills

Dos árboles:

| Carpeta | Para quién | Carga |
|---------|------------|--------|
| `skills/companion/` | Jone en Telegram (vida / companion) | App: `SkillRegistry` siempre |
| `skills/dev/` | Desarrollo Kore en Cursor | Cursor rules; **no** van al bot salvo `LOAD_DEV_SKILLS=1` |

Mismo formato markdown + frontmatter. Frontmatter opcional: `scope: companion | dev | both`.

- Companion → playbooks + comandos `/…` en Telegram.
- Dev → playbooks para el agente en Cursor:
  - `dev/open.md` — arrancar (lee último close + PLAN)
  - `dev/close.md` — cerrar (escribe `docs/closes/YYYY-MM-DD.md`)
