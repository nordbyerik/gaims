from typing import List, Dict, Any, Type
from abc import ABC, abstractmethod

from communication.communication import Message
from games.action import Action
from agents.models import Model, ModelFactory

from configs.agent_config import AgentConfig
from configs.prompt_config import PromptConfig

class Agent():
    def __init__(self, agent_config: AgentConfig):
        self.id = agent_config.id
        self.persona = agent_config.system_propmt

        self.prompt_config = agent_config.prompt_config

        self.utility = 0
        self.observations = []
        self.plans = []
        self.actions = []

        model_factory = ModelFactory()
        self.model = model_factory.create_model(agent_config.model_config)

    def observe(self, context: Dict[str, Any]) -> None:
        formatted_context, system_prompt = self.prompt_config.format_observe_context(context)
        llm_repsonse = self.model.observe(formatted_context, system_prompt=self.persona)
        self.observations.append(llm_repsonse) # TODO: Add better observation management      

    def observe_communication(self, context: Dict[str, Any]) -> None:
        formatted_context, system_prompt = self.prompt_config.format_observe_communication_context(context)
        llm_repsonse = self.model.observe(formatted_context, system_prompt=self.persona)
        self.observations.append(llm_repsonse) # TODO: Add better observation management

    def communicate(self, context: Dict[str, Any]) -> Message:
        formatted_context, system_prompt = self.prompt_config.format_communicate_context(context)
        formatted_messages = formatted_context

        llm_repsonse = self.model.communicate(formatted_messages, system_prompt=self.persona)
        message = Message(self.id, llm_repsonse.receiver, llm_repsonse.message_content)
        return message

    def act(self, context: Dict[str, Any]) -> Action:
        formatted_context, system_prompt = self.prompt_config.format_action_context(context)
        formatted_context = formatted_context
        llm_repsonse = self.model.act(formatted_context, system_prompt=self.persona)
        action = Action(agent_id=self.id,action_id=llm_repsonse.action_id)
        return action


