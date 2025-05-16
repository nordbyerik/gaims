from abc import ABC, abstractmethod
from typing import Union, List, Dict, Tuple, Any
import random

class Message():
  def __init__(self, sender: str, receiver: str | List[str], message_content: str, id: int = None):
    self.sender = sender
    self.receiver = receiver
    self.message = message_content # Renamed to avoid confusion if 'message' is a Message object
    self.received = False 
    self.id = id

  def __eq__(self, other: Any) -> bool:
    if not isinstance(other, Message):
      return NotImplemented
    return (self.sender == other.sender and
            self.receiver == other.receiver and
            self.message == other.message and
            self.id == other.id)

  def __repr__(self) -> str:
    return (f"Message(sender='{self.sender}', receiver='{self.receiver}', "
            f"message='{self.message}', id={self.id}, received={self.received})")

class CommunicationMedium(ABC):
  def __init__(self, adjacency_list: Dict[str, List[str]]):
    self.adjacency_list = adjacency_list
    # Stores messages keyed by sender, then by receiver: {sender: {receiver: [MessageObjects]}}
    self.messages = {}
    self.message_history: List[Tuple[str, str, Message]] = []
    self.message_count: int = 0

  def send_message(self, sender: str, receiver: str | List[str], message_content: str) -> Message:
    """
    Creates and stores a message from sender to receiver.
    The message is stored in self.messages, retrievable by an agent acting as a receiver.
    """
    msg_obj = Message(sender, receiver, message_content, self.message_count)
    self.message_count += 1

    # Ensure sender's entry exists
    if sender not in self.messages:
      self.messages[sender] = {}
    # Ensure receiver's list exists under the sender
    if isinstance(receiver, list):
      for rec in receiver:
        if rec not in self.messages[sender]: 
          self.messages[sender][rec] = []
        self.messages[sender][rec].append(msg_obj)
    elif receiver not in self.messages[sender]:
        if receiver not in self.messages[sender]:
          self.messages[sender][receiver] = []
        self.messages[sender][rec].append(msg_obj)


    self.message_history.append((sender, receiver, msg_obj)) # Store the actual message object
    return msg_obj

  def broadcast_message(self, sender: str, message_content: str) -> List[Message]:
    """
    Sends a message from the sender to all agents in its adjacency list.
    """
    sent_messages: List[Message] = []
    if sender in self.adjacency_list:
      for receiver in self.adjacency_list[sender]:
        # Corrected argument order: sender, receiver, message_content
        msg_obj = self.send_message(sender, receiver, message_content)
        sent_messages.append(msg_obj)
    return sent_messages

  def pop_messages_for_agent(self, agent_name: str) -> Dict[str, List[Message]]:
    """
    Retrieves all messages where 'agent_name' is the receiver, grouped by sender.
    Marks messages as 'received' and removes them from the pending message store.
    """
    retrieved_messages: Dict[str, List[Message]] = {}
    # Iterate over a copy of senders if we modify self.messages during iteration
    for sender in list(self.messages.keys()):
        if agent_name in self.messages[sender]:
            if sender not in retrieved_messages:
                retrieved_messages[sender] = []
            
            # Add messages to retrieved_messages and mark them
            for msg_obj in self.messages[sender][agent_name]:
                msg_obj.received = True # Mark as logically received by the agent
                retrieved_messages[sender].append(msg_obj)
            
            # Remove these messages from the store for this sender-receiver pair
            del self.messages[sender][agent_name]
            if not self.messages[sender]: # If no more receivers for this sender
                del self.messages[sender]
    return retrieved_messages

  def get_all_pending_messages_for_agent(self, agent_name: str) -> Dict[str, List[Message]]:
    """
    Gets all messages where 'agent_name' is the receiver, grouped by sender,
    without removing them from the message store or marking them as received.
    """
    agents_messages = self.messages.get(agent_name, {})
    pending_messages: Dict[str, List[Message]] = {}

    for sender, messages in agents_messages.items():
        pending = [msg for msg in messages if not msg.received and agent_name in msg.receiver]
        if pending:
            pending_messages[sender] = pending
            for msg in pending:
                msg.received = True

    return pending_messages

  def get_communication_partners(self, agent_name: str) -> List[str]:
    return self.adjacency_list.get(agent_name, [])

  def clear_messages(self) -> None:
    """Clears all pending messages from the medium."""
    self.messages = {}

class FullyConnectedCommunicationMedium(CommunicationMedium):
  def __init__(self, agents: List[str]):
    # Agents can send to any other agent, but not themselves by default.
    adjacency_list: Dict[str, List[str]] = {
        agent.id: [other_agent.id for other_agent in agents if other_agent != agent]
        for agent in agents
    }
    super().__init__(adjacency_list)


class SparseCommunicationMedium(CommunicationMedium):
  def __init__(self, agents: List[str], seed: Union[int, None] = None):
    if seed is not None:
        random.seed(seed)
    
    adjacency_list: Dict[str, List[str]] = {}
    if not agents:
        pass # adjacency_list remains empty
    else:
        for agent in agents:
            possible_receivers = [other for other in agents if other != agent]
            if not possible_receivers:
                adjacency_list[agent] = []
            else:
                num_connections = random.randint(0, len(possible_receivers))
                adjacency_list[agent] = random.sample(possible_receivers, num_connections)
    super().__init__(adjacency_list)


class LinearCommunicationMedium(CommunicationMedium):
  def __init__(self, agents: List[str]):
    adjacency_list: Dict[str, List[str]] = {}
    num_agents = len(agents)
    for i, agent in enumerate(agents):
      if i < num_agents - 1:
        adjacency_list[agent] = [agents[i+1]]
      else:
        adjacency_list[agent] = [] # Last agent sends to no one
    super().__init__(adjacency_list)

class RingCommunicationMedium(CommunicationMedium):
  def __init__(self, agents: List[str]):
    adjacency_list: Dict[str, List[str]] = {}
    num_agents = len(agents)
    if num_agents == 0:
        pass
    elif num_agents == 1: # Agent sends to itself in a 1-agent ring
        adjacency_list[agents[0]] = [agents[0]]
    else:
        for i, agent in enumerate(agents):
            adjacency_list[agent] = [agents[(i + 1) % num_agents]]
    super().__init__(adjacency_list)

class StarCommunicationMedium(CommunicationMedium):
  def __init__(self, agents: List[str]):
    adjacency_list: Dict[str, List[str]] = {}
    if not agents:
        pass
    elif len(agents) == 1:
      # A single agent star; does not send to anyone including self by this definition.
      adjacency_list = {agents[0]: []}
    else:
      center_agent = agents[0]
      peripheral_agents = agents[1:]
      # Peripherals send to center
      for p_agent in peripheral_agents:
        adjacency_list[p_agent] = [center_agent]
      # Center sends to all peripherals
      adjacency_list[center_agent] = list(peripheral_agents)
    super().__init__(adjacency_list)


class CommunicationMediumFactory:
  @staticmethod
  def create_communication_medium(medium_type: str, agents: List[str]) -> CommunicationMedium:
    if medium_type == "ring":
      return RingCommunicationMedium(agents)
    elif medium_type == "star":
      return StarCommunicationMedium(agents)
    elif medium_type == "fully_connected":
      return FullyConnectedCommunicationMedium(agents)
    elif medium_type == "linear":
      return LinearCommunicationMedium(agents)
    elif medium_type == "sparse":
      return SparseCommunicationMedium(agents)  # Assuming you have a NoneCommunicationMedium class for "none
    else:
      raise ValueError(f"Unknown communication medium type: {medium_type}")