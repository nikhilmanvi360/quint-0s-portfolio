"""
QuintOS Architecture & Schema Contract Test Suite
Author: Nikhil Manvi

Validates contract compliance, Pydantic v2 domain schemas, and SSRF guard
boundaries without relying on live network or external databases.
"""

import pytest
from datetime import datetime, timezone
from contracts.schemas import (
    SecurityFinding,
    SeverityLevel,
    FindingCategory,
    FindingStatus,
    AuditTarget,
)
from contracts.ssrf_guard import is_ssrf_vulnerable_target


# ── Finding Schema Compliance Tests ──────────────────────────────────────────

def test_valid_security_finding_contract():
    """Verify that a compliant finding successfully parses and validates."""
    finding = SecurityFinding(
        id="SEC-SW-2026-0001",
        module="SupplyWatch",
        rule_id="SW-TYPO-01",
        title="Typosquatting Risk: collorama",
        severity=SeverityLevel.HIGH,
        risk_score=40,
        category=FindingCategory.SUPPLY_CHAIN,
        asset="requirements.txt:5",
        evidence="collorama==0.4.6 (dist: 1 to colorama)",
        description="Potential supply chain typo-squatting candidate mimicking 'colorama'.",
        remediation="Verify package spelling with official PyPI namespace.",
        status=FindingStatus.OPEN,
    )
    assert finding.id == "SEC-SW-2026-0001"
    assert finding.risk_score == 40
    assert finding.severity == SeverityLevel.HIGH


@pytest.mark.parametrize("invalid_score", [-1, 101, 250])
def test_risk_score_boundary_enforcement(invalid_score):
    """Ensure the 0-100 bounded invariant is strictly upheld by Pydantic."""
    with pytest.raises(ValueError):
        SecurityFinding(
            id="SEC-ERR-001",
            module="SecretWatch",
            rule_id="SEC-ENTROPY-01",
            title="Boundary Violation Test",
            severity=SeverityLevel.CRITICAL,
            risk_score=invalid_score,
            category=FindingCategory.SECRET_LEAK,
            asset=".env:1",
            evidence="N/A",
            description="Test out of bound scores.",
            remediation="None",
        )


# ── SSRF Defense Boundary Tests ──────────────────────────────────────────────

@pytest.mark.parametrize("private_target", [
    "http://10.0.0.1/admin",
    "http://192.168.1.254/router",
    "http://172.16.5.10:8080",
    "http://169.254.169.254/latest/meta-data/",  # Cloud metadata
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://localhost:8000",
])
def test_ssrf_disallowed_targets(private_target):
    """Confirm all internal/cloud metadata addresses are proactively blocked."""
    is_blocked, reason = is_ssrf_vulnerable_target(private_target, allow_loopback_for_testing=False)
    assert is_blocked is True
    assert reason != ""


def test_ssrf_disallow_unsupported_schemes():
    """Protocols like gopher://, file://, or ftp:// must be rejected."""
    is_blocked, reason = is_ssrf_vulnerable_target("file:///etc/passwd")
    assert is_blocked is True
    assert "Unsupported protocol scheme" in reason


def test_audit_target_default_values():
    """Verify default analysis modules are populated as expected."""
    target = AuditTarget(target_path="./")
    assert "secretwatch" in target.enable_modules
    assert "apisentry" in target.enable_modules
    assert target.strict_mode is False
