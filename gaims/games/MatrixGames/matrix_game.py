from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
import torch

from agents.agent import Agent, Action
from games.game import Game, GameConfig

class MatrixGameAction(Action):
    """Action for matrix-based games"""
    def __init__(self, action_id: int, action_name: str = None):
        super().__init__(action_id)
        self.action_name = action_name or str(action_id)
    
    def execute(self):
        return self.action_id
    
    def __str__(self):
        return self.action_name


class MatrixGameGenerator:
    """
    Represents a two-player normal-form game and provides methods
    to analyze it, specifically finding pure strategy Nash Equilibria.
    """

    def __init__(self, num_actions_p1, num_actions_p2, min_payoff=-10, max_payoff=10):
        """
        Initializes and generates a random two-player normal-form game.

        Args:
            num_actions_p1 (int): The number of actions available to Player 1.
            num_actions_p2 (int): The number of actions available to Player 2.
            min_payoff (int): The minimum possible payoff value.
            max_payoff (int): The maximum possible payoff value.

        Raises:
            ValueError: If number of actions is not positive or min_payoff >= max_payoff.
        """
        if num_actions_p1 <= 0 or num_actions_p2 <= 0:
            raise ValueError("Number of actions must be positive.")
        if min_payoff >= max_payoff:
            raise ValueError("min_payoff must be less than max_payoff.")

        self.num_actions_p1 = num_actions_p1
        self.num_actions_p2 = num_actions_p2
        self.min_payoff = min_payoff
        self.max_payoff = max_payoff

        # Generate random integer payoffs for each player for each action combination
        self.payoffs = []
        self._pure_nash_equilibria = None # Cache for equilibria

    @property
    def player1_payoffs(self):
        """Returns the payoff matrix for Player 1."""
        return self.payoffs[:, :, 0]

    @property
    def player2_payoffs(self):
        """Returns the payoff matrix for Player 2."""
        return self.payoffs[:, :, 1]
    
    def generate_random_payoffs(self):
        """Generates new random payoffs for the game."""
        self.payoffs = np.random.randint(self.min_payoff, self.max_payoff + 1,
                                         size=(self.num_actions_p1, self.num_actions_p2, 2))
        self.payoffs = torch.Tensor(self.payoffs)
        
        pure_nash_equilibria = self.find_pure_strategy_nash_equilibria() # Reset cache
        return self.payoffs, pure_nash_equilibria

    def find_pure_strategy_nash_equilibria(self):
        """
        Finds all pure strategy Nash Equilibria in the game.

        Results are cached after the first call.

        Returns:
            list: A list of tuples, where each tuple (i, j) represents a pure
                  strategy Nash Equilibrium (Player 1 plays action i, Player 2
                  plays action j). Returns an empty list if no pure strategy NE exist.
        """

        nash_equilibria = []
        # Iterate through every possible action profile (cell in the payoff matrix)
        for i in range(self.num_actions_p1):
            for j in range(self.num_actions_p2):
                # Get the payoffs for the current action profile (i, j)
                p1_payoff = self.payoffs[i, j, 0]
                p2_payoff = self.payoffs[i, j, 1]

                # Check if Player 1 has an incentive to deviate
                is_p1_best_response = True
                for alt_i in range(self.num_actions_p1):
                    if self.payoffs[alt_i, j, 0] > p1_payoff:
                        is_p1_best_response = False
                        break # Found a better action for P1

                if not is_p1_best_response:
                    continue # Not an NE, check next profile

                # Check if Player 2 has an incentive to deviate
                is_p2_best_response = True
                for alt_j in range(self.num_actions_p2):
                    if self.payoffs[i, alt_j, 1] > p2_payoff:
                        is_p2_best_response = False
                        break # Found a better action for P2

                # If neither player wants to deviate, it's a Nash Equilibrium
                if is_p1_best_response and is_p2_best_response:
                    nash_equilibria.append(torch.Tensor((i, j)))

        # Cache the result
        self._pure_nash_equilibria = nash_equilibria
        return self._pure_nash_equilibria




class MatrixGame(Game):
    def __init__(self, config: GameConfig):
        super().__init__(config)
        self.payoff_matrix = config.get('payoff_matrix', None)
        self.num_players = config.get('num_players', 2)
        self.num_actions = config.get('num_actions', 2)
        self.actions = [MatrixGameAction(i) for i in range(self.num_actions)]

    def __str__(self):
        return_string = ""
        return_string += f"Matrix Game with {self.num_players} players and {self.num_actions} actions per player\n"
        return_string += f"Payoff Matrix: {self.payoff_matrix}\n"
        return return_string

    def _to_dict(self):
        payoff_dict = {}
        for player_index in range(self.num_players):
            for action_index in range(self.num_actions):
                for opponent_action_index in range(self.num_actions):
                    # TODO: Should handle multiple players
                    if player_index == 0:
                        payoff_dict[player_index, action_index, opponent_action_index] = self.payoff_matrix[action_index, opponent_action_index, player_index]
                    else:
                        payoff_dict[player_index, action_index, opponent_action_index] = self.payoff_matrix[opponent_action_index, action_index, player_index]
        
        return payoff_dict
    
