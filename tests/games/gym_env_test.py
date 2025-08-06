import unittest
import numpy as np

from gaims.gym_env import GaimsEnv
from gaims.configs.game_config import GameConfig
from gaims.configs.agent_config import AgentConfig
from gaims.agents.models import ModelConfig
from gaims.games.matrix_games.matrix_game import MatrixGameState
from gaims.configs.prompt_config import game_prompts

import torch
import nashpy as nash

class TestGaimsEnv(unittest.TestCase):

    def setUp(self):
        game_config = GameConfig(num_rounds=10, num_actions=2, num_agents=2, game_type="matrix_game")
        game_prompt = game_prompts.get("neutral")
        agent_configs = [
            AgentConfig(id=0, prompt_config=game_prompt, model_config=ModelConfig(model_name="gemini")),
            AgentConfig(id=1, prompt_config=game_prompt, model_config=ModelConfig(model_name="gemini"))
        ]
        game_state = MatrixGameState(game_config)
        self.env = GaimsEnv(game_config, agent_configs, game_state)

    def test_env_creation(self):
        self.assertIsInstance(self.env, GaimsEnv)

    def test_reset(self):
        obs, info = self.env.reset()
        self.assertIn('payoff_matrix', obs)
        self.assertIn('player_utility', obs)
        self.assertIn('nash_equilibria', info)
        self.assertEqual(self.env.game_state.round, 0)
        self.assertEqual(self.env.game_state.player_utility, 0)

    def test_step(self):
        self.env.reset()
        action = self.env.action_space.sample()
        obs, reward, done, info = self.env.step(action)
        self.assertIn('payoff_matrix', obs)
        self.assertIn('player_utility', obs)
        self.assertIn('nash_equilibria', info)
        self.assertEqual(self.env.game_state.round, 1)

    def test_nash_equilibrium_prisoners_dilemma(self):
        # Prisoner's Dilemma payoff matrix
        # (Cooperate, Cooperate), (Cooperate, Defect)
        # (Defect, Cooperate), (Defect, Defect)
        # Player 1 (row player) payoffs
        p1_payoffs = np.array([[3, 0], [5, 1]])
        # Player 2 (column player) payoffs
        p2_payoffs = np.array([[3, 5], [0, 1]])

        # Create a nashpy game
        game = nash.Game(p1_payoffs, p2_payoffs)
        # Find pure strategy Nash Equilibria using nashpy
        nashpy_equilibria = sorted([(np.where(eq[0] == 1)[0][0], np.where(eq[1] == 1)[0][0]) for eq in game.support_enumeration()])

        # Set the payoff matrix in the environment's game_state
        # Note: The game_state expects a torch tensor with shape (num_actions, num_actions, 2)
        payoffs_tensor = torch.tensor([[[3, 3], [0, 5]], [[5, 0], [1, 1]]], dtype=torch.float32)
        self.env.game_state.payoff_matrix = payoffs_tensor
        
        # Calculate Nash Equilibria using the environment's method
        self.env.game_state.nash_equilibria = self.env.game_state.find_pure_strategy_nash_equilibria()
        
        # Sort the results for consistent comparison
        gaims_equilibria = sorted(self.env.game_state.nash_equilibria)

        self.assertEqual(gaims_equilibria, nashpy_equilibria)

    def test_render(self):
        # Just call render to ensure it doesn't raise an error
        self.env.render()
        # No assert needed, as we are just checking for execution without errors

if __name__ == '__main__':
    unittest.main()
