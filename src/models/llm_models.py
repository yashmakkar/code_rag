from src.utils.config import config
from langchain.chat_models import init_chat_model

llm = init_chat_model("gemini-2.5-flash-preview-05-20", temperature = 0, model_provider="google_genai")