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


from tqdm import tqdm


class Action():
    def __init__(self, decision: str, value: float):
        self.action = decision
        self.value = value


class PlayerModelWrapper():
    def __init__(self, model: str, selected_layers: List[str]):
        self.model_string = model
        self.model = AutoModelForCausalLM.from_pretrained(model, load_in_4bit=True)
        self.model.eval()
        self.tokenizer = AutoTokenizer.from_pretrained(model)

        self.hooks = {}
        for layer in selected_layers:
            self.hooks[layer] = ActivationHook(self.model, layer)

    def generate_response_from_plain_text(self, message: str):
        inputs = self.tokenizer(message, return_tensors="pt")
        outputs = self.model.generate(**inputs, max_new_tokens=5)
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer_text = generated_text[len(message):].strip()

        if "0" in answer_text:
            return 0
        elif "1" in answer_text:
            return 1
        
        return np.random.randint(0, 1)
    
    def generate_response_from_logits(self, message):
        inputs = self.tokenizer(message, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs.to(self.model.device))

        options = ["0", "1"]
        option_probs = torch.zeros(len(options))
        for option in options:
            
            option_token_id = self.tokenizer(option, return_tensors="pt", add_special_tokens=False).input_ids[-1] # Shape [1]

            # Calculate the logit value (result is shape [1])
            logit_tensor = outputs.logits[0, -1, option_token_id]

            # --- FIX ---
            # Extract the scalar value using .item() before assignment
            print(logit_tensor)
            option_probs[options.index(option)] = logit_tensor.item()

        return np.argmax(option_probs)
    
    # TODO: See here: https://github.com/cma1114/activation_steering
    def get_activations(self, layer):
        return self.hooks[layer].activations[:, -1, :].detach().cpu()

    

class PlayerConfig():
    def __init__(self, use_logits=True):
        self.use_logits = use_logits

class Player():
    # NOTE: Could either have the players themselves observe the state and run it through an internal 
    # model, or have the game itself observe the state and pass it to the players through a prompt.
    # Starting w/ just having the game supply the state to the players for simplicity's sake.
    def __init__(self, model: PlayerModelWrapper, config=PlayerConfig()):
        self.model = model
        self.use_logits = config.use_logits
        self.activations = None

        # TODO: Later
        self.utility = 0
        self.observations = []
        self.plans = []
        self.messages_sent = []
        self.messages_received = []
        self.actions = []

    def query_model(self, prompt: str):
        response = self.model.send_message(prompt, logits=self.use_logits)
        return response

    def observe(self):
        raise NotImplementedError("Observe method not implemented")

    def plan(self):
        raise NotImplementedError("Plan method not implemented")

    def communicate(self, messages: Dict[str, List[str]]):
        raise NotImplementedError("Communicate method not implemented")
    
    def act(self, prompt: str) -> Action:
        return self.query_model(prompt)

class GameConfig:
    def __init__(self, number_of_rounds: int, num_players: int, num_actions: int, payoff_matrix: List[List[int]], template, options):

        payoff_matrix = torch.Tensor(payoff_matrix).reshape(num_actions, num_actions, num_players)

        assert number_of_rounds > 0, "Number of rounds must be greater than 0"
        assert num_players > 0, "Number of players must be greater than 0"
        assert num_actions > 0, "Number of actions must be greater than 0"
        assert len(payoff_matrix) == num_players, "Payoff matrix must have the same number of rows as players"
        assert all(len(row) == num_actions for row in payoff_matrix), "Payoff matrix must have the same number of columns as actions"



        self.number_of_rounds = number_of_rounds
        self.num_players = num_players
        self.num_actions = num_actions

        self.payoff_matrix = payoff_matrix

        self.template = template
        self.options = options
    
    def get(self, key, default=None):
        return getattr(self, key, default)

class Game(ABC):
    def __init__(self, player: Player, config: Dict[str, Any]):
        self.config = config
        self.player = player
        self.current_round = 0
        self.max_rounds = config.get('max_rounds', 10)
        self.scores = [0] * config.get('num_players', 2)
        self.payoff_matrix = config.get('payoff_matrix', None)
        self.prompt_format = config.get('prompt_format', None)

        self.template = config.get('template', None)
        self.options = config.get('options', None)

        self.num_players = config.get('num_players', None)
        self.num_actions = config.get('num_actions', None)



    def game_state_to_dict(self):
        payoff_dict = {}
        for player_index in range(self.num_players):
            for action_index in range(self.num_actions):
                for opponent_action_index in range(self.num_actions):
                    # TODO: Should handle multiple players
                    if player_index == 0:
                        payoff_dict[player_index, action_index, opponent_action_index] = self.payoff_matrix[action_index, opponent_action_index, player_index]
                    else:
                        payoff_dict[player_index, action_index, opponent_action_index] = self.payoff_matrix[opponent_action_index, action_index, player_index]
        
        return payoff_dict
    

    def payoff_matrix_to_prompt(self, payoff_dict, include_opponent_payoff=False):
        options = self.options
        template = self.template

        if self.options is None:
            options = ["Defect", "Cooperate"]
        if self.template is None:
            template = {
                'game_header': "Interaction Scenario:\n",
                'player_header': "Evaluate your choices.\nIf you select:\n",
                'action_header': " {player_action}, consider the potential outcomes:\n",
                'payoff_line': "    Paired against {opponent_action}: Result = {payoff}",
                'opponent_payoff': " (Opponent Result: {opponent_payoff})",
                'newline': "\n",
                'options': 'Which will you choose? (0 for {action_zero}, 1 for {action_one}) ',
                'queue': 'Input your choice (0/1):'
            }
        


        prompt = template['game_header']
        prompt += template['player_header']
        for action_index in range(self.num_actions):
            player_action = options[action_index]
            prompt += template['action_header'].format(player_action=player_action)
            for opponent_action_index in range(self.num_actions):
                opponent_action = options[opponent_action_index]
                payoff = payoff_dict[0, action_index, opponent_action_index] # TODO: Make this work for both players
                prompt += template['payoff_line'].format(
                    opponent_action=opponent_action,
                    payoff=payoff
                )
                
                if include_opponent_payoff:
                    opponent_payoff = payoff_dict[1, opponent_action_index, action_index] # TODO: Make this work for both players
                    prompt += template['opponent_payoff'].format(opponent_payoff=opponent_payoff)
                
                prompt += template['newline']
        prompt += template['options'].format(action_zero=options[0], action_one=options[1])
        prompt += template['queue']
        prompt += " "
        return prompt

    # TODO: Implement more complex game logic here
    # TODO: Allow for batching
    def step(self):
        payoff_dict = self.game_state_to_dict()
        prompt = self.payoff_matrix_to_prompt(payoff_dict)

        player_action = self.player.act(prompt)
        return player_action
        



class TwoPlayerGameGenerator:
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
        self.payoffs = np.random.randint(self.min_payoff, self.max_payoff + 1,
                                         size=(self.num_actions_p1, self.num_actions_p2, 2))
        self.payoffs = torch.Tensor(self.payoffs)
        
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

    def display_game(self):
        """Prints the game details and payoffs to the console."""
        print("--- Two-Player Game ---")
        print(f"Player 1 Actions: {self.num_actions_p1}")
        print(f"Player 2 Actions: {self.num_actions_p2}")
        print(f"Payoff Range: [{self.min_payoff}, {self.max_payoff}]")
        print("-" * 25)
        print("Combined Payoff Tensor (P1 Payoff, P2 Payoff):")
        print(self.payoffs)
        print("-" * 25)
        print("Player 1 Payoff Matrix:")
        print(self.player1_payoffs)
        print("-" * 25)
        print("Player 2 Payoff Matrix:")
        print(self.player2_payoffs)
        print("-" * 25)


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
    game = TwoPlayerGameGenerator(p1_actions, p2_actions, min_payoff_val, max_payoff_val)

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
