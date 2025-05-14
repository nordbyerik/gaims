from typing import Any, List

# Assuming these are defined in maigcom.definitions
from configs.game_config import GameConfig
from configs.agent_config import AgentConfig

from games.game import Game # For _setup_agents
from agents.models import ModelConfig 
from games.matrix_games.matrix_game import MatrixGameState
from games.resource_sharing.resource_sharing_game import ResourceSharingGameState
from games.negotiation.negotiation_game import NegotiationGameState

from dotenv import load_dotenv
import logging
logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

logger = logging.getLogger(__name__)

load_dotenv()

class MainGameLoop:
    def __init__(self, game_config: GameConfig, agent_configs: List[AgentConfig], matrix_game_state: MatrixGameState):
        self.game_config = game_config
        self.agent_configs = agent_configs
        self.matrix_game_state = matrix_game_state

        self.current_round = 0
        
        self.game = Game(self.game_config, self.agent_configs, matrix_game_state)


    def run_game(self):
        """Main loop that drives the game through rounds."""
        for r in range(self.game_config.num_rounds):
            self.current_round = r
            print(f"\n--- Round {self.current_round + 1} ---")

            self.run_round()

            if self._check_termination_conditions():
                print("Game over: Termination conditions met.")
                break
        self._log_game_results()
        print("Game finished.")

    def run_round(self):
        """Logic for a single round with distinct phases."""
        if self.game_config.observe:
            self.game.observe() # Update game state based on environment
        if self.game_config.communicate:
            self.game.communicate()
        if self.game_config.act:
            self.game.act()
            


    def _check_termination_conditions(self) -> bool:
        # Example: Check win/loss conditions based on state_manager.get_ground_truth_state()
        # or if max rounds reached.
        if self.current_round >= self.game_config.max_rounds - 1:
            return True
        # Add other game-specific termination logic here
        return False

    def _log_round_summary(self):
        # Implement logging for research purposes if needed
        # e.g., print current scores, key state variables
        print("\n--- Round Summary ---")
        pass

    def _log_game_results(self):
        print("\n--- Game Results ---")
        # Summarize game outcome, final scores, etc.
        # final_state = self.state_manager.get_ground_truth_state()
        # print(f"Final State: {final_state}")
        pass

# TODO:

# Things to make variable:
    # Commmunication topologies
    # Amount of knowledge past to agents
    # The agent personas
    # Which steps are taken (i.e. skip communication)
    # Method of conversation (i.e. number of rounds)
    # Whether logits/actual stuff is used

# Make interoperable with stuff like OpenSpiel and Gymnasium

from configs.prompt_config import game_prompts
if __name__ == "__main__":
    game_config = GameConfig(num_rounds=10, num_actions=2, num_agents=2, game_type="matrix_game", observe=True, communicate=True, act=True)
    
    game_prompt = game_prompts.get("neutral")
    agent_configs = [
        AgentConfig(id=0, prompt_config=game_prompt, model_config=ModelConfig(model_name="microsoft/Phi-3-mini-4k-instruct")), 
        AgentConfig(id=1, prompt_config=game_prompt, model_config=ModelConfig(model_name="microsoft/Phi-3-mini-4k-instruct"))
    ]

    if game_config.game_type == "matrix_game":
        game_state = MatrixGameState(game_config)
    elif game_config.game_type == "resource_sharing":
        game_state = ResourceSharingGameState(game_config)
    elif game_config.game_type == "negotiation":
        game_state = NegotiationGameState(game_config)

    game = MainGameLoop(game_config, agent_configs, game_state)
    game.run_game()