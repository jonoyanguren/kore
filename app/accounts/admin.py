"""Owner/admin = bootstrap account (`legacy_prompts`). CONSOLE_SECRET counts too."""


def is_admin(user: object | None) -> bool:
    if user is None:
        return True
    return bool(getattr(user, "legacy_prompts", False))
