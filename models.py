import logging
import os
import random
import string
from google import genai
from abc import ABC, abstractmethod

# Use Gemini for now since it has a free API.
# Ideally we would end up using two models from different labs.
GEMINI_CLIENT = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

log = logging.getLogger("hot")


class Model(ABC):
    @abstractmethod
    def send_message(self, message: str) -> str:
        pass


class Gemini(Model):
    def __init__(self, identifier: str | None = None, model: str = "gemini-2.0-flash"):
        self.client = GEMINI_CLIENT
        self._chat = GEMINI_CLIENT.chats.create(model=model)
        self._identifier = identifier or "".join(
            random.choices(string.ascii_lowercase, k=5)
        )

    def send_message(self, message: str) -> str:
        log.info(f"--> {self._identifier}: {message}")
        response = self._chat.send_message(message).text
        log.info(f"{self._identifier} -->: {response}")
        return response
