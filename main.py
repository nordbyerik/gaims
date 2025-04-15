import logging
import sys
from models import Gemini
from prisoners import Player, play_repeated_dilemma

log = logging.getLogger("hot")


def main():
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler(sys.stdout))

    blue_model = Gemini("Blue")
    red_model = Gemini("Red ")

    print(
        play_repeated_dilemma(
            Player("Blue", blue_model), Player("Red ", red_model), rounds=2
        )
    )


if __name__ == "__main__":
    main()
