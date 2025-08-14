import gymnasium as gym
import logging
from gymnasium import spaces
import numpy as np

from gaims.games.matrix_games.matrix_game import MatrixGameState, MatrixAction
from gaims.configs.game_config import GameConfig
from gaims.configs.agent_config import AgentConfig
from gaims.games.action import Action
from gaims.agents.models import ModelConfig, LocalModel, StructureParsingException
from gaims.configs.prompt_config import game_prompts
from gaims.communication.communication import CommunicationMediumFactory


log = logging.getLogger(__name__)

class GaimsEnv(gym.Env):
    metadata = {'render.modes': ['human']}
    

    def __init__(self, game_config, agent_configs, game_state, agents):
        super(GaimsEnv, self).__init__()

        self.game_config = game_config
        self.agent_configs = agent_configs
        self.game_state = game_state
        self.agents = agents

        self.logged_events = []

        self.communication_medium = None
        if game_config.communication_type != None:
            self.communication_medium = (
                CommunicationMediumFactory.create_communication_medium(
                    game_config.communication_type, agents
                )
            )

        self.action_space = spaces.Discrete(self.game_config.num_actions)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=self.game_state.payoff_matrix.shape, dtype=np.float32)

        self.agent_activations = {}

    def step(self, action):

        # Observe
        if self.game_config.observe:
            for agent in self.agents:
                context = {
                    "agent_id": agent.id,
                    "state": self.game_state.get_state(),
                    "round": self.game_state.round,
                    "num_rounds": self.game_config.num_rounds,
                    "communication_partners": (
                        self.communication_medium.get_communication_partners(agent.id)
                        if self.communication_medium != None
                        else None
                    ),
                    "agent_observations": agent.observations,
                    "agent_persona": agent.persona,
                }
                logging_info = agent.observe(context)
                logging_info["round_num"] = self.game_state.round
                self.logged_events.append(logging_info)

        # Communicate
        if self.communication_medium != None:
            for agent in self.agents:
                context = {
                    "agent_id": agent.id,
                    "state": self.game_state.get_state(),
                    "round": self.game_state.round,
                    "num_rounds": self.game_config.num_rounds,
                    "agent_observations": agent.observations,
                    "communication_partners": (
                        self.communication_medium.get_communication_partners(agent.id)
                        if self.communication_medium != None
                        else None
                    ),
                    "agent_persona": agent.persona,
                }
                message, logging_info = agent.communicate(context)
                logging_info["round_num"] = self.game_state.round
                self.logged_events.append(logging_info)

                self.communication_medium.send_message(
                    agent.id, message.receiver, message.message
                )

        for agent in self.agents:
            context = {
                "agent_id": agent.id,
                "state": self.game_state.get_state(),
                "round": self.game_state.round,
                "num_rounds": self.game_config.num_rounds,
                "agent_observations": agent.observations,
                "communication_partners": (
                    self.communication_medium.get_communication_partners(agent.id)
                    if self.communication_medium != None
                    else None
                ),
                "messages": (
                    self.communication_medium.get_all_pending_messages_for_agent(
                        agent.id
                    )
                    if self.communication_medium != None
                    else None
                ),
                "agent_persona": agent.persona,
            }
            logging_info = agent.observe_communication(context)
            logging_info["round_num"] = self.game_state.round
            self.logged_events.append(logging_info)

        # All agents take an action
        actions = []
        for agent in self.agents:
            # For now, a simplified context for the agent to act
            context = {
                "agent_id": agent.id,
                "state": self.game_state.get_state(),
                "round": self.game_state.round,
                "num_rounds": self.game_config.num_rounds,
                "agent_observations": agent.observations,
                "communication_partners": (
                    self.communication_medium.get_communication_partners(agent.id)
                    if self.communication_medium != None
                    else None
                ),
                "agent_persona": agent.persona,
            }
            agent_action, logging_info = agent.act(context)

            if type(agent.model) == LocalModel:

                for key in agent.model.hooks.keys():
                    if key not in self.agent_activations.keys():
                        self.agent_activations[key] = []
                    self.agent_activations[key].append(agent.model.get_activations(key))
            matrix_action = MatrixAction(
                agent_id=agent.id, action_id=agent_action.action_id
            )
            actions.append({"agent_id": agent.id, "action": matrix_action})

            logging_info["round_num"] = self.game_state.round
            logging_info["agent_action"] = matrix_action
            self.logged_events.append(logging_info)

            log.info(f"Agent {agent.id} took action {agent_action.action_id}")

        # TODO: Roll this into the game_state.step()
        for act in actions:
            self.game_state.step_agent(act['action'])

        self.game_state.step()

        observation = self.game_state.get_state()
        reward = self.game_state.player_utility # In matrix games, we can use player utility as reward
        done = self.game_state.round >= self.game_config.num_rounds
        info = {"nash_equilibria": self.game_state.nash_equilibria}

        log.info(f"Reward: {reward}")
        log.info(f"Nash Equilibria: {info['nash_equilibria']}")

        return observation, reward, done, info

    def reset(self):
        # Reset the state of the environment to an initial state
        self.game_state.reset()
        return self.game_state.get_state(), {
            "nash_equilibria": self.game_state.nash_equilibria
        }

    def gather_activaton(self, context, agent_id=0):
        agent = self.agents[agent_id]
        try:
            agent_action = agent.act(context)
        except StructureParsingException:
            agent_action = Action(agent_id=agent.id, action_id=0)
        model_activations = {}

        if type(agent.model) == LocalModel:
            for key in agent.model.hooks.keys():
                if key not in model_activations.keys():
                    model_activations[key] = []
                model_activations[key].append(agent.model.get_activations(key))

        matrix_action = MatrixAction(
            agent_id=agent.id, action_id=agent_action.action_id
        )

        return model_activations, matrix_action

    def render(self, mode='human', close=False):
        # Render the environment to the screen
        log.info(f"Round: {self.game_state.round}")
        log.info(f"Player Utility: {self.game_state.player_utility}")
        log.info(f"Payoff Matrix: \n{self.game_state.payoff_matrix}")

        print(f"Round: {self.game_state.round}")
        print(f"Player Utility: {self.game_state.player_utility}")
        print(f"Payoff Matrix: \n{self.game_state.payoff_matrix}")
    def get_activations(self):
        return self.agent_activations
