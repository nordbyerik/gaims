from abc import ABC, abstractmethod
from typing import Union

# NOTE: Options for setup. 
# Contain sender reciever and message info in one Message object
# Have Message only contain the info, have cenral messages dict which managers player to player comms
# Decentralize the messages and have players track their own messages



class GameEnvironment(ABC):
  def __init__(self, players):
    self.players = players

  @abstractmethod
  def step(self):
    pass
  
  @abstractmethod
  def reset(self):
    pass
  
