"""Post-P1.5 R3 bounded evidence-resolution adapter.

The implementation deliberately separates paper-level source acquisition from
proposition-level span and judgment artifacts.  It is small, provider-aware,
and cacheable; it is not a provider orchestration platform.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import html
import json
import re
from typing import Any, Protocol
import urllib.parse
import urllib.request
import urllib.error

from .epistemic_route import SCHEMA_VERSION, SemanticBoundaryError


SOURCE_REPRESENTATIONS = (
    "IDENTITY_ONLY",
    "ABSTRACT",
    "FULL_TEXT",
    "OTHER_ACCESSIBLE_CONTENT",
    "INACCESSIBLE",
)
GROUNDING_STATES = (
    "NO_SPAN",
    "CANDIDATE_SPAN",
    "CITABLE_SPAN",
    "NOT_ADDRESSED",
    "AMBIGUOUS",
    "SOURCE_CONTENT_NOT_ACCESSIBLE",
)
EVIDENCE_ROLES = (
    "BACKGROUND",
    "METHOD",
    "RESULT",
    "STATISTICAL_RESULT",
    "DISCUSSION",
    "AUTHOR_INTERPRETATION",
    "LIMITATION",
    "OTHER",
)
RELATIONS = ("SUPPORTS", "CONTRADICTS", "PARTIALLY_SUPPORTS", "NOT_GROUNDED")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_id(prefix: str, *values: str) -> str:
    digest = _sha256_text("\x1f".join(values))[:12]
    return f"{prefix}-{digest}"


def _normalized_doi(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    return normalized or None


def canonical_identity_key(canonical_evidence: dict[str, Any]) -> str:
    canonical = canonical_evidence.get("canonical") or {}
    doi = _normalized_doi(canonical.get("doi"))
    if doi:
        return f"doi:{doi}"
    title = (canonical.get("title") or "").strip().casefold()
    year = canonical.get("year")
    if not title:
        raise SemanticBoundaryError("canonical identity has neither DOI nor title")
    return f"title-year:{title}:{year}"


@dataclass(frozen=True)
class SourceMaterial:
    canonical_identity: dict[str, Any]
    representation_type: str
    locator: str
    content: str
    access_provenance: dict[str, Any]

    def __post_init__(self) -> None:
        if self.representation_type not in SOURCE_REPRESENTATIONS:
            raise SemanticBoundaryError(
                f"invalid source representation: {self.representation_type!r}"
            )
        if self.representation_type in {"IDENTITY_ONLY", "INACCESSIBLE"}:
            if self.content:
                raise SemanticBoundaryError("non-content source state cannot carry content")
        elif not self.content.strip():
            raise SemanticBoundaryError("accessible source material must carry content")


class SourceAdapter(Protocol):
    name: str

    def fetch(self, canonical_evidence: dict[str, Any]) -> SourceMaterial | None:
        """Return matching source material, or ``None`` when unavailable."""


@dataclass
class InMemorySourceAdapter:
    """Hermetic adapter for tests and reproducible offline demonstrations."""

    materials_by_identity: dict[str, SourceMaterial]
    name: str = "in_memory_source_adapter"
    fetch_count: int = 0

    def fetch(self, canonical_evidence: dict[str, Any]) -> SourceMaterial | None:
        self.fetch_count += 1
        return self.materials_by_identity.get(canonical_identity_key(canonical_evidence))


@dataclass
class OpenAlexAbstractAdapter:
    """Minimal live abstract adapter keyed by the already resolved DOI."""

    name: str = "openalex_abstract_v1"
    timeout_seconds: float = 20.0
    user_agent: str = "MAFS-Package-A/1.0 (mailto:mafs@example.invalid)"

    @staticmethod
    def _reconstruct_abstract(index: dict[str, list[int]] | None) -> str:
        if not index:
            return ""
        positions: list[tuple[int, str]] = []
        for word, offsets in index.items():
            for offset in offsets:
                positions.append((int(offset), word))
        positions.sort(key=lambda pair: pair[0])
        return " ".join(word for _, word in positions)

    def fetch(self, canonical_evidence: dict[str, Any]) -> SourceMaterial | None:
        canonical = canonical_evidence.get("canonical") or {}
        doi = _normalized_doi(canonical.get("doi"))
        if not doi:
            return None
        encoded = urllib.parse.quote(f"https://doi.org/{doi}", safe="")
        url = f"https://api.openalex.org/works/{encoded}"
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
                status = getattr(response, "status", 200)
        except (OSError, urllib.error.URLError):
            return None
        if status != 200:
            return None
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        observed_doi = _normalized_doi(payload.get("doi"))
        if observed_doi != doi:
            raise SemanticBoundaryError(
                f"OpenAlex source identity mismatch: expected {doi!r}, got {observed_doi!r}"
            )
        content = self._reconstruct_abstract(payload.get("abstract_inverted_index"))
        if not content:
            return None
        return SourceMaterial(
            canonical_identity={
                "doi": doi,
                "title": payload.get("title") or canonical.get("title"),
                "year": payload.get("publication_year") or canonical.get("year"),
            },
            representation_type="ABSTRACT",
            locator=url,
            content=content,
            access_provenance={
                "adapter": self.name,
                "retrieved_at": _now_iso(),
                "request_url": url,
                "response_sha256": hashlib.sha256(body).hexdigest(),
                "lawful_access": "public_api",
            },
        )


@dataclass(frozen=True)
class SourceDocument:
    source_document_id: str
    canonical_identity: dict[str, Any]
    source_representation_type: str
    source_locator: str | None
    access_provenance: dict[str, Any]
    content_hash: str | None
    normalized_content_ref: str | None
    source_integrity_status: str
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"SD-[a-f0-9]{12}", self.source_document_id):
            raise SemanticBoundaryError(f"invalid source_document_id: {self.source_document_id!r}")
        if self.source_representation_type not in SOURCE_REPRESENTATIONS:
            raise SemanticBoundaryError("invalid source_representation_type")
        has_content = self.source_representation_type not in {"IDENTITY_ONLY", "INACCESSIBLE"}
        if has_content and (not self.content_hash or not self.normalized_content_ref):
            raise SemanticBoundaryError("accessible SourceDocument requires content hash and ref")
        if not has_content and (self.content_hash is not None or self.normalized_content_ref is not None):
            raise SemanticBoundaryError("non-content SourceDocument cannot claim content hash/ref")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "source_document_id": self.source_document_id,
            "canonical_identity": dict(self.canonical_identity),
            "source_representation_type": self.source_representation_type,
            "source_locator": self.source_locator,
            "access_provenance": dict(self.access_provenance),
            "content_hash": self.content_hash,
            "normalized_content_ref": self.normalized_content_ref,
            "source_integrity_status": self.source_integrity_status,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class EvidenceSpan:
    span_id: str
    source_document_id: str
    locator: str
    text: str
    evidence_role: str
    span_integrity_status: str
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"ES-[a-f0-9]{12}", self.span_id):
            raise SemanticBoundaryError(f"invalid span_id: {self.span_id!r}")
        if self.evidence_role not in EVIDENCE_ROLES:
            raise SemanticBoundaryError(f"invalid evidence_role: {self.evidence_role!r}")
        if not self.locator or not self.text:
            raise SemanticBoundaryError("EvidenceSpan requires locator and text")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "span_id": self.span_id,
            "source_document_id": self.source_document_id,
            "locator": self.locator,
            "text": self.text,
            "evidence_role": self.evidence_role,
            "span_integrity_status": self.span_integrity_status,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class PropositionRequest:
    proposition_id: str
    text: str
    expected_source_document_id: str | None = None
    required_evidence_roles: tuple[str, ...] = ()
    requires_statistical_result: bool = False
    explicit_only: bool = True

    def __post_init__(self) -> None:
        if not self.proposition_id or not self.text.strip():
            raise SemanticBoundaryError("PropositionRequest requires id and text")
        unknown = set(self.required_evidence_roles) - set(EVIDENCE_ROLES)
        if unknown:
            raise SemanticBoundaryError(f"unknown required evidence roles: {sorted(unknown)}")


@dataclass(frozen=True)
class PropositionEvidence:
    proposition_evidence_id: str
    proposition_id: str
    source_document_id: str
    span_ids: tuple[str, ...]
    relation: str
    sufficiency_rationale: str
    uncertainty: str
    grounding_status: str
    provenance: dict[str, Any]
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"PE-[a-f0-9]{12}", self.proposition_evidence_id):
            raise SemanticBoundaryError(
                f"invalid proposition_evidence_id: {self.proposition_evidence_id!r}"
            )
        if self.relation not in RELATIONS:
            raise SemanticBoundaryError(f"invalid proposition relation: {self.relation!r}")
        if self.grounding_status not in GROUNDING_STATES:
            raise SemanticBoundaryError(f"invalid grounding_status: {self.grounding_status!r}")
        grounded = self.grounding_status == "CITABLE_SPAN"
        if grounded and not self.span_ids:
            raise SemanticBoundaryError("CITABLE_SPAN proposition evidence requires spans")
        if grounded and self.relation == "NOT_GROUNDED":
            raise SemanticBoundaryError("CITABLE_SPAN evidence requires a grounded relation")
        if not grounded and self.relation != "NOT_GROUNDED":
            raise SemanticBoundaryError("non-grounded state must use NOT_GROUNDED relation")
        if not self.sufficiency_rationale.strip() or not self.uncertainty.strip():
            raise SemanticBoundaryError("PropositionEvidence requires rationale and uncertainty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "proposition_evidence_id": self.proposition_evidence_id,
            "proposition_id": self.proposition_id,
            "source_document_id": self.source_document_id,
            "span_ids": list(self.span_ids),
            "relation": self.relation,
            "sufficiency_rationale": self.sufficiency_rationale,
            "uncertainty": self.uncertainty,
            "grounding_status": self.grounding_status,
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
        }


@dataclass
class EvidenceResolutionSession:
    adapters: tuple[SourceAdapter, ...]
    _documents_by_identity: dict[str, SourceDocument] = field(default_factory=dict, init=False)
    _content_by_document_id: dict[str, str] = field(default_factory=dict, init=False)
    _spans_by_id: dict[str, EvidenceSpan] = field(default_factory=dict, init=False)
    source_fetches: int = 0
    source_cache_hits: int = 0

    @staticmethod
    def _assert_material_matches(
        canonical_evidence: dict[str, Any], material: SourceMaterial
    ) -> None:
        expected = canonical_identity_key(canonical_evidence)
        observed_evidence = {"canonical": material.canonical_identity}
        observed = canonical_identity_key(observed_evidence)
        if expected != observed:
            raise SemanticBoundaryError(
                f"source identity mismatch: expected {expected!r}, observed {observed!r}"
            )

    def resolve_source(self, canonical_evidence: dict[str, Any]) -> SourceDocument:
        identity_key = canonical_identity_key(canonical_evidence)
        cached = self._documents_by_identity.get(identity_key)
        if cached is not None:
            self.source_cache_hits += 1
            return cached
        material: SourceMaterial | None = None
        used_adapter: str | None = None
        for adapter in self.adapters:
            self.source_fetches += 1
            material = adapter.fetch(canonical_evidence)
            if material is not None:
                used_adapter = adapter.name
                break
        canonical = dict(canonical_evidence.get("canonical") or {})
        source_id = _stable_id("SD", identity_key)
        if material is None:
            document = SourceDocument(
                source_document_id=source_id,
                canonical_identity=canonical,
                source_representation_type="INACCESSIBLE",
                source_locator=None,
                access_provenance={"adapters_attempted": [a.name for a in self.adapters]},
                content_hash=None,
                normalized_content_ref=None,
                source_integrity_status="SOURCE_CONTENT_NOT_ACCESSIBLE",
            )
        else:
            self._assert_material_matches(canonical_evidence, material)
            normalized = html.unescape(re.sub(r"<[^>]+>", " ", material.content))
            normalized = re.sub(r"\s+", " ", normalized).strip()
            content_hash = _sha256_text(normalized)
            document = SourceDocument(
                source_document_id=source_id,
                canonical_identity=canonical,
                source_representation_type=material.representation_type,
                source_locator=material.locator,
                access_provenance={**material.access_provenance, "adapter": used_adapter},
                content_hash=content_hash,
                normalized_content_ref=f"content://sha256/{content_hash}",
                source_integrity_status="VERIFIED_IDENTITY_MATCH",
            )
            self._content_by_document_id[source_id] = normalized
        self._documents_by_identity[identity_key] = document
        return document

    def source_content(self, source_document_id: str) -> str | None:
        return self._content_by_document_id.get(source_document_id)

    def create_span(
        self,
        *,
        source_document: SourceDocument,
        text: str,
        evidence_role: str,
    ) -> EvidenceSpan:
        content = self._content_by_document_id.get(source_document.source_document_id)
        if content is None:
            raise SemanticBoundaryError("cannot create span from inaccessible source")
        start = content.find(text)
        if start < 0:
            raise SemanticBoundaryError("evidence span text is not an exact source substring")
        end = start + len(text)
        span = EvidenceSpan(
            span_id=_stable_id("ES", source_document.source_document_id, str(start), text),
            source_document_id=source_document.source_document_id,
            locator=f"chars:{start}-{end}",
            text=text,
            evidence_role=evidence_role,
            span_integrity_status="VERIFIED_EXACT_SUBSTRING",
        )
        self._spans_by_id[span.span_id] = span
        return span

    def adjudicate(
        self,
        *,
        request: PropositionRequest,
        source_document: SourceDocument,
        spans: tuple[EvidenceSpan, ...],
        relation: str,
        sufficiency_rationale: str,
        uncertainty: str,
        grounding_status: str = "CITABLE_SPAN",
        inference_mode: str = "EXPLICIT",
        adjudication_authority: str = "external_semantic_adjudicator",
    ) -> PropositionEvidence:
        if request.expected_source_document_id and (
            request.expected_source_document_id != source_document.source_document_id
        ):
            raise SemanticBoundaryError("wrong source document for proposition request")
        for span in spans:
            if span.source_document_id != source_document.source_document_id:
                raise SemanticBoundaryError("wrong-source span in proposition judgment")
            if self._spans_by_id.get(span.span_id) != span:
                raise SemanticBoundaryError("unregistered or modified EvidenceSpan")
        if grounding_status == "CITABLE_SPAN":
            if not spans:
                raise SemanticBoundaryError("model prior cannot replace a source span")
            roles = {span.evidence_role for span in spans}
            if request.required_evidence_roles and not (
                roles & set(request.required_evidence_roles)
            ):
                raise SemanticBoundaryError(
                    "evidence role is insufficient for the proposition request"
                )
            if request.requires_statistical_result and "STATISTICAL_RESULT" not in roles:
                raise SemanticBoundaryError(
                    "raw counts or non-statistical text cannot establish statistical significance"
                )
            if request.explicit_only and inference_mode != "EXPLICIT":
                raise SemanticBoundaryError(
                    "indirect implication cannot establish an explicit proposition"
                )
        evidence = PropositionEvidence(
            proposition_evidence_id=_stable_id(
                "PE", request.proposition_id, source_document.source_document_id,
                relation, grounding_status, *(span.span_id for span in spans)
            ),
            proposition_id=request.proposition_id,
            source_document_id=source_document.source_document_id,
            span_ids=tuple(span.span_id for span in spans),
            relation=relation,
            sufficiency_rationale=sufficiency_rationale,
            uncertainty=uncertainty,
            grounding_status=grounding_status,
            provenance={
                "source_document_id": source_document.source_document_id,
                "span_ids": [span.span_id for span in spans],
                "adjudication_authority": adjudication_authority,
                "inference_mode": inference_mode,
                "model_prior_used_as_evidence": False,
            },
        )
        return evidence

    def ungrounded(
        self,
        *,
        request: PropositionRequest,
        source_document: SourceDocument,
        grounding_status: str,
        rationale: str,
        uncertainty: str,
    ) -> PropositionEvidence:
        if grounding_status not in {
            "NO_SPAN", "NOT_ADDRESSED", "AMBIGUOUS", "SOURCE_CONTENT_NOT_ACCESSIBLE"
        }:
            raise SemanticBoundaryError("invalid ungrounded terminal state")
        return self.adjudicate(
            request=request,
            source_document=source_document,
            spans=(),
            relation="NOT_GROUNDED",
            sufficiency_rationale=rationale,
            uncertainty=uncertainty,
            grounding_status=grounding_status,
            inference_mode="NONE",
        )
