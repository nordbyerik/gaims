import os
from copy import deepcopy
from dotenv import load_dotenv
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import numpy as np
import matplotlib.pyplot as plt

load_dotenv()

from typing import Any, List, Dict, Tuple

from gaims.configs.game_config import GameConfig
from gaims.configs.agent_config import AgentConfig
from gaims.agents.models import ModelConfig
from gaims.agents.agent import Agent
from gaims.games.matrix_games.matrix_game import MatrixGameState
from gaims.games.resource_sharing.resource_sharing_game import ResourceSharingGameState
from gaims.games.negotiation.negotiation_game import NegotiationGameState
from gaims.gym_env import GaimsEnv
import logging

logging.basicConfig(filename="example.log", encoding="utf-8", level=logging.INFO)
logger = logging.getLogger(__name__)

from gaims.configs.prompt_config import game_prompts

def visualize_attention(attention_weights, tokens, filename="attention_visualization.png"):
    """
    Visualizes attention weights as a heatmap.
    """
    if attention_weights is None:
        print("No attention weights to visualize.")
        return

    # Assuming attention_weights is a tensor, let's average over attention heads.
    # Shape: (batch, heads, seq_len, seq_len)
    attention_matrix = attention_weights.mean(dim=1).squeeze(0).cpu().numpy()

    fig, ax = plt.subplots(figsize=(12, 10))
    cax = ax.matshow(attention_matrix, cmap='viridis')
    fig.colorbar(cax)

    ax.set_xticks(np.arange(len(tokens)))
    ax.set_yticks(np.arange(len(tokens)))

    ax.set_xticklabels(tokens, rotation=90)
    ax.set_yticklabels(tokens)

    ax.set_xlabel("Key")
    ax.set_ylabel("Query")
    ax.set_title("Attention Head Average")

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"Attention visualization saved to {filename}")


class Activations(Dataset):
    def __init__(self):
        self.activations = []
        self.variation = []
        self.nash_eq_type = []
        self.framing = []
        self.persona = []

    def __len__(self):
        return len(self.activations)

    def __getitem__(self, idx):
        return (
            self.activations[idx],
            self.variation[idx],
            self.nash_eq_type[idx],
            self.framing[idx],
            self.persona[idx],
        )

    def append(self, activation, variation, nash_eq_type, framing, persona):
        self.activations.append(activation)
        self.variation.append(variation)
        self.nash_eq_type.append(nash_eq_type)
        self.framing.append(framing)
        self.persona.append(persona)


class LinearProbe(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(LinearProbe, self).__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, x):
        return self.linear(x)


def main():
    torch.cuda.empty_cache()

    # Let's run for one specific setting to get a clear attention map
    variation = "_defection"
    nash_eq_type = "prisoners_dilemma"
    game_flavor = "security_arms"
    persona = "competitive"
    layer_to_viz = "model.layers.23.self_attn"

    framing = game_flavor + variation

    game_config = GameConfig(
        num_rounds=1,
        num_actions=2,
        num_agents=2,
        game_type="matrix_game",
        observe=False,
        communication_type=None,
    )
    framing_prompt = game_prompts.get(framing)
    system_prompt_config_0 = persona

    agent_configs = [
        AgentConfig(
            id=0,
            name=framing_prompt.agent_names[0],
            prompt_config=framing_prompt,
            system_prompt_config=system_prompt_config_0,
            model_config=ModelConfig(
                model_name="unsloth/gpt-oss-20b",
                activation_layers=[layer_to_viz],
                max_tokens=1,
                capture_attention_weights=True, # Important!
            ),
        ),
        AgentConfig(
            id=1,
            name=framing_prompt.agent_names[1],
            prompt_config=framing_prompt,
            system_prompt_config=persona,
            model_config=ModelConfig(model_name="gemini"),
        ),
    ]

    agents = [Agent(config) for config in agent_configs]
    game_state = MatrixGameState(game_config, game_type=nash_eq_type)
    env = GaimsEnv(game_config, agent_configs, game_state, agents)
    obs, info = env.reset()

    # We need the raw prompt to get the tokens for visualization
    raw_prompt = agents[0].format_prompt(obs[0])
    
    # This will run the model and trigger the hooks to capture attention
    _, _ = agents[0].model.send_message(raw_prompt)

    # Retrieve activations (which are now attention weights)
    attention_weights = agents[0].model.get_activations(layer_to_viz)

    # Get tokens from the tokenizer
    tokenizer = agents[0].model.tokenizer
    tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(raw_prompt))

    visualize_attention(attention_weights, tokens, filename=f"attention_{persona}_{game_flavor}.png")

    env.close()


if __name__ == "__main__":
    main()