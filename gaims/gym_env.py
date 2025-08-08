import gymnasium as gym
from gymnasium import spaces
import numpy as np

from gaims.games.matrix_games.matrix_game import MatrixGameState, MatrixAction
from gaims.configs.game_config import GameConfig
from gaims.configs.agent_config import AgentConfig
from gaims.agents.models import ModelConfig, LocalModel
from gaims.configs.prompt_config import game_prompts
from gaims.communication.communication import CommunicationMediumFactory

class GaimsEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, game_config, agent_configs, game_state, agents):
        super(GaimsEnv, self).__init__()

        self.game_config = game_config
        self.agent_configs = agent_configs
        self.game_state = game_state
        self.agents = agents

        self.communication_medium = None
        if game_config.communication_type != None:
            self.communication_medium = CommunicationMediumFactory.create_communication_medium(game_config.type)

        self.action_space = spaces.Discrete(self.game_config.num_actions)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=self.game_state.payoff_matrix.shape, dtype=np.float32)

        self.agent_activations = {}

    def step(self, action):

        # Observe
        if self.game_state.observe:
            for agent in self.agents:
                context = {
                    "agent_id": agent.id,
                    "state": self.game_state.get_state(),
                    "round": self.game_state.round,
                    "communication_partners": self.game_config.
                }
                agent.observe(context)

        # Communicate
        if self.game_state.communication_type != None:
            for agent in self.agents:
                context = {
                    "agent_id": agent.id,
                    "state": self.game_state.get_state(),
                    "round": self.game_state.round,
                }
                agent.communicate(context)

        for agent in self.agents:
            context = {
                "agent_id": agent.id,
                "state": self.game_state.get_state(),
                "round": self.game_state.round,
            }
            agent.observe_communication(context)

        # All agents take an action
        actions = []
        for agent in self.agents:
            # For now, a simplified context for the agent to act
            context = {
                "agent_id": agent.id,
                "state": self.game_state.get_state(),
                "round": self.game_state.round,
            }
            agent_action = agent.act(context)
            if type(agent.model) == LocalModel:

                for key in agent.model.hooks.keys():
                    if key not in self.agent_activations.keys():
                        self.agent_activations[key] = []
                    self.agent_activations[key].append(agent.model.get_activations(key))
            matrix_action = MatrixAction(
                agent_id=agent.id, action_id=agent_action.action_id
            )
            actions.append({"agent_id": agent.id, "action": matrix_action})

        # TODO: Roll this into the game_state.step()
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
        self.game_state.reset()
        return self.game_state.get_state(), {
            "nash_equilibria": self.game_state.nash_equilibria
        }
    
    def gather_steps(self):
        """
        Instead of running the full simulation, just gather the prompts
        """
        for agent in self.agents:
            context = {
                "agent_id": agent.id,
                "state": self.game_state.get_state(),
                "round": self.game_state.round,
            }

    def render(self, mode='human', close=False):
        # Render the environment to the screen
        print(f"Round: {self.game_state.round}")
        print(f"Player Utility: {self.game_state.player_utility}")
        print(f"Payoff Matrix: \n{self.game_state.payoff_matrix}")

    def get_activations(self):
        return self.agent_activations
