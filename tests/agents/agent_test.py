import unittest
from gaims.agents.agent import LLMAgent, AgentConfig, SystemPromptConfig, ObservationConfig, Action
from gaims.agents.model import Model

class TestLLMAgent(unittest.TestCase):
    def setUp(self):
        # Create a mock model
        self.mock_model = Model()
        self.mock_model.generate_response = lambda x: "Mock response"
        # Create a system prompt config
        self.system_prompt_config = SystemPromptConfig(
            template="You are a helpful assistant.",
            variables={}
        )

        # Create an observation config
        self.observation_config = ObservationConfig(
            observation_format="Observation: {observation}"
        )