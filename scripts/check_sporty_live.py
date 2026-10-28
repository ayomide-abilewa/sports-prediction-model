import sys
from backend.ingestion.sportybet_service import fetch_sporty_upcoming_events, fetch_sporty_live_events

live = fetch_sporty_live_events()
print(f"=== REAL LIVE MATCHES ON SPORTYBET RIGHT NOW ({len(live)}) ===")
for ev in live:
    score = ev.get('setScore', '0:0')
    status = ev.get('matchStatus', '')
    cat = ev.get('sport', {}).get('category', {}).get('name', '')
    tourn = ev.get('sport', {}).get('category', {}).get('tournament', {}).get('name', '')
    print(f"{ev.get('homeTeamName')} {score} {ev.get('awayTeamName')} | {status} | {cat} - {tourn}")

up = fetch_sporty_upcoming_events()
print(f"\n=== REAL UPCOMING MATCHES ON SPORTYBET TODAY ({len(up)}) ===")
for ev in up:
    start = ev.get('estimateStartTime')
    cat = ev.get('sport', {}).get('category', {}).get('name', '')
    tourn = ev.get('sport', {}).get('category', {}).get('tournament', {}).get('name', '')
    print(f"{ev.get('homeTeamName')} vs {ev.get('awayTeamName')} | {start} | {cat} - {tourn}")
