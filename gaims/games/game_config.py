import torch
from typing import List, Union, Dict, Any

class GameConfig:
    def __init__(self, 
                 game_id: str, 
                 game_name: str, 
                 game_description: str, 
                 num_agents: int, 
                 num_rounds: int, 
                 simulatneous: bool, 
                 cooperative: bool, 
                 information_availability: str, 
                 discrete: bool, 
                 stakes: str, 
                 framing: str
                 ):
        
        self.game_id = game_id
        self.game_name = game_name
        self.game_description = game_description
        self.num_agents = num_agents
        self.num_rounds = num_rounds
        self.simulatneous = simulatneous
        self.cooperative = cooperative
        self.information_availability = information_availability
        self.discrete = discrete
        self.stakes = stakes
        self.framing = framing

    def __str__(self):
        return f"GameConfig(game_id={self.game_id}, game_name={self.game_name})"
    


class GameConfig:
    def __init__(self, number_of_rounds: int, num_players: int, num_actions: int, payoff_matrix: List[List[int]], **kwargs):

        payoff_matrix = torch.Tensor(payoff_matrix).reshape(num_actions, num_actions, num_players)

        assert number_of_rounds > 0, "Number of rounds must be greater than 0"
        assert num_players > 0, "Number of players must be greater than 0"
        assert num_actions > 0, "Number of actions must be greater than 0"
        assert len(payoff_matrix) == num_players, "Payoff matrix must have the same number of rows as players"
        assert all(len(row) == num_actions for row in payoff_matrix), "Payoff matrix must have the same number of columns as actions"

        self.game_id = kwargs.game_id
        self.game_name = kwargs.game_name
        self.game_description = kwargs.game_description
        self.simulatneous = kwargs.simulatneous
        self.cooperative = kwargs.cooperative
        self.information_availability = kwargs.information_availability
        self.discrete = kwargs.discrete


        self.number_of_rounds = number_of_rounds
        self.num_players = num_players
        self.num_actions = num_actions
    
    def get(self, key, default=None):
        return getattr(self, key, default)
