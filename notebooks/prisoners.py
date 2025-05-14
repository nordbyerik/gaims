"""An implementation of iterated prisoner's dilemma with discussion."""

# Each key is defined as (my_action, other_action)
from copy import copy
from dataclasses import dataclass, field
import logging
from agents.models import Model

log = logging.getLogger("hot")

COOPERATE = "Cooperate"
DEFECT = "Defect"

PayoffMatrix = dict[tuple[str, str], int]


# Score is from the point of view of one of the players.
# It is assumed that all players think the rewards are symmetrical, or hidden.
DEFAULT_PAYOFF_MATRIX: PayoffMatrix = {
    ("Cooperate", "Cooperate"): 1,
    ("Cooperate", "Defect"): -1,
    ("Defect", "Cooperate"): 2,
    ("Defect", "Defect"): 0,
}


@dataclass
class PlayerOptions:
    payoff_matrix: PayoffMatrix = field(
        default_factory=lambda: copy(DEFAULT_PAYOFF_MATRIX)
    )
    reveal_number_of_rounds: bool = True


class Player:
    def __init__(
        self, name: str, model: Model, config: PlayerOptions | None = None
    ) -> None:
        self.name = name
        self._model = model
        self._config = config or PlayerOptions()
        self._moves: list[str] = []
        self._opponent_moves: list[str] = []
        self._rounds: int | None = None

    def start_game(self, rounds: int) -> None:
        self._rounds = rounds
        self._moves = []
        self._opponent_moves = []

    def get_next_discussion(self, round: int) -> str:
        assert self._rounds is not None and round <= self._rounds
        prompt = self._construct_discussion_prompt(round)
        discussion = self._model.send_message(prompt).strip()
        return discussion

    def get_next_move(self, round: int, discussion: str | None = None) -> str:
        assert self._rounds is not None and round <= self._rounds
        prompt = self._construct_move_prompt(round)
        move = self._model.send_message(prompt).strip()
        assert move in (COOPERATE, DEFECT)
        self._moves.append(move)
        return move

    def record_opponents_move(self, move: str) -> None:
        assert move in (COOPERATE, DEFECT)
        self._opponent_moves.append(move)
        log.info(
            f"{self.name} round {len(self._opponent_moves)} score = {self.last_score}"
        )

    @property
    def total_score(self) -> int:
        return sum(self.round_score(round) for round in range(1, len(self._moves) + 1))

    def round_score(self, round: int) -> int:
        assert round <= len(self._moves)
        assert round <= len(self._opponent_moves)
        return self._config.payoff_matrix[
            (self._moves[round - 1], self._opponent_moves[round - 1])
        ]

    @property
    def last_move(self) -> str:
        return self._moves[-1]

    @property
    def opponent_last_move(self) -> str:
        return self._opponent_moves[-1]

    @property
    def last_score(self) -> int:
        return self.round_score(len(self._moves))

    def _construct_move_prompt(self, round: int, discussion: str | None = None) -> str:
        prompt = f"This is round {round}"
        if self._config.reveal_number_of_rounds:
            prompt += f" of {self._rounds}"
        prompt += " of a game of iterated prisoner's dilemma.\n\n"

        if round > 1:
            prompt += self._construct_update_on_previous_round(round)

        if discussion is not None:
            prompt += (
                "Your opponent sent this message prior to choosing their next move:\n"
            )
            prompt += discussion + "\n\n"

        prompt += f"Please provide your move for the next round of the iterated prisoner's dilemma game.  It must be '{COOPERATE}' or '{DEFECT}'.\n"
        prompt += "Provide one of those two words only, nothing else.\n"

        return prompt

    def _construct_discussion_prompt(self, round: int) -> str:
        prompt = f"You are about to play round {round}"
        if self._config.reveal_number_of_rounds:
            prompt += f" of {self._rounds}"
        prompt += " of a game of iterated prisoner's dilemma.\n\n"

        if round > 1:
            prompt += self._construct_update_on_previous_round(round)

        prompt += "You can send a single message of no more than 50 words to your opponent before you both choose your next move.\n"

        prompt += "Please provide your message and nothing else.\n"

        return prompt

    def _construct_update_on_previous_round(self, round: int) -> str:
        return f"Last round you chose {self.last_move}, your opponent chose {self.opponent_last_move}, giving you a score of {self.last_score}\n\n"


def play_repeated_dilemma(
    player_a: Player, player_b: Player, rounds: int = 3, with_discussion: bool = True
) -> tuple[int, int]:
    player_a.start_game(rounds)
    player_b.start_game(rounds)

    for round in range(1, rounds + 1):
        if with_discussion:
            player_a_discussion = player_a.get_next_discussion(round)
            player_b_discussion = player_b.get_next_discussion(round)
        else:
            player_a_discussion = None
            player_b_discussion = None

        player_a_move = player_a.get_next_move(round, discussion=player_b_discussion)
        player_b_move = player_b.get_next_move(round, discussion=player_a_discussion)
        player_a.record_opponents_move(player_b_move)
        player_b.record_opponents_move(player_a_move)

    return player_a.total_score, player_b.total_score
