from src.service.python_code_parser import PythonCodeParser


parser = PythonCodeParser()
    
# Replace with your file path
file_path = "/Users/yashmakkar/Documents/Project/code_rag/temp_dir/test_samples/agent_to_agent/agent_1/agent1.py"


parser.parse_file(file_path)
