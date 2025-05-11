from typing import List, Dict, Any

class GamePromptTemplate():
    def __init__(self, template: Dict[str, str], action_names: List[str]):
        self.game_header = template.get('game_header', "Interaction Scenario:\n")
        self.player_header = template.get('player_header', "Evaluate your choices.\nIf you select:\n")
        self.action_header = template.get('action_header', " {player_action}, consider the potential outcomes:\n")
        self.payoff_line = template.get('payoff_line', "    Paired against {opponent_action}: Result = {payoff}")
        self.opponent_payoff = template.get('opponent_payoff', " (Opponent Result: {opponent_payoff})")

        self.observation_queue = template.get('observation_header', "Given that this is the current state of the game: {state}\n What plans and observations do you have?") 

        # TODO: Add in the ability 
        self.communication_queue = template.get('communication_header', "You may communicate with your opponent.\n")
        self.communication_queue += template.get('communication_queue', "Input your message:")

        self.newline = template.get('newline', "\n")

        self.options = template.get('options', "Which will you choose? (0 for {action_zero}, 1 for {action_one}) ")
        self.queue = template.get('queue', "Input your choice (0/1):")
    
        self.action_names = action_names


    def format_observe_context(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_intro(context['state']['payoff_dict'])
        prompt += self.template['observation_header']
        return prompt
    
    def format_observe_communication_context(self, context: Dict[str, Any]) -> str:
        pass
    def format_communicate_context(self, context: Dict[str, Any]) -> str:

        for action_index in range(self.num_actions):
            player_action = self.options[action_index]
            prompt += self.template['action_header'].format(player_action=player_action)
            for opponent_action_index in range(self.num_actions):
                opponent_action = self.options[opponent_action_index]
                payoff = payoff_dict[0, action_index, opponent_action_index] # TODO: Make this work for both players
                prompt += self.vtemplate['payoff_line'].format(
                    opponent_action=opponent_action,
                    payoff=payoff
                )
                
                if include_opponent_payoff:
                    opponent_payoff = payoff_dict[1, opponent_action_index, action_index] # TODO: Make this work for both players
                    prompt += self.template['opponent_payoff'].format(opponent_payoff=opponent_payoff)
                
                prompt += self.template['newline']

        prompt += self.template['options'].format(action_zero=self.options[0], action_one=self.options[1])
        prompt += self.template['queue']
        prompt += " "
        return prompt

    def format_action_context(self, context: Dict[str, Any]) -> str:
        pass
    

# 1. Classic Neutral / Abstract
action_names_neutral = ["Action A", "Action B"]
template_neutral = {
    'game_header': "Interaction Scenario:\n",
    'player_header': "Evaluate your choices.\nIf you select:\n",
    'action_header': " {player_action}, consider the potential outcomes:\n",
    'payoff_line': "    Paired against {opponent_action}: Result = {payoff}",
    'opponent_payoff': " (Opponent Result: {opponent_payoff})",
    'newline': "\n",
    'options': 'Which will you choose? (0 for {action_zero}, 1 for {action_one}) ',
    'queue': 'Input your choice (0/1):'
}

# 2. Business Competition
action_names_business = ["Compete Aggressively", "Cooperate on Pricing"]
template_business = {
    'game_header': "*** Market Strategy Simulation ***\n",
    'player_header': "Your Firm's Strategic Options:\n",
    'action_header': " Option: {player_action}\nWhat happens if you take this path?\n",
    'payoff_line': "    If your competitor chooses {opponent_action}, your profit is {payoff}.",
    'opponent_payoff': " (Competitor's profit: {opponent_payoff})",
    'newline': "\n",
    'options': 'Select strategy: 0 = {action_zero}, 1 = {action_one}. ',
    'queue': 'Decision (0 or 1) -> '
}

# 3. Business Investment
action_names_investment = ["Invest Heavily", "Invest Cautiously"]
template_investment = {
    'game_header': "Joint Venture Investment Decision\n",
    'player_header': "Considering your investment level:\n",
    'action_header': " If you choose to '{player_action}':\n",
    'payoff_line': "    Should your partner '{opponent_action}', your return is {payoff}.",
    'opponent_payoff': " (Partner's return: {opponent_payoff})",
    'newline': "\n",
    'options': 'Choose 0 ({action_zero}) or 1 ({action_one}) ',
    'queue': 'Investment Level (0/1): '
}

# 4. National Security / Arms Race
action_names_security = ["Increase Arms", "Maintain Status Quo"]
template_security = {
    'game_header': "Geopolitical Standoff Analysis:\n",
    'player_header': "Your nation's potential actions:\n",
    'action_header': " Policy Decision: {player_action}\nConsequences are as follows:\n",
    'payoff_line': "    Versus their choice of '{opponent_action}': National Security Index = {payoff}.",
    'opponent_payoff': " (Adversary's Index: {opponent_payoff})",
    'newline': "\n",
    'options': 'Enter 0 to {action_zero}, or 1 to {action_one}. ',
    'queue': 'Directive (0 or 1): '
}

# 5. National Security / Intelligence Sharing
action_names_intel = ["Withhold Intel", "Share Intel"]
template_intel = {
    'game_header': "Alliance Intelligence Protocol:\n",
    'player_header': "Regarding sensitive information, you could:\n",
    'action_header': " {player_action} with your ally.\nHere's the breakdown:\n",
    'payoff_line': "    If they decide to '{opponent_action}': Your strategic advantage is {payoff}.",
    'opponent_payoff': " (Ally's advantage: {opponent_payoff})",
    'newline': "\n",
    'options': 'Make your choice: 0={action_zero}, 1={action_one}? ',
    'queue': 'Decision (0 or 1): '
}

# 6. Good vs. Evil / Moral Dilemma
action_names_moral = ["Betray Trust", "Remain Loyal"]
template_moral = {
    'game_header': "A Test of Character!\n",
    'player_header': "What path will you walk? If you choose to...\n",
    'action_header': " {player_action}...\n...the consequences unfold:\n",
    'payoff_line': "    Against their choice to '{opponent_action}': Your fate yields {payoff} points.",
    'opponent_payoff': " (Their fate: {opponent_payoff} points)",
    'newline': "\n",
    'options': 'Temptation calls... Choose 0 ({action_zero}) or 1 ({action_one})! ',
    'queue': 'Your Soul\'s Choice (0 or 1): '
}

# 7. Environmental Cooperation
action_names_env = ["Pollute (High Profit)", "Protect Environment (Lower Profit)"]
template_environmental = {
    'game_header': "Global Environmental Accord:\n",
    'player_header': "Your country's environmental policy choice impacts everyone.\nIf you choose to:\n",
    'action_header': " {player_action}:\n",
    'payoff_line': "    And the other major nation chooses to '{opponent_action}': Your economic score is {payoff}.",
    'opponent_payoff': " (Their economic score: {opponent_payoff}) \n    (Note: Higher pollution negatively impacts a separate global 'Health Score')",
    'newline': "\n",
    'options': 'Policy: 0 for {action_zero}, 1 for {action_one}. ',
    'queue': 'Select Policy (0/1): '
}

# 8. Social Dilemma / Community Contribution
action_names_social = ["Free Ride", "Contribute Effort"]
template_social = {
    'game_header': "-- Community Project --\n",
    'player_header': "How much will you contribute to the shared goal?\n",
    'action_header': "If you decide to '{player_action}':\n",
    'payoff_line': "    When your partner decides to '{opponent_action}': Your personal benefit is {payoff}.",
    'opponent_payoff': " (Partner's benefit: {opponent_payoff})",
    'newline': "\n",
    'options': 'What will you do? [0: {action_zero}, 1: {action_one}] ',
    'queue': 'Your Action (0 or 1): '
}


# Consolidated Dictionary of Game Prompts
game_prompts = {
    "neutral": {
        "action_names": action_names_neutral,
        "template": template_neutral
    },
    "business_competition": {
        "action_names": action_names_business,
        "template": template_business
    },
    "business_investment": {
        "action_names": action_names_investment,
        "template": template_investment
    },
    "security_arms": {
        "action_names": action_names_security,
        "template": template_security
    },
    "security_intel": {
        "action_names": action_names_intel,
        "template": template_intel
    },
    "moral_dilemma": {
        "action_names": action_names_moral,
        "template": template_moral
    },
    "environmental": {
        "action_names": action_names_env,
        "template": template_environmental
    },
    "social_dilemma": {
        "action_names": action_names_social,
        "template": template_social
    }
}