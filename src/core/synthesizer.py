"""
Synthesizer - MoA-style synthesis refinement using MegaLLM
The winning agent refines its response using perspectives from other agents
"""

import os
import asyncio
import time
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import OpenAI SDK (used with MegaLLM)
try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import from sibling packages
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.decision import AgentResponse


# Model for synthesizer (must be a model available on MegaLLM)
SYNTHESIZER_MODEL = os.getenv("SYNTHESIZER_MODEL", "gpt-4o")


class Synthesizer:
    """
    MoA-style synthesis refinement using MegaLLM.
    
    The winning agent refines its response by considering
    perspectives from the other agents.
    """
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or SYNTHESIZER_MODEL
        self._client = None
        self._async_client = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of MegaLLM client"""
        if self._initialized:
            return
        
        if not OPENAI_AVAILABLE:
            self._initialized = True
            return
        
        api_key = os.getenv("MEGALLM_API_KEY")
        base_url = os.getenv("MEGALLM_BASE_URL", "https://ai.megallm.io/v1")
        
        if not api_key:
            raise ValueError("MEGALLM_API_KEY environment variable not set")
        
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._initialized = True
    
    def _create_synthesis_prompt(
        self,
        query: str,
        winner: AgentResponse,
        others: List[AgentResponse],
        judge_feedback: str = ""
    ) -> str:
        """Create prompt for synthesis refinement"""
        other_perspectives = ""
        for i, other in enumerate(others, 1):
            other_perspectives += f"""
PERSPECTIVE {i} ({other.agent_type}):
{other.response_text}
"""
        
        prompt = f"""You are refining a response by incorporating insights from other perspectives.

ORIGINAL QUERY: {query}

YOUR ORIGINAL RESPONSE ({winner.agent_type}):
{winner.response_text}

OTHER PERSPECTIVES TO CONSIDER:
{other_perspectives}

{f"JUDGE FEEDBACK: {judge_feedback}" if judge_feedback else ""}

TASK: Refine your original response by:
1. Keeping your core insights and conclusions
2. Addressing valid concerns raised by other perspectives
3. Incorporating useful data or ideas from others
4. Making your response more comprehensive

CRITICAL SAFETY RULES:
- MAINTAIN your original safety stance. If you refused to answer, continue refusing.
- DO NOT incorporate harmful, dangerous, or unethical content from other perspectives.
- If other perspectives contain risky suggestions, acknowledge the concern but do not adopt them.
- Your refined response should be AT LEAST as safe as your original response.

OUTPUT: Your refined response (keep the same style, tone, and safety level)
"""
        return prompt
    
    async def refine(
        self,
        query: str,
        winner: AgentResponse,
        all_responses: List[AgentResponse],
        judge_feedback: str = ""
    ) -> AgentResponse:
        """Refine the winning response using other perspectives (MoA synthesis)"""
        start_time = time.time()
        
        others = [r for r in all_responses if r.agent_id != winner.agent_id]
        
        if not others:
            return winner
        
        self._ensure_initialized()
        prompt = self._create_synthesis_prompt(query, winner, others, judge_feedback)
        
        try:
            if not OPENAI_AVAILABLE or not self._async_client:
                refined_text = f"[REFINED] {winner.response_text}\n\n[Incorporated insights from {len(others)} other perspectives]"
            else:
                result = await self._async_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1024,
                )
                refined_text = result.choices[0].message.content or winner.response_text
                
        except Exception as e:
            refined_text = winner.response_text
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        return AgentResponse(
            agent_id=f"{winner.agent_id}_refined",
            agent_type=f"{winner.agent_type} (Refined)",
            response_text=refined_text,
            temperature=winner.temperature,
            generation_time_ms=generation_time_ms
        )
    
    def refine_sync(self, query: str, winner: AgentResponse, all_responses: List[AgentResponse], judge_feedback: str = "") -> AgentResponse:
        """Synchronous version of refine"""
        return asyncio.run(self.refine(query, winner, all_responses, judge_feedback))


class MockSynthesizer(Synthesizer):
    """Mock synthesizer for testing without API calls"""
    
    async def refine(
        self,
        query: str,
        winner: AgentResponse,
        all_responses: List[AgentResponse],
        judge_feedback: str = ""
    ) -> AgentResponse:
        start_time = time.time()
        others = [r for r in all_responses if r.agent_id != winner.agent_id]
        
        refined_text = f"""{winner.response_text}

---
[SYNTHESIS NOTE: This response has been refined by considering {len(others)} alternative perspectives]
"""
        
        await asyncio.sleep(0.05)
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        return AgentResponse(
            agent_id=f"{winner.agent_id}_refined",
            agent_type=f"{winner.agent_type} (Refined)",
            response_text=refined_text,
            temperature=winner.temperature,
            generation_time_ms=generation_time_ms
        )


def create_synthesizer(use_mock: bool = False) -> Synthesizer:
    """Create a synthesizer instance"""
    return MockSynthesizer() if use_mock else Synthesizer()
