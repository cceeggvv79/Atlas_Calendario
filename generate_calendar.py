"""
Genera un calendario .ics con los partidos de Atlas FC (Liga MX)
usando la API interna (no oficial) de ESPN.

Uso:
    python generate_calendar.py

Salida:
    atlas.ics  (listo para subir a GitHub Pages / hosting)
"""

import requests
from datetime import datetime, timedelta
from ics import Calendar, Event
from ics.grammar.parse import ContentLine

# ---------- CONFIG ----------
LEAGUE_SLUG = "all"       # "all" trae TODAS las competencias del equipo (Liga MX + Leagues Cup + Copas)
TEAM_ID = "216"           # Atlas en ESPN
TEAM_LABEL = "Atlas FC"
TEAM_MATCH_NAME = "Atlas"     # texto exacto que ESPN usa para Atlas en displayName
TEAM_EMOJI = "\U0001F98A"     # 🦊 zorro
OUTPUT_FILE = "atlas.ics"
DURATION_MINUTES = 120    # duración estimada de un partido para el evento

SCHEDULE_URL = (
    f"https://site.api.espn.com/apis/site/v2/sports/soccer/"
    f"{LEAGUE_SLUG}/teams/{TEAM_ID}/schedule?fixture=true"
)
# ------------------------------


def with_emoji(team_name: str) -> str:
    """Le pone el emoji de zorro al lado de 'Atlas' (y variantes)."""
    if TEAM_MATCH_NAME.lower() in team_name.lower():
        return f"{team_name} {TEAM_EMOJI}"
    return team_name


def fetch_schedule() -> list[dict]:
    resp = requests.get(SCHEDULE_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("events", [])


def parse_kickoff(iso_date: str) -> datetime | None:
    if not iso_date:
        return None
    try:
        # ESPN entrega fechas en UTC, formato tipo 2026-08-02T01:00Z
        return datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_teams(competitors: list[dict]) -> tuple[str, str]:
    home = away = "?"
    for c in competitors:
        name = (c.get("team") or {}).get("displayName", "?")
        if c.get("homeAway") == "home":
            home = name
        elif c.get("homeAway") == "away":
            away = name
    return home, away


def build_calendar(events: list[dict]) -> Calendar:
    cal = Calendar()
    cal.extra.append(ContentLine(name="X-WR-CALNAME", value=f"{TEAM_LABEL} - Liga MX"))
    cal.extra.append(
        ContentLine(name="X-WR-CALDESC", value=f"Calendario no oficial de partidos de {TEAM_LABEL}")
    )

    for ev in events:
        event_id = ev.get("id")
        kickoff = parse_kickoff(ev.get("date"))
        if not event_id or kickoff is None:
            continue

        competitions = ev.get("competitions") or []
        if not competitions:
            continue
        comp = competitions[0]

        home, away = extract_teams(comp.get("competitors", []))
        home, away = with_emoji(home), with_emoji(away)
        venue = ((comp.get("venue") or {}).get("fullName")) or ""

        # nombre real de la competencia (Liga MX, Leagues Cup, Copa, etc.)
        competition_name = (
            (ev.get("league") or {}).get("name")
            or (ev.get("season") or {}).get("slug")
            or "Liga MX"
        )

        # nombre de la jornada/ronda si está disponible
        week = ev.get("week", {})
        week_number = week.get("number") if isinstance(week, dict) else None

        e = Event()
        e.uid = f"{event_id}@atlas-calendar"
        e.name = f"{home} vs {away}"
        e.begin = kickoff
        e.duration = timedelta(minutes=DURATION_MINUTES)
        if venue:
            e.location = venue

        desc_parts = [competition_name]
        if week_number:
            desc_parts.append(f"Jornada {week_number}")
        e.description = " - ".join(desc_parts)

        cal.events.add(e)

    return cal


def main():
    events = fetch_schedule()
    print(f"Partidos encontrados para {TEAM_LABEL}: {len(events)}")

    cal = build_calendar(events)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())

    print(f"Listo: {OUTPUT_FILE} generado con {len(cal.events)} eventos.")


if __name__ == "__main__":
    main()