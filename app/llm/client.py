from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-4o"):
        self._api_key = api_key
        self._base_url = base_url
        self.model = model
        self._client = None

    def _get_api_key(self):
        return self._api_key or os.getenv("OPENAI_API_KEY")

    def _get_base_url(self):
        return self._base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def initialize(self):
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("No API key provided, LLM will use fallback mode")
            self._client = None
            return False

        try:
            self._client = ChatOpenAI(
                api_key=api_key,
                base_url=self._get_base_url(),
                model=self.model,
                temperature=0.7,
            )
            logger.info(f"LLM initialized with model: {self.model}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self._client = None
            return False

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self._client:
            return None

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            response = self._client.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return None

    def is_available(self) -> bool:
        return self._client is not None


llm_client = LLMClient()
