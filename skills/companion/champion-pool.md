---
name: champion-pool
description: Armar y revisar la champion pool de LoL (3–5 champs, AD/AP, blind vs counter, piedra-papel-tijera). Usar con /pool o si habla de pool, OTP, qué pickear, bans o draft.
commands: [/pool, /championpool]
tools: [list_memory, save_memory]
---

# Champion pool (Pochi / iTero)

Playbook para **qué campeones tener** y **cuándo sacarlos**. No es “qué pickear en este draft concreto” (eso es otro vídeo / overlay iTero). Datos live: tools `lol_*` + `web_search` del parche. Pool de Jon: `list_memory` (lol / preferences) y guarda con `save_memory` si cierran una pool.

Fuente: framework de Pochi (OTP + pool mínima, un difícil, AD/AP, counters del main). Herramienta: [iTero](https://www.itero.gg/) (builder + overlay que recomienda de **tu** pool en champ select).

## Tesis

- Subir elo: **pocos champs**. OTP está bien. Aun así hace falta pool para ban, para cuando te lo pican, y porque a mucha gente el OTP le aburre.
- Más champs = más difícil de dominar. **Un solo difícil**; el resto que funcionen con pocas partidas.
- Mejor un champ mediocre **bien jugado** que el pick “perfecto” si eres flojo con él.
- Tamaño: **3 a 5**. Más de 5, de más.
- Empieza por el champ **que te divierte**. Si no hay main, empieza por un **blind pick** sólido.

## Cómo construir (orden)

1. Main / favorito (el difícil, le metes las partidas).
2. Cubrir **AD y AP** (evitar full AD o full AP de equipo → Tabis / MR contra todo).
3. Un champ **fácil** del otro estilo (si eres asesino, un mago de control simple; no tres hiper-mecánicos).
4. Opcional: **counter del main** (si te lo pican, tú lo destrozas) y/o un specialist fácil que **nunca** sales a ciegas (Trundle vs tanques).
5. No clones: tres champs que hacen lo mismo no aportan (Aatrox + Sett + el mismo split). Sí Fiora + Gwen: distinto (rango/farms bajo torre vs CC claro; AD vs AP).
6. Fill / rol secundario: **un** champ fácil (Nautilus support, Malphite mid/top) **o el mismo main en otra línea** (Ekko mid/jg/top/ADC). Maestría > rol óptimo.

## Blind picks (siempre jugables)

Campeón que sales **sin saber** matchup ni comp. Peor matchup existe; sigue haciendo su trabajo.

| Rol | Ejemplos del vídeo |
|-----|-------------------|
| Top | Jax, Shen |
| Jungla | Wukong |
| Mid | mago de control: Viktor, Syndra |
| ADC | Jinx, Tristana |
| Support | Thresh (gancho, linterna, versátil) |

## Piedra / papel / tijera

- **Piedra** — aguantan, quieren que te tires encima (guardianes, front-to-back). Support: Braum. Jungla: Shaco (su mejor versión es que te eches).
- **Tijera** — se tiran al cuello (vanguardia / engage: Nautilus, Malphite, Rell). Sufren vs buen disengage. Counterean al papel (Malphite vs Xerath: se acabó el poke).
- **Papel** — poke / asedio desde lejos (Xerath, Teemo, Jayce). Counterean piedra si el rival no tiene engage.

Support es donde más importa el ciclo: **Janna vs Braum, Braum vs Rell, Rell vs Janna**. No hace falta cubrir todos los arquetipos de **todos** los roles: cubre los de **tu** línea.

Si eres poke y te van a saltar: alguien que frene (Janna, Shaco, Viktor W/escudo).

## Counterpick de pool (no blind)

Champ fácil, **pocas** partidas, solo cuando el rival se lo pone a huevo. No aprendas el Trundle vs Pantheon. Ejemplos: Trundle vs tanques top; Zilean si blind-piquean Braum/Taric.

Si un champ de tu pool es **hard counter de tu main**, oro: te pican el main → tú lo rompes (Malphite vs Irelia).

## Ejemplos (del vídeo)

**Top, main Irelia:** Irelia (difícil, AD, split) + Malphite (tanque, initiate, AP, counter Irelia) + Mordekaiser (AP fácil) + Trundle (vs tanques). Pool de 4.

**Jungla, main Shaco (Pochi):** Shaco (AD/AP, muy baneado) + Fiddlesticks (partidas ya metidas, AP) + Nocturne (fácil, le encanta vs Shaco: Q revela, E marca el real) + Ivern (roto, Daisy ~ control tipo Shaco, fuerte vs comps sin rompeescudos / no asesinos).

**Mid mal:** Zed + Syndra + Ahri + Zilean = tres/cuatro difíciles. **Mid bien, main Zed:** Zed + Akali (asesino AP, mismo playstyle, más fácil de lo que parece si ya eres asesino) + Malzahar (mago de control fácil) + opcional meta abusable (ej. Tristana mid si el parche lo pide — **comprueba meta ahora**, no copies el ejemplo ciego).

**ADC, blind Jinx:** Jinx + Seraphine (AP/utilidad, fácil, si el equipo es full AD) + Xayah (vs Nocturne / para protegerte) + MF (early, vs Jinx, o si tu equipo tiene Jarvan/Camille/Malphite y el rival no tiene movilidad).

**Support:** Rell (tijera/engage) + Janna (papel/peel) + Braum (piedra). Extra exótico (Renata) solo en spots que tú marques.

## Cómo responder

1. Pregunta rol + main (o sácalo de memoria / `lol_*`). Una pregunta si falta.
2. Propón pool **3–5** con función de cada uno: main / blind / AD|AP / counter / specialist.
3. Di **cuándo no** sacarlos (nunca a ciegas el specialist).
4. Si pide “qué saco ahora”: usa la pool + draft (engage/poke/tank) + forma reciente `lol_*`. No inventes counters; si dudas, `web_search`.
5. iTero: builder guiado (elo, rol, sugerencias) o **Ajustes → Champion Pool** a mano; en partida la overlay recomienda **dentro de tu pool**.
6. Al cerrar una pool: `save_memory` categoría `preferences` o `lol` (si existe), una línea por champ y para qué.

## No hacer

- Llenar la pool de Yasuo + Katarina + LeBlanc (tres difíciles en mid).
- Tres clones del mismo job.
- Decir “adapta el estilo del rival” como si eso = saberlo jugar.
- Copiar picks “rotos del parche” del vídeo sin mirar el parche actual.
