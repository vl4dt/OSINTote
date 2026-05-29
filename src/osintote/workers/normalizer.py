# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Target normalization & deduplication.

Provides :class:`TargetNormalizer` which:
  - canonicalises target names (lowercase, strip dots, IP compression)
  - links discovered targets via relationships (hosts, resolves_to, ptr)
  - resolves canonical targets for a target set

Example::

    normalizer = TargetNormalizer()
    canonical = normalizer.normalize("Example.COM.")
    # → "example.com"

    links = normalizer.link("example.com", "93.184.216.34", "resolves_to")
    # → ("example.com", "93.184.216.34", RelationshipType.RESOLVES_TO)
"""

from __future__ import annotations

import ipaddress
import re
from typing import ClassVar

from osintote.models.orm import RelationshipType

# ── Normalizer ──────────────────────────────────────────────────────────────


class TargetNormalizer:
    """Canonicalise, link, and deduplicate target names.

    Normalisation rules
    ────────────────────
    1. Lowercase
    2. Strip leading/trailing dots
    3. Collapse consecutive dots
    4. Remove "www" prefix
    5. For IPv4, use :func:`ipaddress.ip_address` canonical form
    6. For IPv6, use compressed form

    Relationship linking
    ────────────────────
    :meth:`link` returns a 3-tuple (source, target, type) that can be
    persisted as a :class:`osintote.models.orm.Relationship`.
    """

    # Known TLDs that should prevent www-stripping
    _PROTECTED_TLDS: ClassVar[set[str]] = {
        "co.uk", "com.au", "org.uk", "net.nz",
        "ac.uk", "gov.uk",
    }

    def __init__(self, protected_tlds: set[str] | None = None) -> None:
        """Initialise with optional custom protected TLDs."""
        self._protected = self._PROTECTED_TLDS.copy()
        if protected_tlds is not None:
            self._protected.update(protected_tlds)

    # ── Normalisation ───────────────────────────────────────────────────

    def normalize(self, raw: str) -> str:
        """Canonicalise a target name.

        Examples
        --------
        >>> n = TargetNormalizer()
        >>> n.normalize("Example.COM.")
        'example.com'
        >>> n.normalize("www.example.com")
        'example.com'
        >>> n.normalize("010.000.001.001")
        '10.0.1.1'
        >>> n.normalize("::ffff:192.168.1.1")
        '192.168.1.1'
        """
        name = raw.strip()

        # 1. Lowercase
        name = name.lower()

        # 2. Strip trailing dot
        if name.endswith("."):
            name = name[:-1]

        # 3. Collapse consecutive dots
        while ".." in name:
            name = name.replace("..", ".")

        # 4. IPv4 / IPv6 detection (strip leading zeros first)
        try:
            # Handle IPv4 with leading zeros (e.g. "010.000.001.001")
            candidate = re.sub(
                r"(?:(?:^|(?<=\.)))0+(\d)",
                r"\1",
                name,
            )
            addr = ipaddress.ip_address(candidate)
            return str(addr)  # canonical compressed form
        except ValueError:
            pass

        # 5. Remove www. prefix (unless TLD is protected)
        parts = name.split(".")
        if len(parts) >= 2 and parts[0].lower() == "www":
            tld = ".".join(parts[-2:])
            if tld not in self._protected:
                parts = parts[1:]
                name = ".".join(parts)

        # 6. Strip leading/trailing dots again (safety net)
        name = name.strip(".")

        return name

    # ── Relationships ───────────────────────────────────────────────────

    def link(
        self,
        source: str,
        target: str,
        relation: str,
    ) -> tuple[str, str, RelationshipType]:
        """Return a (source, target, type) triple for persistence.

        Parameters
        ----------
        source:
            Normalised source target.
        target:
            Normalised discovered target.
        relation:
            One of :class:`RelationshipType` values.

        Returns
        -------
        tuple[str, str, RelationshipType]

        Raises
        ------
        ValueError
            If *relation* is not a valid :class:`RelationshipType`.
        """
        try:
            rel_type = RelationshipType(relation)
        except ValueError as err:
            raise ValueError(
                f"Invalid relationship type: {relation!r}. "
                f"Must be one of {list(RelationshipType)}"
            ) from err

        return (source, target, rel_type)

    # ── Deduplication ───────────────────────────────────────────────────

    def dedup(self, targets: list[str]) -> list[str]:
        """Return unique canonical targets preserving order.

        >>> n = TargetNormalizer()
        >>> n.dedup(["example.com.", "Example.COM", "  www.example.com  "])
        ['example.com']
        """
        seen: set[str] = set()
        result: list[str] = []
        for raw in targets:
            canon = self.normalize(raw)
            if canon and canon not in seen:
                seen.add(canon)
                result.append(canon)
        return result

    # ── Relationship resolution ─────────────────────────────────────────

    def resolve(
        self,
        source: str,
        links: list[tuple[str, str, RelationshipType]],
        target_type: str | None = None,
    ) -> list[str]:
        """Find all targets linked to *source* by the given *links*.

        Parameters
        ----------
        source:
            Normalised source target name.
        links:
            List of (source, target, RelationshipType) triples.
        target_type:
            If given, only return links of this type.

        Returns
        -------
        list[str]
            Normalised target names that are linked to *source*.
        """
        results: list[str] = []
        for src, tgt, rel in links:
            if src != source:
                continue
            if target_type and rel.value != target_type:
                continue
            results.append(tgt)
        return results
