# Owner: agent-platform
import uuid
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from .confidence_calibrator import ConfidenceCalibrator
from .evidence_gap_detector import EvidenceGapDetector

logger = logging.getLogger(__name__)

class UncertaintyEstimator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.calibrator = ConfidenceCalibrator()
        self.gap_detector = EvidenceGapDetector(db)

    async def estimate(self, run_id: uuid.UUID, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimates uncertainty for a given run based on metrics and tool consistency.
        """
        # 1. Gather Metrics
        evidence_score = context.get("evidence_score", 0.5)
        contradiction_score = context.get("contradiction_score", 0.0)
        source_coverage = context.get("source_coverage", 0.5)
        
        # 2. Calibrate Confidence
        metrics = {
            "evidence_score": evidence_score,
            "contradiction_score": contradiction_score,
            "source_coverage": source_coverage,
            "tool_result_consistency": context.get("tool_result_consistency", 1.0),
            "memory_conflict_score": context.get("memory_conflict_score", 0.0)
        }
        
        confidence_score = self.calibrator.calculate(metrics)
        
        # 3. Detect Evidence Gaps
        gaps = await self.gap_detector.detect(run_id, metrics)
        
        return {
            "confidence_score": confidence_score,
            "metrics": metrics,
            "gaps": gaps
        }
