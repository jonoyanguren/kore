---
name: tono
description: Actualizar el tono del usuario (companion + email) a partir de cómo escribe en el chat.
commands: [/tono, /voice]
tools: [get_voice, list_recent_user_chat, update_voice]
---

# Tono

Objetivo: **ajustar cómo le hablas y cómo redactas mails en su nombre**. El tono es del usuario de esta cuenta, no de un perfil fijo.

## Arranque (`/tono` o `/voice`)

1. Llama `get_voice` y `list_recent_user_chat` (limit 24).
2. Mira **cómo escribe el usuario** (largo, trato, calor, humor, si firma). Ignora comandos `/…`.
3. Propón un ajuste concreto (chips): address / length / warmth / humor / signoff + notes de una línea si hace falta.
4. Llama `update_voice` con **solo los campos que cambian** (o todos si el perfil estaba vacío / solo prosa vieja).
5. Confirma en 2–4 líneas qué quedó. STOP.

## Si hay poco chat

- Si `list_recent_user_chat` está vacío: di el tono actual (`get_voice`) y pide que escriba un poco o que lo cambie en Más → Tu tono. No inventes un perfil.
- Si el usuario dice explícitamente cómo quiere el tono (“más corto”, “de usted”), actualiza eso y para.

## No hacer

- No copies el tono de Jon ni de un companion de ejemplo.
- No vuelques el historial. No lances misiones ni entrevistas.
- No pidas un ensayo: esto es inferencia + confirmación corta.
- No mezcles hechos de memoria (trabajo, gente) con el tono; eso es `/entrevista`.
