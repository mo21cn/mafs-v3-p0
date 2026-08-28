"""Capability vocabulary: closed core enum + namespaced extension (P0 §5).

Core capabilities are schema-validated as a closed set. Extensions use the form
``<provider>.<verb>`` where ``provider`` must be a known provider name.

This module never silently accepts an unknown string. Every capability is either
core or a well-formed extension whose provider portion is registered.
"""
from __future__ import annotations
import re
from typing import Iterable


# Core capability names (P0 §5, master contract §7.8/§8.1)
CORE_CAPABILITIES: frozenset[str] = frozenset({
    "search.query",
    "search.fielded_query",
    "search.pagination",
    "result.ranked",
    "result.provider_id",
    "resolve.doi",
    "resolve.pmid",
    "metadata.snapshot",
})


_EXTENSION_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


class CapabilityVocabularyError(ValueError):
    """Raised when a capability is neither core nor a valid extension."""


def is_core(cap: str) -> bool:
    return cap in CORE_CAPABILITIES


def is_extension(cap: str, registered_providers: Iterable[str]) -> bool:
    if not _EXTENSION_RE.match(cap or ""):
        return False
    provider, _, _verb = cap.partition(".")
    return provider in set(registered_providers)


def is_known(cap: str, registered_providers: Iterable[str]) -> bool:
    """True iff ``cap`` is core OR a well-formed extension whose provider is registered."""
    if is_core(cap):
        return True
    return is_extension(cap, registered_providers)


def validate_capabilities(
    caps: Iterable[str],
    registered_providers: Iterable[str],
) -> None:
    """Validate every capability; raise CapabilityVocabularyError on first failure.

    Empty list is rejected: a SearchOrder/Provider must declare at least one capability.
    """
    providers = set(registered_providers)
    seen: list[str] = []
    for cap in caps:
        if not isinstance(cap, str) or not cap:
            raise CapabilityVocabularyError(f"capability is not a non-empty string: {cap!r}")
        if not is_known(cap, providers):
            raise CapabilityVocabularyError(
                f"capability {cap!r} is neither a core capability nor a registered-provider extension"
            )
        seen.append(cap)
    if not seen:
        raise CapabilityVocabularyError("capability list must not be empty")


def extension_provider(cap: str) -> str | None:
    """Return the provider portion of an extension capability, or None if core/invalid."""
    if not _EXTENSION_RE.match(cap or ""):
        return None
    return cap.partition(".")[0]
