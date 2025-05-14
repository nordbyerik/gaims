from abc import ABC, abstractmethod
from typing import List, Dict, Any
class Action(ABC):
    def __init__(self, agent_id: int, action_id: int, values: List[float] = None):
        self.agent_id = agent_id
        self.action_id = action_id