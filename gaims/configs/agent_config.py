from typing import Dict, Type, List, Any
from gaims.configs.prompt_config import PromptConfig
from gaims.agents.models import Model, GeminiModel, LocalModel, ModelConfig

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
    def __init__(self, persona: str):
        self.system_prompt = PERSONA_TEMPLATES[persona]

    def get_system_prompt(self) -> str:
        return self.system_prompt


class AgentConfig:
    def __init__(self, 
                 id: str, 
                 prompt_config: PromptConfig, 
                 system_prompt_config: SystemPromptConfig = SystemPromptConfig("neutral"),
                 model_config: ModelConfig = ModelConfig(model_name="gemini")
                 ):
        self.id = id
        self.system_propmt = system_prompt_config.get_system_prompt() # TODO: This is kinda gross
        self.prompt_config = prompt_config
        self.model_config = model_config



