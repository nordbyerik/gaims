from typing import Any

class GameConfig:
    def __init__(self, 
                 num_agents: int = 2, 
                 num_rounds: int = 1, 
                 num_actions: int = 2, 
                 simulatneous: bool = True, 
                 cooperative: bool = False, 
                 stakes: str = 'neutral', 
                 framing: str = 'neutral',
                 observe: bool = False,
                 communication_type: str = False,
                 **kwargs
                 ):
        
        self.num_agents = num_agents
        self.num_actions = num_actions
        self.num_rounds = num_rounds
        self.simulatneous = simulatneous
        self.cooperative = cooperative
        self.stakes = stakes
        self.framing = framing

        self.communication_type = communication_type
        self.observe = observe

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return f"GameConfig(game_id={self.game_id}, game_name={self.game_name})"
    
    def __repr__(self):
        return self.__str__()
    
    def to_dict(self):
        return {
            'num_actions': self.num_actions,
            'num_rounds': self.num_rounds,
            'simulatneous': self.simulatneous,
            'cooperative': self.cooperative,
            'stakes': self.stakes,
            'framing': self.framing,
            'observe': self.observe,
            'communicate': self.communicate,
            'act': self.act,
        }
    
    def get(self, key, default=None):
        return self.to_dict().get(key, default)
