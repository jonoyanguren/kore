# Spike — piloto de pago (2026-08-30)

**Fase (D31): cerrar el piloto.** Solo las 8 tareas técnicas de [`TODO.md`](../TODO.md).

Kore ya es usable para Jon. **No** está listo para que un extraño pague y se vaya.

Wedge del piloto: **Día + Gmail reply + una misión**. No el OS entero. No Telegram (sigue siendo Jon). No app. No layout 1.6.

## Ya tienes

- Cuentas aisladas (un SQLite + vault + Gmail tokens por usuario)
- Onboarding nombre + tono (chips) + `/tono`
- Consola: Día, chat, board, Misiones
- Gmail reply (draft → editar → enviar) y Calendar read/write
- 1 máquina Fly; OpenRouter compartido

## Bloquea cobrar

| # | Qué | Por qué |
|---|-----|---------|
| 1 | **Gate** | Registro abierto + tu `OPENROUTER_API_KEY` = un random te vacía el crédito. |
| 2 | **Tope LLM** | Gasto no está acotado por usuario. Un modo Duro o 5 misiones te pegan. |
| 3 | **Gmail Testing** | OAuth en Testing → 403 si no está en testers GCP. Sin correo, el wedge se cae. |
| 4 | **Stripe** | Checkout + webhook desde el principio (empresa lista). |

## No bloquea

Notify misión, `/entrevista`, PDF, cola, móvil, logo, Telegram multi, misión→tareas, polish digest “como Jon”.

## Riesgos de producto

- Competidor real = Gmail + notas + ChatGPT, no otra app.
- Si el piloto no usa Gmail o no lanza una misión en 7 días, no hay producto, hay cuenta.
- Dream 09:00 × N users corre contra **tu** factura (tope primero).

## Lista de tareas (técnicas)

Ver [`TODO.md`](../TODO.md). Hecho: flag `allowed` + tope LLM + Stripe (Checkout + webhooks) + registro abierto. Queda: legal.

Env: `PILOT_LLM_CAP_USD=0.5`.
Stripe: `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` + `STRIPE_PRICE_5` / `_10` / `_20`. Vacío = sin paywall.
Planes públicos: **5 / 10 / 20 € al mes**. 5 € abre; 10 y 20 son más mes. Cada plan lleva un ejemplo de uso diario. Modelos: 5=Flash · 10=Flash+Haiku · 20=híbrido Pro+Haiku. Tope interno hoy: $1 / $2 / $3 (retocar tras dogfood). Webhook: `POST https://kore.fly.dev/api/stripe/webhook`.

Cortar cuenta: `make account-off EMAIL=…` · reactivar: `make account-on EMAIL=…`.
Tope LLM: owner (`legacy_prompts`) no corta. Otros: `PILOT_LLM_CAP_USD` o `users.llm_cap_usd`. `make account-cap EMAIL=… USD=0` (0 = sin tope; Stripe no lo pisa). `make account-cap-show`.

## Hecho del piloto (testable)

Registro + pago + tope LLM + Gmail usable en una cuenta que no sea Jon.
