import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from src.service.graph_services import GraphDB

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PythonCodeParser:
    """Enhanced Python code parser using Tree-sitter"""
    
    def __init__(self):
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)
        self.processed_nodes = set()  # Avoid duplicates
        self.imports = []
        self.graph_db = GraphDB()  
        
    def reset(self):
        """Reset parser state for new file"""
        self.processed_nodes.clear()
        self.imports.clear()
    
    def parse_file(self, file_path: str) -> tuple[List[Dict], List[Dict]]:
        """Parse a Python file and return nodes and relationships"""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            
            tree = self.parser.parse(bytes(content, "utf-8"))
            self.reset()
            
            # Start parsing from root
            self._parse_node(tree.root_node, file_path, None)
            
            # Create single import node for this file if imports exist
            self._create_import_node(file_path)
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return [], []
    
    def _parse_node(self, node: Node, file_path: str, parent_id: Optional[str]) -> None:
        """Recursively parse tree nodes"""
        file_name = Path(file_path).name
        
        # Handle different node types
        if node.type == "module":
            self._handle_module(node, file_path, file_name)
            
        elif node.type == "class_definition":
            class_id = self._handle_class_definition(node, file_path, parent_id)
            parent_id = class_id  # Update parent for children
            
        elif node.type == "function_definition":
            func_id = self._handle_function_definition(node, file_path, parent_id)
            parent_id = func_id  # Update parent for children
            
        elif node.type in ["import_statement", "import_from_statement"]:
            self._collect_import(node)
            
        elif node.type == "call":
            self._handle_method_call(node, parent_id)
        
        # Recursively process children
        for child in node.children:
            self._parse_node(child, file_path, parent_id)
    
    def _handle_module(self, node: Node, file_path: str, file_name: str) -> None:
        """Handle module node"""
        node_id = f"file:{file_name}"
        if node_id not in self.processed_nodes:
            labels = ["File"]
            properties = {
                "id": node_id,
                "name": file_name,
                "description": "",
                "file_path": file_path,
                "code_block": node.text.decode("utf-8")
            }
            self.graph_db.create_node(labels, properties)
            self.processed_nodes.add(node_id)
    
    def _handle_class_definition(self, node: Node, file_path: str, parent_id: Optional[str]) -> Optional[str]:
        """Handle class definition node"""
        class_name = self._extract_identifier(node)
        if not class_name:
            return None
        
        node_id = f"class:{class_name}"
        
        if node_id not in self.processed_nodes:
            # Extract docstring and base classes
            base_classes = self._extract_base_classes(node)

            labels = ["Class"]
            properties = {
                "id": node_id,
                "name": class_name,
                "description": "",
                "file_path": file_path,
                "base_classes": base_classes,
                "code_block": node.text.decode("utf-8")
            }
            self.graph_db.create_node(labels, properties)
            self.processed_nodes.add(node_id)

            # Create relationship with parent (file or class)
            if not parent_id:
                parent_id = f"file:{Path(file_path).name}"
            
            self._add_relationship(node_id, parent_id, "DEFINED_IN")
        
        return node_id
    
    def _handle_function_definition(self, node: Node, file_path: str, parent_id: Optional[str]) -> Optional[str]:
        """Handle function/method definition node"""
        func_name = self._extract_identifier(node)
        if not func_name:
            return None
            
        node_id = f"method:{func_name}" 
        
        if node_id not in self.processed_nodes:
            # Extract function details
            is_async = any(child.type == "async" for child in node.children)
            parameters = self._extract_parameters(node)

            labels = ["Method"]
            properties = {
                "id": node_id,
                "name": func_name,
                "description": "",
                "file_path": file_path,
                "method_type": "async" if is_async else "sync",
                "parameters": parameters,
                "code_block": node.text.decode("utf-8")
            }
            
            self.graph_db.create_node(labels, properties)
            self.processed_nodes.add(node_id)

            # Create relationship with parent (file or class)
            if not parent_id:
                parent_id = f"file:{Path(file_path).name}"
            
            self._add_relationship(node_id, parent_id, "DEFINED_IN")
        
        return node_id
    
    def _collect_import(self, node: Node) -> None:
        """Collect import statements for later processing"""
        import_info = node.text.decode('utf-8').strip()
        if import_info:
            self.imports.append(import_info)
    
    def _create_import_node(self, file_path: str) -> None:
        """Create a single import node for all imports in the file"""
        imports = self.imports
        if not imports:
            return
            
        file_name = Path(file_path).name
        import_id = f"import:{file_name}"

        labels = ["Import"]
        properties = {
            "id": import_id,
            "name": "imports",
            "description": f"All imports for {file_name}",
            "file_path": file_path,
            "code_block": "\n".join(imports)
        }
        
        self.graph_db.create_node(labels, properties)
        self.processed_nodes.add(import_id)
        
        # Link to file
        file_id = f"file:{file_name}"
        self._add_relationship(import_id, file_id, "IMPORTS_FOR")
    
    def _handle_method_call(self, node: Node, parent_id: Optional[str]) -> None:
        """Handle method calls"""
        if not node.children:
            return
            
        method_node = node.children[0]
        method_name = self._extract_method_name(method_node)
        
        if method_name and parent_id:
            # Create relationship showing method usage
            method_id = f"method:{method_name}"
            self._add_relationship(method_id, parent_id, "CALLED_IN")
    
    def _extract_identifier(self, node: Node) -> Optional[str]:
        """Extract identifier name from node"""
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode('utf-8')
        return None
    
    def _extract_base_classes(self, node: Node) -> List[str]:
        """Extract base classes from class definition"""
        base_classes = []
        for child in node.children:
            if child.type == "argument_list":
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        base_classes.append(grandchild.text.decode('utf-8'))
        return base_classes
    
    def _extract_parameters(self, node: Node) -> List[str]:
        """Extract parameters from function definition"""
        parameters = []
        for child in node.children:
            if child.type == "parameters":
                for param in child.children:
                    if param.type == "identifier":
                        parameters.append(param.text.decode('utf-8'))
                    elif param.type == "typed_parameter":
                        # Extract parameter name from typed parameter
                        for subchild in param.children:
                            if subchild.type == "identifier":
                                parameters.append(subchild.text.decode('utf-8'))
                                break
        return parameters
    
    def _extract_method_name(self, node: Node) -> Optional[str]:
        """Extract method name from call node"""
        if node.type == "identifier":
            return node.text.decode('utf-8')
        elif node.type == "attribute":
            # Handle self.method() or super().method()
            text = node.text.decode('utf-8')
            if "." in text:
                return text.split(".")[-1]
        return None
    
    def _add_relationship(self, start_id: str, end_id: str, label: str, properties: Dict = None):
        """Add relationship between nodes"""
        if properties is None:
            properties = {}
        
        self.graph_db.create_node_and_relationship(start_id, end_id, label, properties)


