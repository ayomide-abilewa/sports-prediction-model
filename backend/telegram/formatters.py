from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

# West Africa Time (WAT) is UTC+1
WAT = timezone(timedelta(hours=1))


class TelegramFormatter:
    """Formats analytical betting predictions and accumulators for Telegram distribution."""

    @staticmethod
    def format_wat_time(utc_dt: datetime) -> str:
        """Converts UTC datetime to formatted WAT string."""
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        wat_dt = utc_dt.astimezone(WAT)
        return wat_dt.strftime("%d %b %H:%M WAT")

    @classmethod
    def format_single_prediction(cls, pred: dict[str, Any]) -> str:
        """Formats a single market prediction message."""
        fixture = pred.get("fixture", "Unknown Fixture")
        league = pred.get("league", "Football")
        kickoff_str = pred.get("kickoff", "")
        if kickoff_str:
            try:
                dt = datetime.fromisoformat(kickoff_str)
                time_display = cls.format_wat_time(dt)
            except Exception:
                time_display = kickoff_str
        else:
            time_display = "TBD"

        market = pred.get("market_type", "").upper()
        selection = pred.get("selection", "").title()
        model_prob = pred.get("model_probability", 0.0)
        odds = pred.get("available_odds", 0.0)
        fair_odds = pred.get("fair_odds", 0.0)
        ev = pred.get("expected_value", 0.0)
        tier = pred.get("confidence_tier", "Sharp Value")

        ev_sign = "+" if ev > 0 else ""
        ev_str = f"{ev_sign}{ev * 100.0:.1f}%"

        msg = (
            f"🎯 *MATCH PREDICTION*\n"
            f"🏆 *{league}*\n"
            f"⚽ *{fixture}*\n"
            f"⏰ 🕒 {time_display}\n\n"
            f"📊 *Market:* `{market}`\n"
            f"💡 *Selection:* `{selection}`\n\n"
            f"📈 *Model Probability:* `{model_prob * 100:.1f}%`\n"
            f"💰 *Available Odds:* `{odds:.2f}`\n"
            f"⚖️ *Fair Odds:* `{fair_odds:.2f}`\n"
            f"✨ *Expected Value (EV):* `{ev_str}`\n"
            f"🏷️ *Classification:* `{tier}`\n\n"
            f"⚠️ _Disclaimer: Probability estimates reflect statistical modeling. Stake responsibly._"
        )
        return msg

    @classmethod
    def format_accumulator_slip(cls, slip: dict[str, Any], booking_code: str | None = None) -> str:
        """Formats an accumulator combination bet slip."""
        slip_name = slip.get("slip_name", "Curated Accumulator")
        combined_odds = slip.get("combined_odds", 0.0)
        joint_prob = slip.get("joint_probability", 0.0)
        exp_return = slip.get("expected_return", 0.0)
        risk = slip.get("risk_class", "Moderate")

        legs_text = []
        for i, leg in enumerate(slip.get("legs", []), start=1):
            fixture = leg.get("fixture", "")
            market = leg.get("market", "").upper()
            sel = leg.get("selection", "").title()
            odds = leg.get("odds", 0.0)
            prob = leg.get("probability", 0.0)
            legs_text.append(
                f"{i}. *{fixture}*\n"
                f"   👉 `{market}: {sel}` @ *{odds:.2f}* (P: {prob * 100:.0f}%)"
            )

        legs_formatted = "\n\n".join(legs_text)
        code_block = f"\n🔖 *Booking Code (SportyBet):* `{booking_code}`" if booking_code else ""

        return (
            f"📋 *{slip_name.upper()}*\n"
            f"🛡️ *Risk Rating:* `{risk}`\n\n"
            f"{legs_formatted}\n\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"🔢 *Total Legs:* `{len(slip.get('legs', []))}`\n"
            f"🚀 *Combined Odds:* `{combined_odds:.2f}`\n"
            f"🎯 *Joint Probability:* `{joint_prob * 100:.1f}%`\n"
            f"📈 *Expected Return:* `+{exp_return * 100:.1f}%`"
            f"{code_block}\n\n"
            f"⚠️ _Notice: High odds accumulators entail high variance. Never risk essential capital._"
        )
