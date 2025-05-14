from typing import List, Dict, Any, Tuple
from abc import ABC
import torch

class PromptConfig(ABC):
    # TODO: Set this up for generalized games
    def __init__(self, template: Dict[str, str], action_names: List[str]):
        self.game_header = template.get('game_header', "Interaction Scenario:\n")

        # Action section
        self.player_header = template.get('player_header', "Evaluate your choices.\nIf you select:\n")
        self.action_header = template.get('action_header', " {player_action}, consider the potential outcomes:\n")
        self.payoff_line = template.get('payoff_line', "    Paired against {opponent_action}: Result = {payoff}")
        self.opponent_payoff = template.get('opponent_payoff', " (Opponent Result: {opponent_payoff})")
        self.options = template.get('options', "Which will you choose? (0 for {action_zero}, 1 for {action_one}) ")
        self.cue = template.get('cue', "Input your choice (0/1):")

        # Observation section
        self.observation_header = template.get('observation_header', "Here is the current state of the game: {state}\n ") 
        self.observation_cue = template.get('observation_cue', "Given that, write down your plans and observations.")
        self.observation_format = template.get('observation_format', "Here are the prior observations you've made: {observations}\n")

        # Communication section
        self.communication_header = template.get('communication_header', "You may send a message to others. You can choose from this list of: {adjacency_list}\n")
        self.communication_cue = template.get('communication_cue', "Input your message:")

        # Communication observation section
        self.communication_observation_header = template.get('communication_observation_header', "Here are what your opponents said:\n")
        self.communication_observation_message_line = template.get('communication_observation_message_line', "Player {sender} said: {message}\n ")
        self.communication_observation_cue = template.get('communication_observation_cue', "Given that, write down your plans and observations.")

        self.newline = template.get('newline', "\n")

        self.action_names = template.get('action_names', ["Cooperate", "Defect"])
    

    def prompt_intro(self, context) -> str:
        prompt = self.game_header
        prompt += self.observation_format.format(observations=context['agent_observations'])
        return prompt
    

    def format_observe_context(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_intro(context)
        prompt += self.observation_header.format(state=context['state'])
        prompt += self.observation_cue
        return prompt
    
    def format_observe_communication_context(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_intro(context)
        
        prompt += self.communication_observation_header
                                                               
        
        messages = ""
        for idx, message in context['messages'].items():
            for msg in message:
                messages += self.communication_observation_message_line.format(
                    sender=msg.sender, receiver=msg.receiver, message=msg.message
                    ) + self.newline

        prompt += self.communication_observation_cue
        return prompt

    def format_communicate_context(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_intro(context)
        prompt += self.communication_header.format(adjacency_list=context['adjacency_list'])
        prompt += self.communication_cue
        return prompt

    def format_action_context(self, context: Dict[str, Any]) -> str:
        prompt = self.prompt_intro(context)
        for action_index in range(context['num_actions']):
            player_action = self.action_names[action_index]
            prompt += self.action_header.format(player_action=player_action)
            for opponent_action_index in range(context['num_actions']):
                opponent_action = self.action_names[opponent_action_index]
                payoff = torch.tensor(context['state']['payoff_matrix'])[0, action_index, opponent_action_index] # TODO: Make this work for both players
                prompt += self.payoff_line.format(
                    opponent_action=opponent_action,
                    payoff=payoff
                )
                
                opponent_payoff = context['state']['payoff_matrix'][1, opponent_action_index, action_index] # TODO: Make this work for both players
                prompt += self.opponent_payoff.format(opponent_payoff=opponent_payoff)
                
                prompt += self.newline

        prompt += self.options.format(action_zero=self.action_names[0], action_one=self.action_names[1])
        prompt += self.cue
        prompt += " "
        return prompt
    

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
    'cue': 'Input your choice (0/1):'
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
    'cue': 'Decision (0 or 1) -> '
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
    'cue': 'Investment Level (0/1): '
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
    'cue': 'Directive (0 or 1): '
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
    'cue': 'Decision (0 or 1): '
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
    'cue': 'Your Soul\'s Choice (0 or 1): '
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
    'cue': 'Select Policy (0/1): '
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