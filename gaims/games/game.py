from typing import List, Union, Dict, Any
from abc import ABC, abstractmethod

from agents.agent import Agent
from communication.communication import CommunicationMedium
from configs.game_config import GameConfig
class GameState(ABC):
    def __init__(self, game_config: GameConfig, **kwargs):
        self.game_config = game_config
        self.round = 0
        self.actions = []
        for key, value in kwargs.items():
            setattr(self, key, value)
        
    def step_agent(self, action: Any):
        self.actions.append(( action, self.round))
    
    @abstractmethod
    def step(self):
        pass

    def update(self, new_state: Dict[str, Any]):
        self.state.update(new_state)

    def update_agent_state(self, agent: Agent, new_state: Dict[str, Any]):
        if agent.id not in self.state:
            self.state[agent.id] = {}
        self.state[agent.id].update(new_state)

    @abstractmethod
    def get_state(self, agent: Agent) -> Dict[str, Any]:
        pass


class Game(ABC):

    def __init__(self, config: GameConfig, agent_configs: List[Dict[str, Any]], game_state: GameState):
        self.config = config

        self.game_state = game_state

        self.communication_medium = CommunicationMedium(config.get('communication_medium', None))
        self.agents = [Agent(agent_config) for agent_config in agent_configs]

    def aggregate_context(self, agent_id):
        state = self.game_state.get_state()
        messages = self.communication_medium.get_all_pending_messages_for_agent(agent_id)
        agent_observations = self.agents[agent_id].observations
        
        return {
            "state": state,
            "messages": messages,
            "agent_observations": agent_observations,
            "agent_id": agent_id,
            # TODO: Just pass the config as a whole
            "num_rounds": self.config.num_rounds,
            "num_actions": self.config.num_actions,
            "adjacency_list": self.communication_medium.adjacency_list
        }

    def observe(self):
        for agent in self.agents:
            context = self.aggregate_context(agent.id)
            agent.observe(context)
            
    def communicate(self):
        communication_actions = []
        for agent in self.agents:
            context = self.aggregate_context(agent.id)
            communication_actions.append(agent.communicate(context))

        for communication_action in communication_actions:
            if communication_action.receiver == -1:
                self.communication_medium.broadcast_message(communication_action.message)
            else:
                self.communication_medium.send_message(communication_action.sender, communication_action.receiver, communication_action.message)

        for agent in self.agents:
            context = self.aggregate_context(agent.id)
            agent.observe_communication(context)

    def act(self):
        actions = []
        for agent in self.agents:
            context = self.aggregate_context(agent.id)
            action = agent.act(context)
            actions.append({
                'agent_id': agent.id,
                'action':action
            }) # TODO: Consolidate data structures
        
        # TODO: Allow for both simulatneous and sequential action execution
        for action in actions:
            self.game_state.step_agent(action['action'])
            
        self.game_state.step()
    





        
