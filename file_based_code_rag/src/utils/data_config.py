CODE_EXTENSIONS = [".py", ".js", ".jsx", ".java", ".cpp", ".c", ".rb", ".go", ".php", ".ts", ".tsx", ".swift", ".sh", ".html"]
CONFIG_FILE_EXTENSIONS = [".json", ".yml", ".yaml", ".xml"]
DOCUMENT_EXTENSIONS = [".md", ".txt"]
BUILD_EXTENSIONS = ["Dockerfile", "Makefile"]

ALLOWED_FILE_EXTENSIONS = CODE_EXTENSIONS + CONFIG_FILE_EXTENSIONS + BUILD_EXTENSIONS
ALLOWED_FILE_SIZE = 100000     # In bytes
CHUNK_SIZE = 150       # Characters
CHUNK_OVERLAP = 30       # Characters