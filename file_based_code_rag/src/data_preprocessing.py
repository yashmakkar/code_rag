import asyncio
from typing import List, Dict, Any
from langchain.schema import SystemMessage, HumanMessage
from langchain_core.documents import Document
from src.text_split_models import md_splitter, recursive_splitter
from src.github_services import Github


def zip_file_data(files: List[str], contents: List[str]) -> List[Dict[str, str]]:
    """Pair file paths with contents, skipping empty entries."""
    return [
        {"file_path": file, "content": content}
        for file, content in zip(files, contents)
        if content.strip()
    ]


def split_documentation_docs(docs: List[Dict[str, Any]]) -> List[Document]:
    """
    Split documentation files (Markdown and plain text) into smaller chunks.

    Args:
        docs: List of {"file_path": str, "content": str}

    Returns:
        List of LangChain Document objects with split content and metadata.
    """
    splitted_data: List[Document] = []

    for data in docs:
        file_path = data.get("file_path")
        content = data.get("content")

        if not file_path or not content:
            continue

        # Choose splitter based on file extension
        splitter = md_splitter if file_path.lower().endswith(".md") else recursive_splitter
        split_docs = splitter.split_text(content)

        for doc in split_docs:
            splitted_data.append(
                Document(
                    page_content=doc.page_content,
                    metadata={"file_path": file_path, **doc.metadata},
                )
            )

    return splitted_data


def create_input(file_text: str) -> List:
    """Create the system + human messages for LLM code summarization."""
    return [
        SystemMessage(
            content = """
            You are a large language‑model designed to assist with code analysis and documentation.
            When presented with a block of source code, produce a *concise yet comprehensive* natural‑language description
            that captures the code’s intent, structure, and key behavior.  This description will be stored in an embedding
            vector and used for similarity search in a Code Retrieval‑Augmented Generation (Code‑RAG) system.

            Guidelines for the description:

            1. **High‑level Overview** (1‑2 sentences)
                - Summarize the purpose of the code block and the problem it solves.

            2. **Structure & Components** (2‑4 sentences)
                - List the main modules, classes, and functions, including their main responsibilities.

            3. **Key Algorithms & Logic** (3‑5 sentences)
                - Describe the core logic or algorithmic steps in plain language.
                - Highlight any non‑obvious control flow, data structures, or recursion.

            4. **Edge Cases & Robustness** (1‑2 sentences)
                - Note any boundary conditions, error handling, or validation performed.

            5. **Complexity & Performance** (1‑2 sentences)
                - Mention time/space complexity of the most expensive part, if applicable.

            6. **Design Decisions / Trade‑offs** (optional, 1 sentence)
                - Briefly state a notable architectural or API choice that could affect usage.

            **Formatting Rules** 

            - Use clear, short sentences.
            - Avoid code fragments; refer to identifiers by name only.
            - Keep the total length < 150 words to ensure a lightweight embedding.
            - End with a brief sentence that can serve as a vector label if needed.

            **Example Output** 
            
            This code defines a thread‑safe Least‑Recently‑Used (LRU) cache that stores up to maxSize items. 
            It exposes get(key), set(key, value), and remove(key) methods.
            Internally, a doubly‑linked list tracks usage order while a hash map provides O(1) lookups.
            When set exceeds maxSize, the tail node is evicted.
            All operations lock a mutex to guarantee thread safety.
            Time complexity is O(1) per operation, with O(n) memory overhead for n entries.
            The cache prioritizes recent access patterns, making it suitable for database result caching.```
            """
        ),
        HumanMessage(
            content=file_text
        )
    ]


async def generate_descriptions(llm: Any, files: List[Dict[str, str]]) -> List[Document]:
    """
    Generate natural-language code descriptions using an LLM.

    Args:
        llm: Async LangChain-compatible model
        files: List of {"file_path": str, "content": str}

    Returns:
        List of Documents, each containing LLM-generated description + metadata
    """
    tasks = [
        llm.ainvoke(create_input(file["content"]))
        for file in files
        if file.get("content")
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    docs: List[Document] = []
    for file, result in zip(files, results):
        if isinstance(result, Exception):
            # Skip failed generations but keep record if needed
            continue
        docs.append(
            Document(
                page_content=result.content,
                metadata={
                    "file_path": file["file_path"],
                    "code": file["content"],
                },
            )
        )
    return docs


async def build_repo_index(llm: Any, github_client: Github) -> List[Document]:
    """
    Full pipeline for building repo index for RAG:

    1. Fetch repository code + documentation files
    2. Download relevant contents
    3. Generate natural language descriptions for code
    4. Split documentation into chunks
    5. Consolidate everything into a Document list
    """
    code_files, doc_files = await github_client.get_all_useful_files()

    code_content, doc_content = await asyncio.gather(
        github_client.download_useful_files(code_files),
        github_client.download_useful_files(doc_files),
    )

    # Pair files & contents
    code_data = zip_file_data(code_files, code_content)
    doc_data = zip_file_data(doc_files, doc_content)

    # Generate code summaries with LLM
    code_docs = await generate_descriptions(llm, code_data)

    # Split documentation into chunks
    splitted_docs = split_documentation_docs(doc_data)

    # Consolidate for final indexing
    return code_docs + splitted_docs
