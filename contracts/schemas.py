"""
QuintOS Universal Security Contract — Domain Models & Schemas
Version: 1.0.0
Author: Nikhil Manvi

These schemas define the universal data contract shared across all five QuintOS
security modules and the Sentinel Hub aggregation gateway.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SeverityLevel(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingCategory(str, Enum):
    SUPPLY_CHAIN = "supply_chain"
    SECRET_LEAK = "secret_leak"
    CONTAINER_HARDENING = "container_hardening"
    IAC_MISCONFIG = "iac_misconfig"
    API_SECURITY = "api_security"
    CLOUD_POSTURE = "cloud_posture"


class FindingStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class SecurityFinding(BaseModel):
    """
    Standardized finding emitted by any QuintOS security micro-engine.
    Guarantees strict type safety and cross-module compatibility.
    """
    id: str = Field(..., description="Unique deterministic identifier (e.g. SEC-SW-2026-0042)")
    module: str = Field(..., description="Originating module (e.g. SupplyWatch, SecretWatch)")
    rule_id: str = Field(..., description="Canonical rule code for the vulnerability")
    title: str = Field(..., max_length=120, description="Concise finding headline")
    severity: SeverityLevel = Field(..., description="Standardized severity tier")
    risk_score: int = Field(..., ge=0, le=100, description="Deterministic 0-100 risk score")
    category: FindingCategory = Field(..., description="Taxonomy classification")
    asset: str = Field(..., description="Target file path, URL, or cloud resource identifier")
    line_number: Optional[int] = Field(None, ge=1, description="Line number if static code finding")
    evidence: str = Field(..., description="Masked code snippet or server header proof")
    description: str = Field(..., description="Detailed explanation of the risk mechanism")
    remediation: str = Field(..., description="Actionable developer fix instructions")
    status: FindingStatus = Field(default=FindingStatus.OPEN)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Module-specific context")

    @field_validator("risk_score")
    @classmethod
    def validate_risk_bounds(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError("risk_score must reside within the bounded interval [0, 100]")
        return v


class ModuleHealthStatus(BaseModel):
    """Health and operational telemetry emitted by each microservice."""
    module_name: str
    port: int
    is_healthy: bool
    version: str = "1.0.0"
    uptime_seconds: float
    active_scans: int = 0
    last_scan_timestamp: Optional[datetime] = None


class AuditTarget(BaseModel):
    """Specification of an audit target submitted to the gateway."""
    target_path: Optional[str] = None
    target_url: Optional[str] = None
    enable_modules: List[str] = Field(
        default_factory=lambda: [
            "supplywatch", "secretwatch", "infraguard", "apisentry", "cloudposture"
        ]
    )
    max_scan_depth: int = Field(default=8, ge=1, le=16)
    strict_mode: bool = Field(default=False, description="Fail CI pipeline on any HIGH or CRITICAL")


class BlastRadiusNode(BaseModel):
    id: str
    label: str
    type: str  # "asset", "finding", or "identity"
    severity: Optional[SeverityLevel] = None


class BlastRadiusEdge(BaseModel):
    source: str
    target: str
    relation: str  # "exposes", "compromises", "hosts"


class BlastRadiusGraph(BaseModel):
    """Topological graph depicting correlated attack pathways."""
    nodes: List[BlastRadiusNode] = Field(default_factory=list)
    edges: List[BlastRadiusEdge] = Field(default_factory=list)
    cumulative_risk: int = Field(default=0, ge=0, le=100)
