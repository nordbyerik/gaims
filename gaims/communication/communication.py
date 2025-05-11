from abc import ABC, abstractmethod
from typing import Union

import random

class Message():
  def __init__(self, sender, receiver, message, id):
    self.sender = sender
    self.receiver = receiver
    self.message = message

    self.recieved = False
    self.id = id


class CommunicationMedium(ABC):
  def __init__(self, adjacency_list):
    self.adjacency_list = adjacency_list
    self.messages = {}
    self.message_history = []
    self.message_count = 0

  def send_message(self, sender: str, receiver: str, message: str):
    message = Message(sender, receiver, message, self.message_count)
    self.message_count += 1

    if sender not in self.messages:
      self.messages[sender] = {}
    if receiver not in self.mesages[sender]:
      self.messages[sender][receiver] = []

    self.messages[sender][receiver].append(message)
    self.message_history.append((sender, receiver, message))

  def broadcast_message(self, message, sender):
    for receiver in self.adjacency_list[sender]:
      self.send_message(message, sender, receiver)

  def get_messages(self, agent):
    if agent not in self.messages:
      return {}
    
    messages = self.messages[agent]
    self.messages[agent] = {}
    return messages

  def clear_messages(self):
    self.messages = {}


class FullyConnectedCommunicationMedium(CommunicationMedium):
  def __init__(self, agents):
    adjacency_list = {agent: agents for agent in agents}
    super().__init__(adjacency_list)


class SparseCommunicationMedium(CommunicationMedium):
  def __init__(self, agents):
    # Randomly connect agents
    adjacency_list = {agent: [random.choice(agents) for _ in range(random.randint(1, len(agents)))] for agent in agents}
    super().__init__(adjacency_list)


class LinearCommunicationMedium(CommunicationMedium):
  def __init__(self, agents):
    adjacency_list = {agent: [agents[i+1]] if i < len(agents) - 1 else [] for i, agent in enumerate(agents)}
    super().__init__(adjacency_list)

class RingCommunicationMedium(CommunicationMedium):
  def __init__(self, agents):
    adjacency_list = {agent: [agents[(i+1) % len(agents)]] for i, agent in enumerate(agents)}
    super().__init__(adjacency_list)

class StarCommunicationMedium(CommunicationMedium):
  def __init__(self, agents):
    center_agent = agents[0]
    adjacency_list = {agent: [center_agent] for agent in agents}
    adjacency_list[center_agent] = agents[1:]
    super().__init__(adjacency_list)









