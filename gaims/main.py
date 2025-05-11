# maigcom/main_loop.py

from typing import Any, Dict, List, Optional, Tuple

# Assuming these are defined in maigcom.definitions
from .definitions import (
    GameConfig,
    AgentConfig,
    GameAction,
    CommunicationAction,
    AggregatedObservation # Though ObservationAggregator produces this
)

# Assuming these are defined in their respective files
from .games.game import (
    Game # For _setup_agents
)

from .agents import (
    BaseAgent,          # For type hinting
    LLMAgent            # For concrete instantiation
)


class MainGameLoop:
    def __init__(self, game_config: GameConfig, agent_configs_data: List[Dict[str, Any]]):
        self.game_config = game_config
        self.agent_configs = [AgentConfig(**cfg) for cfg in agent_configs_data]

        self.current_round = 0
        self.current_phase = "" # "PLAN_COMMUNICATE", "COMMUNICATE_EXECUTE", "FINALIZE_ACTION", "POST_PROCESS"
        
        self.game = Game(self.game_config, self.agent_configs)


    def run_game(self):
        """Main loop that drives the game through rounds."""
        for r in range(self.game_config.max_rounds):
            self.current_round = r
            self.time_manager.set_current_round(r)
            print(f"\n--- Round {self.current_round + 1} ---")

            self.run_round()

            if self._check_termination_conditions():
                print("Game over: Termination conditions met.")
                break
        self._log_game_results()
        print("Game finished.")

    def run_round(self):
        """Logic for a single round with distinct phases."""
        if self.game_config['observe']:
            self.game.observe() # Update game state based on environment
        if self.game_config['communicate']:
            self.game.communicate()
        if self.game_config['act']:
            self.game.act()

            
        self.state_manager.end_of_round_update() # Passive updates to state
        self._log_round_summary()


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


if __name__ == "__main__":
    game_config = GameConfig(max_rounds=10, observe=False, communicate=False, act=True)
    game = Game()
    game.run_game()