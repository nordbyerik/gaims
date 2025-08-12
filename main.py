import os
from copy import deepcopy
from dotenv import load_dotenv
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

load_dotenv()

from typing import Any, List, Dict, Tuple

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
import numpy as np

logging.basicConfig(filename="example.log", encoding="utf-8", level=logging.INFO)

logger = logging.getLogger(__name__)


from gaims.configs.prompt_config import game_prompts


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

    context = {
        "agent_id": 0,
        "state": {
            "player_utility": 0,
            "payoff_matrix": [[[9.0, 0.0], [12.0, -4.0]], [[1.0, -1.0], [4.0, 3.0]]],
        },
        "round": 0,
        "agent_observations": [],
        "communication_partners": ["Country B"],
        "agent_persona": "You are a competitive agent who aims to maximize your own utility. You make strategic decisions to outperform others and achieve the best possible outcome for yourself.",
    }

    activations = Activations()
    torch.cuda.empty_cache()

    for i in range(10):
        for variation in ["", "_defection", "_collusion"]:
            for nash_eq_type in ["cooperate", "defect"]:
                for game_flavor in [
                    "environmental",
                    "moral_dilemma",
                    "neutral",
                    "security_arms",
                ]:
                    for persona in [
                        "competitive",
                        "cooperative",
                        "neutral",
                    ]:

                        framing = game_flavor + variation

                        game_config = GameConfig(
                            num_rounds=1,
                            num_actions=2,
                            num_agents=2,
                            game_type="matrix_game",
                            observe=False,
                            communication_type=None,
                        )
                        framing = game_prompts.get(framing)
                        nash_eq_type = nash_eq_type
                        system_prompt_config_0 = persona  # Personas
                        system_prompt_config_1 = persona

                        agent_configs = [
                            AgentConfig(
                                id=0,
                                name=framing.agent_names[0],
                                prompt_config=framing,
                                system_prompt_config=system_prompt_config_0,
                                model_config=ModelConfig(
                                    model_name="Qwen/Qwen2.5-0.5B-Instruct",
                                    activation_layers=[
                                        "model.layers.16.mlp",
                                    ],
                                    max_tokens=1,
                                ),
                            ),
                            AgentConfig(
                                id=1,
                                name=framing.agent_names[1],
                                prompt_config=framing,
                                system_prompt_config=system_prompt_config_1,
                                model_config=ModelConfig(model_name="gemini"),
                            ),
                        ]

                        agents = [Agent(config) for config in agent_configs]

                        if game_config.game_type == "matrix_game":
                            game_state = MatrixGameState(
                                game_config, game_type=nash_eq_type
                            )
                        elif game_config.game_type == "resource_sharing":
                            game_state = ResourceSharingGameState(game_config)
                        elif game_config.game_type == "negotiation":
                            game_state = NegotiationGameState(game_config)

                        env = GaimsEnv(game_config, agent_configs, game_state, agents)
                        obs, info = env.reset()

                        context_copy = context.copy()
                        context_copy["state"][
                            "payoff_matrix"
                        ] = env.game_state.payoff_matrix
                        context_copy["agent_persona"] = agents[0].persona

                        model_activations, matrix_action = env.gather_activaton(context)

                        activations.append(
                            model_activations,
                            variation,
                            nash_eq_type,
                            game_flavor,
                            persona,
                        )

                        env.close()

    classify_activations(activations, "model.layers.16.mlp", "persona")
    classify_activations(activations, "model.layers.16.mlp", "variation")
    classify_activations(activations, "model.layers.16.mlp", "nash_eq_type")
    classify_activations(activations, "model.layers.16.mlp", "framing")


class ProbeDataset(Dataset):
    def __init__(
        self, activations_data: torch.Tensor, labels: List, label_to_idx: Dict
    ):
        self.activations = activations_data
        self.labels = torch.tensor([label_to_idx[l] for l in labels], dtype=torch.long)

    def __len__(self):
        return len(self.activations)

    def __getitem__(self, idx):
        return self.activations[idx], self.labels[idx]


def classify_activations(
    activations, layer_name, classification_type, batch_size=32, device="mps"
):
    activations_copy = deepcopy(activations)
    activations_copy.activations = [
        activation[layer_name][0][:, -1, :].squeeze()
        for activation in activations.activations
    ]
    activations_copy.activations = torch.stack(activations_copy.activations)

    labels = getattr(activations_copy, classification_type)
    label_set = sorted(list(set(labels)))
    label_to_idx = {label: idx for idx, label in enumerate(label_set)}
    output_size = len(label_set)

    probe_dataset = ProbeDataset(activations_copy.activations, labels, label_to_idx)
    probe_dataset = probe_dataset
    dataloader = DataLoader(probe_dataset, batch_size=batch_size, shuffle=True)

    input_size = probe_dataset.activations.shape[1]
    probe = LinearProbe(input_size, output_size).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(probe.parameters(), lr=0.0001)

    # 4. Training loop
    probe.train()

    num_epochs = 100
    for epoch in range(num_epochs):
        for inputs, targets in dataloader:
            optimizer.zero_grad()
            outputs = probe(inputs.float().to(device))
            loss = criterion(outputs, targets.to(device))
            loss.backward()
            optimizer.step()

        print(f"Epoch {epoch+1}/{num_epochs}, Loss: {loss.item():.4f}")

    probe.eval()

    # 2. Extract and prepare data for Scikit-learn
    X_list = []
    y_list = []
    for batch_X, batch_y in dataloader:
        X_list.append(batch_X.cpu().detach().to(torch.float32).numpy())
        y_list.append(batch_y.cpu().detach().to(torch.float32).numpy())

    X_numpy = np.concatenate(X_list)
    y_numpy = np.concatenate(y_list)

    # 3. Use the NumPy data with Scikit-learn
    X_train, X_test, y_train, y_test = train_test_split(
        X_numpy, y_numpy, test_size=0.2, random_state=42
    )

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    score = model.score(X_test, y_test)
    print(f"Scikit-learn model accuracy: {score}")

    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in dataloader:
            outputs = probe(inputs.float())
            _, predicted = torch.max(outputs.data, 1)
            total += targets.size(0)
            correct += np.sum(
                [
                    (i == j)
                    for i, j in zip(
                        predicted.cpu().detach().to(torch.float32).numpy(),
                        targets.cpu().detach().to(torch.float32).numpy(),
                    )
                ]
            ).item()

    accuracy = 100 * correct / total
    print(f"Accuracy of the linear probe on the dataset: {accuracy:.2f}%")


def main_full_sim():
    activations = Activations()
    torch.cuda.empty_cache()

    for i in range(5):
        for nash_eq_type in ["cooperate", "defect"]:
            for framing in ["environmental", "moral_dilemma", "neutral"]:

                game_config = GameConfig(
                    num_rounds=1,
                    num_actions=2,
                    num_agents=2,
                    game_type="matrix_game",
                    observe=True,
                    communication_type="fully_connected",
                )

                framing = game_prompts.get(framing)
                nash_eq_type = nash_eq_type
                system_prompt_config_0 = "competitive"  # Personas
                system_prompt_config_1 = "cooperative"

                agent_configs = [
                    AgentConfig(
                        id=0,
                        name=framing.agent_names[0],
                        prompt_config=framing,
                        system_prompt_config=system_prompt_config_0,
                        model_config=ModelConfig(
                            model_name="Qwen/Qwen2.5-0.5B-Instruct",
                            activation_layers=[
                                "model.layers.16.mlp",
                            ],
                        ),
                    ),
                    AgentConfig(
                        id=1,
                        name=framing.agent_names[1],
                        prompt_config=framing,
                        system_prompt_config=system_prompt_config_1,
                        model_config=ModelConfig(model_name="gemini"),
                    ),
                ]

                agents = [Agent(config) for config in agent_configs]

                if game_config.game_type == "matrix_game":
                    game_state = MatrixGameState(game_config, game_type=nash_eq_type)
                elif game_config.game_type == "resource_sharing":
                    game_state = ResourceSharingGameState(game_config)
                elif game_config.game_type == "negotiation":
                    game_state = NegotiationGameState(game_config)

                env = GaimsEnv(game_config, agent_configs, game_state, agents)

                obs, info = env.reset()
                done = False
                while not done:
                    env.render()
                    action = env.action_space.sample()  # Sample a random action
                    obs, reward, done, info = env.step(action)

                    activation = env.get_activations()

                    activations.append(
                        activation,
                        nash_eq_type == "cooperate",
                        nash_eq_type == "defect",
                        False,
                        False,
                    )

                env.close()

    torch.save(activations, "activations_data.pt")


if __name__ == "__main__":
    main()
