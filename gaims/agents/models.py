import logging
import os
import random
import string
from google import genai
from abc import ABC, abstractmethod

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpoint


from typing import List
import torch
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer
from utils.activation_hook import ActivationHook

from communication.communication import Message



# Use Gemini for now since it has a free API.
# Ideally we would end up using two models from different labs.

log = logging.getLogger("hot")

class ModelConfig():
    def __init__(self):
        pass

class Model(ABC):
    def __init__(self, identifier: str | None = None, model_name: str = "unsloth/Llama-3.2-3B-Instruct"):
        self._identifier = identifier or "".join(
            random.choices(string.ascii_lowercase, k=5)
        )
        self.model_name = model_name

    @abstractmethod
    def send_message(self, message: str) -> str:
        pass


class GeminiModel(Model):
    def __init__(self, identifier: str | None = None, model: str = "gemini-2.0-flash"):
        super().__init__(identifier, model)
        self.llm = ChatGoogleGenerativeAI(model=model)

    def send_message(self, message: str, structure=None) -> str:
        log.info(f"--> {self._identifier}: {message}")
        
        if structure is not None:
            llm = self.llm.with_structured_output(structure)
        else:
            llm = self.llm

        response = llm.invoke(message).text
        log.info(f"{self._identifier} -->: {response}")
        return response
    

from pydantic import BaseModel, Field
from typing import Literal

class MessageStructure(BaseModel):
    message: str = Field()
    recipient: int = Field()

class ActionStructure(BaseModel):
    action: Literal[0, 1] = Field()



class LocalModel(Model):
    # TODO: Create a model config
    def __init__(self, identifier: str | None = None, 
                 model: str = "unsloth/Llama-3.2-3B-Instruct", 
                 selected_layers: List[str] = ["model.layers.15.mlp"]
                 ):
        self.model_string = model
        self.model = AutoModelForCausalLM.from_pretrained(model, load_in_4bit=True)
        self.model.eval()
        self.tokenizer = AutoTokenizer.from_pretrained(model)

        self.hooks = {}
        for layer in selected_layers:
            self.hooks[layer] = ActivationHook(self.model, layer)
    
    def observe(self, message: str) -> str:
        return self.send_message(message)
    
    def communicate(self, message: str) -> Message:
        # TODO: Make this more complex
        response = self.send_message(message, )
        message_sender = self._identifier
        message = Message(sender=message_sender, content=response)

    def send_message(self, message: str, response_type: str = "full_response"):
        if response_type == "full_response":
            return self.generate_response(message)
        elif response_type == "logits":
            return self.generate_response_from_logits(message)
        elif response_type == "plain_text":
            return self.generate_response_from_plain_text(message)

    def generate_response(self, message: str):
        inputs = self.tokenizer(message, return_tensors="pt")
        outputs = self.model.generate(**inputs)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def generate_response_from_plain_text(self, message: str, options=["0", "1"]):
        inputs = self.tokenizer(message, return_tensors="pt")
        outputs = self.model.generate(**inputs, max_new_tokens=5)
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer_text = generated_text[len(message):].strip()
        for option in options:
            if option in answer_text:
                return option
        
        return np.random.randint(0, 1)
    
    def generate_response_from_logits(self, message, options=["0", "1"]):
        inputs = self.tokenizer(message, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs.to(self.model.device))

        option_probs = torch.zeros(len(options))
        for option in options:
            
            option_token_id = self.tokenizer(option, return_tensors="pt", add_special_tokens=False).input_ids[-1] # Shape [1]

            # Calculate the logit value (result is shape [1])
            logit_tensor = outputs.logits[0, -1, option_token_id]

            option_probs[options.index(option)] = logit_tensor.item()

        return np.argmax(option_probs)
    
    def get_activations(self, layer):
        return self.hooks[layer].activations[:, -1, :].detach().cpu()