"""
Base Judge - Abstract base class for all council judges
Judges evaluate agent responses using rubrics (they do NOT generate content)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import time

# Import from sibling package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.decision import AgentResponse, JudgeEvaluation


class BaseJudge(ABC):
    """
    Abstract base class for all council judges.
    
    Key principle: Judges ONLY evaluate - they do NOT generate new content.
    
    All judges must:
    1. Have an ID and type
    2. Have a rubric with scoring dimensions
    3. Implement the evaluate() method
    4. Return JudgeEvaluation objects
    """
    
    def __init__(
        self,
        judge_id: str,
        judge_type: str,
        rubric: Dict[str, Any]
    ):
        """
        Initialize base judge.
        
        Args:
            judge_id: Unique identifier for this judge
            judge_type: Type of judge (Factuality, Safety)
            rubric: Dictionary with dimensions and weights
        """
        self.judge_id = judge_id
        self.judge_type = judge_type
        self.rubric = rubric
        self.dimensions = rubric.get('dimensions', {})
    
    @abstractmethod
    async def evaluate(
        self,
        query: str,
        responses: List[AgentResponse]
    ) -> List[JudgeEvaluation]:
        """
        Evaluate all agent responses.
        
        This method must be implemented by all concrete judges.
        
        Args:
            query: The original user query
            responses: List of AgentResponses to evaluate
            
        Returns:
            List of JudgeEvaluation objects (one per response)
        """
        pass
    
    def calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        """
        Calculate weighted total score from dimension scores.
        
        Args:
            scores: Dictionary mapping dimension name to score (0-10)
            
        Returns:
            Weighted average score (0-10)
        """
        total = 0.0
        total_weight = 0.0
        
        for dim_name, dim_config in self.dimensions.items():
            if dim_name in scores:
                weight = dim_config.get('weight', 0.25)
                total += scores[dim_name] * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Return weighted average (already in 0-10 scale)
        return total / total_weight
    
    def get_rubric_prompt(self) -> str:
        """
        Format rubric as prompt text for LLM evaluation.
        
        Returns:
            Formatted rubric string
        """
        lines = [f"RUBRIC FOR {self.judge_type.upper()} EVALUATION:\n"]
        
        for dim_name, dim_config in self.dimensions.items():
            weight_pct = int(dim_config.get('weight', 0.25) * 100)
            desc = dim_config.get('description', '')
            lines.append(f"- {dim_name.upper()} ({weight_pct}%): {desc}")
        
        lines.append("\nScore each dimension from 0-10.")
        return '\n'.join(lines)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.judge_id}, type={self.judge_type})"
