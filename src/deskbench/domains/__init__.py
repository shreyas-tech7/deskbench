"""The domain registry. Add a domain by adding a package here (see docs/ADD_A_DOMAIN.md)."""

from __future__ import annotations

from . import bikeparts

DOMAINS = {d.name: d for d in (bikeparts.DOMAIN,)}


def all_tasks():
    return [(d, t) for d in DOMAINS.values() for t in d.tasks]
