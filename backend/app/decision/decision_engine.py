"""
Decision & Explanation Engine.

Deterministic rules + a deterministic explanation template — no LLM call
required to run. Plug an LLM in later ONLY to polish the wording of
`summary`/`recommended_actions`, and only ever feed it values already
computed here. It must never be allowed to invent numbers.

Thresholds below are placeholders (flagged in the P1 doc as "example
only — validate with P3/P4 or a domain reference before treating as
operational guidance").
"""
from __future__ import annotations

from backend.app.decision.explanation_llm import generate_llm_explanation
from backend.app.schemas import AgentResponse, Decision, DecisionFactor, FinalDecision, Plan

# --- placeholder thresholds, tune with P3 (weather) & P4 (geofence) --------
WAVE_AVOID_M = 2.0
WAVE_CAUTION_M = 1.2
WIND_CAUTION_KMH = 25
WIND_AVOID_KMH = 45

WEIGHTS = {"chlorophyll": 0.3, "sst": 0.2, "weather_risk": 0.3, "geofence_risk": 0.2}


class DecisionEngine:
    def make_decision(self, plan: Plan, agent_responses: list[AgentResponse]) -> FinalDecision:
        by_agent = {r.agent: r for r in agent_responses}
        weather = by_agent.get("weather")
        ocean = by_agent.get("ocean")
        geo = by_agent.get("geospatial")

        factors: list[DecisionFactor] = []
        limitations: list[str] = []
        confidences: list[float] = []

        label = "SAFE"

        # --- weather-driven rules ---
        has_cyclone_alert = False
        wave_height = None
        wind_speed = None
        if weather and weather.status == "success":
            data = weather.data
            wind_speed = data.get("wind_speed_kmh")
            wave_height = data.get("wave_height_m")
            has_cyclone_alert = any(
                a.get("type") in ("cyclone", "storm") for a in data.get("alerts", [])
            )
            confidences.append(weather.confidence)
            limitations.extend(weather.limitations)

            if wave_height is not None:
                impact = "severe" if wave_height >= WAVE_AVOID_M else (
                    "moderate" if wave_height >= WAVE_CAUTION_M else "favourable"
                )
                factors.append(DecisionFactor(name="wave_height", value=f"{wave_height} m", impact=impact, source="weather"))
            if wind_speed is not None:
                impact = "severe" if wind_speed >= WIND_AVOID_KMH else (
                    "moderate" if wind_speed >= WIND_CAUTION_KMH else "favourable"
                )
                factors.append(DecisionFactor(name="wind_speed", value=f"{wind_speed} km/h", impact=impact, source="weather"))
        else:
            limitations.append("Weather data unavailable — decision confidence reduced")

        # --- ocean-driven factors (context, not safety-gating) ---
        sst = chlorophyll = None
        if ocean and ocean.status == "success":
            data = ocean.data
            sst = data.get("sst_c")
            chlorophyll = data.get("chlorophyll_mg_m3")
            confidences.append(ocean.confidence)
            limitations.extend(ocean.limitations)
            if sst is not None:
                factors.append(DecisionFactor(name="sst", value=f"{sst} °C", impact="favourable", source="ocean"))
            if chlorophyll is not None:
                factors.append(
                    DecisionFactor(name="chlorophyll", value=f"{chlorophyll} mg/m³", impact="favourable", source="ocean")
                )
        else:
            limitations.append("Ocean data unavailable — suitability score less reliable")

        # --- geospatial rules ---
        in_restricted_zone = False
        if geo and geo.status == "success":
            data = geo.data
            in_restricted_zone = bool(data.get("in_restricted_zone", False))
            confidences.append(geo.confidence)
            limitations.extend(geo.limitations)
            factors.append(
                DecisionFactor(
                    name="geofence",
                    value="Inside restricted zone" if in_restricted_zone else "Outside restricted zones",
                    impact="severe" if in_restricted_zone else "neutral",
                    source="geospatial",
                )
            )
        else:
            limitations.append("Geospatial check unavailable — geofence risk unknown")

        # --- apply safety rule ladder ---
        if has_cyclone_alert or in_restricted_zone or (wave_height is not None and wave_height >= WAVE_AVOID_M):
            label = "AVOID"
        elif (wind_speed is not None and wind_speed >= WIND_CAUTION_KMH) or (
            wave_height is not None and wave_height >= WAVE_CAUTION_M
        ):
            label = "CAUTION"
        else:
            label = "SAFE"

        suitability = self._suitability_score(sst, chlorophyll, wind_speed, wave_height, in_restricted_zone)

        summary = self._build_summary(label, factors)
        # Optional: rephrase the deterministic summary via LLM if ANTHROPIC_API_KEY
        # is set. Falls back to the deterministic `summary` above on any failure —
        # see explanation_llm.py for why this is safe to call unconditionally.
        llm_summary = generate_llm_explanation(
            label=label,
            factors=[f.model_dump() for f in factors],
            deterministic_summary=summary,
        )
        if llm_summary:
            summary = llm_summary

        recommended_actions = self._recommend_actions(label, wind_speed, wave_height)
        overall_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.3

        evidence_trail = [
            {"agent": r.agent, "source": e.source, "url": e.url, "retrieved_at": e.retrieved_at.isoformat()}
            for r in agent_responses
            for e in r.evidence
        ]

        decision = Decision(
            type=plan.intent,
            label=label,
            summary=summary,
            factors=factors,
            suitability_score=suitability,
            recommended_actions=recommended_actions,
            confidence=overall_confidence,
            limitations=sorted(set(limitations)),
        )

        return FinalDecision(
            session_id=plan.session_id,
            plan_id=plan.plan_id,
            decision=decision,
            evidence_trail=evidence_trail,
        )

    # --- helpers ------------------------------------------------------

    def _suitability_score(
        self,
        sst: float | None,
        chlorophyll: float | None,
        wind_speed: float | None,
        wave_height: float | None,
        in_restricted_zone: bool,
    ) -> float:
        # Normalize each component to 0-1. These normalizations are
        # illustrative placeholders — tune against real baselines with P2/P3.
        sst_score = 1.0 if sst is not None and 24 <= sst <= 30 else 0.4
        chlorophyll_score = min((chlorophyll or 0) / 1.0, 1.0)
        weather_risk = min(((wind_speed or 0) / WIND_AVOID_KMH + (wave_height or 0) / WAVE_AVOID_M) / 2, 1.0)
        geofence_risk = 1.0 if in_restricted_zone else 0.0

        score = (
            WEIGHTS["chlorophyll"] * chlorophyll_score
            + WEIGHTS["sst"] * sst_score
            - WEIGHTS["weather_risk"] * weather_risk
            - WEIGHTS["geofence_risk"] * geofence_risk
        )
        return round(max(0.0, min(1.0, score)), 2)

    def _build_summary(self, label: str, factors: list[DecisionFactor]) -> str:
        severe = [f for f in factors if f.impact == "severe"]
        moderate = [f for f in factors if f.impact == "moderate"]
        if label == "AVOID":
            reasons = ", ".join(f.name for f in severe) or "elevated risk factors"
            return f"Conditions are unsafe for a normal fishing trip due to {reasons}. Avoid departure."
        if label == "CAUTION":
            reasons = ", ".join(f.name for f in moderate) or "moderately elevated conditions"
            return f"Conditions are generally acceptable but {reasons} warrant caution, especially for small boats."
        return "Conditions look favourable for a normal fishing trip with standard precautions."

    def _recommend_actions(self, label: str, wind_speed: float | None, wave_height: float | None) -> list[str]:
        if label == "AVOID":
            return [
                "Do not depart until conditions improve",
                "Monitor official IMD/INCOIS advisories",
                "Check again closer to departure time",
            ]
        if label == "CAUTION":
            actions = ["Prefer larger, more stable boats if possible", "Avoid going far offshore"]
            if wind_speed and wind_speed >= WIND_CAUTION_KMH:
                actions.append("Watch for sudden wind shifts")
            if wave_height and wave_height >= WAVE_CAUTION_M:
                actions.append("Expect choppier water; secure gear accordingly")
            return actions
        return ["Standard safety precautions apply", "Carry communication and safety equipment as usual"]
