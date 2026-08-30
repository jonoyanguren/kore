"""Structured voice profile for the signed-in user (companion + email)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

VOICE_MARK = 1

ADDRESS = ("tu", "usted", "da_igual")
LENGTH = ("telegrafico", "corto", "normal")
WARMTH = ("directo", "neutro", "cercano")
HUMOR = ("cero", "seco", "si")
SIGNOFF = ("nada", "nombre", "saludo")

LABELS: dict[str, dict[str, str]] = {
    "address": {"tu": "Tú", "usted": "Usted", "da_igual": "Da igual"},
    "length": {
        "telegrafico": "Telegráfico",
        "corto": "Corto",
        "normal": "Normal",
    },
    "warmth": {"directo": "Directo", "neutro": "Neutro", "cercano": "Cercano"},
    "humor": {"cero": "Cero", "seco": "Seco", "si": "Un poco"},
    "signoff": {
        "nada": "Sin firma",
        "nombre": "Solo el nombre",
        "saludo": "Un saludo + nombre",
    },
}


def _pick(value: str, allowed: tuple[str, ...], default: str) -> str:
    v = (value or "").strip().lower()
    return v if v in allowed else default


@dataclass
class VoiceProfile:
    address: str = "tu"
    length: str = "corto"
    warmth: str = "directo"
    humor: str = "seco"
    signoff: str = "nombre"
    notes: str = ""
    structured: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "length": self.length,
            "warmth": self.warmth,
            "humor": self.humor,
            "signoff": self.signoff,
            "notes": self.notes,
        }

    def to_storage(self) -> str:
        payload = {"kore_voice": VOICE_MARK, **self.to_dict()}
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def to_prose(self, owner_name: str) -> str:
        who = (owner_name or "el usuario").strip() or "el usuario"
        addr = {
            "tu": f"Tutea a {who}.",
            "usted": f"Trata de usted a {who}.",
            "da_igual": f"Tuteo o usted, según el contexto de {who}.",
        }[self.address]
        length = {
            "telegrafico": "Frases mínimas; cero relleno.",
            "corto": "Corto y concreto; sin párrafos de más.",
            "normal": "Longitud normal; claro, sin enrollarse.",
        }[self.length]
        warmth = {
            "directo": "Directo; no endulces ni suavices de más.",
            "neutro": "Neutro, profesional-cercano.",
            "cercano": "Cercano y cálido, sin ñoñería.",
        }[self.warmth]
        humor = {
            "cero": "Sin humor ni guiños.",
            "seco": "Humor seco, nunca payaso.",
            "si": "Un poco de humor si encaja.",
        }[self.humor]
        sign = {
            "nada": "En email: sin firma.",
            "nombre": f"En email: cierra solo con «{who}».",
            "saludo": f"En email: «Un saludo,» + «{who}».",
        }[self.signoff]
        lines = [
            f"Cómo habla y escribe {who}:",
            f"- {addr}",
            f"- {length}",
            f"- {warmth}",
            f"- {humor}",
            f"- {sign}",
        ]
        extra = self.notes.strip()
        if extra:
            lines.append(f"- Extra: {extra}")
        return "\n".join(lines)

    def merge(self, patch: dict[str, Any]) -> VoiceProfile:
        data = self.to_dict()
        for key in ("address", "length", "warmth", "humor", "signoff", "notes"):
            if key in patch and patch[key] is not None:
                data[key] = patch[key]
        nxt = voice_from_dict(data)
        nxt.structured = True
        return nxt


def voice_from_dict(data: dict[str, Any]) -> VoiceProfile:
    notes = str(data.get("notes") or "").strip()[:400]
    return VoiceProfile(
        address=_pick(str(data.get("address") or ""), ADDRESS, "tu"),
        length=_pick(str(data.get("length") or ""), LENGTH, "corto"),
        warmth=_pick(str(data.get("warmth") or ""), WARMTH, "directo"),
        humor=_pick(str(data.get("humor") or ""), HUMOR, "seco"),
        signoff=_pick(str(data.get("signoff") or ""), SIGNOFF, "nombre"),
        notes=notes,
        structured=True,
    )


def parse_voice(raw: str) -> VoiceProfile:
    text = (raw or "").strip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and data.get("kore_voice") == VOICE_MARK:
            return voice_from_dict(data)
    if text:
        return VoiceProfile(notes=text[:400], structured=False)
    return VoiceProfile()


def voice_for_prompt(raw: str, owner_name: str) -> str:
    voice = parse_voice(raw)
    if voice.structured:
        return voice.to_prose(owner_name)
    return voice.notes.strip()


def reply_system_for(owner_name: str, raw_tone: str) -> str:
    who = (owner_name or "el usuario").strip() or "el usuario"
    tone = voice_for_prompt(raw_tone, who)
    block = tone or f"Tono de {who}: profesional-cercano, corto y concreto."
    return (
        f"Eres el assistant de {who}. Redactas UNA respuesta por email EN SU NOMBRE.\n\n"
        "Responde SOLO el cuerpo del mail (texto plano), sin asunto, sin JSON, "
        "sin markdown fences.\n\n"
        "Reglas:\n"
        f"- Idioma del mail original; si no está claro, español de {who}.\n"
        "- No inventes compromisos, fechas ni datos que no estén en el mail.\n"
        "- Si falta info para responder bien, pide lo mínimo en 1–2 frases.\n"
        "- No digas que eres una IA.\n\n"
        f"{block}"
    )
