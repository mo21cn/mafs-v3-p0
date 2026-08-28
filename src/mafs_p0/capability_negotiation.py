"""Capability negotiation (P0 §7).

Mechanical rule:
    SearchOrder.required_capabilities  ⊆  Provider.capabilities

If false, the SearchOrder is NOT_EXECUTABLE. We never silently fall back.

Extension namespaces: the ``<namespace>.<verb>`` form of an extension capability
matches a provider whose ``effective_namespace()`` equals ``<namespace>``. This
separates the versioned provider identity (``openalex_v1``) from the extension
prefix (``openalex.related_works``).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable

from .capability_vocabulary import (
    is_known,
    validate_capabilities,
    CapabilityVocabularyError,
)
from .search_order import SearchOrder
from .provider_manifest import ProviderManifest


def registered_namespaces(providers: Iterable[ProviderManifest]) -> set[str]:
    return {p.effective_namespace() for p in providers}


@dataclass
class NegotiationResult:
    search_order_id: str
    matched_provider_name: str | None
    matched_provider_version: str | None
    missing_capabilities: list[str] = field(default_factory=list)
    executable: bool = False
    blocker: str | None = None


def _provider_caps_set(p: ProviderManifest) -> set[str]:
    return set(p.capabilities)


def negotiate(
    so: SearchOrder,
    providers: Iterable[ProviderManifest],
) -> NegotiationResult:
    """Return the first provider that mechanically subsumes the SearchOrder's required capabilities.

    Ties on multiple providers resolve to the first one declared (deterministic).
    """
    providers_list = list(providers)
    namespaces = registered_namespaces(providers_list)
    # First, ensure every required_capability is at least well-formed (core or registered extension).
    try:
        validate_capabilities(so.required_capabilities, namespaces)
    except CapabilityVocabularyError as e:
        return NegotiationResult(
            search_order_id=so.search_order_id,
            matched_provider_name=None,
            matched_provider_version=None,
            missing_capabilities=list(so.required_capabilities),
            executable=False,
            blocker=f"capability vocabulary error: {e}",
        )

    required = set(so.required_capabilities)
    for p in providers_list:
        if required.issubset(_provider_caps_set(p)):
            return NegotiationResult(
                search_order_id=so.search_order_id,
                matched_provider_name=p.name,
                matched_provider_version=p.version,
                missing_capabilities=[],
                executable=True,
                blocker=None,
            )
    # Cleaner: list everything required that NO provider exposes.
    union_caps: set[str] = set()
    for p in providers_list:
        union_caps |= _provider_caps_set(p)
    missing = sorted(required - union_caps)
    return NegotiationResult(
        search_order_id=so.search_order_id,
        matched_provider_name=None,
        matched_provider_version=None,
        missing_capabilities=missing,
        executable=False,
        blocker="no provider exposes all required_capabilities",
    )


def negotiate_all(
    search_orders: Iterable[SearchOrder],
    providers: Iterable[ProviderManifest],
) -> list[NegotiationResult]:
    return [negotiate(so, providers) for so in search_orders]
