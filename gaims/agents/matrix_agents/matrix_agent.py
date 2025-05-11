from agents.agent import LLMAgent
from typing import Dict, Any, List
from agents.models import Model

from agents.agent import AgentConfig

def to_prompt(self, payoff_dict, include_opponent_payoff=False):

    prompt = self.template['game_header']
    prompt += self.template['player_header']
    
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
class MatrixAgentConfig(AgentConfig):
    def __init__(self, id: str, persona: str, tags: List[str], options: List[str], values: List[List[int]]):
        super().__init__(id, persona, tags)
        self.options = options                          
        self.values = values

class MatrixAgent(LLMAgent):
    def __init__(self, agent_config: MatrixAgentConfig, model: Model):
        super().__init__(agent_config, model)

        self.options = agent_config.options
        self.values = agent_config.values
        self.num_actions = len(self.options)
        self.template = self.load_template('matrix_agent')

    
    def prompt_intro(self, payoff_dict, include_opponent_payoff=False):
        prompt = self.template.game_header
        prompt += self.template.player_header
        return prompt

