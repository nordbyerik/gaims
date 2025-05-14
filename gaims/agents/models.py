import os
import logging
import random
import string
from abc import ABC

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFacePipeline, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from games.action import Action
from communication.communication import Message

from pydantic import BaseModel, Field
from typing import Literal, List

log = logging.getLogger(__name__)
logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

class MessageStructure(BaseModel):
    message: str = Field(description="The message to send")
    recipient: int | List[int] = Field(description="The recipient of the message")

class ActionStructure(BaseModel):
    action_id: int = Field(description="The action to take")

class ModelConfig():
    def __init__(self, model_name: str):
        self.model_name = model_name


class Model(ABC):
    def __init__(self, identifier: str | None = None, model_name: str = "unsloth/Llama-3.2-3B-Instruct"):
        self._identifier = identifier or "".join(
            random.choices(string.ascii_lowercase, k=5)
        )
        self.model_name = model_name

    def send_message(self, message: str, structure: BaseModel | None = None, system_prompt: str | None = None) -> str | BaseModel:
        log.info(f"--> {self._identifier}: {message}")

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        messages.append(HumanMessage(content=message))
        structure = structure

        if structure is not None:
            llm = self.llm.with_structured_output(structure)
        else:
            llm = self.llm

        response = llm.invoke(messages)
        log.info(f"{self._identifier} -->: {response}")
        return response

    def observe(self, message: str, **kwargs) -> str:
        return self.send_message(message, **kwargs)
    
    def communicate(self, message: str, **kwargs) -> Message:
        # TODO: Make this more complex
        response = self.send_message(message, structure=MessageStructure, **kwargs)
        return response
    
    def act(self, message: str, **kwargs) -> Action:
        response = self.send_message(message, structure=ActionStructure, **kwargs)
        return response

    
class GeminiModel(Model):
    def __init__(self, identifier: str | None = None, model: str = "gemini-2.0-flash"):
        super().__init__(identifier, model)
        self.llm = ChatGoogleGenerativeAI(model=model, api_key=os.getenv("GEMINI_API_KEY"))
    

class LocalModel(Model):
    def __init__(self, identifier: str | None = None, 
                 model: str = "EleutherAI/pythia-14m" #google/gemma-3-1b-it
                 ):
        super().__init__(identifier, model)
        
        pipe = HuggingFacePipeline.from_model_id(
            model_id="Qwen/Qwen3-0.6B",
            task="text-generation",
            # device=0,  # replace with device_map="auto" to use the accelerate library.
            pipeline_kwargs={"max_new_tokens": 100, "pad_token_id":0},
        )

        from langchain_huggingface import HuggingFaceEndpoint
        llm = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen3-0.6B",
            task="text-generation",
            max_new_tokens=512,
            do_sample=False,
            repetition_penalty=1.03,
        )

        self.llm = ChatHuggingFace(llm=llm)
    
    def get_activations(self, layer):
        return self.hooks[layer].activations[:, -1, :].detach().cpu()
    

class ModelFactory:
    @staticmethod
    def create_model(model_config: ModelConfig) -> Model:
        if model_config.model_name == "local":
            return LocalModel() 
        else:
            return GeminiModel()
        