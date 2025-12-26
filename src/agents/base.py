"""
Base Agent - Abstract base class for all council agents
Defines the interface that all agents must implement
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any
import time

# Import from sibling package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.decision import AgentResponse


class BaseAgent(ABC):
    """
    Abstract base class for all council agents.
    
    All agents must:
    1. Have an ID and type
    2. Have a system prompt (from STORM config)
    3. Have a temperature setting
    4. Implement the generate() method
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        system_prompt: str,
        temperature: float = 0.5,
        role: str = "",
        goal: str = ""
    ):
        """
        Initialize base agent.
        
        Args:
            agent_id: Unique identifier for this agent
            agent_type: Type of agent (Analytical, Creative, Safety Advocate)
            system_prompt: STORM-style system prompt with adversarial goal
            temperature: Generation temperature (0.0 = deterministic, 1.0 = creative)
            role: Role title (e.g., "Chief Data Officer")
            goal: Agent's goal (e.g., "KILL THE PROPOSAL")
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.role = role
        self.goal = goal
    
    @abstractmethod
    async def generate(self, query: str) -> AgentResponse:
        """
        Generate a response to the given query.
        
        This method must be implemented by all concrete agents.
        
        Args:
            query: The user's query/question
            
        Returns:
            AgentResponse with the generated text and metadata
        """
        pass
    
    def _create_prompt(self, query: str) -> str:
        """
        Create the full prompt by combining system prompt and user query.
        
        Args:
            query: The user's query
            
        Returns:
            Full prompt string
        """
        return f"""{self.system_prompt}

---

USER QUERY: {query}

---

YOUR RESPONSE (as {self.role}):"""
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id}, type={self.agent_type}, temp={self.temperature})"
