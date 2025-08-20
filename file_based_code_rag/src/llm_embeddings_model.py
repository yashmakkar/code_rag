from langchain.chat_models import init_chat_model
from langchain_huggingface import HuggingFaceEmbeddings
from src.utils.config import config


openai_llm = init_chat_model(model="openai:gpt-4o-mini", api_key=config.openai_api_key)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")