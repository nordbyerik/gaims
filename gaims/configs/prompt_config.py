from abc import ABC
from typing import Dict, List, Any, Optional


class PromptConfig(ABC):
    def __init__(self, template: Dict[str, str], action_names: List[str], agent_names: List[str]):

        self.system_prompt = template.get('system_prompt', "You are an AI agent participating in a game.")

        self.game_header = template.get('game_header', "You are participating in a game.\n")

        # Player and Round Information (for general intro)
        self.players_info_header = template.get('players_info_header', "There are {num_players} players in total.\n")
        self.agent_identity_header = template.get('agent_identity_header', "You are player {agent_id}.\n")
        self.finite_rounds_header = template.get('finite_rounds_header', "You will play {rounds} rounds in total.\n")
        # For finite games with current round:
        self.round_header = template.get('round_header', "It is currently round {round_number} of {total_rounds_str}.\n")
        self.infinite_rounds_header = template.get('infinite_rounds_header', "You will play an unknown or very large number of rounds.\n")
        self.single_round_header = template.get('single_round_header', "You will play a single round.\n")
        # For infinite/unknown total rounds, but current round known:
        self.current_round_info = template.get('current_round_info', "This is round {current_round}.\n")


        # Communication Rules (for general intro)
        self.communication_allowed_specific = template.get('communication_allowed_specific', "You will be allowed to communicate with the following players: {communication_partners}.\n")
        self.communication_allowed_all = template.get('communication_allowed_all', "You will be allowed to communicate with all other players.\n")
        self.communication_not_allowed = template.get('communication_not_allowed', "You cannot communicate with any other players.\n")

        # Observation Formatting (for general intro and specific observation steps)
        self.observation_format = template.get('observation_format', "Your prior observations: {observations}\n")
        
        # Payoff Rules Templates (used in _format_payoff_rules)
        # Note: The original snippet had a self.player_header for payouts that was overwritten.
        # We introduce a specific template for the payoff section header.
        self.payoff_section_header = template.get('payoff_section_header', "Payoff Details (for you, Player {agent_id}):\n")
        # These are from the original "Action section"
        self.action_header = template.get('action_header', "  If you choose {player_action}, your potential outcomes are:\n")
        self.payoff_line = template.get('payoff_line', "    - Paired against another player's action {opponent_action}: Your Result = {payoff}")
        # self.opponent_payoff template is no longer used to maintain N-player generality easily.

        # Action Query Templates (used in format_action_context)
        self.action_query = template.get('action_query', "Which action will you choose? ")
        self.action_option_format = template.get('action_option_format', "{index} for {action_name}")
        self.action_cue = template.get('action_cue', "Input your choice (number):")

        # Observation Step
        self.observation_step_header = template.get('observation_step_header', "Current game state: {state}\n")
        self.observation_step_cue = template.get('observation_step_cue', "Given the current state, game rules, and your past observations, write down your thoughts, plans, and any new observations.")

        # Communication Step
        self.communication_step_header = template.get('communication_step_header', "You may now send a message. You can send to: {adjacency_list}\n")
        self.communication_step_cue = template.get('communication_step_cue', "Enter your message (or leave blank for no message):")

        # Communication Observation Step
        self.communication_observation_step_header = template.get('communication_observation_step_header', "Here are the messages you received:\n")
        self.communication_observation_message_line = template.get('communication_observation_message_line', "Player {sender} said: {message}\n")
        self.communication_observation_step_cue = template.get('communication_observation_step_cue', "Given these messages, game rules, and prior information, write down your thoughts, plans, and any new observations.")

        self.newline = template.get('newline', "\n")

        self.action_names = action_names
        self.agent_names = agent_names

    
    def _format_payoff_rules(self, context: Dict[str, Any]) -> str:
        """
        Formats the game's payoff rules for the current player.
        Context keys used:
        - agent_id (int)
        - state (Dict): Must contain 'payoff_matrix'.
            - state['payoff_matrix'] (list/array-like): agent_idx, own_action_idx, other_player_action_idx
        - action_names (List[str]): From self.action_names
        """
        rules_prompt = ""
        agent_id = context.get('agent_id')
        payoff_matrix = context.get('state', {}).get('payoff_matrix')
        num_players = context.get('num_players')

        if agent_id is None:
            rules_prompt += "Your player ID is not specified, so personalized payoff rules cannot be shown.\n"
            return rules_prompt
        
        player_descriptor = f"{self.agent_names[agent_id]}"
        rules_prompt += self.payoff_section_header.format(agent_id=player_descriptor)

        if payoff_matrix is None:
            rules_prompt += "Payoff matrix is currently unavailable.\n"
            return rules_prompt
        
        try:
            num_player_actions = len(self.action_names)
            num_opponent_actions = len(self.action_names) 

            for player_action_idx in range(num_player_actions):
                player_action_name = self.action_names[player_action_idx]
                rules_prompt += self.action_header.format(player_action=player_action_name)

                for opponent_action_idx in range(num_opponent_actions):
                    opponent_action_name = self.action_names[opponent_action_idx]
                    try:
                        # Direct indexing for list of lists or numpy array
                        own_payoff = payoff_matrix[agent_id][player_action_idx][opponent_action_idx]
                    except IndexError:
                        own_payoff = "N/A (IndexError)"
                    except TypeError: # E.g. if payoff_matrix is not subscriptable as expected
                        own_payoff = "N/A (TypeError)"
                        # Break inner loop if matrix structure is unexpected for further opponent actions
                        rules_prompt += f"    - Error accessing payoff for opponent action {opponent_action_name}\n"
                        break 
                    
                    rules_prompt += self.payoff_line.format(
                        opponent_action=opponent_action_name,
                        payoff=own_payoff
                    )
                rules_prompt += self.newline # Add a newline after all outcomes for a player_action
            
        except Exception as e:
            rules_prompt += f"Could not display full payoff rules due to an error: {e}\n"
        
        return rules_prompt + self.newline


    def prompt_intro(self, context: Dict[str, Any]) -> str:
        """
        Generates the introductory part of the prompt, common to all steps.
        Now includes payoff rules.
        """
        prompt = self.game_header

        # Player information
        if 'num_players' in context:
            prompt += self.players_info_header.format(num_players=context['num_players'])
        if 'agent_id' in context:
            prompt += self.agent_identity_header.format(agent_id=context['agent_id'])

        # Round information
        num_rounds = context.get('num_rounds')
        current_round = context.get('current_round')

        if num_rounds == 1:
            prompt += self.single_round_header
        elif current_round is not None:
            if num_rounds == float('inf') or num_rounds is None: # Treat None as potentially infinite
                prompt += self.infinite_rounds_header
                prompt += self.current_round_info.format(current_round=current_round)
            elif num_rounds > 1:
                prompt += self.finite_rounds_header.format(rounds=num_rounds)
                prompt += self.round_header.format(round_number=current_round, total_rounds_str=str(num_rounds))
        elif num_rounds == float('inf') or num_rounds is None: # If only total rounds info is available (no current round yet)
             prompt += self.infinite_rounds_header
        elif num_rounds > 1: # Finite rounds but no current round info
            prompt += self.finite_rounds_header.format(rounds=num_rounds)


        # Communication information
        if context.get('can_communicate_all', False):
            prompt += self.communication_allowed_all
        elif context.get('communication_partners'):
            partners_str = ", ".join(map(str, context['communication_partners']))
            prompt += self.communication_allowed_specific.format(communication_partners=partners_str)
        else:
            prompt += self.communication_not_allowed
        
        prompt += self.newline
        
        # Game Rules / Payoff Matrix
        prompt += self._format_payoff_rules(context)
        
        # Past observations
        observations = context.get('agent_observations', "You have no prior observations for this game.")
        prompt += self.observation_format.format(observations=observations)
        prompt += self.newline
        return prompt

    def format_observe_context(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_intro(context)
        prompt += self.observation_step_header.format(state=context.get('state_summary', context.get('state', 'The current state is not specified.'))) # Added state_summary option
        prompt += self.observation_step_cue
        return prompt, self.system_prompt

    def format_observe_communication_context(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_intro(context)
        prompt += self.communication_observation_step_header
        
        messages_received_str = ""
        if 'messages' in context and context['messages']:
            # Assuming messages is Dict[sender_id, List[MessageObject]] or similar
            # For flexibility, let's iterate if it's a list of messages or a dict of lists
            if isinstance(context['messages'], dict):
                all_messages = []
                for msg_list in context['messages'].values():
                    all_messages.extend(msg_list)
            elif isinstance(context['messages'], list):
                all_messages = context['messages']
            else:
                all_messages = []

            if not all_messages:
                 messages_received_str = "You have received no new messages this round." + self.newline
            else:
                for msg_obj in all_messages: # Assuming msg_obj has .sender and .message
                    sender_display = getattr(msg_obj, 'sender', 'Unknown sender') 
                    message_text = getattr(msg_obj, 'message', 'Empty or invalid message')
                    messages_received_str += self.communication_observation_message_line.format(
                        sender=sender_display, message=message_text
                    )
        else:
            messages_received_str = "You have received no messages." + self.newline

        prompt += messages_received_str
        prompt += self.newline
        prompt += self.communication_observation_step_cue
        return prompt, self.system_prompt

    def format_communicate_context(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_intro(context)
        adjacency_display = "relevant players/groups" 
        if 'adjacency_list' in context:
            if isinstance(context['adjacency_list'], list) and context['adjacency_list']:
                adjacency_display = ", ".join(map(str, context['adjacency_list']))
            elif isinstance(context['adjacency_list'], str) and context['adjacency_list']: # If it's already a string
                 adjacency_display = context['adjacency_list']
            elif not context['adjacency_list']: # Empty list
                adjacency_display = "no one specific (broadcast may be possible if supported)"


        prompt += self.communication_step_header.format(adjacency_list=adjacency_display)
        prompt += self.communication_step_cue
        return prompt, self.system_prompt

    def format_action_context(self, context: Dict[str, Any]) -> str:
        """
        Formats the prompt for the action selection step.
        Payoff rules are now included via prompt_intro.
        """
        prompt = self.prompt_intro(context)
        prompt += self.action_query
        
        options_str_parts = []
        if not self.action_names:
            prompt += "No actions are defined." + self.newline
        else:
            for i, name in enumerate(self.action_names):
                options_str_parts.append(self.action_option_format.format(index=i, action_name=name))
            prompt += "(" + ", ".join(options_str_parts) + ")" + self.newline
        
        prompt += self.action_cue
        prompt += " " 
        return prompt, self.system_prompt
    

# 1. Classic Neutral / Abstract
action_names_neutral = ["Action A", "Action B"]
agent_names_neutral = ["Player 1", "Player 2"]
template_neutral = {
    'game_header': "Interaction Scenario:\n",
    'player_header': "Evaluate your choices.\nIf you select:\n",
    'action_header': " {player_action}, consider the potential outcomes:\n",
    'payoff_line': "    Paired against {opponent_action}: Result = {payoff}",
    'opponent_payoff': " (Opponent Result: {opponent_payoff})",
    'newline': "\n",
    'options': 'Which will you choose? (0 for {action_zero}, 1 for {action_one}) ',
    'cue': 'Input your choice (0/1):'
}

# 2. Business Competition
action_names_business = ["Compete Aggressively", "Cooperate on Pricing"]
agent_names_business = ["Firm A", "Firm B"]
template_business = {
    'game_header': "*** Market Strategy Simulation ***\n",
    'player_header': "Your Firm's Strategic Options:\n",
    'action_header': " Option: {player_action}\nWhat happens if you take this path?\n",
    'payoff_line': "    If your competitor chooses {opponent_action}, your profit is {payoff}.",
    'opponent_payoff': " (Competitor's profit: {opponent_payoff})",
    'newline': "\n",
    'options': 'Select strategy: 0 = {action_zero}, 1 = {action_one}. ',
    'cue': 'Decision (0 or 1) -> '
}

# 3. Business Investment
action_names_investment = ["Invest Heavily", "Invest Cautiously"]
agent_names_investment = ["Investor A", "Investor B"]
template_investment = {
    'game_header': "Joint Venture Investment Decision\n",
    'player_header': "Considering your investment level:\n",
    'action_header': " If you choose to '{player_action}':\n",
    'payoff_line': "    Should your partner '{opponent_action}', your return is {payoff}.",
    'opponent_payoff': " (Partner's return: {opponent_payoff})",
    'newline': "\n",
    'options': 'Choose 0 ({action_zero}) or 1 ({action_one}) ',
    'cue': 'Investment Level (0/1): '
}

# 4. National Security / Arms Race
action_names_security = ["Increase Arms", "Maintain Status Quo"]
agent_names_security = ["Nation A", "Nation B"]
template_security = {
    'game_header': "Geopolitical Standoff Analysis:\n",
    'player_header': "Your nation's potential actions:\n",
    'action_header': " Policy Decision: {player_action}\nConsequences are as follows:\n",
    'payoff_line': "    Versus their choice of '{opponent_action}': National Security Index = {payoff}.",
    'opponent_payoff': " (Adversary's Index: {opponent_payoff})",
    'newline': "\n",
    'options': 'Enter 0 to {action_zero}, or 1 to {action_one}. ',
    'cue': 'Directive (0 or 1): '
}

# 5. National Security / Intelligence Sharing
action_names_intel = ["Withhold Intel", "Share Intel"]
agent_names_intel = ["Alliance A", "Alliance B"]
template_intel = {
    'game_header': "Alliance Intelligence Protocol:\n",
    'player_header': "Regarding sensitive information, you could:\n",
    'action_header': " {player_action} with your ally.\nHere's the breakdown:\n",
    'payoff_line': "    If they decide to '{opponent_action}': Your strategic advantage is {payoff}.",
    'opponent_payoff': " (Ally's advantage: {opponent_payoff})",
    'newline': "\n",
    'options': 'Make your choice: 0={action_zero}, 1={action_one}? ',
    'cue': 'Decision (0 or 1): '
}

# 6. Good vs. Evil / Moral Dilemma
action_names_moral = ["Betray Trust", "Remain Loyal"]
agent_names_moral = ["The Hero", "The Villain"]
template_moral = {
    'game_header': "A Test of Character!\n",
    'player_header': "What path will you walk? If you choose to...\n",
    'action_header': " {player_action}...\n...the consequences unfold:\n",
    'payoff_line': "    Against their choice to '{opponent_action}': Your fate yields {payoff} points.",
    'opponent_payoff': " (Their fate: {opponent_payoff} points)",
    'newline': "\n",
    'options': 'Temptation calls... Choose 0 ({action_zero}) or 1 ({action_one})! ',
    'cue': 'Your Soul\'s Choice (0 or 1): '
}

# 7. Environmental Cooperation
action_names_env = ["Pollute (High Profit)", "Protect Environment (Lower Profit)"]
agent_names_env = ["Country A", "Country B"]
template_environmental = {
    'game_header': "Global Environmental Accord:\n",
    'player_header': "Your country's environmental policy choice impacts everyone.\nIf you choose to:\n",
    'action_header': " {player_action}:\n",
    'payoff_line': "    And the other major nation chooses to '{opponent_action}': Your economic score is {payoff}.",
    'opponent_payoff': " (Their economic score: {opponent_payoff}) \n    (Note: Higher pollution negatively impacts a separate global 'Health Score')",
    'newline': "\n",
    'options': 'Policy: 0 for {action_zero}, 1 for {action_one}. ',
    'cue': 'Select Policy (0/1): '
}

# 8. Social Dilemma / Community Contribution
action_names_social = ["Free Ride", "Contribute Effort"]
agent_names_social = ["You", "Partner"]
template_social = {
    'game_header': "-- Community Project --\n",
    'player_header': "How much will you contribute to the shared goal?\n",
    'action_header': "If you decide to '{player_action}':\n",
    'payoff_line': "    When your partner decides to '{opponent_action}': Your personal benefit is {payoff}.",
    'opponent_payoff': " (Partner's benefit: {opponent_payoff})",
    'newline': "\n",
    'options': 'What will you do? [0: {action_zero}, 1: {action_one}] ',
    'cue': 'Your Action (0 or 1): '
}


# Consolidated Dictionary of Game Prompts
game_prompts = {
    "neutral": PromptConfig(template_neutral, action_names_neutral),
    "business_competition": PromptConfig(template_business, action_names_business),
    "business_investment": PromptConfig(template_investment, action_names_investment),
    "security_arms": PromptConfig(template_security, action_names_security),
    "security_intel": PromptConfig(template_intel, action_names_intel),
    "moral_dilemma": PromptConfig(template_moral, action_names_moral),
    "environmental": PromptConfig(template_environmental, action_names_env),
    "social_dilemma": PromptConfig(template_social, action_names_social)
}