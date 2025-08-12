import re
import json


def parse_game_logs(file_path):

    try:
        with open(file_path, "r") as f:
            log_data = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return []

    rounds = []
    lines = log_data.split("\n")
    current_round_data = None
    current_interaction = None

    # Regex patterns for parsing the log file.
    # The patterns are adapted from the provided JavaScript code.
    round_regex = re.compile(r"^INFO:gaims\.gym_env:Round: (\d+)")
    utility_regex = re.compile(r"^INFO:gaims\.gym_env:Player Utility: ([\d\.\-]+)")
    # Using a non-greedy match and a lookahead to handle the multi-line payoff matrix
    payoff_regex = re.compile(
        r"^INFO:gaims\.gym_env:Payoff Matrix:\s*\n(tensor\(\[\[\[.*?\]\]\]\))",
        re.DOTALL,
    )
    interaction_start_regex = re.compile(
        r"^INFO:gaims\.agents\.models:--> (.*?): (.*?):"
    )
    # Using a non-greedy match to capture the thoughts content until the next specific log line
    thoughts_regex = re.compile(
        r"Given the current state, game rules, and your past observations, write down your thoughts, plans, and any new observations\.\nINFO:gaims\.agents\.models:.*? -->: ([\s\S]*?)(?=\nWhich action will you choose?|You may now send a message|INFO:gaims\.gym_env:Agent \d+ took action)"
    )
    message_regex = re.compile(
        r"Here are the messages you received:\nPlayer \d+ said: ([\s\S]*?)\n\nGiven these messages, game rules, and prior information,"
    )
    action_regex = re.compile(r"^INFO:gaims\.gym_env:Agent (\d+) took action (\d+)")
    reward_regex = re.compile(r"^INFO:gaims\.gym_env:Reward: tensor\(\[(.*?)\]\)")
    # The nash equilibria format is a bit tricky, so we'll handle the parsing after the match.
    nash_regex = re.compile(r"^INFO:gaims\.gym_env:Nash Equilibria: \[(.*?)\]")

    # Iterate through each line of the log data
    for i, line in enumerate(lines):
        if round_regex.match(line):
            if current_round_data:
                # If there's an ongoing interaction, save it before moving to the next round
                if current_interaction:
                    current_round_data["interactions"].append(current_interaction)
                rounds.append(current_round_data)

            # Start a new round data dictionary
            current_round_data = {
                "round": int(round_regex.match(line).group(1)),
                "player_utility": None,
                "payoff_matrix": None,
                "interactions": [],
                "actions": [],
                "reward": None,
                "nash_equilibria": None,
            }
            current_interaction = None

        if current_round_data:
            # Check for player utility
            if utility_regex.match(line):
                current_round_data["player_utility"] = float(
                    utility_regex.match(line).group(1)
                )

            # Check for payoff matrix, this might span multiple lines
            payoff_match = payoff_regex.match("\n".join(lines[i:]))
            if payoff_match:
                current_round_data["payoff_matrix"] = payoff_match.group(1)

            # Check for a new interaction starting
            interaction_match = interaction_start_regex.match(line)
            if interaction_match:
                if current_interaction:
                    current_round_data["interactions"].append(current_interaction)
                current_interaction = {
                    "player": interaction_match.group(1),
                    "role": interaction_match.group(2),
                    "thoughts": None,
                    "received_message": None,
                }

            # If an interaction is active, check for thoughts and messages
            if current_interaction:
                remaining_log = "\n".join(lines[i:])
                thoughts_match = thoughts_regex.search(remaining_log)
                if thoughts_match and not current_interaction["thoughts"]:
                    current_interaction["thoughts"] = thoughts_match.group(1).strip()

                message_match = message_regex.search(remaining_log)
                if message_match and not current_interaction["received_message"]:
                    current_interaction["received_message"] = message_match.group(
                        1
                    ).strip()

            # Check for actions
            action_match = action_regex.match(line)
            if action_match:
                current_round_data["actions"].append(
                    {
                        "player": int(action_match.group(1)),
                        "action": int(action_match.group(2)),
                    }
                )

            # Check for rewards
            reward_match = reward_regex.match(line)
            if reward_match:
                current_round_data["reward"] = [
                    float(s) for s in reward_match.group(1).split(", ")
                ]

            # Check for Nash equilibria
            nash_match = nash_regex.match(line)
            if nash_match:
                nash_string = nash_match.group(1)
                # The regex will capture something like '(0, 0), (1, 1)'
                # We split by '), (' and re-add the parentheses to get the tuples
                current_round_data["nash_equilibria"] = [
                    f"({s})" for s in nash_string.split("), (")
                ]

    # Don't forget to append the last round after the loop finishes
    if current_round_data:
        if current_interaction:
            current_round_data["interactions"].append(current_interaction)
        rounds.append(current_round_data)

    return rounds


log_file_name = "example.log"

print(f"Log data written to '{log_file_name}'.")

parsed_logs = parse_game_logs(log_file_name)

print("\n--- Parsed Logs ---")
print(json.dumps(parsed_logs, indent=2))
