from typing import List, Dict, Any
from enum import Enum
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

    def __init__(self, game_config: GameConfig, payoffs = None, game_type = "random"):
        super().__init__(game_config)
        self.game_type = game_type
        self.reset()

    def step(self):
        actions = [0 for _ in range(self.game_config.num_agents)]
        for action, round in self.actions:
            if round == self.round:
                actions[action.agent_id] = action.action_id

        self.player_utility += self.payoff_matrix[actions[0], actions[1], :]
        self.round += 1

    def reset(self):
        super().reset()
        if self.game_type == "random":
            self.payoff_matrix = self.generate_random_payoffs()
        elif self.game_type == "prisoners_dilemma":
            self.payoff_matrix = self.generate_random_prisoners_dilemma()
        elif self.game_type == "stag_hunt":
            self.payoff_matrix = self.generate_random_stag_hunt()
        elif self.game_type == "battle_of_the_sexes":
            self.payoff_matrix = self.generate_random_battle_of_the_sexes()
        elif self.game_type == "chicken":
            self.payoff_matrix = self.generate_random_chicken()
        elif self.game_type == "cooperate":
            self.payoff_matrix = self.generate_random_cooperate()
        elif self.game_type == "defect":
            self.payoff_matrix = self.generate_random_defect()

        self.round = 0
        self.player_utility = 0
        self.nash_equilibria = self.find_pure_strategy_nash_equilibria()

    def get_state(self) -> Dict[str, Any]:
        return {"player_utility": self.player_utility, "payoff_matrix": self.payoff_matrix}

    def __str__(self):
        return_string = ""
        return_string += f"Matrix Game with {self.game_config.num_agents} players and {self.game_config.num_actions} actions per player\n"
        return_string += f"Payoff Matrix: {self.payoff_matrix}\n"
        return return_string

    def generate_random_payoffs(self):
        return torch.randint(-2, 2, (self.game_config.num_actions, self.game_config.num_actions, 2))


    def generate_random_prisoners_dilemma(self):
        # Cooperate (0), Defect (1)
        # Condition: T > R > P > S
        S = torch.randint(-10, 0, (1,)).item()
        P = torch.randint(S + 1, S + 10, (1,)).item()
        R = torch.randint(P + 1, P + 10, (1,)).item()
        T = torch.randint(R + 1, R + 10, (1,)).item()

        payoff_matrix = torch.tensor([
            # Player 1's payoffs
            [[R, S], [T, P]],
            # Player 2's payoffs
            [[R, T], [S, P]]
        ], dtype=torch.float32)
        return payoff_matrix

    def generate_random_chicken(self):
        # Swerve (0), Straight (1)
        # Condition: S > T > C > P
        P = torch.randint(-10, -5, (1,)).item()
        C = torch.randint(P + 1, P + 5, (1,)).item()
        T = torch.randint(C + 1, C + 5, (1,)).item()
        S = torch.randint(T + 1, T + 5, (1,)).item()

        payoff_matrix = torch.tensor([
            # Player 1's payoffs
            [[C, T], [S, P]],
            # Player 2's payoffs
            [[C, S], [T, P]]
        ], dtype=torch.float32)
        return payoff_matrix

    def generate_random_battle_of_the_sexes(self):
        # Opera (0), Football (1)
        # Condition: A > B > C
        C = torch.randint(-5, 0, (1,)).item()
        B = torch.randint(C + 1, C + 5, (1,)).item()
        A = torch.randint(B + 1, B + 5, (1,)).item()

        payoff_matrix = torch.tensor([
            # Player 1's payoffs
            [[A, C], [C, B]],
            # Player 2's payoffs
            [[B, C], [C, A]]
        ], dtype=torch.float32)
        return payoff_matrix

    def generate_random_stag_hunt(self):
        # Stag (0), Hare (1)
        # Condition: A > B > C
        C = torch.randint(-5, 0, (1,)).item()
        B = torch.randint(C + 1, C + 5, (1,)).item()
        A = torch.randint(B + 1, B + 5, (1,)).item()

        payoff_matrix = torch.tensor([
            # Player 1's payoffs
            [[A, C], [B, B]],
            # Player 2's payoffs
            [[A, B], [C, B]]
        ], dtype=torch.float32)
        return payoff_matrix

    def generate_random_cooperate(self):
        # Player 1 payoffs
        p1_cooperate_c = torch.randint(1, 10, (1,)).item()
        p1_cooperate_d = torch.randint(1, 10, (1,)).item()
        p1_defect_c = torch.randint(-5, 0, (1,)).item()
        p1_defect_d = torch.randint(-5, 0, (1,)).item()

        # Player 2 payoffs
        p2_cooperate_c = torch.randint(1, 10, (1,)).item()
        p2_defect_c = torch.randint(1, 10, (1,)).item()
        p2_cooperate_d = torch.randint(-5, 0, (1,)).item()
        p2_defect_d = torch.randint(-5, 0, (1,)).item()

        payoff_matrix = torch.tensor([
            # Player 1's payoffs
            [[p1_cooperate_c, p1_cooperate_d], [p1_defect_c, p1_defect_d]],
            # Player 2's payoffs
            [[p2_cooperate_c, p2_defect_c], [p2_cooperate_d, p2_defect_d]]
        ], dtype=torch.float32)
        return payoff_matrix

    def generate_random_defect(self):
        # Player 1 payoffs
        p1_defect_c = torch.randint(1, 10, (1,)).item()
        p1_defect_d = torch.randint(1, 10, (1,)).item()
        p1_cooperate_c = torch.randint(-5, 0, (1,)).item()
        p1_cooperate_d = torch.randint(-5, 0, (1,)).item()

        # Player 2 payoffs
        p2_defect_c = torch.randint(1, 10, (1,)).item()
        p2_cooperate_d = torch.randint(1, 10, (1,)).item()
        p2_cooperate_c = torch.randint(-5, 0, (1,)).item()
        p2_defect_d = torch.randint(-5, 0, (1,)).item()

        payoff_matrix = torch.tensor([
            # Player 1's payoffs
            [[p1_cooperate_c, p1_cooperate_d], [p1_defect_c, p1_defect_d]],
            # Player 2's payoffs
            [[p2_cooperate_c, p2_defect_c], [p2_cooperate_d, p2_defect_d]]
        ], dtype=torch.float32)
        return payoff_matrix
    
    def find_pure_strategy_nash_equilibria(self):
        nash_equilibria = []
        rows, cols, _ = self.payoff_matrix.shape
        for i in range(rows):
            for j in range(cols):
                # Check if player 1 can do better by changing row
                is_p1_best = all(self.payoff_matrix[i, j, 0] >= self.payoff_matrix[k, j, 0] for k in range(rows))
                # Check if player 2 can do better by changing column
                is_p2_best = all(self.payoff_matrix[i, j, 1] >= self.payoff_matrix[i, k, 1] for k in range(cols))

                if is_p1_best and is_p2_best:
                    nash_equilibria.append((i, j))
        return nash_equilibria
