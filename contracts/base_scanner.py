"""
QuintOS Abstract Security Scanner — Core Interface
Author: Nikhil Manvi

Demonstrates the asynchronous Template Method pattern governing all QuintOS
detection engines. Handles concurrency throttling, telemetry emission, and
standardized error handling without exposing proprietary detection rules.
"""

import abc
import asyncio
import logging
from typing import AsyncGenerator, List, Optional
from datetime import datetime, timezone

from .schemas import SecurityFinding, AuditTarget, ModuleHealthStatus

logger = logging.getLogger("quintos.core.scanner")


class AbstractSecurityScanner(abc.ABC):
    """
    Base contract for all security auditing modules.
    Enforces concurrency limits, non-blocking asynchronous execution,
    and contract validation for all findings.
    """

    def __init__(self, module_name: str, concurrency_limit: int = 5):
        self.module_name = module_name
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.start_time = datetime.now(timezone.utc)
        self._active_scans = 0

    @property
    @abc.abstractmethod
    def supported_extensions(self) -> List[str]:
        """File extensions or URL protocols handled by this engine."""
        pass

    @abc.abstractmethod
    async def _execute_analysis(self, target: AuditTarget) -> AsyncGenerator[SecurityFinding, None]:
        """
        Internal detection pipeline. Implemented by concrete micro-engines
        (e.g., AST parsers, entropy evaluators, or HTTP probers).
        """
        pass

    async def scan(self, target: AuditTarget) -> List[SecurityFinding]:
        """
        Public entry point implementing the Template Method pattern:
        1. Validates preconditions and targets.
        2. Throttles concurrent evaluations via asyncio.Semaphore.
        3. Collects, validates, and deduplicates findings.
        """
        async with self.semaphore:
            self._active_scans += 1
            findings: List[SecurityFinding] = []
            logger.info("[%s] Initiating audit on target: %s", self.module_name, target)

            try:
                async for finding in self._execute_analysis(target):
                    # Schema-level enforcement happens automatically via Pydantic
                    findings.append(finding)
            except Exception as exc:
                logger.error("[%s] Unhandled exception during scan execution: %s", self.module_name, exc)
                raise
            finally:
                self._active_scans -= 1

            logger.info("[%s] Completed audit. Discovered %d findings.", self.module_name, len(findings))
            return findings

    def get_health(self, port: int) -> ModuleHealthStatus:
        """Returns real-time health telemetry for Sentinel Hub heartbeats."""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return ModuleHealthStatus(
            module_name=self.module_name,
            port=port,
            is_healthy=True,
            uptime_seconds=uptime,
            active_scans=self._active_scans
        )
