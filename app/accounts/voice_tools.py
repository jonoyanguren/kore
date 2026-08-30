"""Tools to read/update the signed-in user's voice profile."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.accounts.context import current_memory, current_profile
from app.accounts.store import AccountStore
from app.accounts.voice import parse_voice, voice_from_dict

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def build_voice_tools(
    accounts: AccountStore,
) -> tuple[list[dict], dict[str, ToolHandler]]:
    async def _get_voice(_args: dict[str, Any]) -> str:
        profile = current_profile.get()
        if profile is None:
            return "No hay usuario en esta sesión."
        voice = parse_voice(profile.companion_tone)
        return voice.to_prose(profile.owner_name)

    async def _list_recent_user_chat(args: dict[str, Any]) -> str:
        memory = current_memory.get()
        if memory is None:
            return "No hay chat en esta sesión."
        limit = min(max(int(args.get("limit") or 24), 4), 40)
        rows = await memory.list_recent_messages(limit=80)
        user_lines = [
            content.strip()
            for _id, role, content, _at in rows
            if role == "user" and (content or "").strip()
        ]
        user_lines = user_lines[-limit:]
        if not user_lines:
            return "El usuario aún no ha escrito en el chat."
        clipped: list[str] = []
        for line in user_lines:
            if line.startswith("/"):
                continue
            clipped.append(line[:400])
        if not clipped:
            return "Solo hay comandos; no hay prosa del usuario."
        return "Mensajes recientes del usuario (cómo escribe):\n- " + "\n- ".join(
            clipped
        )

    async def _update_voice(args: dict[str, Any]) -> str:
        profile = current_profile.get()
        if profile is None:
            return "No hay usuario en esta sesión."
        current = parse_voice(profile.companion_tone)
        patch = {
            k: args.get(k)
            for k in ("address", "length", "warmth", "humor", "signoff", "notes")
            if args.get(k) not in (None, "")
        }
        if not patch:
            return "Nada que actualizar. Pasa address/length/warmth/humor/signoff/notes."
        nxt = current.merge(patch)
        # validate via from_dict
        nxt = voice_from_dict(nxt.to_dict())
        updated = await accounts.update_companion(
            profile.user_id,
            companion_tone=nxt.to_storage(),
        )
        if updated is None:
            return "No pude guardar el tono."
        current_profile.set(updated.profile())
        return "Tono guardado.\n" + nxt.to_prose(updated.owner_name)

    schemas: list[dict] = [
        {
            "type": "function",
            "function": {
                "name": "get_voice",
                "description": (
                    "Leer el tono/voz actual del usuario (cómo le hablas y "
                    "cómo redactar emails en su nombre)."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_recent_user_chat",
                "description": (
                    "Últimos mensajes del usuario en el chat (su forma de escribir). "
                    "Úsalo antes de actualizar el tono."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Cuántos mensajes de usuario (4–40)",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_voice",
                "description": (
                    "Actualizar el tono del usuario. Solo los campos que pases; "
                    "el resto se mantiene. address=tu|usted|da_igual; "
                    "length=telegrafico|corto|normal; warmth=directo|neutro|cercano; "
                    "humor=cero|seco|si; signoff=nada|nombre|saludo."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "address": {"type": "string"},
                        "length": {"type": "string"},
                        "warmth": {"type": "string"},
                        "humor": {"type": "string"},
                        "signoff": {"type": "string"},
                        "notes": {
                            "type": "string",
                            "description": "Una línea extra (opcional, máx 400)",
                        },
                    },
                },
            },
        },
    ]
    handlers: dict[str, ToolHandler] = {
        "get_voice": _get_voice,
        "list_recent_user_chat": _list_recent_user_chat,
        "update_voice": _update_voice,
    }
    return schemas, handlers
