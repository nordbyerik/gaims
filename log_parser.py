import re

def parse_game_log(log_text):
    """
    Parses the game log text and organizes it into a structured dictionary.
    
    Args:
        log_text (str): The full text of the game log.
    
    Returns:
        dict: A dictionary containing the parsed game data.
    """
    game_data = {'rounds': []}
    
    # Split the log by round. The round number is in a pattern like "Round: X"
    # We will use a regex to capture the round number and the text of the round.
    rounds_raw = re.split(r'INFO:gaims\.gym_env:Round: (\d+)\n', log_text)
    
    # The first element is everything before the first round, which we can ignore for now.
    # We iterate through the captured rounds.
    for i in range(1, len(rounds_raw), 2):
        round_number = int(rounds_raw[i])
        round_text = rounds_raw[i+1]
        
        round_data = {'round_number': round_number, 'steps': []}
        
        # Extract Player Utility and Payoff Matrix
        utility_match = re.search(r'INFO:gaims\.gym_env:Player Utility: (.*)', round_text)
        if utility_match:
            round_data['utility'] = utility_match.group(1).strip()
            
        payoff_match = re.search(r'INFO:gaims\.gym_env:Payoff Matrix:\s*\n(tensor\(.*?\))', round_text, re.DOTALL)
        if payoff_match:
            round_data['payoff_matrix'] = payoff_match.group(1).strip()

        # Split the round text by steps, marked by "**STEP**"
        steps_raw = re.split(r'INFO:gaims\.agents\.agent:\*\*STEP\*\* ==> ', round_text)
        for step_raw in steps_raw[1:]:
            step_data = {}
            
            # Use a regex to capture agent, model, action, message, and response
            # The pattern is complex due to the nested `assistantfinal` blocks
            step_match = re.search(
                r'LOGGED_AGENT: (.*?),\s*LOGGED_AGENT_MODEL: (.*?),\s*LOGGED_ACTION: (.*?),\s*LOGGED_MESSAGE: (.*?)'
                r'LOGGED_RESPONSE: (.*?)assistantfinal(.*?)', 
                step_raw, re.DOTALL
            )
            
            if step_match:
                step_data['agent'] = step_match.group(1).strip()
                step_data['model'] = step_match.group(2).strip()
                step_data['action'] = step_match.group(3).strip()
                
                # The message part needs careful cleaning
                message_content = step_match.group(4).strip()
                message_content = re.sub(r'DEBUG:.*?|INFO:.*?|assistantanalysis.*?|\n', '', message_content, flags=re.DOTALL)
                message_content = re.sub(r'Here are the messages you received:.*?Given these messages, game rules, and prior information, write down your thoughts, plans, and any new observations.,', '', message_content, flags=re.DOTALL)
                step_data['message'] = message_content.strip()

                # The log response contains the AI's internal thought process and the final action/message
                log_response_content = step_match.group(5).strip()
                analysis = re.sub(r'assistantanalysis(.*?)(?=\nINFO:gaims|$)assistantfinal', r'\1', log_response_content, flags=re.DOTALL)
                step_data['internal_analysis'] = analysis.strip()
                
                final_response = step_match.group(6).strip()
                step_data['final_response'] = final_response
                
                # Check for and extract any messages received within the step
                messages_received_match = re.search(r'Here are the messages you received:\s*(.*?)(?=Given these messages|\Z)', step_raw, re.DOTALL)
                if messages_received_match:
                    step_data['messages_received'] = messages_received_match.group(1).strip()

                round_data['steps'].append(step_data)
            
        game_data['rounds'].append(round_data)

    # Handle the final reward/utility which is after all rounds
    final_reward_match = re.search(r'INFO:gaims\.gym_env:Reward: (.*)', log_text)
    if final_reward_match:
        game_data['final_reward'] = final_reward_match.group(1).strip()
        
    return game_data

def format_markdown(game_data):
    """
    Formats the parsed game data into a collapsible markdown string.
    
    Args:
        game_data (dict): The dictionary containing parsed game data.
        
    Returns:
        str: A string formatted with collapsible markdown.
    """
    if not game_data or not game_data['rounds']:
        return "Could not parse the game log."

    markdown_output = "# Geopolitical Standoff Analysis\n\n"

    for round_data in game_data['rounds']:
        markdown_output += f"<details><summary><b>Round {round_data['round_number'] + 1}</b></summary>\n\n"

        # Add round summary if available
        if 'utility' in round_data:
            markdown_output += f"Player Utility (Cumulative): `{round_data['utility']}`\n"
        if 'payoff_matrix' in round_data:
            markdown_output += f"Payoff Matrix:\n`{round_data['payoff_matrix']}`\n"

        markdown_output += "---\n\n"

        for step in round_data['steps']:
            markdown_output += f"<details><summary><b>Step: {step.get('agent')} ({step.get('action')})</b></summary>\n\n"

            if 'messages_received' in step and step['messages_received']:
                markdown_output += "### Messages Received\n"
                markdown_output += f"```text\n{step['messages_received']}\n```\n"

            markdown_output += "### Agent Internal Analysis\n"
            markdown_output += f"```text\n{step.get('internal_analysis', 'No internal analysis.')}\n```\n"

            if 'final_response' in step and step['final_response']:
                markdown_output += "### Final Response\n"
                markdown_output += f"```text\n{step['final_response']}\n```\n"

            markdown_output += "</details>\n\n"

        markdown_output += "</details>\n\n"

    if 'final_reward' in game_data:
        markdown_output += f"### Game End\nFinal Reward: `{game_data['final_reward']}`\n"

    return markdown_output


def format_markdown(game_data):
    """
    Formats the parsed game data into a collapsible markdown string.
    
    Args:
        game_data (dict): The dictionary containing parsed game data.
        
    Returns:
        str: A string formatted with collapsible markdown.
    """
    if not game_data:
        return "Could not parse the game log."

    markdown_output = "# Geopolitical Standoff Analysis\n\n"

    for round_data in game_data['rounds']:
        markdown_output += f"<details><summary><b>Round {round_data['round_number'] + 1}</b></summary>\n\n"

        # Add round summary if available
        if 'utility' in round_data:
            markdown_output += f"- Player Utility: `{round_data['utility']}`\n"
        if 'payoff_matrix' in round_data:
            markdown_output += f"- Payoff Matrix: `{round_data['payoff_matrix']}`\n"

        for step in round_data['steps']:
            markdown_output += f"<details><summary><b>Step: {step['agent']} ({step['action']})</b></summary>\n\n"

            if 'messages_received' in step and step['messages_received']:
                markdown_output += f"### Messages Received\n"
                markdown_output += f"```text\n{step['messages_received']}\n```\n"

            markdown_output += f"### Agent Internal Analysis\n"
            markdown_output += f"```text\n{step['internal_analysis']}\n```\n"

            if 'final_response' in step and step['final_response']:
                markdown_output += f"### Final Response\n"
                markdown_output += f"```text\n{step['final_response']}\n```\n"

            markdown_output += "</details>\n\n"

        markdown_output += "</details>\n\n"

    return markdown_output


def main():

    with open("example.log", "r") as f:
        log_text = f.read()

    parsed_data = parse_game_log(log_text)
    formatted_output = format_markdown(parsed_data)

    with open("example.md", "w") as f:
        f.write(formatted_output)


if __name__ == "__main__":
    main()
