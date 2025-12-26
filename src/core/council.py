"""
Council Orchestrator - Main LLM Council logic
Implements the full MALT pipeline: Generator → Verifier → Corrector
Includes Kill Switch philosophy and all research-backed features
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Import from sibling packages
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.decision import (
    Decision, BlockedDecision, AgentResponse, 
    JudgeEvaluation, RiskLevel
)
from src.core.synthesizer import Synthesizer, MockSynthesizer, create_synthesizer
from src.agents.generators import create_council_agents, run_agents_parallel
from src.judges.evaluators import (
    create_council_judges, run_judges_on_responses,
    check_judge_disagreement, get_disagreement_details
)
from src.safety.gate import SafetyGate
from src.audit.logger import AuditLogger


class LLMCouncil:
    """
    Main LLM Council orchestrator.
    
    Implements the full decision pipeline:
    1. Safety Gate - Block harmful queries
    2. Generator Phase (MALT) - 3 agents generate in parallel
    3. Verifier Phase (MALT) - 2 judges evaluate all responses
    4. Selection - Pick best response based on scores
    5. Synthesis (MoA) - Winner refines using other perspectives
    6. Corrector Phase (MALT) - Retry if confidence is low
    7. Kill Switch - Warn but don't auto-block low confidence
    8. Audit - Log everything
    """
    
    def __init__(
        self,
        agents_config: str = "config/agents.yaml",
        rubric_config: str = "config/rubric.yaml",
        safety_config: str = "config/safety.yaml",
        audit_log: str = "logs/audit.jsonl",
        use_mock: bool = False,
        confidence_threshold: float = 0.6,
        max_retries: int = 1,
        skip_synthesis: bool = False,
        model_overrides: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the LLM Council.
        """
        # Create components
        self.agents = create_council_agents(
            agents_config, 
            use_mock=use_mock,
            model_overrides=model_overrides
        )
        self.judges = create_council_judges(rubric_config, use_mock=use_mock)
        self.safety_gate = SafetyGate(safety_config)
        self.audit_logger = AuditLogger(audit_log)
        self.synthesizer = create_synthesizer(use_mock=use_mock)
        
        # Configuration
        self.use_mock = use_mock
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries
        self.skip_synthesis = skip_synthesis
    


    # Splitting edits to avoid complexity.

    
    async def decide(self, query: str) -> Decision | BlockedDecision:
        """
        Main decision method - runs the full council pipeline.
        
        Args:
            query: User's query/question
            
        Returns:
            Decision or BlockedDecision object
        """
        start_time = time.time()
        decision_id = str(uuid.uuid4())[:8]
        
        # ========================================
        # STEP 1: Safety Gate
        # ========================================
        safety_result = self.safety_gate.check(query)
        
        if not safety_result.passed:
            blocked = BlockedDecision(
                decision_id=decision_id,
                timestamp=datetime.now(),
                query=query,
                safety_passed=False,
                block_reason=safety_result.reason,
                matched_patterns=safety_result.matched_patterns
            )
            self.audit_logger.log(blocked)
            return blocked
        
        # ========================================
        # STEP 2: Generator Phase (MALT)
        # Run 3 agents in parallel
        # ========================================
        agent_responses = await run_agents_parallel(self.agents, query)
        
        # ========================================
        # STEP 3: Verifier Phase (MALT)
        # 2 judges evaluate all responses
        # ========================================
        evaluations = await run_judges_on_responses(
            self.judges, query, agent_responses
        )
        
        # Check for judge disagreement (Auto-Arena)
        judge_disagreement = check_judge_disagreement(evaluations)
        
        # ========================================
        # STEP 4: Selection
        # Pick the best response based on scores
        # ========================================
        selected, confidence, selection_reasoning = self._select_best(
            agent_responses, evaluations
        )
        
        # ========================================
        # STEP 5: Synthesis (MoA)
        # Winner refines using other perspectives
        # ========================================
        if self.skip_synthesis:
            refined_response = selected
            was_refined = False
        else:
            refined_response = await self.synthesizer.refine(
                query, selected, agent_responses
            )
            was_refined = True
        
        # ========================================
        # STEP 6: Corrector Phase (MALT)
        # Retry if confidence is below threshold
        # ========================================
        was_retried = False
        retry_feedback = ""
        
        if confidence < self.confidence_threshold and self.max_retries > 0:
            # Get feedback from judges
            retry_feedback = self._get_judge_feedback(evaluations, selected)
            
            # Re-run with feedback (simplified: just re-synthesize)
            # In a full implementation, would re-prompt the agent
            if retry_feedback:
                refined_response = await self.synthesizer.refine(
                    query, selected, agent_responses, retry_feedback
                )
                was_retried = True
                
                # Recalculate confidence with small boost for retry
                confidence = min(1.0, confidence + 0.1)
        
        # ========================================
        # STEP 7: Risk Assessment & Kill Switch
        # Calculate risk level but DON'T auto-block
        # ========================================
        risk_level, identified_risks = self._assess_risk(
            evaluations, confidence, judge_disagreement
        )
        
        # KILL SWITCH: Warn but don't block
        # Add warning for low confidence (transparency over automation)
        if confidence < self.confidence_threshold and risk_level != RiskLevel.CRITICAL:
            identified_risks.append(
                f"⚠️ LOW CONFIDENCE ({confidence:.0%}): Human review recommended"
            )
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
        
        if judge_disagreement:
            identified_risks.append(
                "⚠️ JUDGES DISAGREE: Different judges rated this differently"
            )
        
        # ========================================
        # STEP 8: Build Decision Object
        # ========================================
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Extract citations from response (simple extraction)
        citations = self._extract_citations(refined_response.response_text)
        
        decision = Decision(
            decision_id=decision_id,
            timestamp=datetime.now(),
            query=query,
            agent_responses=agent_responses,
            judge_evaluations=evaluations,
            selected_response=selected,
            refined_response=refined_response,
            confidence_score=confidence,
            risk_level=risk_level,
            identified_risks=identified_risks,
            citations=citations,
            selection_reasoning=selection_reasoning,
            retry_feedback=retry_feedback,
            processing_time_ms=processing_time_ms,
            safety_passed=True,
            judge_disagreement=judge_disagreement,
            was_refined=was_refined,
            was_retried=was_retried
        )
        
        # ========================================
        # STEP 9: Audit Log
        # ========================================
        self.audit_logger.log(decision)
        
        return decision
    
    def decide_sync(self, query: str) -> Decision | BlockedDecision:
        """Synchronous version of decide"""
        return asyncio.run(self.decide(query))

    async def decide_generator(
        self, 
        query: str, 
        skip_synthesis: bool = False,
        word_limit: Optional[int] = None
    ):
        """
        Generator version of decide that yields intermediate progress.
        
        Yields:
            Tuple[str, Any]: (stage, data)
            stages: "start", "agents", "judges", "final"
        """
        start_time = time.time()
        decision_id = str(uuid.uuid4())[:8]
        
        yield ("start", None)
        
        # STEP 1: Safety Gate
        safety_result = self.safety_gate.check(query)
        
        if not safety_result.passed:
            blocked = BlockedDecision(
                decision_id=decision_id,
                timestamp=datetime.now(),
                query=query,
                safety_passed=False,
                block_reason=safety_result.reason,
                matched_patterns=safety_result.matched_patterns
            )
            self.audit_logger.log(blocked)
            yield ("blocked", blocked)
            return

        # STEP 2: Generator Phase
        # Live Parallel Streaming
        
        # 1. Initialize empty containers
        agent_responses = []
        agents_list = list(self.agents.values())
        
        for agent in agents_list:
             agent_responses.append(AgentResponse(
                 agent_id=agent.agent_id,
                 agent_type=agent.agent_type,
                 response_text="", # Starts empty
                 temperature=agent.temperature,
                 generation_time_ms=0
             ))
        
        # 2. Define streaming task
        async def stream_task(agent, response_obj):
            t0 = time.time()
            full_text = ""
            async for chunk in agent.generate_stream(query, word_limit=word_limit):
                full_text += chunk
                response_obj.response_text = full_text
            response_obj.generation_time_ms = int((time.time() - t0) * 1000)

        # 3. Launch tasks
        tasks = [asyncio.create_task(stream_task(a, r)) for a, r in zip(agents_list, agent_responses)]
        
        # 4. Polling Loop to update UI while agents type
        while not all(t.done() for t in tasks):
            yield ("agents", agent_responses)
            await asyncio.sleep(0.05) # 50ms refresh rate
            
        # 5. Final Yield to ensure completion
        yield ("agents", agent_responses)
        
        # STEP 3: Verifier Phase
        evaluations = await run_judges_on_responses(
            self.judges, query, agent_responses
        )
        judge_disagreement = check_judge_disagreement(evaluations)
        yield ("judges", (agent_responses, evaluations))
        
        # STEP 4: Selection
        selected, confidence, selection_reasoning = self._select_best(
            agent_responses, evaluations
        )
        
        # STEP 5: Synthesis
        if self.skip_synthesis:
            refined_response = selected
            was_refined = False
        else:
            refined_response = await self.synthesizer.refine(
                query, selected, agent_responses
            )
            was_refined = True
        
        # STEP 6: Corrector Phase
        was_retried = False
        retry_feedback = ""
        
        if confidence < self.confidence_threshold and self.max_retries > 0:
            retry_feedback = self._get_judge_feedback(evaluations, selected)
            if retry_feedback:
                refined_response = await self.synthesizer.refine(
                    query, selected, agent_responses, retry_feedback
                )
                was_retried = True
                confidence = min(1.0, confidence + 0.1)
        
        # STEP 7: Risk
        risk_level, identified_risks = self._assess_risk(
            evaluations, confidence, judge_disagreement
        )
        
        if confidence < self.confidence_threshold and risk_level != RiskLevel.CRITICAL:
            identified_risks.append(
                f"⚠️ LOW CONFIDENCE ({confidence:.0%}): Human review recommended"
            )
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
        
        if judge_disagreement:
            identified_risks.append(
                "⚠️ JUDGES DISAGREE: Different judges rated this differently"
            )
        
        # STEP 8: Decision Object
        processing_time_ms = int((time.time() - start_time) * 1000)
        citations = self._extract_citations(refined_response.response_text)
        
        decision = Decision(
            decision_id=decision_id,
            timestamp=datetime.now(),
            query=query,
            agent_responses=agent_responses,
            judge_evaluations=evaluations,
            selected_response=selected,
            refined_response=refined_response,
            confidence_score=confidence,
            risk_level=risk_level,
            identified_risks=identified_risks,
            citations=citations,
            selection_reasoning=selection_reasoning,
            retry_feedback=retry_feedback,
            processing_time_ms=processing_time_ms,
            safety_passed=True,
            judge_disagreement=judge_disagreement,
            was_refined=was_refined,
            was_retried=was_retried
        )
        
        self.audit_logger.log(decision)
        yield ("final", decision)
    
    def _select_best(
        self,
        responses: List[AgentResponse],
        evaluations: List[JudgeEvaluation]
    ) -> Tuple[AgentResponse, float, str]:
        """
        Select the best response based on judge evaluations.
        
        Returns:
            Tuple of (best_response, confidence, reasoning)
        """
        # Calculate average score per agent
        agent_scores: Dict[str, List[float]] = {}
        agent_issues: Dict[str, List[str]] = {}
        
        for eval in evaluations:
            agent_id = eval.target_agent_id
            if agent_id not in agent_scores:
                agent_scores[agent_id] = []
                agent_issues[agent_id] = []
            agent_scores[agent_id].append(eval.total_score)
            agent_issues[agent_id].extend(eval.flagged_issues)
        
        # Calculate averages
        avg_scores = {
            agent_id: sum(scores) / len(scores)
            for agent_id, scores in agent_scores.items()
        }
        
        # Find best score
        best_score = max(avg_scores.values())
        
        # Find all agents with the best score (handle ties)
        top_agents = [aid for aid, score in avg_scores.items() if score == best_score]
        
        # Tie-breaker: Prioritize Safety Advocate if involved in tie
        best_agent_id = top_agents[0]
        for aid in top_agents:
            if "safety" in aid.lower() or "advocate" in aid.lower():
                best_agent_id = aid
                break
        
        # Find the corresponding response
        best_response = None
        for response in responses:
            if response.agent_id == best_agent_id:
                best_response = response
                break
        
        if best_response is None:
            best_response = responses[0]  # Fallback
        
        # Calculate confidence (0-1 scale from 0-10 score)
        confidence = best_score / 10.0
        
        # Build reasoning
        scores_str = ", ".join(
            f"{k}: {v:.1f}" for k, v in sorted(avg_scores.items(), key=lambda x: -x[1])
        )
        issues = agent_issues.get(best_agent_id, [])
        issues_str = f" Issues: {issues}" if issues else ""
        
        reasoning = f"Selected {best_response.agent_type} with highest average score. Scores: {scores_str}.{issues_str}"
        
        return best_response, confidence, reasoning
    
    def _get_judge_feedback(
        self,
        evaluations: List[JudgeEvaluation],
        selected: AgentResponse
    ) -> str:
        """Get aggregated feedback from judges for the selected response"""
        feedback_parts = []
        
        for eval in evaluations:
            if eval.target_agent_id == selected.agent_id:
                if eval.flagged_issues:
                    feedback_parts.append(
                        f"{eval.judge_type} Judge: {'; '.join(eval.flagged_issues)}"
                    )
                elif eval.reasoning:
                    feedback_parts.append(
                        f"{eval.judge_type} Judge: {eval.reasoning}"
                    )
        
        return " | ".join(feedback_parts) if feedback_parts else ""
    
    def _assess_risk(
        self,
        evaluations: List[JudgeEvaluation],
        confidence: float,
        judge_disagreement: bool
    ) -> Tuple[RiskLevel, List[str]]:
        """
        Assess risk level based on evaluations and confidence.
        
        Returns:
            Tuple of (RiskLevel, list of identified risks)
        """
        risks = []
        
        # Check for low scores in safety dimensions
        safety_concerns = []
        for eval in evaluations:
            if eval.judge_type == "Safety":
                for dim, score in eval.scores.items():
                    if score < 5:
                        safety_concerns.append(f"Low {dim} score: {score}")
        
        if safety_concerns:
            risks.extend(safety_concerns)
        
        # Collect flagged issues
        for eval in evaluations:
            for issue in eval.flagged_issues:
                if issue not in risks:
                    risks.append(issue)
        
        # Determine risk level (more reasonable thresholds)
        if any("harmful" in r.lower() or "dangerous" in r.lower() for r in risks):
            return RiskLevel.CRITICAL, risks
        elif len(risks) >= 4 or confidence < 0.4:
            return RiskLevel.HIGH, risks
        elif len(risks) >= 2 or confidence < 0.6 or judge_disagreement:
            return RiskLevel.MEDIUM, risks
        else:
            return RiskLevel.LOW, risks
    
    def _extract_citations(self, text: str) -> List[str]:
        """
        Extract citations/sources from response text.
        Simple heuristic-based extraction.
        """
        import re
        citations = []
        
        # Look for URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        citations.extend(urls)
        
        # Look for "according to X" or "source: X" patterns
        source_patterns = [
            r'according to ([^,\.]+)',
            r'source:\s*([^,\.]+)',
            r'cited from ([^,\.]+)',
        ]
        for pattern in source_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            citations.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for c in citations:
            if c.lower() not in seen:
                seen.add(c.lower())
                unique.append(c)
        
        return unique[:10]  # Limit to 10


def create_council(
    use_mock: bool = False,
    **kwargs
) -> LLMCouncil:
    """
    Create an LLM Council instance.
    
    Args:
        use_mock: Use mock components for testing
        **kwargs: Additional arguments for LLMCouncil
        
    Returns:
        Configured LLMCouncil instance
    """
    return LLMCouncil(use_mock=use_mock, **kwargs)
