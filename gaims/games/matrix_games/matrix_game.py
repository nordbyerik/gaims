from typing import List, Dict, Any
from abc import ABC
from gaims.games.game import GameState
from gaims.games.action import Action
from gaims.configs.game_config import GameConfig

import numpy as np
import torch

class MatrixAction(Action):
    def __init__(self, agent_id: int, action_id: int, values: List[float] = None):
        self.agent_id = agent_id
        self.action_id = action_id

class MatrixGameState(GameState):
    def __init__(self, game_config: GameConfig, payoffs = None):
        super().__init__(game_config)
        self.payoff_matrix = self.generate_random_payoffs() if payoffs is None else payoffs
        self.player_utility = 0

    def step(self):
        actions = [0 for _ in range(self.game_config.num_agents)]
        for action, round in self.actions:
            if round == self.round:
                actions[action.agent_id] = action.action_id

        self.player_utility += self.payoff_matrix[actions[0], actions[1], 0]
        self.round += 1

    def get_state(self) -> Dict[str, Any]:
        return {"player_utility": self.player_utility, "payoff_matrix": self.payoff_matrix}
          
    def __str__(self):
        return_string = ""
        return_string += f"Matrix Game with {self.game_config.num_agents} players and {self.game_config.num_actions} actions per player\n"
        return_string += f"Payoff Matrix: {self.payoff_matrix}\n"
        return return_string

    def generate_random_payoffs(self):
        return torch.randint(-2, 2, (self.game_config.num_actions, self.game_config.num_actions, 2))
