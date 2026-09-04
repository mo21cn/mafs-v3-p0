"""Post-P1.5 R1 semantic route artifacts and fail-closed review.

The module does not invent routes from upstream prose.  A model or human
planner must externalize an ``EpistemicRoute`` and a semantic fidelity review.
Deterministic code validates those artifacts and blocks execution when their
declared status is not ``PRESERVED``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any


SCHEMA_VERSION = "3.0-post-p1p5-a"
FIDELITY_STATUSES = ("PRESERVED", "CONTRACTED", "DRIFTED", "UNRESOLVED")
ROUTE_STATUSES = ("PROPOSED", "ADMITTED", "BLOCKED", "RETIRED")

_FORBIDDEN_IDENTITY_KEYS = {
    "expected_doi",
    "known_target_doi",
    "target_doi",
    "expected_title",
    "exact_target_title",
    "known_target_title",
    "target_paper_identity",
    "evaluator_held_paper_identity",
    "benchmark_oracle_identity",
}
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)


class SemanticBoundaryError(ValueError):
    """Raised when a Package A semantic invariant would be crossed."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def assert_open_discovery_pure(payload: Any, *, path: str = "$") -> None:
    """Reject target-identity leakage anywhere in an open-discovery artifact.

    This is intentionally a boundary check rather than a scientific-quality
    score.  It catches explicit oracle fields and DOI-shaped values.  It does
    not use lexical similarity to decide whether a route is scientifically
    independent or faithful.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_norm = str(key).strip().lower()
            if key_norm in _FORBIDDEN_IDENTITY_KEYS:
                raise SemanticBoundaryError(
                    f"open discovery target identity is forbidden at {path}.{key}"
                )
            assert_open_discovery_pure(value, path=f"{path}.{key}")
        return
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            assert_open_discovery_pure(value, path=f"{path}[{index}]")
        return
    if isinstance(payload, str) and _DOI_RE.search(payload):
        raise SemanticBoundaryError(
            f"DOI-shaped target identity is forbidden in open discovery at {path}"
        )


@dataclass(frozen=True)
class EpistemicRoute:
    route_id: str
    origin_requirement_id: str
    semantic_intent: str
    independence_rationale: str
    framing_consequence: str
    search_vocabulary: tuple[str, ...]
    disciplinary_neighborhood: tuple[str, ...]
    evidence_need: str
    source_requirement: dict[str, Any]
    search_intent: str
    uncertainty: str
    status: str = "PROPOSED"
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"ER-[0-9]{3,6}", self.route_id):
            raise SemanticBoundaryError(f"invalid route_id: {self.route_id!r}")
        required_text = {
            "origin_requirement_id": self.origin_requirement_id,
            "semantic_intent": self.semantic_intent,
            "independence_rationale": self.independence_rationale,
            "evidence_need": self.evidence_need,
            "search_intent": self.search_intent,
            "uncertainty": self.uncertainty,
        }
        empty = [name for name, value in required_text.items() if not value.strip()]
        if empty:
            raise SemanticBoundaryError(f"empty EpistemicRoute fields: {empty}")
        if not self.search_vocabulary:
            raise SemanticBoundaryError("search_vocabulary must not be empty")
        if self.status not in ROUTE_STATUSES:
            raise SemanticBoundaryError(f"invalid route status: {self.status!r}")
        assert_open_discovery_pure(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpistemicRoute":
        return cls(
            route_id=data["route_id"],
            origin_requirement_id=data["origin_requirement_id"],
            semantic_intent=data["semantic_intent"],
            independence_rationale=data["independence_rationale"],
            framing_consequence=data.get("framing_consequence", ""),
            search_vocabulary=tuple(data["search_vocabulary"]),
            disciplinary_neighborhood=tuple(data.get("disciplinary_neighborhood", [])),
            evidence_need=data["evidence_need"],
            source_requirement=dict(data["source_requirement"]),
            search_intent=data["search_intent"],
            uncertainty=data["uncertainty"],
            status=data.get("status", "PROPOSED"),
            created_at=data.get("created_at", _now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "route_id": self.route_id,
            "origin_requirement_id": self.origin_requirement_id,
            "semantic_intent": self.semantic_intent,
            "independence_rationale": self.independence_rationale,
            "framing_consequence": self.framing_consequence,
            "search_vocabulary": list(self.search_vocabulary),
            "disciplinary_neighborhood": list(self.disciplinary_neighborhood),
            "evidence_need": self.evidence_need,
            "source_requirement": dict(self.source_requirement),
            "search_intent": self.search_intent,
            "uncertainty": self.uncertainty,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RequirementRouteFidelityReview:
    review_id: str
    requirement_id: str
    route_id: str
    status: str
    preserved_obligations: tuple[str, ...]
    omitted_obligations: tuple[str, ...]
    added_scope: tuple[str, ...]
    rationale: str
    review_authority: str
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"RFR-[0-9]{3,6}", self.review_id):
            raise SemanticBoundaryError(f"invalid review_id: {self.review_id!r}")
        if self.status not in FIDELITY_STATUSES:
            raise SemanticBoundaryError(f"invalid fidelity status: {self.status!r}")
        if not self.rationale.strip() or not self.review_authority.strip():
            raise SemanticBoundaryError("fidelity review requires rationale and authority")
        if self.status == "PRESERVED" and self.omitted_obligations:
            raise SemanticBoundaryError(
                "PRESERVED fidelity review cannot declare omitted obligations"
            )

    @property
    def execution_allowed(self) -> bool:
        return self.status == "PRESERVED"

    def require_execution_allowed(self, route: EpistemicRoute) -> None:
        if self.requirement_id != route.origin_requirement_id or self.route_id != route.route_id:
            raise SemanticBoundaryError("fidelity review lineage does not match route")
        if not self.execution_allowed:
            raise SemanticBoundaryError(
                f"route execution blocked by fidelity status {self.status}"
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequirementRouteFidelityReview":
        return cls(
            review_id=data["review_id"],
            requirement_id=data["requirement_id"],
            route_id=data["route_id"],
            status=data["status"],
            preserved_obligations=tuple(data.get("preserved_obligations", [])),
            omitted_obligations=tuple(data.get("omitted_obligations", [])),
            added_scope=tuple(data.get("added_scope", [])),
            rationale=data["rationale"],
            review_authority=data["review_authority"],
            created_at=data.get("created_at", _now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "review_id": self.review_id,
            "requirement_id": self.requirement_id,
            "route_id": self.route_id,
            "status": self.status,
            "execution_allowed": self.execution_allowed,
            "preserved_obligations": list(self.preserved_obligations),
            "omitted_obligations": list(self.omitted_obligations),
            "added_scope": list(self.added_scope),
            "rationale": self.rationale,
            "review_authority": self.review_authority,
            "created_at": self.created_at,
        }
