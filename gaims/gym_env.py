import gymnasium as gym
from gymnasium import spaces
import numpy as np

from gaims.games.matrix_games.matrix_game import MatrixGameState, MatrixAction
from gaims.configs.game_config import GameConfig
from gaims.configs.agent_config import AgentConfig
from gaims.agents.models import ModelConfig
from gaims.configs.prompt_config import game_prompts

class GaimsEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, game_config, agent_configs, game_state, agents):
        super(GaimsEnv, self).__init__()

        self.game_config = game_config
        self.agent_configs = agent_configs
        self.game_state = game_state
        self.agents = agents

        self.action_space = spaces.Discrete(self.game_config.num_actions)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=self.game_state.payoff_matrix.shape, dtype=np.float32)

    def step(self, action):
        # All agents take an action
        actions = []
        for agent in self.agents:
            # For now, a simplified context for the agent to act
            context = {
                "state": self.game_state.get_state(),
                "round": self.game_state.round,
            }
            agent_action = agent.act(context)
            matrix_action = MatrixAction(
                agent_id=agent.id, action_id=agent_action.action_id
            )
            actions.append({"agent_id": agent.id, "action": matrix_action})

        for act in actions:
            self.game_state.step_agent(act['action'])

        self.game_state.step()

        observation = self.game_state.get_state()
        reward = self.game_state.player_utility # In matrix games, we can use player utility as reward
        done = self.game_state.round >= self.game_config.num_rounds
        info = {"nash_equilibria": self.game_state.nash_equilibria}

        return observation, reward, done, info

    def reset(self):
        # Reset the state of the environment to an initial state
        self.game_state.round = 0
        self.game_state.actions = []
        self.game_state.player_utility = 0
        self.game_state.payoff_matrix = self.game_state.generate_random_payoffs()
        self.game_state.nash_equilibria = (
            self.game_state.find_pure_strategy_nash_equilibria()
        )
        return self.game_state.get_state(), {
            "nash_equilibria": self.game_state.nash_equilibria
        }

    def render(self, mode='human', close=False):
        # Render the environment to the screen
        print(f"Round: {self.game_state.round}")
        print(f"Player Utility: {self.game_state.player_utility}")
        print(f"Payoff Matrix: \n{self.game_state.payoff_matrix}")
