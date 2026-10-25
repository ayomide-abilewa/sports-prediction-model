from __future__ import annotations

import re
import unicodedata
from rapidfuzz import fuzz, process
import structlog

logger = structlog.get_logger()


class TeamMapper:
    """Normalizes team names across heterogeneous data sources.
    
    Combines:
    1. Exact alias dictionary (comprehensive curated mappings)
    2. String preprocessing (accent removal, prefix/suffix stripping)
    3. RapidFuzz token set ratio matching with safety threshold
    """

    # Curated mappings: canonical_name -> list of known aliases
    DEFAULT_ALIASES: dict[str, list[str]] = {
        # England - Premier League & Championship
        "Arsenal": ["Arsenal FC", "Arsenal London"],
        "Aston Villa": ["Villa", "Aston Villa FC"],
        "Bournemouth": ["AFC Bournemouth", "Bournemouth AFC"],
        "Brentford": ["Brentford FC"],
        "Brighton": ["Brighton and Hove Albion", "Brighton & Hove Albion", "Brighton & Hove", "Brighton Hove"],
        "Chelsea": ["Chelsea FC", "Chelsea London"],
        "Crystal Palace": ["Palace", "Crystal Palace FC"],
        "Everton": ["Everton FC"],
        "Fulham": ["Fulham FC"],
        "Ipswich": ["Ipswich Town", "Ipswich Town FC"],
        "Leicester": ["Leicester City", "Leicester City FC"],
        "Liverpool": ["Liverpool FC"],
        "Manchester City": ["Man City", "Manchester C", "Man. City", "MCFC"],
        "Manchester United": ["Man United", "Man Utd", "Manchester Utd", "Man. United", "MUFC"],
        "Newcastle": ["Newcastle United", "Newcastle Utd", "Newcastle United FC"],
        "Nottingham Forest": ["Nott'm Forest", "Nottm Forest", "Nottingham", "Forest"],
        "Southampton": ["Southampton FC", "Saints"],
        "Tottenham": ["Spurs", "Tottenham Hotspur", "Tottenham Hotspur FC"],
        "West Ham": ["West Ham United", "West Ham Utd", "WHU"],
        "Wolves": ["Wolverhampton", "Wolverhampton Wanderers", "Wolves FC"],
        "Leeds": ["Leeds United", "Leeds Utd"],
        "Burnley": ["Burnley FC"],
        "Sheffield United": ["Sheff Utd", "Sheffield Utd", "Sheff United"],

        # Spain - La Liga
        "Athletic Bilbao": ["Ath Bilbao", "Athletic Club", "Athletic de Bilbao"],
        "Atletico Madrid": ["Atl. Madrid", "Atlético Madrid", "Atletico", "Atleti", "Atl Madrid"],
        "Barcelona": ["FC Barcelona", "Barca", "Barça"],
        "Celta Vigo": ["Celta", "RC Celta", "Celta de Vigo"],
        "Espanyol": ["RCD Espanyol", "Espanyol Barcelona"],
        "Getafe": ["Getafe CF"],
        "Girona": ["Girona FC"],
        "Mallorca": ["RCD Mallorca", "Real Mallorca"],
        "Osasuna": ["CA Osasuna"],
        "Rayo Vallecano": ["Rayo", "Vallecano"],
        "Real Betis": ["Betis", "Real Betis Balompie"],
        "Real Madrid": ["R. Madrid", "Real"],
        "Real Sociedad": ["Sociedad", "R. Sociedad", "La Real"],
        "Sevilla": ["Sevilla FC"],
        "Valencia": ["Valencia CF"],
        "Villarreal": ["Villarreal CF", "Yellow Submarine"],

        # Italy - Serie A
        "AC Milan": ["Milan", "AC Milan Milan"],
        "Atalanta": ["Atalanta BC"],
        "Bologna": ["Bologna FC"],
        "Fiorentina": ["ACF Fiorentina"],
        "Inter": ["Inter Milan", "Internazionale", "FC Internazionale Milano"],
        "Juventus": ["Juve", "Juventus FC", "Juventus Turin"],
        "Lazio": ["SS Lazio", "Lazio Rome"],
        "Napoli": ["SSC Napoli"],
        "Roma": ["AS Roma"],
        "Torino": ["Torino FC"],

        # Germany - Bundesliga
        "Bayern Munich": ["Bayern Munich", "Bayern München", "FC Bayern", "Bayern"],
        "Borussia Dortmund": ["Dortmund", "BVB", "Borussia Dortmund 09"],
        "Bayer Leverkusen": ["Leverkusen", "Bayer 04 Leverkusen", "B04"],
        "RB Leipzig": ["Leipzig", "RasenBallsport Leipzig"],
        "Eintracht Frankfurt": ["Frankfurt", "Eintracht"],
        "VfB Stuttgart": ["Stuttgart"],
        "Borussia Monchengladbach": ["M'gladbach", "Monchengladbach", "Borussia M'gladbach", "Gladbach"],

        # France - Ligue 1
        "Paris Saint-Germain": ["PSG", "Paris SG", "Paris Saint Germain"],
        "Marseille": ["Olympique de Marseille", "OM"],
        "Monaco": ["AS Monaco", "Monaco FC"],
        "Lyon": ["Olympique Lyonnais", "OL"],
        "Lille": ["LOSC", "LOSC Lille"],
        "Lens": ["RC Lens"],
        "Rennes": ["Stade Rennais", "Stade Rennais FC"],
        "Nice": ["OGC Nice"],
    }

    def __init__(self, custom_aliases: dict[str, list[str]] | None = None, min_confidence: float = 85.0):
        self.min_confidence = min_confidence
        self.aliases: dict[str, str] = {}  # alias_normalized -> canonical_name
        self.canonical_list: list[str] = []

        all_mappings = dict(self.DEFAULT_ALIASES)
        if custom_aliases:
            all_mappings.update(custom_aliases)

        for canonical, alias_list in all_mappings.items():
            norm_canonical = self.normalize_string(canonical)
            self.aliases[norm_canonical] = canonical
            if canonical not in self.canonical_list:
                self.canonical_list.append(canonical)

            for alias in alias_list:
                norm_alias = self.normalize_string(alias)
                self.aliases[norm_alias] = canonical

    @staticmethod
    def normalize_string(text: str) -> str:
        """Strip accents, special punctuation, and lowercase."""
        if not text:
            return ""
        # Decompose unicode characters to strip diacritics/accents
        nfkd_form = unicodedata.normalize("NFKD", text)
        ascii_text = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        # Replace punctuation with space
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", ascii_text).lower()
        # Collapse multiple spaces
        return re.sub(r"\s+", " ", cleaned).strip()

    def resolve(self, raw_name: str, available_canonical: list[str] | None = None) -> tuple[str, float]:
        """Resolves a raw team name to its canonical name.
        
        Returns:
            (canonical_name, confidence_score)
        """
        if not raw_name:
            return "", 0.0

        norm_raw = self.normalize_string(raw_name)

        # 1. Exact alias match
        if norm_raw in self.aliases:
            return self.aliases[norm_raw], 100.0

        # 2. Fuzzy token set ratio matching against known canonicals and aliases
        search_targets = available_canonical if available_canonical else list(self.aliases.keys())
        if not search_targets:
            return raw_name, 50.0

        best_match = process.extractOne(
            norm_raw,
            search_targets,
            scorer=fuzz.token_set_ratio,
        )

        if best_match:
            matched_key, score, _ = best_match
            if score >= self.min_confidence:
                # If matched_key was an alias, look up canonical
                canonical = self.aliases.get(matched_key, matched_key)
                self.aliases[norm_raw] = canonical
                return canonical, float(score)

        # 3. Fallback: return raw name with lower confidence score
        logger.warning(
            "team_mapper_unresolved",
            raw_name=raw_name,
            best_candidate=best_match[0] if best_match else None,
            score=best_match[1] if best_match else 0,
        )
        return raw_name.strip(), float(best_match[1]) if best_match else 0.0


team_mapper = TeamMapper()
