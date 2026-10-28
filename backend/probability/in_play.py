from __future__ import annotations

import math
from typing import Any
import numpy as np
from scipy.stats import poisson


class InPlayPredictionEngine:
    """Quantitative Bayesian In-Play Football Prediction Engine.
    
    Dynamically projects scoreline distributions, next goal probabilities,
    and live in-play betting markets using pre-match baselines adjusted for
    in-game elapsed minutes, live momentum, and tactical game states.
    """

    def __init__(self, home_advantage: float = 0.20):
        self.home_advantage = home_advantage

    def calculate_in_play_probabilities(
        self,
        home_team: str,
        away_team: str,
        minute: int,
        score_home: int,
        score_away: int,
        pre_match_xg_home: float = 1.45,
        pre_match_xg_away: float = 1.15,
        live_stats: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Calculates live in-play probabilities and picks what to carry.
        
        Args:
            home_team: Home club name
            away_team: Away club name
            minute: Current match minute (e.g. 35, 68, 82)
            score_home: Current home goals scored
            score_away: Current away goals scored
            pre_match_xg_home: Pre-match expected goals for home
            pre_match_xg_away: Pre-match expected goals for away
            live_stats: In-game stats (possession, shots, shots_on_target, corners, etc.)
        """
        stats = live_stats or {}
        possession_h = stats.get("possession_home")
        sot_h = stats.get("shots_on_target_home")
        sot_a = stats.get("shots_on_target_away")
        red_cards_h = stats.get("red_cards_home", 0) or 0
        red_cards_a = stats.get("red_cards_away", 0) or 0
        corners_h = stats.get("corners_home")
        corners_a = stats.get("corners_away")
        cards_h = stats.get("cards_home")
        cards_a = stats.get("cards_away")

        # 1. Remaining time fraction
        elapsed = min(max(minute, 1), 94)
        rem_fraction = max(1.0, 90.0 - elapsed) / 90.0

        # 2. In-game momentum factors
        if sot_h is not None and sot_a is not None:
            sot_total = sot_h + sot_a
            sot_diff = sot_h - sot_a
            momentum_h = 1.0 + (0.20 * (sot_diff / max(1, sot_total)))
            momentum_a = 1.0 - (0.20 * (sot_diff / max(1, sot_total)))
        else:
            momentum_h = momentum_a = 1.0

        # Possession skew
        if possession_h is not None and 0 < possession_h < 100:
            poss_factor_h = (possession_h / 50.0) ** 0.4
            poss_factor_a = ((100.0 - possession_h) / 50.0) ** 0.4
        else:
            poss_factor_h = poss_factor_a = 1.0

        # Red card adjustment
        red_factor_h = 0.65 if red_cards_h > 0 else 1.0
        red_factor_a = 0.65 if red_cards_a > 0 else 1.0
        red_boost_for_opponent_h = 1.25 if red_cards_a > 0 else 1.0
        red_boost_for_opponent_a = 1.25 if red_cards_h > 0 else 1.0

        # Game state effect (leading team defends more, trailing team pushes)
        lead = score_home - score_away
        if lead > 0:
            # Home leading
            state_h = 0.88
            state_a = 1.15
        elif lead < 0:
            # Away leading
            state_h = 1.18
            state_a = 0.88
        else:
            state_h = 1.0
            state_a = 1.0

        # Remaining expected goals lambda and mu
        lambda_rem = max(
            0.02,
            pre_match_xg_home * rem_fraction * momentum_h * poss_factor_h * red_factor_h * red_boost_for_opponent_h * state_h,
        )
        mu_rem = max(
            0.02,
            pre_match_xg_away * rem_fraction * momentum_a * poss_factor_a * red_factor_a * red_boost_for_opponent_a * state_a,
        )

        # 3. Joint distribution for remaining goals (up to 6 additional goals each)
        max_rem = 6
        p_matrix = np.zeros((max_rem + 1, max_rem + 1), dtype=float)
        for h_rem in range(max_rem + 1):
            for a_rem in range(max_rem + 1):
                p_matrix[h_rem, a_rem] = poisson.pmf(h_rem, lambda_rem) * poisson.pmf(a_rem, mu_rem)

        p_sum = np.sum(p_matrix)
        if p_sum > 0:
            p_matrix /= p_sum

        # 4. Final Full-Time Result (1X2)
        prob_home = 0.0
        prob_draw = 0.0
        prob_away = 0.0

        for h_rem in range(max_rem + 1):
            for a_rem in range(max_rem + 1):
                p = p_matrix[h_rem, a_rem]
                ft_h = score_home + h_rem
                ft_a = score_away + a_rem
                if ft_h > ft_a:
                    prob_home += p
                elif ft_h == ft_a:
                    prob_draw += p
                else:
                    prob_away += p

        prob_1x = prob_home + prob_draw
        prob_x2 = prob_draw + prob_away
        prob_12 = prob_home + prob_away

        # 5. Next Goal Probabilities
        sum_lambdas = lambda_rem + mu_rem
        prob_at_least_one_more = float(1.0 - math.exp(-sum_lambdas))
        prob_no_more_goals = float(math.exp(-sum_lambdas))

        prob_next_home = (lambda_rem / sum_lambdas) * prob_at_least_one_more if sum_lambdas > 0 else 0.0
        prob_next_away = (mu_rem / sum_lambdas) * prob_at_least_one_more if sum_lambdas > 0 else 0.0

        # 6. Live Match Totals (Over / Under from Current Score)
        curr_goals = score_home + score_away
        totals: dict[str, dict[str, float]] = {}

        for line in (curr_goals + 0.5, curr_goals + 1.5, curr_goals + 2.5):
            over_p = 0.0
            for h_rem in range(max_rem + 1):
                for a_rem in range(max_rem + 1):
                    if (curr_goals + h_rem + a_rem) > line:
                        over_p += p_matrix[h_rem, a_rem]
            totals[f"over_under_{line}"] = {
                "over": round(float(over_p), 4),
                "under": round(float(1.0 - over_p), 4),
            }

        # 7. Live GG / NG (Both Teams to Score)
        btts_settled = score_home >= 1 and score_away >= 1
        if btts_settled:
            p_gg = None
            p_ng = None
        elif score_home >= 1 and score_away == 0:
            p_gg = float(1.0 - math.exp(-mu_rem))
            p_ng = float(1.0 - p_gg)
        elif score_home == 0 and score_away >= 1:
            p_gg = float(1.0 - math.exp(-lambda_rem))
            p_ng = float(1.0 - p_gg)
        else:
            p_gg = float((1.0 - math.exp(-lambda_rem)) * (1.0 - math.exp(-mu_rem)))
            p_ng = float(1.0 - p_gg)

        # 8. Live Corners & Cards Projection
        proj_corners = round(corners_h + corners_a + 9.5 * rem_fraction, 1) if corners_h is not None and corners_a is not None else None
        proj_cards = round(cards_h + cards_a + 4.2 * rem_fraction, 1) if cards_h is not None and cards_a is not None else None

        # 9. Formulate Live In-Play Recommendations ("What to Carry")
        evaluated_in_play: list[dict[str, Any]] = []

        # Candidate live options
        candidates = [
            ("Live Full Time (1X2)", f"{home_team} to Win", prob_home, 1.0 / max(prob_home, 0.01)),
            ("Live Full Time (1X2)", f"{away_team} to Win", prob_away, 1.0 / max(prob_away, 0.01)),
            ("Live Full Time (1X2)", "Draw", prob_draw, 1.0 / max(prob_draw, 0.01)),
            ("Live Double Chance", f"{home_team} or Draw (1X)", prob_1x, 1.0 / max(prob_1x, 0.01)),
            ("Live Double Chance", f"Draw or {away_team} (X2)", prob_x2, 1.0 / max(prob_x2, 0.01)),
            ("Next Goal", f"Next Goal: {home_team}", prob_next_home, 1.0 / max(prob_next_home, 0.01)),
            ("Next Goal", f"Next Goal: {away_team}", prob_next_away, 1.0 / max(prob_next_away, 0.01)),
            ("Next Goal", "No More Goals", prob_no_more_goals, 1.0 / max(prob_no_more_goals, 0.01)),
        ]
        if not btts_settled:
            candidates.extend([
                ("Live GG / NG", "GG (Both Teams Score - Yes)", p_gg, 1.0 / max(p_gg, 0.01)),
                ("Live GG / NG", "NG (Clean Sheet from here - No)", p_ng, 1.0 / max(p_ng, 0.01)),
            ])

        # Add live totals
        for line_key, ou in totals.items():
            line_val = line_key.replace("over_under_", "")
            candidates.append(("Live Match Goals", f"Over {line_val} Goals", ou["over"], 1.0 / max(ou["over"], 0.01)))
            candidates.append(("Live Match Goals", f"Under {line_val} Goals", ou["under"], 1.0 / max(ou["under"], 0.01)))

        for m_cat, sel, p, f_odds in candidates:
            if p is None or p < 0.25 or p >= 0.995:
                continue
            evaluated_in_play.append({
                "market": m_cat,
                "selection": sel,
                "probability": round(p, 4),
                "fair_odds": round(f_odds, 2),
                "live_odds": None,
                "confidence_tier": (
                    "Tier 1 – In-Play Banker" if p >= 0.75
                    else ("Tier 2 – High Conviction" if p >= 0.60 else "Solid Value")
                ),
            })
            evaluated_in_play[-1]["confidence_tier"] = "Uncalibrated model estimate"

        # Rank to find the #1 Surest In-Play Call
        evaluated_in_play.sort(key=lambda x: x["probability"], reverse=True)
        surest_in_play = next(
            (pick for pick in evaluated_in_play if pick["market"] in {"Next Goal", "Live Match Goals"}),
            None,
        )

        # Build analytical live narrative
        narrative = self._generate_in_play_narrative(
            home_team, away_team, minute, score_home, score_away,
            surest_in_play, lambda_rem, mu_rem, stats
        )

        return {
            "minute": minute,
            "score": {"home": score_home, "away": score_away},
            "remaining_projected_xg": {
                "home": round(lambda_rem, 2),
                "away": round(mu_rem, 2),
                "total": round(lambda_rem + mu_rem, 2),
            },
            "1x2": {
                "home": round(prob_home, 4),
                "draw": round(prob_draw, 4),
                "away": round(prob_away, 4),
            },
            "double_chance": {
                "1x": round(prob_1x, 4),
                "x2": round(prob_x2, 4),
                "12": round(prob_12, 4),
            },
            "next_goal": {
                "home": round(prob_next_home, 4),
                "away": round(prob_next_away, 4),
                "no_more_goals": round(prob_no_more_goals, 4),
            },
            "totals": totals,
            "btts": {
                "gg": round(p_gg, 4) if p_gg is not None else None,
                "ng": round(p_ng, 4) if p_ng is not None else None,
            },
            "projected_corners": proj_corners,
            "projected_cards": proj_cards,
            "surest_in_play_pick": surest_in_play,
            "top_in_play_picks": evaluated_in_play[:4],
            "live_narrative": narrative,
            "all_live_markets": evaluated_in_play,
        }

    def _generate_in_play_narrative(
        self,
        home: str,
        away: str,
        minute: int,
        score_h: int,
        score_a: int,
        surest: dict[str, Any] | None,
        lambda_rem: float,
        mu_rem: float,
        stats: dict[str, Any],
    ) -> str:
        pick_note = (
            f"Model outlook: {surest['selection']} at {surest['probability'] * 100:.1f}%. "
            if surest else "No supported open market forecast is available. "
        )
        return (
            f"{minute}' live, score {score_h}-{score_a}. Team-history model estimates "
            f"{lambda_rem + mu_rem:.2f} remaining xG. {pick_note}This estimate is uncalibrated; live bookmaker odds are unavailable."
        )


in_play_engine = InPlayPredictionEngine()
