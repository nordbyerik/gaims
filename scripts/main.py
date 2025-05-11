from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
import torch

from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import Dataset
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

from utils.activation_hook import ActivationHook
from configs.game_simple_configs import game_prompts
from agents.agent_factory import AgentFactory
from agents.agent import Agent
from agents.models import Model, LocalModel

from tqdm import tqdm


import logging
import sys

import dotenv

dotenv.load_dotenv()
log = logging.getLogger("hot")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class Action():
    def __init__(self, decision: str, value: float):
        self.action = decision
        self.value = value


class PlayerConfig():
    def __init__(self, use_logits=True):
        self.use_logits = use_logits



def train_classifier(activations, responses):
    X_train, X_test, y_train, y_test = train_test_split(activations, responses, test_size=0.2, random_state=42)

    print(X_train.shape, X_test.shape, y_train.shape, y_test.shape)
    print(X_train[:5], y_train[:5])

    classifier = LogisticRegression(max_iter=1000)
    classifier.fit(X_train, y_train)

    y_pred = classifier.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Classifier Accuracy: {accuracy * 100:.2f}%")
    return classifier, accuracy


# --- Example Usage ---
if __name__ == "__main__":
    # Define game parameters
    p1_actions = 2
    p2_actions = 2
    min_payoff_val = -5
    max_payoff_val = 5

    # Generate random payoffs and find Nash equilibria
    game = MatrixGameGenerator(p1_actions, p2_actions, min_payoff_val, max_payoff_val)

    defect_game_configs = set()
    cooperate_game_configs = set()
    game_configs = set()
    for i in range(10):
        payoffs, pure_nash_equilibria = game.generate_random_payoffs()
        
        if i == 0:
            game.display_game()
            print(payoffs)
            print(payoffs.flatten())
            print(payoffs.flatten().reshape(2, 2, 2))

        payoffs = torch.Tensor(payoffs).flatten()
        if len(pure_nash_equilibria) == 1:
            if pure_nash_equilibria[0][0] == 0:
                defect_game_configs.add((payoffs, 0))
            elif pure_nash_equilibria[0][0] == 1:
                cooperate_game_configs.add((payoffs, 1))

        game_configs.add((payoffs, tuple(pure_nash_equilibria)))


    # TODO: Add in ambiguous nash equilibria games

    game_configs_payoffs = torch.Tensor([game_config[0].tolist() for game_config in defect_game_configs] + [game_config[0].tolist() for game_config in cooperate_game_configs])
    game_configs_nash = torch.Tensor([game_config[1] for game_config in defect_game_configs] + [game_config[1] for game_config in cooperate_game_configs])


    # Convert to dataset
    data = [
        {"payoffs": payoff, "nash": nash}
        for payoff, nash in zip(game_configs_payoffs, game_configs_nash)
    ]
    game_configs_dataset = Dataset.from_list(data)


    # NOTE: Did we really need to go full OOP on this?
    # Probably not 
    selected_layers = ['model.layers.15.mlp']
    model = PlayerModelWrapper('unsloth/Llama-3.2-3B-Instruct', selected_layers=selected_layers)
    player = Player(model)

    # Building classification dataset


    iterations = 0
    correct = 0
    cooperate_activations = []
    cooperate_responses = []
    for cooperate_game in game_configs_dataset:
        for game_prompt in game_prompts.values():
            for layer in selected_layers:
                for orders in range(2):
                    options = game_prompt['action_names'][::-1] if orders == 1 else game_prompt['action_names'] # Want to make sure we don't just train a "1" classifier so have defect and cooperate be flipped 
                    game_config = GameConfig(number_of_rounds=1, num_players=2, num_actions=2, payoff_matrix=cooperate_game['payoffs'], template=game_prompt['template'], options=options)
                    game = Game(player, game_config)
                    choice = game.step()

                    if orders == 1:
                        choice = abs(choice - 1) # Flip the choice back if the order is flipped

                    if choice == cooperate_game['nash']:
                        correct += 1

                    cooperate_responses.append(choice)
                    cooperate_activations.append(np.squeeze(game.player.model.get_activations(layer)))
                    iterations += 1

                    print("Choice: ", choice)
                    print("Nash: ", cooperate_game['nash'])
                    print(f"Correct: {correct}/{iterations}")

 
    activations = np.array(cooperate_activations)
    responses = np.array(cooperate_responses)
    train_classifier(activations, responses)
