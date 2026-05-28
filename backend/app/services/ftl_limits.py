"""Operator-specific FTL limit resolution.

Queries the latest ACCEPTED constraint set for an operator and merges its
``final_value`` overrides over the KCARs 2025 baseline in
``ftl_engine.LIMITS``.  Falls back to the unmodified baseline when no
accepted set exists so callers don't need to handle None.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.constraint import (
    ConstraintRule,
    ConstraintSet,
    ConstraintSetStatus,
)
from app.services import ftl_engine


def _apply_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of LIMITS with dotted-key overrides applied."""
    merged: dict[str, Any] = copy.deepcopy(dict(ftl_engine.LIMITS))
    for dotted_key, value in overrides.items():
        if "." in dotted_key:
            parent, child = dotted_key.split(".", 1)
            group = merged.get(parent)
            if isinstance(group, dict):
                # Coerce string sub-keys back to int where the baseline uses int keys
                # (e.g. fdp_aug_3_pilot, tz_recovery).
                typed_child: Any = child
                if group and all(isinstance(k, int) for k in group):
                    try:
                        typed_child = int(child)
                    except ValueError:
                        pass
                group[typed_child] = value
        elif dotted_key in merged:
            merged[dotted_key] = value
    return merged


def resolve_limits(operator_id: uuid.UUID, session: Session) -> dict[str, Any]:
    """Return limits for ``operator_id``, merged from the latest ACCEPTED set.

    Returns the generic baseline unchanged when no accepted constraint set
    exists for the operator.
    """
    cset = session.scalars(
        select(ConstraintSet)
        .where(
            ConstraintSet.operator_id == operator_id,
            ConstraintSet.status == ConstraintSetStatus.ACCEPTED,
        )
        .order_by(ConstraintSet.accepted_at.desc())
        .limit(1)
    ).first()
    if cset is None:
        return copy.deepcopy(dict(ftl_engine.LIMITS))

    rules = session.scalars(
        select(ConstraintRule).where(
            ConstraintRule.constraint_set_id == cset.id,
            ConstraintRule.final_value.isnot(None),
        )
    ).all()
    overrides = {r.rule_key: r.final_value for r in rules}
    return _apply_overrides(overrides)


def check_fdp_for_operator(
    fdp: ftl_engine.FdpInput,
    operator_id: uuid.UUID,
    session: Session,
) -> list[ftl_engine.FtlVerdict]:
    """Resolve operator limits then delegate to ``ftl_engine.check_fdp``."""
    limits = resolve_limits(operator_id, session)
    return ftl_engine.check_fdp(fdp, limits=limits)
