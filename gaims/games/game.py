from typing import List, Union, Dict, Any

from agents.agent import Agent
from abc import ABC, abstractmethod

from games.game_config import GameConfig

from communication.communication import CommunicationMedium
from agents.agent import AgentInterface

from agents.agent import Agent


class GameState(ABC):
    def __init__(self, state: Dict[str, Any]):
        self.state = state

    @abstractmethod
    def make_action(self, agent: int, action: Any):
        pass
        
    def update(self, new_state: Dict[str, Any]):
        self.state.update(new_state)

    def update_agent_state(self, agent: Agent, new_state: Dict[str, Any]):
        if agent.id not in self.state:
            self.state[agent.id] = {}
        self.state[agent.id].update(new_state)

    def get_state(self, agent: Agent) -> Dict[str, Any]:
        """Get the state relevant to a specific agent"""
        agent_state = self.state.get(agent.id, {})
        shared_state = self.state.get("shared", {})
        return {**agent_state, **shared_state}


class Game(ABC):

    def __init__(self, config: Dict[str, Any], agent_configs: List[Dict[str, Any]]):
        self.config = config
        self.current_round = 0
        self.max_rounds = config.get('max_rounds', 1)
        self.scores = [0] * config.get('num_players', 2)
        self.payoff_matrix = config.get('payoff_matrix', None)
        self.prompt_format = config.get('prompt_format', None)

        self.template = config.get('template', None)
        self.options = config.get('options', None)

        self.num_players = config.get('num_players', None)
        self.num_actions = config.get('num_actions', None)

        self.communication_medium = CommunicationMedium(config.get('communication_medium', None))
        self.game_state = GameState(self.game_config)

        self.agents = [Agent(agent_config) for agent_config in agent_configs]

    def aggregate_context(self, agent_id):
        state = self.game_state.get_state()
        messages = self.communication_medium.get_messages(agent_id)
        
        return {
            "state": state,
            "messages": messages
        }

    def observe(self):
        for agent_id, agent in self.agents.items():
            context = self.aggregate_context(agent_id)
            agent.observe(context)
            
    def communicate(self):
        communication_actions = []
        for agent_id, agent in self.agents.items():
            context = self.aggregate_context(agent_id)
            communication_actions = agent.communicate(context)

        for communication_action in communication_actions:
            if communication_action['type'] == 'broadcast':
                self.communication_medium.broadcast_message(communication_action['message'])
            else:
                self.communication_medium.send_message(communication_action['sender'], communication_action['receiver'], communication_action['message'])

        for agent_id, agent in self.agents.items():
            context = self.aggregate_context(agent_id)
            agent.observe_communication(context)

    def act(self):
        actions = []
        for agent_id, agent in self.agents.items():
            context = self.aggregate_context(agent_id)
            action = agent.act(context)
            actions.append({'agent_id': agent_id,'action':action})
        
        # TODO: Allow for both simulatneous and sequential action execution
        for action in actions:
            self.game_state.make_action(action['agent_id'], action['action'])
    


    # TODO: Implement more complex game logic here
    # TODO: Allow for batching
    def step(self):
        payoff_dict = self.game_state_to_dict()
        prompt = self.payoff_matrix_to_prompt(payoff_dict)

        player_action = self.player.act(prompt)
        return player_action
        
