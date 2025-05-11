from typing import List, Dict, Any, Type
from abc import ABC, abstractmethod

from communication.message import Message
from agents.models import Model, LocalModel
from agents.models import GeminiModel, LocalModel

# Registry of available agent types
AGENT_REGISTRY: Dict[str, Type[Model]] = {
    # LLM-based agents
    "google": GeminiModel,  # Google API-based agent
    "huggingface": LocalModel,  # Hugging Face model-based agent
}

# Persona templates for different agent types
PERSONA_TEMPLATES: Dict[str, str] = {
    "cooperative": "You are a cooperative agent who values mutual benefit and long-term relationships. "
                  "You prefer solutions that benefit everyone involved, even if it means sacrificing "
                  "some personal gain in the short term.",
    
    "competitive": "You are a competitive agent who aims to maximize your own utility. "
                  "You make strategic decisions to outperform others and achieve the best possible outcome for yourself.",
    
    "fair": "You are a fair agent who values equitable outcomes. "
           "You believe in treating others as you would want to be treated, and you strive for solutions "
           "that distribute benefits and burdens fairly among all participants.",
    
    "vengeful": "You are a vengeful agent who remembers past interactions. "
               "You reward cooperation with cooperation, but you will retaliate against those who have harmed you in the past.",
    
    "risk_averse": "You are a risk-averse agent who prefers safer options with more certain outcomes. "
                  "You avoid high-risk situations, even if they offer potentially higher rewards.",
    
    "risk_seeking": "You are a risk-seeking agent who is willing to take chances for potentially higher rewards. "
                   "You are comfortable with uncertainty and are drawn to high-risk, high-reward opportunities.",
    
    "neutral": "You are a neutral agent who makes decisions based on the specific situation at hand. "
              "You have no inherent biases towards cooperation or competition, and you evaluate each scenario independently."
}


class SystemPromptConfig:
    def __init__(self, template: str, game_rules: str, persona: str, variables: Dict[str, str] = None):
        self.template = template
        self.game_rules = game_rules
        self.persona = persona
        self.variables = variables

    def get_system_prompt(self) -> str:
        return self.template.format(**self.variables)


class AgentConfig:
    def __init__(self, id: str, system_prompt_config: SystemPromptConfig, tags: List[str]):
        self.id = id
        self.system_prompt_config = system_prompt_config
        self.tags = tags


class Action(ABC):
    def __init__(self, action_id: int, values: float = None):
        self.action_id = action_id
        self.values = values


class LLMAgent():
    def __init__(self, agent_config: AgentConfig, model: Model):
        self.id = agent_config.id
        self.persona = agent_config.persona
        self.tags = agent_config.tags

        self.model = model

        self.utility = 0
        self.observations = []
        self.plans = []
        self.actions = []
    
        self.model = model

    def observe(self, context: Dict[str, Any]) -> None:
        formatted_context = self.format_observe_context(context)
        llm_repsonse = self.model.observe(formatted_context)
        self.observations.append(llm_repsonse) # TODO: Add better observation management      

    def observe_communication(self, context: Dict[str, Any]) -> None:
        formatted_context = self.format_observe_communication_context(context)
        llm_repsonse = self.model.observe_communication(formatted_context)
        self.observations.append(llm_repsonse) # TODO: Add better observation management

    def communicate(self, context: Dict[str, Any]) -> Message:
        formatted_context = self.format_communicate_context(context)
        formatted_messages = formatted_context

        llm_repsonse = self.model.communicate(formatted_messages)
        return llm_repsonse

    def act(self, context: Dict[str, Any]) -> Action:
        formatted_context = self.format_action_context(context)
        formatted_context = formatted_context

        llm_repsonse = self.model.act(formatted_context)
        return llm_repsonse


