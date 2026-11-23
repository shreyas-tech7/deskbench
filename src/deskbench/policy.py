"""Policy rules every domain shares, plus small date helpers for the domain rules."""

from __future__ import annotations

import re
from datetime import date, datetime

from .core import READ, WRITE, CallCtx, Rule

YES = re.compile(r"^\s*(yes|yeah|yep|please do|go ahead|confirmed)\b", re.I)  # "sure, my zip is" is not a yes


def identity(ctx: CallCtx) -> str | None:
    if ctx.tool.kind not in (READ, WRITE) or ctx.tool.owner is None:
        return None
    owner = ctx.tool.owner(ctx.db, ctx.args)
    if owner is None:  # unknown record: the tool itself rejects the call
        return None
    if ctx.session.verified is None:
        return f"{ctx.tool.name} touched account {owner} before the identity check"
    if ctx.session.verified != owner:
        return f"{ctx.tool.name} touched account {owner}, but the verified customer is {ctx.session.verified}"
    return None


def confirmation(ctx: CallCtx) -> str | None:
    if ctx.tool.kind == WRITE and not YES.match(ctx.last_user or ""):
        return f"{ctx.tool.name} ran without an explicit yes from the customer"
    return None


COMMON_RULES = [
    Rule(
        "IDENTITY",
        "Verify the customer before you read or change their account, and touch only that account.",
        identity,
    ),
    Rule(
        "CONFIRM",
        "Before any change, describe it and get an explicit yes from the customer.",
        confirmation,
    ),
]


def day(text: str) -> date:
    return date.fromisoformat(text[:10])


def moment(text: str) -> datetime:
    return datetime.fromisoformat(text)
