from typing import List, Union, Dict, Any
from abc import ABC, abstractmethod

from gaims.agents.agent import Agent
    

from gaims.configs.game_config import GameConfig
class GameState(ABC):
    def __init__(self, game_config: GameConfig, **kwargs):
        self.game_config = game_config
        self.round = 0
        self.actions = []
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        self.observe = game_config.observe
        
        
    def step_agent(self, action: Any):
        self.actions.append(( action, self.round))
    
    @abstractmethod
    def step(self):
        pass

    def reset(self):
        self.round = 0
        self.actions = []


    def update(self, new_state: Dict[str, Any]):
        self.state.update(new_state)

    def update_agent_state(self, agent: Agent, new_state: Dict[str, Any]):
        if agent.id not in self.state:
            self.state[agent.id] = {}
        self.state[agent.id].update(new_state)

    @abstractmethod
    def get_state(self, agent: Agent) -> Dict[str, Any]:
        pass
    





        
