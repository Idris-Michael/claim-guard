"""Stops AI-written sales copy from citing results nobody verified."""

from claim_guard.claims import Claim, find_claims
from claim_guard.guard import PLACEHOLDER, Finding, GuardResult, VerifiedSource, guard

__all__ = ["PLACEHOLDER", "Claim", "Finding", "GuardResult", "VerifiedSource", "find_claims", "guard"]
