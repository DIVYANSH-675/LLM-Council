"""
Decision Object - Structured output from the LLM Council
Contains all data structures for the council's decision pipeline
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum
import json


class RiskLevel(str, Enum):
    """Risk level classification for decisions"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class AgentResponse:
    """Response from a single agent"""
    agent_id: str
    agent_type: str  # "Analytical", "Creative", "Safety Advocate"
    response_text: str
    temperature: float
    generation_time_ms: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class JudgeEvaluation:
    """Evaluation from a judge"""
    judge_id: str
    judge_type: str  # "Factuality", "Safety"
    target_agent_id: str
    scores: Dict[str, float]  # dimension -> score (0-10)
    total_score: float  # weighted average
    reasoning: str
    flagged_issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Decision:
    """Final decision object from the council"""
    # Identifiers
    decision_id: str
    timestamp: datetime
    query: str
    
    # Agent responses (the proof - all 3 drafts)
    agent_responses: List[AgentResponse]
    
    # Judge evaluations
    judge_evaluations: List[JudgeEvaluation]
    
    # Final selection
    selected_response: AgentResponse
    
    # Confidence & Risk (required by project)
    confidence_score: float  # 0.0 to 1.0
    risk_level: RiskLevel
    identified_risks: List[str]
    
    # Citations (required by project)
    citations: List[str] = field(default_factory=list)
    
    # Reasoning
    selection_reasoning: str = ""
    
    # MoA Synthesis (NEW - stores refined version if applied)
    refined_response: Optional[AgentResponse] = None
    
    # MALT Retry (NEW - stores judge feedback that triggered retry)
    retry_feedback: str = ""
    
    # Metadata
    processing_time_ms: int = 0
    safety_passed: bool = True
    judge_disagreement: bool = False  # Auto-Arena feature
    was_refined: bool = False  # MoA synthesis applied
    was_retried: bool = False  # MALT retry applied
    
    def get_agent_scores(self) -> Dict[str, float]:
        """
        Get average score for each agent across all judges (NEW helper)
        Returns: {"agent_1": 7.5, "agent_2": 8.2, ...}
        """
        agent_scores: Dict[str, List[float]] = {}
        
        for evaluation in self.judge_evaluations:
            agent_id = evaluation.target_agent_id
            if agent_id not in agent_scores:
                agent_scores[agent_id] = []
            agent_scores[agent_id].append(evaluation.total_score)
        
        # Calculate average for each agent
        return {
            agent_id: sum(scores) / len(scores)
            for agent_id, scores in agent_scores.items()
        }
    
    def get_winner_margin(self) -> float:
        """
        Get margin between winner and second place (NEW helper)
        Higher margin = more confident selection
        """
        scores = self.get_agent_scores()
        if len(scores) < 2:
            return 0.0
        
        sorted_scores = sorted(scores.values(), reverse=True)
        return sorted_scores[0] - sorted_scores[1]
    
    def get_final_response_text(self) -> str:
        """
        Get the final response text (refined if available, else selected)
        """
        if self.refined_response:
            return self.refined_response.response_text
        return self.selected_response.response_text
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp.isoformat(),
            "query": self.query,
            "agent_responses": [r.to_dict() for r in self.agent_responses],
            "judge_evaluations": [e.to_dict() for e in self.judge_evaluations],
            "selected_response": self.selected_response.to_dict(),
            "refined_response": self.refined_response.to_dict() if self.refined_response else None,
            "confidence_score": self.confidence_score,
            "risk_level": self.risk_level.value,
            "identified_risks": self.identified_risks,
            "citations": self.citations,
            "selection_reasoning": self.selection_reasoning,
            "retry_feedback": self.retry_feedback,
            "processing_time_ms": self.processing_time_ms,
            "safety_passed": self.safety_passed,
            "judge_disagreement": self.judge_disagreement,
            "was_refined": self.was_refined,
            "was_retried": self.was_retried,
            "agent_scores": self.get_agent_scores()
        }
        return data
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        refinement_note = " (REFINED)" if self.was_refined else ""
        retry_note = " (RETRIED)" if self.was_retried else ""
        
        return f"""
Decision ID: {self.decision_id}
Query: {self.query}
Selected Agent: {self.selected_response.agent_type}{refinement_note}{retry_note}
Confidence: {self.confidence_score:.0%}
Risk Level: {self.risk_level.value}
Processing Time: {self.processing_time_ms}ms
Judge Disagreement: {'Yes' if self.judge_disagreement else 'No'}

Agent Scores:
{chr(10).join(f'- {k}: {v:.1f}/10' for k, v in self.get_agent_scores().items())}

Identified Risks:
{chr(10).join(f'- {risk}' for risk in self.identified_risks) if self.identified_risks else '- None'}

Final Response:
{self.get_final_response_text()[:500]}...
"""


@dataclass
class BlockedDecision:
    """Decision object when query is blocked by safety gate"""
    decision_id: str
    timestamp: datetime
    query: str
    safety_passed: bool = False
    block_reason: str = ""
    matched_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp.isoformat(),
            "query": self.query,
            "safety_passed": self.safety_passed,
            "block_reason": self.block_reason,
            "matched_patterns": self.matched_patterns
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
