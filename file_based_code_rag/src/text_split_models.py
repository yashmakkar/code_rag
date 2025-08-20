from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from src.utils.data_config import CHUNK_SIZE, CHUNK_OVERLAP



HEADERS_TO_SPLIT_ON = [
    ("#", "Header 1"),
    ("##", "Header 2"),
]

md_splitter = MarkdownHeaderTextSplitter(HEADERS_TO_SPLIT_ON)

recursive_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    is_separator_regex=False,
)