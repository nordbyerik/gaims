from typing import List, Dict, Any, Type
from abc import ABC, abstractmethod
import logging

from gaims.communication.communication import Message
from gaims.games.action import Action
from gaims.agents.models import Model, ModelFactory

from gaims.configs.agent_config import AgentConfig

log = logging.getLogger(__name__)
logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

class Agent():
    def __init__(self, agent_config: AgentConfig):
        self.id = agent_config.id
        self.persona = agent_config.system_propmt
        self.name = agent_config.name

        self.prompt_config = agent_config.prompt_config

        self.utility = 0
        self.observations = []
        self.plans = []
        self.actions = []

        model_factory = ModelFactory()
        self.model = model_factory.create_model(agent_config.model_config)

    def observe(self, context: Dict[str, Any]) -> None:
        formatted_context, system_prompt = self.prompt_config.format_observe_context(context)
        llm_repsonse, llm_repsonse_raw = self.model.observe(formatted_context, system_prompt=self.persona)
        log.info(f"**STEP** ==> LOGGED_AGENT: {self.name}, LOGGED_AGENT_MODEL: {self.model._identifier}, LOGGED_ACTION: OBSERVE, LOGGED_MESSAGE: {formatted_context}, LOGGED_RESPONSE: {llm_repsonse_raw}")
        self.observations.append(llm_repsonse) # TODO: Add better observation management      
        return {
            "agent": {self.name},
            "agent_model": {self.model._identifier},
            "step": "communicate",
            "message": {formatted_context},
            "response": {llm_repsonse_raw},
        }

    def observe_communication(self, context: Dict[str, Any]) -> None:
        formatted_context, system_prompt = self.prompt_config.format_observe_communication_context(context)
        llm_repsonse, llm_repsonse_raw = self.model.observe(formatted_context, system_prompt=self.persona)
        log.info(f"**STEP** ==> LOGGED_AGENT: {self.name}, LOGGED_AGENT_MODEL: {self.model._identifier}, LOGGED_ACTION: OBSERVE_COMMUNICATION, LOGGED_MESSAGE: {formatted_context}, LOGGED_RESPONSE: {llm_repsonse_raw}")
        self.observations.append(llm_repsonse) # TODO: Add better observation management
        return {
            "agent": {self.name},
            "agent_model": {self.model._identifier},
            "step": "communicate",
            "message": {formatted_context},
            "response": {llm_repsonse_raw},
        }

    def communicate(self, context: Dict[str, Any]) -> Message:
        formatted_context, system_prompt = self.prompt_config.format_communicate_context(context)
        formatted_messages = formatted_context

        llm_repsonse, llm_repsonse_raw = self.model.communicate(formatted_messages, system_prompt=self.persona)
        log.info(f"**STEP** ==> LOGGED_AGENT: {self.name}, LOGGED_AGENT_MODEL: {self.model._identifier}, LOGGED_ACTION: COMMUNICATE, LOGGED_MESSAGE: {formatted_messages}, LOGGED_RESPONSE: {llm_repsonse_raw}")
        message = Message(self.id, llm_repsonse.receiver, llm_repsonse.message)
        return message, {
            "agent": {self.name},
            "agent_model": {self.model._identifier},
            "step": "communicate",
            "message": {formatted_messages},
            "response": {llm_repsonse_raw},
        }

    def act(self, context: Dict[str, Any]) -> Action:
        formatted_context, system_prompt = self.prompt_config.format_action_context(context)
        llm_repsonse, llm_repsonse_raw = self.model.act(formatted_context, system_prompt=self.persona)
        log.info(f"**STEP** ==> LOGGED_AGENT: {self.name}, LOGGED_AGENT_MODEL: {self.model._identifier}, LOGGED_ACTION: ACT, LOGGED_MESSAGE: {formatted_context}, LOGGED_RESPONSE: {llm_repsonse_raw}")
        action = Action(agent_id=self.id,action_id=llm_repsonse.action_id)
        return action, {
            "agent": {self.name},
            "agent_model": {self.model._identifier},
            "step": "communicate",
            "message": {formatted_context},
            "response": {llm_repsonse_raw},
        }
