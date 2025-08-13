import os
import logging
import random
import string
from abc import ABC

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from transformers import PreTrainedTokenizer

from langchain_huggingface import HuggingFacePipeline  # Corrected import name if it was an issue
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from gaims.utils.huggingface_langchain import ChatHuggingFace

# Assuming these are correctly defined in your project structure
from gaims.games.action import Action # type: ignore
from gaims.communication.communication import Message # type: ignore
from gaims.utils.parse_special_tokens import parse_special_tokens

from pydantic import BaseModel, Field
from typing import List # type: ignore
import torch

import re

log = logging.getLogger(__name__)
logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

class StructureParsingException(Exception):
    def __init__(self, message: str, value: str, structure: BaseModel):
        super().__init__(message)
        self.value = value
        self.structure = structure

class MessageStructure(BaseModel):
    message_content: str = Field(description="The message to send")
    receiver: List[int] = Field(description="The recipient of the message")

class ActionStructure(BaseModel):
    action_id: int = Field(description="The action to take")

class ModelConfig():

    def __init__(
        self,
        model_name: str,
        activation_layers: list[str] | None = None,
        max_tokens: int = 1024,
    ):  # model_name here is the HF repo ID or "gemini"
        self.model_name = model_name
        self.activation_layers = activation_layers
        self.max_tokens = max_tokens


class Model(ABC):
    def __init__(self, identifier: str | None = None, model_name: str = "unsloth/Llama-3.2-3B-Instruct"):
        self._identifier = identifier if identifier is not None else "".join(
            random.choices(string.ascii_lowercase, k=5)
        )
        # For local models, model_name will store the Hugging Face repository ID
        self.model_name = model_name

    def send_message(self, message: str, structure: BaseModel | None = None, system_prompt: str | None = None) -> str | BaseModel: # type: ignore
        """
        Sends a message to the language model and returns the response, optionally parsed into a Pydantic model.

        Args:
            message: The primary message content to send to the model.
            structure: An optional class. If provided, the model's response
                       will be parsed into an instance of this class.
            system_prompt: An optional system message to guide the model's behavior.

        Returns:
            If `structure` is provided, returns an instance of the `structure` BaseModel.
            Otherwise, returns the raw string response from the model.

        Raises:
            StructureParsingException: If the raw response content cannot be converted to the structure.
            ValueError: If the generation begin token is not found in the model's response.
        """

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=message))

        if structure is not None:
            response_content, raw = self._handle_structured_response(messages, structure)
        else:
            response_content = raw = self._handle_unstructured_response(messages)

        return response_content, raw

    def _handle_structured_response(self, messages: list[BaseMessage], structure: BaseModel) -> BaseModel:
        llm_with_structure = self.llm.with_structured_output(structure, include_raw=True) # type: ignore
        full_response = llm_with_structure.invoke(messages)

        # Manually parse response
        raw_response_content = full_response.get("raw", HumanMessage(content="")).content # type: ignore

        assistant_response = raw_response_content.split(messages[-1].content)[-1]

        # If parsed return
        if parsed := full_response.get("parsed"):
            return parsed, assistant_response

        try:
            return structure.model_validate_json(raw_response_content), assistant_response # type: ignore
        except Exception as e:
            if structure == MessageStructure:
                return assistant_response, assistant_response

            elif structure == ActionStructure:
                numbers = re.findall(r"\d+", assistant_response)
                if numbers:
                    return int(numbers[-1]), assistant_response

            raise StructureParsingException(
                f"Failed to parse extracted content into structure",
                raw_response_content,
                structure,
            )

    def _handle_unstructured_response(self, messages: list[BaseMessage]) -> str:
        response_content = self.llm.invoke(messages).content
        response_content = response_content.split(messages[-1].content)[-1]
        return response_content
    def observe(self, message: str, **kwargs) -> str: # type: ignore
        response, raw = self.send_message(message, **kwargs)
        if not isinstance(response, str):
            return str(response)
        return response, raw

    def communicate(self, message: str, **kwargs) -> Message: # type: ignore
        response, raw = self.send_message(message, structure=MessageStructure, **kwargs)

        if isinstance(response, MessageStructure):
            reciever = response.receiver if response.receiver else None
            message_content = (
                response.message_content if response.message_content else None
            )
            raw = message_content
        elif isinstance(response, str):
            reciever = None
            message_content = response
        else:
            reciever = None
            message_content = str(response)

        split_message_content = message_content.split("FINAL_MESSAGE")[-1]

        return Message(sender=self._identifier, receiver=reciever, message_content=split_message_content), raw  # type: ignore

    def act(self, message: str, **kwargs) -> Action: # type: ignore
        response, raw = self.send_message(message, structure=ActionStructure, **kwargs)
        if not isinstance(response, ActionStructure):
            if isinstance(response, int):
                return Action(agent_id=self._identifier, action_id=response), raw
            raise TypeError(f"Expected ActionStructure, got {type(response)}")
        return Action(agent_id=self._identifier, action_id=response.action_id), raw # type: ignore


class RandomModel(Model):
    def __init__(self, identifier: str | None = None, model: str = "random"):
        super().__init__(identifier, model)

    def send_message(self, message: str, structure: BaseModel | None = None, system_prompt: str | None = None) -> str | BaseModel: # type: ignore
        return random.randint(0, 1), "Here's a random choice"

class GeminiModel(Model):
    def __init__(self, identifier: str | None = None, model: str = "gemini-2.0-flash-lite"): # Updated default model
        super().__init__(identifier, model) # Pass model string (e.g. "gemini-1.5-flash") as model_name
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.llm = ChatGoogleGenerativeAI(model=self.model_name, google_api_key=gemini_api_key) # Use self.model_name


from gaims.utils.activation_hook import ActivationHook

class LocalModel(Model):
    # Parameter 'hf_repo_id' is the string like "microsoft/Phi-3-mini-4k-instruct"
    def __init__(
        self,
        hf_repo_id: str = "openai/gpt-oss-20b",
        activation_layers: list[str] | None = None,
        max_tokens: int = 1024,
    ):
        # Pass hf_repo_id as both the instance identifier and the model_name to the base class.
        super().__init__(identifier=hf_repo_id, model_name=hf_repo_id)

        # Load tokenizer and model using the provided hf_repo_id
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name) # Use self.model_name (which is hf_repo_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name, torch_dtype=torch.bfloat16
        )

        pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=max_tokens,
        )
        hf_pipeline_wrapper = HuggingFacePipeline(pipeline=pipe)

        # CRITICAL FIX: Explicitly pass the hf_repo_id as model_id to ChatHuggingFace.
        self.llm = ChatHuggingFace(llm=hf_pipeline_wrapper, model_id=self.model_name)
        self.hooks = {}
        if activation_layers:
            self._register_hooks(activation_layers)

    def _register_hooks(self, layer_names: list):
        for layer_name in layer_names:
            self.hooks[layer_name] = ActivationHook(self.model, layer_name)

    def get_activations(self, layer_name: str):
        if layer_name in self.hooks:
            return self.hooks[layer_name].activations
        else:
            raise ValueError(f"No activation hook registered for layer: {layer_name}")

    def send_message(self, message: str, structure: BaseModel | None = None, system_prompt: str | None = None) -> str | BaseModel: # type: ignore

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=message))

        if structure is not None:
            response_content, raw = self._handle_structured_response(messages, structure)
        else:
            response_content = raw = self._handle_unstructured_response(messages)

        return response_content, raw

    def _handle_structured_response(self, messages: list[BaseMessage], structure: BaseModel) -> BaseModel:
        """
        Handles sending messages to the LLM when a structured response is expected.

        Args:
            messages: A list of BaseMessage objects to send to the LLM.
            structure: The Pydantic BaseModel class to parse the response into.
            tokenizer: The tokenizer used for cleaning the model's response.

        Returns:
            An instance of the provided `structure` BaseModel with data from the LLM's response.

        Raises:
            StructureParsingException: If the raw response content cannot be converted to the structure.
            ValueError: If the generation begin token is not found in the model's response.
        """
        llm_with_structure = self.llm.with_structured_output(structure, include_raw=True) # type: ignore
        full_response = llm_with_structure.invoke(messages)

        raw_response_content = full_response.get("raw", HumanMessage(content="")).content # type: ignore

        assistant_response = raw_response_content.split(messages[-1].content)[-1]
        assistant_response = self._clean_model_tags(assistant_response)

        if parsed := full_response.get("parsed"):
            return parsed, assistant_response  # type: ignore

        # If we tried to get an object but failed... just return the raw content
        if structure == MessageStructure:
            return assistant_response, assistant_response

        elif structure == ActionStructure:
            numbers = re.findall(r"\d+", assistant_response)
            if numbers:
                return int(numbers[-1]), assistant_response

        raise StructureParsingException(
            f"Failed to parse extracted content into structure",
            raw_response_content,
            structure,
        )

    def _handle_unstructured_response(self, messages: list[BaseMessage]) -> str:
        """
        Handles sending messages to the LLM when an unstructured string response is expected.

        Args:
            messages: A list of BaseMessage objects (system and human messages) to send to the LLM.
            tokenizer: The tokenizer used for cleaning the model's response.

        Returns:
            A string containing the cleaned response content from the LLM.

        Raises:
            ValueError: If the generation prompt is not found in the model's response
                        during the cleaning process.
        """
        response_content = self.llm.invoke(messages).content
        response_content = response_content.split(messages[-1].content)[-1]
        response_content = self._clean_model_tags(response_content)
        return response_content

    def _clean_model_tags(self, text: str) -> str:
        """
        Extracts and cleans the model's generated text from the raw response.

        Args:
            text: The raw response text from the model.
            tokenizer: The tokenizer associated with the model, used to identify
                       the generation prompt and special tokens.

        Returns:
            The cleaned text string.

        Raises:
            ValueError: If `tokenizer.apply_chat_template` does not produce a string found within 
                        the input `text`.
        """

        # Strip any additional special tokens
        token_ids = self.tokenizer.encode(text, add_special_tokens=False)
        cleaned_text = self.tokenizer.decode(token_ids, skip_special_tokens=True)

        cleaned_text = cleaned_text.strip()

        return cleaned_text


global model_registry
model_registry = {} # type: ignore

class ModelFactory:
    @staticmethod
    def create_model(model_config: ModelConfig) -> Model:
        requested_model_name = model_config.model_name # This is "gemini" or an HF repo_id

        if requested_model_name == "gemini":
            if "gemini" not in model_registry: # Cache Gemini model instance as well
                model_registry["gemini"] = GeminiModel(identifier="gemini_default_instance", model="gemini-2.0-flash-lite")
            return model_registry["gemini"]
        elif requested_model_name == "random":
            if "random" not in model_registry:
                model_registry["random"] = RandomModel()
            return model_registry["random"]
        else:
            # requested_model_name is treated as a Hugging Face repo_id
            hf_repo_id = requested_model_name

            if hf_repo_id not in model_registry:
                # Pass the hf_repo_id to LocalModel constructor
                model_registry[hf_repo_id] = LocalModel(
                    hf_repo_id=hf_repo_id,
                    activation_layers=model_config.activation_layers,
                    max_tokens=model_config.max_tokens,
                )
            return model_registry[hf_repo_id]
