"""Risk scoring helpers for portfolio-level views."""

from ..models import Farm


def classify_portfolio_risk(farms: list) -> dict:
    """Return aggregate risk summary across all enrolled farms."""
    healthy = sum(1 for f in farms if f.get("health_status") == "healthy")
    mild = sum(1 for f in farms if f.get("health_status") == "mild_stress")
    severe = sum(1 for f in farms if f.get("health_status") == "stress")
    total = len(farms)

    return {
        "total_farms": total,
        "healthy": healthy,
        "mild_stress": mild,
        "severe_stress": severe,
        "stress_rate_pct": round(severe / max(total, 1) * 100, 1),
        "portfolio_health": "good" if severe / max(total, 1) < 0.1 else ("moderate" if severe / max(total, 1) < 0.3 else "high_risk"),
    }
