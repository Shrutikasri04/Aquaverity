"""
Decision & Explanation Engine — v2, integrating P2's real ocean-intelligence
service and P3's real weather-safety service.

Key architectural decision (per P2's docs/P2_HANDOFF.md, which explicitly
states "P3 owns safety. P4 owns route/geofence. P1 combines them."):

  - P3 already runs its own hazard detection + risk scoring against
    official sources (Open-Meteo, INCOIS WW3, SACHET-NDMA). We do NOT
    re-derive wind/wave thresholds ourselves anymore -- P3's risk_level
    is treated as the authoritative safety signal.
  - P2's ocean_opportunity_score (0-100) drives fishing suitability, not
    safety. Per their handoff: "P1 should not assume ... ocean score
    means total trip safety."
  - P1's (our) job is to COMBINE: P3's safety gate + P2's opportunity
    score + P4's geofence check (still mocked until P4 delivers) into
    one FinalDecision with a unified evidence trail and explanation.

Geofence logic and thresholds below are still placeholders where P4's
real service isn't wired in yet.
"""
from __future__ import annotations

from backend.app.decision.explanation_llm import generate_llm_explanation
from backend.app.schemas import AgentResponse, Decision, DecisionFactor, FinalDecision, Plan

# P3's 4-level risk vocabulary -> our 3-level Decision label.
RISK_LEVEL_TO_LABEL = {
    "LOW": "SAFE",
    "MODERATE": "CAUTION",
    "HIGH": "AVOID",
    "EXTREME": "AVOID",
}


class DecisionEngine:
    def make_decision(self, plan: Plan, agent_responses: list[AgentResponse]) -> FinalDecision:
        by_agent = {r.agent: r for r in agent_responses}
        weather = by_agent.get("weather")  # P3: marine_conditions payload
        ocean = by_agent.get("ocean")  # P2: ocean_conditions payload
        geo = by_agent.get("geospatial")  # still mocked pending P4

        factors: list[DecisionFactor] = []
        limitations: list[str] = []
        confidences: list[float] = []
        evidence_trail: list[dict] = []

        # ---------------- P3: weather-safety (authoritative for safety) ----------------
        risk_level = None
        hazards: list[dict] = []
        if weather and weather.status in ("success", "partial"):
            marine = weather.data.get("marine_conditions", {})
            risk = marine.get("risk", {})
            risk_level = risk.get("risk_level")
            hazards = marine.get("hazards", [])
            safety = marine.get("safety", {})
            w = marine.get("weather") or {}
            wave = ((marine.get("ocean") or {}).get("waves")) or {}

            confidences.append(weather.confidence)
            limitations.extend(weather.limitations)

            if w.get("wind_speed_mps") is not None:
                wind_kmh = round(w["wind_speed_mps"] * 3.6, 1)
                factors.append(
                    DecisionFactor(
                        name="wind_speed",
                        value=f"{wind_kmh} km/h",
                        impact=_severity_to_impact(risk_level),
                        source="weather",
                    )
                )
            if wave.get("significant_wave_height_m") is not None:
                factors.append(
                    DecisionFactor(
                        name="wave_height",
                        value=f"{wave['significant_wave_height_m']} m",
                        impact=_severity_to_impact(risk_level),
                        source="weather",
                    )
                )
            for hazard in hazards:
                factors.append(
                    DecisionFactor(
                        name=hazard.get("type", "hazard").lower(),
                        value=hazard.get("message") or str(hazard.get("value", "")),
                        impact="severe" if hazard.get("severity") in ("EXTREME", "HIGH", "RED", "ORANGE") else "moderate",
                        source="weather",
                    )
                )
            if safety.get("message"):
                limitations.append(f"P3 safety note: {safety['message']}")
            for src in marine.get("sources", []):
                evidence_trail.append({"agent": "weather", "source": src, "url": None, "retrieved_at": None})
        else:
            limitations.append("Weather/safety data unavailable — decision confidence reduced")

        # ---------------- P2: ocean intelligence (suitability, not safety) ----------------
        opportunity_score = None
        sst = chlorophyll = pfz_status = None
        if ocean and ocean.status == "success":
            oc = ocean.data.get("ocean_conditions", {})
            ov = oc.get("ocean", {})
            sst = ov.get("sst_c")
            chlorophyll = ov.get("chlorophyll_mg_m3")
            pfz_status = ov.get("pfz_status")
            opportunity_score = ov.get("ocean_opportunity_score")

            confidences.append(ocean.confidence)
            limitations.extend(ocean.limitations)

            if sst is not None:
                factors.append(DecisionFactor(name="sst", value=f"{sst} °C", impact="favourable", source="ocean"))
            if chlorophyll is not None:
                factors.append(
                    DecisionFactor(name="chlorophyll", value=f"{chlorophyll} mg/m³", impact="favourable", source="ocean")
                )
            if pfz_status is not None:
                factors.append(
                    DecisionFactor(
                        name="pfz_status",
                        value=str(pfz_status),
                        impact="favourable" if pfz_status not in ("unknown", None) else "neutral",
                        source="ocean",
                    )
                )
            for e in oc.get("evidence", []):
                evidence_trail.append(
                    {"agent": "ocean", "source": e.get("source"), "url": None, "retrieved_at": e.get("timestamp")}
                )
        else:
            limitations.append("Ocean data unavailable — suitability score less reliable")

        # ---------------- P4: geospatial (still mocked) ----------------
        in_restricted_zone = False
        if geo and geo.status == "success":
            in_restricted_zone = bool(geo.data.get("in_restricted_zone", False))
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
            for e in geo.evidence:
                evidence_trail.append(
                    {"agent": "geospatial", "source": e.source, "url": e.url, "retrieved_at": e.retrieved_at.isoformat()}
                )
        else:
            limitations.append("Geospatial check unavailable — geofence risk unknown")

        # ---------------- combine: P1's job ----------------
        label = RISK_LEVEL_TO_LABEL.get(risk_level, "CAUTION") if risk_level else "CAUTION"
        if in_restricted_zone:
            label = "AVOID"  # geofence veto always wins, per P2's handoff reasoning example

        suitability = round((opportunity_score or 0) / 100, 2) if not in_restricted_zone else 0.0

        summary = self._build_summary(label, risk_level, factors)
        llm_summary = generate_llm_explanation(
            label=label,
            factors=[f.model_dump() for f in factors],
            deterministic_summary=summary,
        )
        if llm_summary:
            summary = llm_summary

        recommended_actions = self._recommend_actions(label, hazards)
        overall_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.3

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

    def _build_summary(self, label: str, risk_level: str | None, factors: list[DecisionFactor]) -> str:
        if label == "AVOID":
            severe = [f.name for f in factors if f.impact == "severe"]
            reasons = ", ".join(severe) or (f"a {risk_level.lower()} risk level" if risk_level else "elevated risk")
            return f"Conditions are unsafe for a normal fishing trip due to {reasons}. Avoid departure."
        if label == "CAUTION":
            return (
                f"Conditions are generally acceptable but P3's risk assessment ({risk_level or 'moderate'}) "
                "warrants caution, especially for small boats."
            )
        return "Conditions look favourable for a normal fishing trip with standard precautions."

    def _recommend_actions(self, label: str, hazards: list[dict]) -> list[str]:
        if label == "AVOID":
            actions = ["Do not depart until conditions improve", "Monitor official IMD/INCOIS/SACHET advisories"]
            if any(h.get("type") == "CYCLONE" for h in hazards):
                actions.append("Cyclone hazard flagged — follow official evacuation guidance if issued")
            return actions
        if label == "CAUTION":
            return [
                "Prefer larger, more stable boats if possible",
                "Avoid going far offshore",
                "Recheck conditions closer to departure time",
            ]
        return ["Standard safety precautions apply", "Carry communication and safety equipment as usual"]


def _severity_to_impact(risk_level: str | None) -> str:
    return {"LOW": "favourable", "MODERATE": "moderate", "HIGH": "severe", "EXTREME": "severe"}.get(
        risk_level, "neutral"
    )
