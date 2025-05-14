from typing import List, Dict, Any
from abc import ABC
from games.game import GameState
from games.action import Action
from configs.game_config import GameConfig

import numpy as np
import torch

# Things that are needed for each game
# - ActionsConfig/Definition
# - GameConfig/Definition <- Below
# - AgentConfig/Definition


class MatrixAction(Action):
    def __init__(self, agent_id: int, action_id: int, values: List[float] = None):
        self.agent_id = agent_id
        self.action_id = action_id

class MatrixGameState(GameState):
    def __init__(self, game_config: GameConfig, payoffs = None):
        super().__init__(game_config)
        generator = MatrixGameGenerator(2, 2, -2, 2)
        self.payoff_matrix, self.optimal_actions = generator.generate_random_payoffs() if payoffs is None else payoffs
        self.player_utility = 0

    def step(self):
        actions = [0 for _ in range(self.game_config.num_agents)]
        for action, round in self.actions:
            if round == self.round:
                actions[action.agent_id] = action.action_id

        self.player_utility += self.payoff_matrix[actions[0], actions[1], 0]

    def get_state(self) -> Dict[str, Any]:
        return {"player_utility": self.player_utility, "payoff_matrix": self.payoff_matrix}
          
    def __str__(self):
        return_string = ""
        return_string += f"Matrix Game with {self.num_players} players and {self.num_actions} actions per player\n"
        return_string += f"Payoff Matrix: {self.payoff_matrix}\n"
        return return_string


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
        self.payoffs = torch.randint(self.min_payoff, self.max_payoff + 1,
                                        size=(self.num_actions_p1, self.num_actions_p2, 2))
        
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
