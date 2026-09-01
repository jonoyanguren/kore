"""CLI: python -m app.accounts.cap show|set  (Fly: make account-cap).

  python -m app.accounts.cap show
  python -m app.accounts.cap show email@x.com
  python -m app.accounts.cap set email@x.com 0     # 0 = sin tope
"""

from __future__ import annotations

import asyncio
import sys

from app.accounts.homes import accounts_db_path
from app.accounts.store import AccountStore, UserRow, normalize_email


def _fmt(user: UserRow) -> str:
    if user.legacy_prompts:
        cap = "unlimited (owner)"
    elif user.llm_cap_usd is None:
        cap = "env default"
    elif user.llm_cap_usd <= 0:
        cap = "unlimited"
    else:
        cap = f"${user.llm_cap_usd:g}"
    plan = user.billing_plan or "-"
    return f"{user.email}  cap={cap}  plan={plan}  legacy={int(user.legacy_prompts)}"


async def _show(email: str | None) -> int:
    accounts = AccountStore(str(accounts_db_path()))
    await accounts.init()
    if email:
        user = await accounts.get_by_email(normalize_email(email))
        if user is None:
            print(f"no existe: {email}", file=sys.stderr)
            return 1
        print(_fmt(user))
        return 0
    users = await accounts.list_users()
    if not users:
        print("sin usuarios")
        return 0
    for user in users:
        print(_fmt(user))
    return 0


async def _set(email: str, raw: str) -> int:
    try:
        cap = float(raw)
    except ValueError:
        print(f"USD no numérico: {raw}", file=sys.stderr)
        return 2
    if cap < 0:
        print("USD >= 0 (0 = sin tope)", file=sys.stderr)
        return 2
    accounts = AccountStore(str(accounts_db_path()))
    await accounts.init()
    updated = await accounts.set_llm_cap(normalize_email(email), cap)
    if updated is None:
        print(f"no existe: {email}", file=sys.stderr)
        return 1
    print(_fmt(updated))
    return 0


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] not in {"show", "set"}:
        print(
            "uso: python -m app.accounts.cap show [email]\n"
            "     python -m app.accounts.cap set email USD   (0 = sin tope)",
            file=sys.stderr,
        )
        sys.exit(2)
    if argv[0] == "show":
        email = argv[1] if len(argv) == 2 else None
        if len(argv) > 2:
            print("uso: python -m app.accounts.cap show [email]", file=sys.stderr)
            sys.exit(2)
        sys.exit(asyncio.run(_show(email)))
    if len(argv) != 3:
        print("uso: python -m app.accounts.cap set email USD", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(_set(argv[1], argv[2])))


if __name__ == "__main__":
    main()
