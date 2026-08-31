"""CLI: python -m app.accounts.flag on|off email@x.com  (Fly: make account-on/off)."""

from __future__ import annotations

import asyncio
import sys

from app.accounts.homes import accounts_db_path
from app.accounts.store import AccountStore, normalize_email


async def _run(action: str, email: str) -> int:
    accounts = AccountStore(str(accounts_db_path()))
    await accounts.init()
    email_n = normalize_email(email)
    user = await accounts.get_by_email(email_n)
    if user is None:
        print(f"no existe: {email_n}", file=sys.stderr)
        return 1
    allowed = action == "on"
    updated = await accounts.set_allowed(email_n, allowed)
    assert updated is not None
    state = "allowed" if updated.allowed else "off"
    print(f"{updated.email} → {state}")
    return 0


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in {"on", "off"}:
        print("uso: python -m app.accounts.flag on|off email", file=sys.stderr)
        sys.exit(2)
    code = asyncio.run(_run(sys.argv[1], sys.argv[2]))
    sys.exit(code)


if __name__ == "__main__":
    main()
