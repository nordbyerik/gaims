import unittest
import random # For testing sparse medium logic if needed, or just its seed usage

# Assuming your classes are in 'communication_models.py'
from communication.communication import (
    Message,
    CommunicationMedium, # Abstract, so tested via concrete implementations
    FullyConnectedCommunicationMedium,
    SparseCommunicationMedium,
    LinearCommunicationMedium,
    RingCommunicationMedium,
    StarCommunicationMedium
)

class TestMessageClass(unittest.TestCase):
    def test_message_creation_and_attributes(self):
        msg = Message(sender="Alice", receiver="Bob", message_content="Hello", id=1)
        self.assertEqual(msg.sender, "Alice")
        self.assertEqual(msg.receiver, "Bob")
        self.assertEqual(msg.message, "Hello")
        self.assertEqual(msg.id, 1)
        self.assertFalse(msg.received)

    def test_message_equality(self):
        msg1 = Message("Alice", "Bob", "Hello", 1)
        msg2 = Message("Alice", "Bob", "Hello", 1)
        msg3 = Message("Charlie", "Bob", "Hello", 1)
        msg4 = Message("Alice", "Dave", "Hello", 1)
        msg5 = Message("Alice", "Bob", "Hi", 1)
        msg6 = Message("Alice", "Bob", "Hello", 2)

        self.assertEqual(msg1, msg2, "Identical messages should be equal")
        self.assertNotEqual(msg1, msg3, "Messages with different senders should not be equal")
        self.assertNotEqual(msg1, msg4, "Messages with different receivers should not be equal")
        self.assertNotEqual(msg1, msg5, "Messages with different content should not be equal")
        self.assertNotEqual(msg1, msg6, "Messages with different IDs should not be equal")
        self.assertNotEqual(msg1, "some string", "Message should not be equal to a non-Message type")

    def test_message_repr(self):
        msg = Message("Alice", "Bob", "Test", 10)
        self.assertIn("Alice", repr(msg))
        self.assertIn("Bob", repr(msg))
        self.assertIn("Test", repr(msg))
        self.assertIn("10", repr(msg))

class BaseCommunicationMediumTests:
    # This is a mixin or a base class for other tests to inherit from.
    # It should not be discovered as a test case itself.
    # Subclasses must define self.medium and self.agents in their setUp.

    def assert_medium_initial_state(self):
        self.assertEqual(self.medium.messages, {}, "Initial messages should be empty")
        self.assertEqual(self.medium.message_history, [], "Initial message_history should be empty")
        self.assertEqual(self.medium.message_count, 0, "Initial message_count should be 0")

    def test_initial_state(self):
        self.assert_medium_initial_state()

    def test_send_message_stores_correctly(self):
        if not hasattr(self, 'agents') or len(self.agents) < 2:
            self.skipTest("Requires at least two agents for distinct sender/receiver.")
        
        sender, receiver = self.agents[0], self.agents[1]
        msg_content = "Test content 1"
        
        msg_obj = self.medium.send_message(sender, receiver, msg_content)
        
        self.assertEqual(self.medium.message_count, 1)
        self.assertEqual(msg_obj.id, 0)
        self.assertEqual(msg_obj.sender, sender)
        self.assertEqual(msg_obj.receiver, receiver)
        self.assertEqual(msg_obj.message, msg_content)
        
        self.assertIn(sender, self.medium.messages)
        self.assertIn(receiver, self.medium.messages[sender])
        self.assertEqual(len(self.medium.messages[sender][receiver]), 1)
        self.assertEqual(self.medium.messages[sender][receiver][0], msg_obj)
        
        self.assertEqual(len(self.medium.message_history), 1)
        self.assertEqual(self.medium.message_history[0], (sender, receiver, msg_obj))

        # Send another message
        msg_content2 = "Test content 2"
        msg_obj2 = self.medium.send_message(sender, receiver, msg_content2)
        self.assertEqual(self.medium.message_count, 2)
        self.assertEqual(msg_obj2.id, 1)
        self.assertEqual(len(self.medium.messages[sender][receiver]), 2)
        self.assertEqual(self.medium.messages[sender][receiver][1], msg_obj2)
        self.assertEqual(len(self.medium.message_history), 2)

    def test_pop_messages_for_agent(self):
        if not hasattr(self, 'agents') or len(self.agents) < 2:
            self.skipTest("Requires at least two agents.")

        sender1, receiver_agent, sender2 = self.agents[0], self.agents[1], self.agents[0]
        if len(self.agents) >= 3: # Use a distinct second sender if available
            sender2 = self.agents[2]
        
        other_receiver = self.agents[0] # A different receiver
        if len(self.agents) >=3 and self.agents[2] != receiver_agent:
            other_receiver = self.agents[2]
        elif receiver_agent == self.agents[0] and len(self.agents) >=2: # ensure other_receiver is different
            other_receiver = self.agents[1]


        msg1_content = "Message 1 for agent"
        msg2_content = "Message 2 for agent"
        msg_other_content = "Message for other agent"

        msg1 = self.medium.send_message(sender1, receiver_agent, msg1_content)
        msg2 = self.medium.send_message(sender2, receiver_agent, msg2_content)
        msg_other = self.medium.send_message(sender1, other_receiver, msg_other_content)

        # Messages before pop
        self.assertTrue(any(msg.message == msg1_content for msg in self.medium.messages.get(sender1, {}).get(receiver_agent, [])))

        popped_messages = self.medium.pop_messages_for_agent(receiver_agent)

        self.assertTrue(msg1.received)
        self.assertTrue(msg2.received)

        self.assertIn(sender1, popped_messages)
        self.assertIn(msg1, popped_messages[sender1])

        if sender1 == sender2 : # if only 2 agents, sender1 and sender2 are the same
             self.assertIn(msg2, popped_messages[sender1])
        else:
             self.assertIn(sender2, popped_messages)
             self.assertIn(msg2, popped_messages[sender2])


        # Check that messages for receiver_agent are removed from the main store
        self.assertNotIn(receiver_agent, self.medium.messages.get(sender1, {}))
        if sender1 != sender2:
            self.assertNotIn(receiver_agent, self.medium.messages.get(sender2, {}))
        
        # Check that messages for other_receiver are still there
        if sender1 in self.medium.messages and other_receiver in self.medium.messages[sender1]:
            self.assertIn(msg_other, self.medium.messages[sender1][other_receiver])
        else: # if sender1's messages were all for receiver_agent, sender1 key might be gone
            if not (sender1 in self.medium.messages and other_receiver in self.medium.messages[sender1]):
                 #This is fine if msg_other was the only one and it was popped, or never existed
                 pass


    def test_get_all_pending_messages_for_agent(self):
        if not hasattr(self, 'agents') or len(self.agents) < 2:
            self.skipTest("Requires at least two agents.")

        sender, receiver = self.agents[0], self.agents[1]
        msg_content = "Pending message"
        msg_obj = self.medium.send_message(sender, receiver, msg_content)

        pending = self.medium.get_all_pending_messages_for_agent(receiver)
        self.assertIn(sender, pending)
        self.assertIn(msg_obj, pending[sender])
        self.assertFalse(msg_obj.received, "Message should not be marked received by 'get_all_pending'")

        # Ensure message is still in the main store
        self.assertIn(sender, self.medium.messages)
        self.assertIn(receiver, self.medium.messages[sender])
        self.assertIn(msg_obj, self.medium.messages[sender][receiver])


    def test_clear_messages(self):
        if not hasattr(self, 'agents') or len(self.agents) < 2:
            self.skipTest("Requires at least two agents.")
        self.medium.send_message(self.agents[0], self.agents[1], "A message to clear")
        self.assertNotEqual(self.medium.messages, {})
        
        original_history_len = len(self.medium.message_history)
        original_count = self.medium.message_count

        self.medium.clear_messages()
        self.assertEqual(self.medium.messages, {})
        
        # Assert history and count are not reset by default
        self.assertEqual(len(self.medium.message_history), original_history_len)
        self.assertEqual(self.medium.message_count, original_count)

    def test_broadcast_message_sends_to_all_in_adjacency(self):
        if not hasattr(self, 'agents') or not self.agents:
            self.skipTest("Requires at least one agent.")

        sender = self.agents[0]
        message_content = "Broadcast Test"
        
        expected_receivers = self.medium.adjacency_list.get(sender, [])
        
        initial_msg_count = self.medium.message_count
        sent_message_objects = self.medium.broadcast_message(sender, message_content)

        self.assertEqual(len(sent_message_objects), len(expected_receivers),
                         f"Expected {len(expected_receivers)} messages, got {len(sent_message_objects)}")
        self.assertEqual(self.medium.message_count, initial_msg_count + len(expected_receivers))

        for i, rec_agent in enumerate(expected_receivers):
            msg_obj = sent_message_objects[i]
            self.assertEqual(msg_obj.sender, sender)
            self.assertEqual(msg_obj.receiver, rec_agent)
            self.assertEqual(msg_obj.message, message_content)

            # Check if the message is in the store for the receiver
            receiver_messages = self.medium.get_all_pending_messages_for_agent(rec_agent)
            self.assertIn(sender, receiver_messages, f"Sender not found in {rec_agent}'s messages")
            self.assertIn(msg_obj, receiver_messages[sender], f"Message not found in {rec_agent}'s messages from {sender}")


class TestFullyConnectedCommunicationMedium(unittest.TestCase, BaseCommunicationMediumTests):
    def setUp(self):
        self.agents = ["A", "B", "C"]
        self.medium = FullyConnectedCommunicationMedium(self.agents)

    def test_fc_adjacency_list_creation(self):
        adj = self.medium.adjacency_list
        self.assertEqual(len(adj), 3)
        self.assertCountEqual(adj["A"], ["B", "C"])
        self.assertCountEqual(adj["B"], ["A", "C"])
        self.assertCountEqual(adj["C"], ["A", "B"])

    def test_fc_single_agent(self):
        medium = FullyConnectedCommunicationMedium(["Solo"])
        self.assertEqual(medium.adjacency_list["Solo"], [])

    def test_fc_no_agents(self):
        medium = FullyConnectedCommunicationMedium([])
        self.assertEqual(medium.adjacency_list, {})


class TestSparseCommunicationMedium(unittest.TestCase, BaseCommunicationMediumTests):
    def setUp(self):
        self.agents = ["S1", "S2", "S3", "S4"]
        # Using a seed for reproducible "random" connections
        self.medium = SparseCommunicationMedium(self.agents, seed=42)

    def test_sparse_adjacency_list_properties(self):
        adj = self.medium.adjacency_list
        self.assertEqual(len(adj), len(self.agents))
        for agent, connections in adj.items():
            self.assertIn(agent, self.agents)
            self.assertIsInstance(connections, list)
            for connected_agent in connections:
                self.assertIn(connected_agent, self.agents)
                self.assertNotEqual(agent, connected_agent, "Agent should not connect to itself")
            # Check for unique connections
            self.assertEqual(len(connections), len(set(connections)))
    
    def test_sparse_reproducibility_with_seed(self):
        medium1 = SparseCommunicationMedium(self.agents, seed=101)
        medium2 = SparseCommunicationMedium(self.agents, seed=101)
        self.assertEqual(medium1.adjacency_list, medium2.adjacency_list)

        medium3 = SparseCommunicationMedium(self.agents, seed=102)
        if self.agents : # Only makes sense if there are agents to connect
             # It's highly probable they will be different with a different seed and multiple agents
             # For very small agent lists (e.g. 2 agents), it might be the same by chance if connections are 0 or 1.
             if len(self.agents) > 2 or any(len(v) > 0 for v in medium1.adjacency_list.values()):
                self.assertNotEqual(medium1.adjacency_list, medium3.adjacency_list, "Adjacency lists with different seeds should likely differ.")


    def test_sparse_no_agents(self):
        medium = SparseCommunicationMedium([], seed=1)
        self.assertEqual(medium.adjacency_list, {})

    def test_sparse_single_agent(self):
        medium = SparseCommunicationMedium(["Solo"], seed=1)
        self.assertEqual(medium.adjacency_list["Solo"], [])


class TestLinearCommunicationMedium(unittest.TestCase, BaseCommunicationMediumTests):
    def setUp(self):
        self.agents = ["L1", "L2", "L3"]
        self.medium = LinearCommunicationMedium(self.agents)

    def test_linear_adjacency_list_creation(self):
        adj = self.medium.adjacency_list
        self.assertEqual(len(adj), 3)
        self.assertEqual(adj["L1"], ["L2"])
        self.assertEqual(adj["L2"], ["L3"])
        self.assertEqual(adj["L3"], [])

    def test_linear_single_agent(self):
        medium = LinearCommunicationMedium(["Solo"])
        self.assertEqual(medium.adjacency_list["Solo"], [])
    
    def test_linear_no_agents(self):
        medium = LinearCommunicationMedium([])
        self.assertEqual(medium.adjacency_list, {})


class TestRingCommunicationMedium(unittest.TestCase, BaseCommunicationMediumTests):
    def setUp(self):
        self.agents = ["R1", "R2", "R3"]
        self.medium = RingCommunicationMedium(self.agents)

    def test_ring_adjacency_list_creation(self):
        adj = self.medium.adjacency_list
        self.assertEqual(len(adj), 3)
        self.assertEqual(adj["R1"], ["R2"])
        self.assertEqual(adj["R2"], ["R3"])
        self.assertEqual(adj["R3"], ["R1"]) # Ring connection

    def test_ring_single_agent_connects_to_self(self):
        medium = RingCommunicationMedium(["Solo"])
        self.assertEqual(medium.adjacency_list["Solo"], ["Solo"])
        # Test broadcast for single agent ring
        sent_msgs = medium.broadcast_message("Solo", "Hello myself")
        self.assertEqual(len(sent_msgs), 1)
        self.assertEqual(sent_msgs[0].receiver, "Solo")
        
        retrieved = medium.pop_messages_for_agent("Solo")
        self.assertIn("Solo", retrieved)
        self.assertEqual(len(retrieved["Solo"]), 1)

    def test_ring_no_agents(self):
        medium = RingCommunicationMedium([])
        self.assertEqual(medium.adjacency_list, {})


class TestStarCommunicationMedium(unittest.TestCase, BaseCommunicationMediumTests):
    def setUp(self):
        # Star: first agent is center, others are peripherals
        self.agents = ["Center", "P1", "P2"]
        self.medium = StarCommunicationMedium(self.agents)

    def test_star_adjacency_list_creation(self):
        adj = self.medium.adjacency_list
        center, p1, p2 = self.agents[0], self.agents[1], self.agents[2]
        
        self.assertEqual(len(adj), 3)
        self.assertCountEqual(adj[center], [p1, p2], "Center should connect to all peripherals")
        self.assertEqual(adj[p1], [center], "Peripheral 1 should connect to center")
        self.assertEqual(adj[p2], [center], "Peripheral 2 should connect to center")

    def test_star_single_agent(self):
        medium = StarCommunicationMedium(["SoloCenter"])
        self.assertEqual(medium.adjacency_list["SoloCenter"], [])

    def test_star_no_agents(self):
        medium = StarCommunicationMedium([])
        self.assertEqual(medium.adjacency_list, {})
        
    def test_star_two_agents(self): # Center and one peripheral
        agents = ["C", "P"]
        medium = StarCommunicationMedium(agents)
        adj = medium.adjacency_list
        self.assertCountEqual(adj["C"], ["P"])
        self.assertEqual(adj["P"], ["C"])


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)