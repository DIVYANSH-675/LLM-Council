"""
Audit Logger - Persistent JSONL logging for all decisions
Creates an immutable trail of all council decisions
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union
from dataclasses import asdict

# Import decision types
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.decision import Decision, BlockedDecision


class AuditLogger:
    """
    Audit logger that persists all decisions to a JSONL file.
    Each line is a complete JSON object for easy parsing.
    """
    
    def __init__(self, log_path: str = "logs/audit.jsonl"):
        """Initialize audit logger with log file path"""
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _hash_query(self, query: str) -> str:
        """Create a short hash of the query for privacy"""
        return hashlib.sha256(query.encode()).hexdigest()[:16]
    
    def log(self, decision: Union[Decision, BlockedDecision]) -> str:
        """
        Log a decision to the audit file.
        
        Args:
            decision: Decision or BlockedDecision object
            
        Returns:
            The decision_id that was logged
        """
        # Create log entry (PRIVACY: Only store query_hash, never raw query)
        entry = {
            "log_timestamp": datetime.now().isoformat(),
            "decision_id": decision.decision_id,
            "query_hash": self._hash_query(decision.query),
            # NOTE: Raw query intentionally NOT logged to protect PII
            "safety_passed": decision.safety_passed,
        }
        
        # Add decision-specific fields
        if isinstance(decision, Decision):
            entry.update({
                "type": "decision",
                "selected_agent": decision.selected_response.agent_type,
                "confidence": decision.confidence_score,
                "risk_level": decision.risk_level.value,
                "risks": decision.identified_risks,
                "processing_time_ms": decision.processing_time_ms,
                "was_refined": decision.was_refined,
                "was_retried": decision.was_retried,
                "judge_disagreement": decision.judge_disagreement,
                "full_decision": decision.to_dict()
            })
        elif isinstance(decision, BlockedDecision):
            entry.update({
                "type": "blocked",
                "block_reason": decision.block_reason,
                "matched_patterns": decision.matched_patterns
            })
        
        # Append to JSONL file
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return decision.decision_id
    
    def get_recent(self, limit: int = 10) -> List[Dict]:
        """
        Get the most recent log entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of log entries (most recent first)
        """
        if not self.log_path.exists():
            return []
        
        with open(self.log_path, 'r') as f:
            lines = f.readlines()
        
        # Parse last N lines
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
        
        # Return in reverse order (most recent first)
        return list(reversed(entries))
    
    def get_by_id(self, decision_id: str) -> Optional[Dict]:
        """
        Get a specific log entry by decision ID.
        
        Args:
            decision_id: The decision ID to search for
            
        Returns:
            The log entry or None if not found
        """
        if not self.log_path.exists():
            return None
        
        with open(self.log_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get('decision_id') == decision_id:
                        return entry
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def get_stats(self) -> Dict:
        """
        Get statistics about logged decisions.
        
        Returns:
            Dictionary with stats (total, blocked, avg_confidence, etc.)
        """
        if not self.log_path.exists():
            return {"total": 0}
        
        total = 0
        blocked = 0
        confidences = []
        risk_levels = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        refined_count = 0
        retried_count = 0
        
        with open(self.log_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    total += 1
                    
                    if entry.get('type') == 'blocked':
                        blocked += 1
                    else:
                        conf = entry.get('confidence', 0)
                        if conf:
                            confidences.append(conf)
                        
                        risk = entry.get('risk_level', 'LOW')
                        if risk in risk_levels:
                            risk_levels[risk] += 1
                        
                        if entry.get('was_refined'):
                            refined_count += 1
                        if entry.get('was_retried'):
                            retried_count += 1
                            
                except json.JSONDecodeError:
                    continue
        
        return {
            "total": total,
            "blocked": blocked,
            "decisions": total - blocked,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "risk_levels": risk_levels,
            "refined_count": refined_count,
            "retried_count": retried_count
        }
    
    def clear(self):
        """Clear all log entries (use with caution!)"""
        if self.log_path.exists():
            self.log_path.unlink()
