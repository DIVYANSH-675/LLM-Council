"""
Generator Agents - Using MegaLLM (OpenAI-compatible API)
Implements the 3 STORM-style adversarial agents with different models for diversity
"""

import os
import time
import asyncio
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import OpenAI SDK (used with MegaLLM)
try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import base classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.agents.base import BaseAgent
from src.core.decision import AgentResponse


# Model mapping for each agent type (must match config/agents.yaml keys)
DEFAULT_MODELS = {
    "analytical": os.getenv("ANALYTICAL_MODEL", "gpt-4o"),
    "creative": os.getenv("CREATIVE_MODEL", "claude-3-5-sonnet-20241022"),
    "pragmatist": os.getenv("PRAGMATIST_MODEL", "gpt-4o"),
}


class MegaLLMAgent(BaseAgent):
    """
    Agent that uses MegaLLM (OpenAI-compatible API) for generation.
    Supports async execution for parallel processing.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        system_prompt: str,
        temperature: float = 0.5,
        role: str = "",
        goal: str = "",
        model_name: str = "gpt-4o"
    ):
        super().__init__(agent_id, agent_type, system_prompt, temperature, role, goal)
        
        self.model_name = model_name
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
    
    async def generate(self, query: str) -> AgentResponse:
        """Generate response using MegaLLM API"""
        start_time = time.time()
        
        self._ensure_initialized()
        
        try:
            if not OPENAI_AVAILABLE or not self._async_client:
                response_text = f"[Mock {self.agent_type} response for: {query[:50]}...]"
            else:
                # Use async client
                response = await self._async_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=self.temperature,
                    max_tokens=1024,
                )
                response_text = response.choices[0].message.content or "[No response]"
                
        except Exception as e:
            response_text = f"[Error generating response: {str(e)}]"
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        return AgentResponse(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            response_text=response_text,
            temperature=self.temperature,
            generation_time_ms=generation_time_ms
        )
    
    async def generate_stream(self, query: str, word_limit: Optional[int] = None):
        """Yield chunks of response using MegaLLM API"""
        self._ensure_initialized()
        
        # Inject word limit into system prompt if provided
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
        ]
        
        if word_limit:
            messages.append({
                "role": "system", 
                "content": f"[SYSTEM INSTRUCTION] IMPORTANT: Limit your response to approximately {word_limit} words."
            })
        
        try:
            if not OPENAI_AVAILABLE or not self._async_client:
                text = f"[Mock {self.agent_type} stream (Limit: {word_limit}) for: {query[:30]}...]"
                for char in text.split(" "):
                    yield char + " "
                    await asyncio.sleep(0.05)
            else:
                stream = await self._async_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=2048 if word_limit and word_limit > 1000 else 1024,
                    stream=True
                )
                async for chunk in stream:
                    content = chunk.choices[0].delta.content or ""
                    if content:
                        yield content
        except Exception as e:
            yield f"[Error: {str(e)}]"

    def generate_sync(self, query: str) -> AgentResponse:
        """Synchronous version of generate"""
        return asyncio.run(self.generate(query))


class MockAgent(BaseAgent):
    """Mock agent for testing without API calls"""
    
    async def generate(self, query: str) -> AgentResponse:
        # ... (unchanged)
        return AgentResponse(...) # Simplified for brevity

    async def generate_stream(self, query: str, word_limit: Optional[int] = None):
        """Mock stream"""
        mock_responses = {
            "Analytical Agent": f"Based on data analysis of '{query[:30]}...', the evidence suggests...",
            "Creative Agent": f"What if we approached '{query[:30]}...' from a completely different angle?",
            "Pragmatist Agent": f"From an operational perspective on '{query[:30]}...', we need to consider execution..."
        }
        text = mock_responses.get(self.agent_type, f"Mock response for {query}")
        
        if word_limit:
            text += f" (Word Limit: {word_limit})"
        
        for word in text.split(" "):
            yield word + " "
            await asyncio.sleep(0.05)


class AgentFactory:
    """Factory to create agents from YAML configuration"""
    
    def __init__(self, config_path: str = "config/agents.yaml", use_mock: bool = False):
        self.config_path = Path(config_path)
        self.use_mock = use_mock
        self._load_config()
    
    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Agent config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def create_agent(self, agent_key: str, model_override: Optional[str] = None) -> BaseAgent:
        """Create a single agent from config"""
        if agent_key not in self.config:
            raise KeyError(f"Agent '{agent_key}' not found in config")
        
        cfg = self.config[agent_key]
        
        # Get model for this agent type (Override > Env > Default)
        if model_override:
            model_name = model_override
        else:
            model_name = DEFAULT_MODELS.get(agent_key, "gpt-4o")
        
        AgentClass = MockAgent if self.use_mock else MegaLLMAgent
        
        kwargs = {
            "agent_id": f"agent_{agent_key}",
            "agent_type": cfg.get('name', agent_key.title()),
            "system_prompt": cfg.get('system_prompt', ''),
            "temperature": cfg.get('temperature', 0.5),
            "role": cfg.get('role', ''),
            "goal": cfg.get('goal', '')
        }
        
        if not self.use_mock:
            kwargs["model_name"] = model_name
        
        return AgentClass(**kwargs)
    
    def create_all_agents(self, model_overrides: Optional[Dict[str, str]] = None) -> Dict[str, BaseAgent]:
        """Create all 3 agents from config"""
        agents = {}
        overrides = model_overrides or {}
        
        for key in self.config:
            agents[key] = self.create_agent(key, model_override=overrides.get(key))
        return agents


async def run_agents_parallel(
    agents: Dict[str, BaseAgent],
    query: str
) -> List[AgentResponse]:
    """Run all agents in parallel using asyncio.gather"""
    tasks = [agent.generate(query) for agent in agents.values()]
    responses = await asyncio.gather(*tasks)
    return list(responses)


def create_council_agents(
    config_path: str = "config/agents.yaml",
    use_mock: bool = False,
    model_overrides: Optional[Dict[str, str]] = None
) -> Dict[str, BaseAgent]:
    """Create the 3 STORM-style council agents"""
    factory = AgentFactory(config_path, use_mock=use_mock)
    return factory.create_all_agents(model_overrides=model_overrides)
