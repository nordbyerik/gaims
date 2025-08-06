import unittest
from unittest.mock import patch, MagicMock, ANY
import random
import string
import logging

# Assuming your provided code is in a file named `your_module.py`
# Adjust the import path if your file structure is different.
from gaims.agents.models import (
    Model,
    GeminiModel,
    LocalModel,
    MessageStructure,
    ActionStructure,
    Message,
    Action,
    ModelConfig
)

# Pydantic models for mocking structured LLM responses
# We define them here again or import them if they are in a separate file accessible to tests
from pydantic import BaseModel, Field
from typing import Literal

from langchain_huggingface.llms.huggingface_pipeline import HuggingFacePipeline
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from gaims.utils.huggingface_langchain import ChatHuggingFace


class MockMessageStructure(BaseModel):
    message: str = Field()
    recipient: int = Field()

class MockActionStructure(BaseModel):
    action_id: Literal[0, 1] = Field()


class TestModel(unittest.TestCase):

    def test_model_config_initialization_with_activation_layers(self):
        model_name = "test_model"
        activation_layers = ["model.layers.0.mlp", "model.layers.1.self_attn"]
        config = ModelConfig(model_name=model_name, activation_layers=activation_layers)
        self.assertEqual(config.model_name, model_name)
        self.assertEqual(config.activation_layers, activation_layers)

    def test_model_initialization_with_identifier(self):
        identifier = "test_id"
        model = Model(identifier=identifier, model_name="test_model_name")
        self.assertEqual(model._identifier, identifier)
        self.assertEqual(model.model_name, "test_model_name")

    def test_model_initialization_without_identifier(self):
        with patch.object(random, 'choices', return_value=list("abcde")) as mock_random_choices:
            model = Model(model_name="test_model_name")
            self.assertEqual(model._identifier, "abcde")
            mock_random_choices.assert_called_once_with(string.ascii_lowercase, k=5)
        self.assertEqual(model.model_name, "test_model_name")

    def test_model_initialization_default_model_name(self):
        model = Model()
        self.assertEqual(model.model_name, "unsloth/Llama-3.2-3B-Instruct") # Default

    @patch('gaims.agents.models.log') # Patching the logger instance used in the module
    def test_send_message_no_structure_no_system_prompt(self, mock_log):
        model = Model()
        model.llm = MagicMock()
        mock_response_content = "Test response"
        mock_response_content = MagicMock(content="Test response")
        model.llm.invoke.return_value = MagicMock(content=mock_response_content.content)

        message_text = "Hello LLM"
        response = model.send_message(message_text)

        self.assertEqual(response, mock_response_content)
        model.llm.invoke.assert_called_once()
        args, _ = model.llm.invoke.call_args
        self.assertEqual(len(args[0]), 1) # Only HumanMessage
        self.assertEqual(args[0][0].content, message_text)
        mock_log.info.assert_any_call(f"--> {model._identifier}: {message_text}")
        mock_log.info.assert_any_call(f"{model._identifier} -->: {mock_response_content}")

    @patch('gaims.agents.models.log')
    def test_send_message_with_system_prompt(self, mock_log):
        model = Model()
        model.llm = MagicMock()
        mock_response_content = MagicMock(content="System guided response")
        model.llm.invoke.return_value = MagicMock(content=mock_response_content.content)

        message_text = "User question"
        system_prompt_text = "You are a helpful assistant."
        response = model.send_message(message_text, system_prompt=system_prompt_text)

        self.assertEqual(response, mock_response_content)
        model.llm.invoke.assert_called_once()
        args, _ = model.llm.invoke.call_args
        self.assertEqual(len(args[0]), 2) # SystemMessage and HumanMessage
        self.assertEqual(args[0][0].content, system_prompt_text)
        self.assertEqual(args[0][0].type, "system")
        self.assertEqual(args[0][1].content, message_text)
        self.assertEqual(args[0][1].type, "human")
        mock_log.info.assert_any_call(f"--> {model._identifier}: {message_text}")
        mock_log.info.assert_any_call(f"{model._identifier} -->: {mock_response_content}")


    @patch('gaims.agents.models.log')
    def test_send_message_with_structure(self, mock_log):
        model = Model()
        model.llm = MagicMock()
        structured_llm_mock = MagicMock()
        model.llm.with_structured_output.return_value = structured_llm_mock

        mock_structured_response = MockMessageStructure(message="Structured message", recipient=1)
        structured_llm_mock.invoke.return_value = {"parsed": mock_structured_response, "raw": MagicMock(content="mock raw content")}

        message_text = "Request for structured data"
        response = model.send_message(message_text, structure=MockMessageStructure)

        self.assertEqual(response, mock_structured_response)
        model.llm.with_structured_output.assert_called_once_with(MockMessageStructure, include_raw=True)
        structured_llm_mock.invoke.assert_called_once()
        args, _ = structured_llm_mock.invoke.call_args
        self.assertEqual(args[0][0].content, message_text)
        mock_log.info.assert_any_call(f"--> {model._identifier}: {message_text}")
        mock_log.info.assert_any_call(f"{model._identifier} -->: {mock_structured_response}")

    def test_observe(self):
        model = Model()
        model.send_message = MagicMock(return_value="Observed")
        
        kwargs = {"system_prompt": "Observe carefully"}
        response = model.observe("Observation message", **kwargs)
        
        self.assertEqual(response, "Observed")
        model.send_message.assert_called_once_with("Observation message", **kwargs)

    def test_communicate(self):
        model = Model(identifier="sender_agent")
        mock_message_structure = MessageStructure(message_content="Hello recipient!", receiver=[5])
        model.send_message = MagicMock(return_value=mock_message_structure)
        
        kwargs = {"system_prompt": "Be communicative"}
        message_obj = model.communicate("Initial greeting", **kwargs)
        
        model.send_message.assert_called_once_with(
            "Initial greeting", MessageStructure, kwargs
        )
        self.assertIsInstance(message_obj, Message)
        self.assertEqual(message_obj.sender, "sender_agent")
        self.assertEqual(message_obj.message, mock_message_structure.message_content)
        self.assertEqual(message_obj.receiver, mock_message_structure.receiver)

    def test_act(self):
        model = Model()
        model._identifier = 123 # Mock identifier to be an integer
        
        model.send_message = MagicMock(return_value=MockActionStructure(action_id=1))

        kwargs = {"system_prompt": "Choose an action"}
        action_obj = model.act("What should I do?", **kwargs)

        self.assertIsInstance(action_obj, Action)
        self.assertEqual(action_obj.action_id, 1)
        self.assertEqual(action_obj.agent_id, 123)
        model.send_message.assert_called_once_with(
            "What should I do?", ActionStructure, kwargs
        )


class TestGeminiModel(unittest.TestCase):

    @patch('gaims.agents.models.ChatGoogleGenerativeAI')
    def test_gemini_model_initialization(self, MockChatGoogleGenerativeAI):
        mock_llm_instance = MagicMock()
        MockChatGoogleGenerativeAI.return_value = mock_llm_instance
        
        identifier = "gemini_tester"
        model_name = "gemini-pro-test" # Test with a non-default model name
        
        gemini_model = GeminiModel(identifier=identifier, model=model_name)
        
        self.assertEqual(gemini_model._identifier, identifier)
        self.assertEqual(gemini_model.model_name, model_name) # Superclass sets this
        MockChatGoogleGenerativeAI.assert_called_once_with(model=model_name, google_api_key=ANY)
        self.assertEqual(gemini_model.llm, mock_llm_instance)

    @patch('gaims.agents.models.ChatGoogleGenerativeAI')
    def test_gemini_model_initialization_default_model(self, MockChatGoogleGenerativeAI):
        mock_llm_instance = MagicMock()
        MockChatGoogleGenerativeAI.return_value = mock_llm_instance

        gemini_model = GeminiModel() # Use default model name

        self.assertIsNotNone(gemini_model._identifier)
        self.assertEqual(gemini_model.model_name, "gemini-1.5-flash") # Default for GeminiModel
        MockChatGoogleGenerativeAI.assert_called_once_with(model="gemini-1.5-flash", google_api_key=ANY)
        self.assertEqual(gemini_model.llm, mock_llm_instance)

    # Methods like send_message, communicate, act are inherited from Model.
    # Their core logic (calling self.llm.invoke) is tested in TestModel.
    # We just need to ensure self.llm is set up correctly, which is done by testing __init__.


class TestLocalModel(unittest.TestCase):

    def _setup_local_model_mocks(self, hf_repo_id, activation_layers):
        mock_tokenizer_instance = MagicMock(spec=AutoTokenizer)
        mock_tokenizer_instance.__class__ = AutoTokenizer  # Mock __class__ for pipeline framework inference
        mock_tokenizer_instance.apply_chat_template.return_value = "mock_template"
        self.MockAutoTokenizer.from_pretrained.return_value = mock_tokenizer_instance

        mock_model_instance = MagicMock(spec=AutoModelForCausalLM)
        mock_model_instance.__class__ = AutoModelForCausalLM  # Mock __class__ for pipeline framework inference
        mock_model_instance.name_or_path = hf_repo_id  # Add name_or_path for HuggingFacePipeline validator
        self.MockAutoModel.from_pretrained.return_value = mock_model_instance
        mock_model_instance.config = MagicMock(architectures=["SomeModelForCausalLM"])  # Mock config for ActivationHook

        mock_pipeline_instance = MagicMock(spec=pipeline)
        mock_pipeline_instance.model = MagicMock(name_or_path=hf_repo_id) # Mock model and its name_or_path
        self.mock_pipeline_func.return_value = mock_pipeline_instance

        mock_model_instance = MagicMock(spec=AutoModelForCausalLM)
        mock_model_instance.__class__ = AutoModelForCausalLM  # Mock __class__ for pipeline framework inference
        mock_model_instance.name_or_path = hf_repo_id  # Add name_or_path for HuggingFacePipeline validator
        self.MockAutoModel.from_pretrained.return_value = mock_model_instance
        mock_model_instance.config = MagicMock(architectures=["SomeModelForCausalLM"])  # Mock config for ActivationHook

        mock_pipeline_instance = MagicMock(spec=pipeline)
        mock_pipeline_instance.model.name_or_path = hf_repo_id  # Mock name_or_path for HuggingFacePipeline validator
        self.mock_pipeline_func.return_value = mock_pipeline_instance

        mock_hf_pipeline_wrapper = MagicMock(spec=HuggingFacePipeline)
        mock_hf_pipeline_wrapper.model_id = hf_repo_id  # Mock model_id for ChatHuggingFace
        self.MockHuggingFacePipeline.return_value = mock_hf_pipeline_wrapper

        mock_chat_hf_instance = MagicMock()
        self.MockChatHuggingFace.return_value = mock_chat_hf_instance

        return LocalModel(hf_repo_id=hf_repo_id, activation_layers=activation_layers)

    @patch('gaims.agents.models.ChatHuggingFace')
    @patch('gaims.agents.models.AutoTokenizer')
    @patch('gaims.agents.models.AutoModelForCausalLM')
    @patch('gaims.agents.models.pipeline')
    def test_local_model_initialization(self, mock_pipeline_func, MockAutoModel, MockAutoTokenizer, MockChatHuggingFace):
        hf_repo_id = "test/local-model-test"
        activation_layers = ["model.layers.0.mlp", "model.layers.1.self_attn"]

        mock_tokenizer_instance = MagicMock(spec=AutoTokenizer)
        mock_tokenizer_instance.__class__ = AutoTokenizer  # Mock __class__ for pipeline framework inference
        MockAutoTokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_tokenizer_instance.apply_chat_template.return_value = "mock_template"

        mock_model_instance = MagicMock(spec=AutoModelForCausalLM)
        mock_model_instance.__class__ = AutoModelForCausalLM  # Mock __class__ for pipeline framework inference
        mock_model_instance.name_or_path = hf_repo_id  # Add name_or_path for HuggingFacePipeline validator
        MockAutoModel.from_pretrained.return_value = mock_model_instance
        mock_model_instance.config = MagicMock(architectures=["SomeModelForCausalLM"])  # Mock config for ActivationHook
        
        mock_pipeline_instance = MagicMock(spec=pipeline)
        mock_pipeline_instance.model.name_or_path = hf_repo_id  # Mock name_or_path for HuggingFacePipeline validator
        mock_pipeline_func.return_value = mock_pipeline_instance

        mock_hf_pipeline_wrapper = MagicMock(spec=HuggingFacePipeline)
        mock_hf_pipeline_wrapper.model_id = hf_repo_id  # Mock model_id for ChatHuggingFace
        MockHuggingFacePipeline.return_value = mock_hf_pipeline_wrapper

        mock_chat_hf_instance = MagicMock()
        MockChatHuggingFace.return_value = mock_chat_hf_instance

        local_model = LocalModel(hf_repo_id=hf_repo_id, activation_layers=activation_layers)

        self.assertEqual(local_model._identifier, hf_repo_id)
        self.assertEqual(local_model.model_name, hf_repo_id)

        MockAutoTokenizer.from_pretrained.assert_called_once_with(hf_repo_id)
        MockAutoModel.from_pretrained.assert_called_once_with(hf_repo_id, torch_dtype=torch.float16)
        mock_pipeline_func.assert_called_once_with(
            "text-generation", model=mock_model_instance, tokenizer=mock_tokenizer_instance, max_new_tokens=520
        )
        MockHuggingFacePipeline.assert_called_once_with(pipeline=mock_pipeline_instance)
        MockChatHuggingFace.assert_called_once_with(llm=mock_hf_pipeline_wrapper, model_id=hf_repo_id)
        self.assertEqual(local_model.llm, mock_chat_hf_instance)

        if activation_layers:
            self.assertEqual(len(local_model.hooks), len(activation_layers))
            for layer_name in activation_layers:
                self.assertIn(layer_name, local_model.hooks)

    @patch('gaims.agents.models.ChatHuggingFace')
    @patch('gaims.agents.models.AutoTokenizer')
    @patch('gaims.agents.models.AutoModelForCausalLM')
    @patch('gaims.agents.models.pipeline')
    def test_local_model_initialization_default_model(self, mock_pipeline_func, MockAutoModel, MockAutoTokenizer, MockChatHuggingFace):
        hf_repo_id = "unsloth/Llama-3.2-3B-Instruct"  # Default for LocalModel
        activation_layers = ["model.layers.0.mlp", "model.layers.1.self_attn"]

        mock_tokenizer_instance = MagicMock(spec=AutoTokenizer)
        mock_tokenizer_instance.__class__ = AutoTokenizer
        MockAutoTokenizer.from_pretrained.return_value = mock_tokenizer_instance

        mock_model_instance = MagicMock(spec=AutoModelForCausalLM)
        mock_model_instance.__class__ = AutoModelForCausalLM
        mock_model_instance.name_or_path = hf_repo_id  # Add name_or_path for HuggingFacePipeline validator
        MockAutoModel.from_pretrained.return_value = mock_model_instance
        mock_model_instance.config = MagicMock(architectures=["SomeModelForCausalLM"])  # Mock config for ActivationHook
        
        mock_pipeline_instance = MagicMock(spec=pipeline)
        mock_pipeline_instance.model.name_or_path = hf_repo_id  # Mock name_or_path for HuggingFacePipeline validator
        mock_pipeline_func.return_value = mock_pipeline_instance
        
        mock_hf_pipeline_wrapper = MagicMock(spec=HuggingFacePipeline)
        mock_hf_pipeline_wrapper.model_id = hf_repo_id  # Mock model_id for ChatHuggingFace
        MockHuggingFacePipeline.return_value = mock_hf_pipeline_wrapper

        mock_chat_hf_instance = MagicMock()
        MockChatHuggingFace.return_value = mock_chat_hf_instance

        local_model = LocalModel(activation_layers=activation_layers) # Use default model name

        self.assertIsNotNone(local_model._identifier)
        self.assertEqual(local_model.model_name, hf_repo_id)  # Default for LocalModel
        MockAutoTokenizer.from_pretrained.assert_called_once_with(hf_repo_id)
        MockAutoModel.from_pretrained.assert_called_once_with(hf_repo_id, torch_dtype=torch.float16)
        mock_pipeline_func.assert_called_once_with(
            "text-generation", model=mock_model_instance, tokenizer=mock_tokenizer_instance, max_new_tokens=520
        )
        MockHuggingFacePipeline.assert_called_once_with(pipeline=mock_pipeline_instance)
        MockChatHuggingFace.assert_called_once_with(llm=mock_hf_pipeline_wrapper, model_id=hf_repo_id)
        self.assertEqual(local_model.llm, mock_chat_hf_instance)
        self.assertEqual(len(local_model.hooks), len(activation_layers))
        for layer_name in activation_layers:
            self.assertIn(layer_name, local_model.hooks)

    def test_get_activations_no_hooks(self):
        with (
            patch('gaims.agents.models.AutoModelForCausalLM.from_pretrained') as MockAutoModel,
            patch('gaims.agents.models.AutoTokenizer.from_pretrained') as MockAutoTokenizer,
            patch('gaims.agents.models.pipeline') as mock_pipeline_func,
        ):
            mock_model_instance = MagicMock(spec=AutoModelForCausalLM)
            mock_model_instance.__class__ = AutoModelForCausalLM
            mock_model_instance.name_or_path = "mock/model-test" # Add name_or_path for HuggingFacePipeline validator
            MockAutoModel.return_value = mock_model_instance
            MockAutoModel.return_value.config = MagicMock(architectures=["SomeModelForCausalLM"])
            mock_pipeline_func.return_value = MagicMock(tokenizer=MockAutoTokenizer.from_pretrained.return_value, model=mock_model_instance, spec=pipeline)
            local_model = LocalModel(activation_layers=[])
            with self.assertRaises(ValueError):
                local_model.get_activations("some_layer")

    def test_get_activations_with_mocked_hooks(self):
        with (
            patch('gaims.agents.models.AutoModelForCausalLM.from_pretrained') as MockAutoModel,
            patch('gaims.agents.models.AutoTokenizer.from_pretrained') as MockAutoTokenizer,
            patch('gaims.agents.models.pipeline') as mock_pipeline_func,
        ):
            MockAutoModel.return_value.config = MagicMock(architectures=["SomeModelForCausalLM"])
            local_model = LocalModel(hf_repo_id="test/local-model-test", activation_layers=["layer1"])
            
            # Mock the hooks attribute and its structure
            mock_hook = MagicMock()
            mock_tensor = MagicMock()
            mock_cpu_tensor = MagicMock()
            
            mock_hook.activations = mock_tensor
            mock_tensor.detach.return_value.cpu.return_value = mock_cpu_tensor
            
            local_model.hooks = {"layer1": mock_hook} # Manually set the mocked hooks
            
            activations = local_model.get_activations("layer1")
            
            self.assertEqual(activations, mock_cpu_tensor)
            mock_hook.activations[:, -1, :].detach.assert_called_once()
            mock_tensor.detach.return_value.cpu.assert_called_once()

    @patch('gaims.agents.models.ChatHuggingFace')
    @patch('gaims.agents.models.AutoTokenizer')
    @patch('gaims.agents.models.AutoModelForCausalLM')
    @patch('gaims.agents.models.pipeline')
    def test_local_model_initialization_default_model(self, mock_pipeline_func, MockAutoModel, MockAutoTokenizer, MockChatHuggingFace):
        hf_repo_id = "unsloth/Llama-3.2-3B-Instruct" # Default for LocalModel
        activation_layers = ["model.layers.0.mlp", "model.layers.1.self_attn"]

        mock_tokenizer_instance = MagicMock(spec=AutoTokenizer)
        mock_tokenizer_instance.__class__ = AutoTokenizer
        MockAutoTokenizer.from_pretrained.return_value = mock_tokenizer_instance

        mock_model_instance = MagicMock(spec=AutoModelForCausalLM)
        mock_model_instance.__class__ = AutoModelForCausalLM
        mock_model_instance.name_or_path = hf_repo_id # Add name_or_path for HuggingFacePipeline validator
        MockAutoModel.from_pretrained.return_value = mock_model_instance
        mock_model_instance.config = MagicMock(architectures=["SomeModelForCausalLM"]) # Mock config for ActivationHook
        
        mock_pipeline_instance = MagicMock(spec=pipeline)
        mock_pipeline_instance.model.name_or_path = hf_repo_id # Mock name_or_path for HuggingFacePipeline validator
        mock_pipeline_func.return_value = mock_pipeline_instance
        
        mock_hf_pipeline_wrapper = MagicMock(spec=HuggingFacePipeline)
        mock_hf_pipeline_wrapper.model_id = hf_repo_id # Mock model_id for ChatHuggingFace
        MockHuggingFacePipeline.return_value = mock_hf_pipeline_wrapper

        mock_chat_hf_instance = MagicMock()
        MockChatHuggingFace.return_value = mock_chat_hf_instance

        local_model = LocalModel(activation_layers=activation_layers) # Use default model name

        self.assertIsNotNone(local_model._identifier)
        self.assertEqual(local_model.model_name, hf_repo_id) # Default for LocalModel
        MockAutoTokenizer.from_pretrained.assert_called_once_with(hf_repo_id)
        MockAutoModel.from_pretrained.assert_called_once_with(hf_repo_id, torch_dtype=torch.float16)
        mock_pipeline_func.assert_called_once_with(
            "text-generation", model=mock_model_instance, tokenizer=mock_tokenizer_instance, max_new_tokens=520
        )
        MockHuggingFacePipeline.assert_called_once_with(pipeline=mock_pipeline_instance)
        MockChatHuggingFace.assert_called_once_with(llm=mock_hf_pipeline_wrapper, model_id=hf_repo_id)
        self.assertEqual(local_model.llm, mock_chat_hf_instance)
        self.assertEqual(len(local_model.hooks), len(activation_layers))
        for layer_name in activation_layers:
            self.assertIn(layer_name, local_model.hooks)

    def test_get_activations_no_hooks(self):
        with (
            patch('gaims.agents.models.AutoModelForCausalLM.from_pretrained') as MockAutoModel,
            patch('gaims.agents.models.AutoTokenizer.from_pretrained') as MockAutoTokenizer,
            patch('gaims.agents.models.pipeline') as mock_pipeline,
        ):
            mock_model_instance = MagicMock(spec=AutoModelForCausalLM)
            mock_model_instance.__class__ = AutoModelForCausalLM
            mock_model_instance.name_or_path = "mock/model-test" # Add name_or_path for HuggingFacePipeline validator
            MockAutoModel.return_value = mock_model_instance
            MockAutoModel.return_value.config = MagicMock(architectures=["SomeModelForCausalLM"])
            mock_pipeline.return_value = MagicMock(tokenizer=MockAutoTokenizer.from_pretrained.return_value, model=mock_model_instance, spec=pipeline)
            local_model = LocalModel(activation_layers=[])
            with self.assertRaises(ValueError):
                local_model.get_activations("some_layer")

    def test_get_activations_with_mocked_hooks(self):
        with (
            patch('gaims.agents.models.AutoModelForCausalLM.from_pretrained') as MockAutoModel,
            patch('gaims.agents.models.AutoTokenizer.from_pretrained') as MockAutoTokenizer,
            patch('gaims.agents.models.pipeline') as mock_pipeline,
        ):
            MockAutoModel.return_value.config = MagicMock(architectures=["SomeModelForCausalLM"])
            local_model = LocalModel(hf_repo_id="test/local-model-test", activation_layers=["layer1"])
            
            # Mock the hooks attribute and its structure
            mock_hook = MagicMock()
            mock_tensor = MagicMock()
            mock_cpu_tensor = MagicMock()
            
            mock_hook.activations = mock_tensor
            mock_tensor.detach.return_value.cpu.return_value = mock_cpu_tensor
            
            local_model.hooks = {"layer1": mock_hook} # Manually set the mocked hooks
            
            activations = local_model.get_activations("layer1")
            
            self.assertEqual(activations, mock_cpu_tensor)
            mock_hook.activations[:, -1, :].detach.assert_called_once()
            mock_tensor.detach.return_value.cpu.assert_called_once()

    def test_get_activations_no_hooks(self):
        with (
            patch('gaims.agents.models.AutoModelForCausalLM.from_pretrained') as MockAutoModel,
            patch('gaims.agents.models.AutoTokenizer.from_pretrained') as MockAutoTokenizer,
            patch('gaims.agents.models.pipeline') as mock_pipeline,
        ):
            mock_model_instance = MagicMock(spec=AutoModelForCausalLM)
            mock_model_instance.__class__ = AutoModelForCausalLM
            mock_model_instance.name_or_path = "mock/model-test" # Add name_or_path for HuggingFacePipeline validator
            MockAutoModel.return_value = mock_model_instance
            MockAutoModel.return_value.config = MagicMock(architectures=["SomeModelForCausalLM"])
            mock_pipeline.return_value = MagicMock(tokenizer=MockAutoTokenizer.from_pretrained.return_value, model=mock_model_instance, spec=pipeline)
            local_model = LocalModel(activation_layers=[])
            with self.assertRaises(ValueError):
                local_model.get_activations("some_layer")

    def test_get_activations_with_mocked_hooks(self):
        with (
            patch('gaims.agents.models.AutoModelForCausalLM.from_pretrained') as MockAutoModel,
            patch('gaims.agents.models.AutoTokenizer.from_pretrained') as MockAutoTokenizer,
            patch('gaims.agents.models.pipeline') as mock_pipeline,
        ):
            MockAutoModel.return_value.config = MagicMock(architectures=["SomeModelForCausalLM"])
            local_model = LocalModel(hf_repo_id="test/local-model-test", activation_layers=["layer1"])
            
            # Mock the hooks attribute and its structure
            mock_hook = MagicMock()
            mock_tensor = MagicMock()
            mock_cpu_tensor = MagicMock()
            
            mock_hook.activations = mock_tensor
            mock_tensor.detach.return_value.cpu.return_value = mock_cpu_tensor
            
            local_model.hooks = {"layer1": mock_hook} # Manually set the mocked hooks
            
            activations = local_model.get_activations("layer1")
            
            self.assertEqual(activations, mock_cpu_tensor)
            mock_hook.activations[:, -1, :].detach.assert_called_once()
            mock_tensor.detach.return_value.cpu.assert_called_once()


if __name__ == '__main__':
    # To make logging output visible during tests if needed (optional)
    # logging.basicConfig(level=logging.INFO)
    unittest.main()