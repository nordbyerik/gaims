import os
from dotenv import load_dotenv
import torch
from torch.utils.data import DataLoader, Dataset

load_dotenv()

from typing import Any, List

# Assuming these are defined in maigcom.definitions
from gaims.configs.game_config import GameConfig
from gaims.configs.agent_config import AgentConfig


from gaims.agents.models import ModelConfig, ModelFactory
from gaims.agents.agent import Agent 
from gaims.games.matrix_games.matrix_game import MatrixGameState
from gaims.games.resource_sharing.resource_sharing_game import ResourceSharingGameState
from gaims.games.negotiation.negotiation_game import NegotiationGameState
from gaims.gym_env import GaimsEnv

import logging
import time

logging.basicConfig(filename="example.log", encoding="utf-8", level=logging.INFO)

logger = logging.getLogger(__name__)


from gaims.configs.prompt_config import game_prompts


class Activations(Dataset):
    def __init__(self):
        self.activations = []
        self.cooperate = []
        self.defect = []
        self.scheme = []
        self.collude = []
    
    def __len__(self):
        return len(self.activations)
    
    def __getitem__(self, idx):
        return self.activations[idx], self.cooperate[idx], self.defect[idx], self.scheme[idx], self.collude[idx]




def main():
    activations = Activations()
    torch.cuda.empty_cache()

    for game_class in ["cooperate", "defect", "chicken", "battle_of_the_sexes", "stag_hunt", "prisoners_dilemma"]
        
        game_config = GameConfig(num_rounds=1, num_actions=2, num_agents=2, game_type="matrix_game", observe=True, communicate=True, act=True)

        game_prompt = game_prompts.get("neutral")
        agent_configs = [
            AgentConfig(id=0, prompt_config=game_prompt, model_config=ModelConfig(model_name="unsloth/gpt-oss-20b", activation_layers=["model.layers.0.mlp", "model.layers.1.self_attn"])), 
            AgentConfig(id=1, prompt_config=game_prompt, model_config=ModelConfig(model_name="gemini"))
        ]

        agents = [Agent(config) for config in agent_configs]

        if game_config.game_type == "matrix_game":
            game_state = MatrixGameState(game_config, game_type=game_class)
        elif game_config.game_type == "resource_sharing":
            game_state = ResourceSharingGameState(game_config)
        elif game_config.game_type == "negotiation":
            game_state = NegotiationGameState(game_config)

        env = GaimsEnv(game_config, agent_configs, game_state, agents)
        
        obs, info = env.reset()
        done = False
        while not done:
            env.render()
            action = env.action_space.sample() # Sample a random action
            obs, reward, done, info = env.step(action)
            print(f"Reward: {reward}")
            print(f"Nash Equilibria: {info['nash_equilibria']}")
        
        env.close()

    
