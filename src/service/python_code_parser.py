import tree_sitter_python as tspython
from tree_sitter import Language, Parser
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NodeInfo:
    """Data class for node information"""
    node_id: str
    node_type: str
    name: str
    file_path: str
    properties: Dict = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}

class PythonCodeParser:
    """Enhanced Python code parser using Tree-sitter"""
    
    def __init__(self):
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)
        self.nodes = []
        self.relationships = []
        self.processed_nodes = set()  # Avoid duplicates
        
    def reset(self):
        """Reset parser state for new file"""
        self.nodes.clear()
        self.relationships.clear()
        self.processed_nodes.clear()
    
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
            
            return self.nodes, self.relationships
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return [], []
    
    def _parse_node(self, node, file_path: str, parent_id: Optional[str]):
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
            self._handle_import(node, file_path)
            
        elif node.type == "call":
            self._handle_method_call(node, file_path, parent_id)
        
        # Recursively process children
        for child in node.children:
            self._parse_node(child, file_path, parent_id)
    
    def _handle_module(self, node, file_path: str, file_name: str):
        """Handle module node"""
        node_id = f"file:{file_name}"
        if node_id not in self.processed_nodes:
            self.nodes.append({
                "type": "node",
                "id": node_id,
                "labels": ["File"],
                "properties": {
                    "name": file_name,
                    "description": "",
                    "file_path": file_path,
                    "size": len(node.text) if node.text else 0
                }
            })
            self.processed_nodes.add(node_id)
    
    def _handle_class_definition(self, node, file_path: str, parent_id: Optional[str]) -> str:
        """Handle class definition node"""
        class_name = self._extract_identifier(node)
        if not class_name:
            return None
            
        node_id = f"class:{class_name}"
        
        if node_id not in self.processed_nodes:
            # Extract docstring and base classes
            docstring = self._extract_docstring(node)
            base_classes = self._extract_base_classes(node)
            
            self.nodes.append({
                "type": "node",
                "id": node_id,
                "labels": ["Class"],
                "properties": {
                    "name": class_name,
                    "description": docstring or "",
                    "file_path": file_path,
                    "base_classes": base_classes,
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1
                }
            })
            self.processed_nodes.add(node_id)
            
            # Create relationship with parent (file or class)
            if not parent_id:
                parent_id = f"file:{Path(file_path).name}"
            
            self._add_relationship(node_id, parent_id, "DEFINED_IN")
        
        return node_id
    
    def _handle_function_definition(self, node, file_path: str, parent_id: Optional[str]) -> str:
        """Handle function/method definition node"""
        func_name = self._extract_identifier(node)
        if not func_name:
            return None
            
        node_id = f"method:{func_name}"
        
        if node_id not in self.processed_nodes:
            # Extract function details
            is_async = any(child.type == "async" for child in node.children)
            docstring = self._extract_docstring(node)
            parameters = self._extract_parameters(node)
            
            self.nodes.append({
                "type": "node",
                "id": node_id,
                "labels": ["Method"],
                "properties": {
                    "name": func_name,
                    "description": docstring or "",
                    "file_path": file_path,
                    "method_type": "async" if is_async else "sync",
                    "parameters": parameters,
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1
                }
            })
            self.processed_nodes.add(node_id)
            
            # Create relationship with parent
            if not parent_id:
                parent_id = f"file:{Path(file_path).name}"
            
            self._add_relationship(node_id, parent_id, "DEFINED_IN")
        
        return node_id
    
    def _handle_import(self, node, file_path: str):
        """Handle import statements"""
        import_text = node.text.decode('utf-8') if node.text else ""
        if not import_text.strip():
            return
            
        # Extract imported modules/items
        imported_items = []
        if node.type == "import_statement":
            # Handle: import module1, module2
            for child in node.children:
                if child.type == "dotted_as_names" or child.type == "aliased_import":
                    imported_items.extend(self._extract_import_items(child))
        elif node.type == "import_from_statement":
            # Handle: from module import item1, item2
            for child in node.children:
                if child.type == "import_list":
                    imported_items.extend(self._extract_import_items(child))
        
        if imported_items:
            file_name = Path(file_path).name
            import_id = f"import:{file_name}:{hash(import_text)}"
            
            if import_id not in self.processed_nodes:
                self.nodes.append({
                    "type": "node",
                    "id": import_id,
                    "labels": ["Import"],
                    "properties": {
                        "name": "import",
                        "description": import_text,
                        "file_path": file_path,
                        "imported_items": imported_items,
                        "line_number": node.start_point[0] + 1
                    }
                })
                self.processed_nodes.add(import_id)
                
                # Link to file
                file_id = f"file:{file_name}"
                self._add_relationship(import_id, file_id, "IMPORTED_IN")
    
    def _handle_method_call(self, node, file_path: str, parent_id: Optional[str]):
        """Handle method calls"""
        if not node.children:
            return
            
        method_node = node.children[0]
        method_name = self._extract_method_name(method_node)
        
        if method_name and parent_id:
            # Create relationship showing method usage
            method_id = f"method:{method_name}"
            self._add_relationship(method_id, parent_id, "CALLED_IN")
    
    def _extract_identifier(self, node) -> Optional[str]:
        """Extract identifier name from node"""
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode('utf-8')
        return None
    
    def _extract_docstring(self, node) -> Optional[str]:
        """Extract docstring from function/class"""
        # Look for first string literal in the body
        for child in node.children:
            if child.type == "block":
                for grandchild in child.children:
                    if grandchild.type == "expression_statement":
                        for ggchild in grandchild.children:
                            if ggchild.type == "string":
                                text = ggchild.text.decode('utf-8')
                                # Remove quotes and clean up
                                return text.strip('"\'').strip()
        return None
    
    def _extract_base_classes(self, node) -> List[str]:
        """Extract base classes from class definition"""
        base_classes = []
        for child in node.children:
            if child.type == "argument_list":
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        base_classes.append(grandchild.text.decode('utf-8'))
        return base_classes
    
    def _extract_parameters(self, node) -> List[str]:
        """Extract parameters from function definition"""
        parameters = []
        for child in node.children:
            if child.type == "parameters":
                for param in child.children:
                    if param.type == "identifier":
                        parameters.append(param.text.decode('utf-8'))
                    elif param.type == "default_parameter":
                        # Extract parameter name from default parameter
                        for subchild in param.children:
                            if subchild.type == "identifier":
                                parameters.append(subchild.text.decode('utf-8'))
                                break
        return parameters
    
    def _extract_import_items(self, node) -> List[str]:
        """Extract imported items from import node"""
        items = []
        if node.type == "identifier":
            items.append(node.text.decode('utf-8'))
        else:
            for child in node.children:
                if child.type == "identifier":
                    items.append(child.text.decode('utf-8'))
                elif child.type == "aliased_import":
                    # Handle "as" imports
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            items.append(subchild.text.decode('utf-8'))
                            break
        return items
    
    def _extract_method_name(self, node) -> Optional[str]:
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
            
        relationship = {
            "type": "relationship",
            "start": {"id": start_id},
            "end": {"id": end_id},
            "label": label,
            "properties": properties
        }
        
        # Avoid duplicate relationships
        rel_key = f"{start_id}-{label}-{end_id}"
        if not any(rel_key == f"{r['start']['id']}-{r['label']}-{r['end']['id']}" for r in self.relationships):
            self.relationships.append(relationship)
    
    def save_results(self, output_dir: str, filename_prefix: str = "parsed"):
        """Save parsing results to files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save full structure
        structure_file = output_path / f"{filename_prefix}_structure.json"
        with open(structure_file, "w", encoding="utf-8") as f:
            json.dump({
                "nodes": self.nodes,
                "relationships": self.relationships
            }, f, indent=2, default=str)
        
        # Save nodes
        nodes_file = output_path / f"{filename_prefix}_nodes.jsonl"
        with open(nodes_file, "w", encoding="utf-8") as f:
            for node in self.nodes:
                f.write(json.dumps(node, default=str) + "\n")
        
        # Save relationships
        relationships_file = output_path / f"{filename_prefix}_relationships.jsonl"
        with open(relationships_file, "w", encoding="utf-8") as f:
            for rel in self.relationships:
                f.write(json.dumps(rel, default=str) + "\n")
        
        logger.info(f"Results saved to {output_path}")
        logger.info(f"Nodes: {len(self.nodes)}, Relationships: {len(self.relationships)}")

if __name__ == "__main__":
    """Main function to demonstrate usage"""
    # Example usage
    parser = PythonCodeParser()
    
    # Replace with your file path
    file_path = "/Users/yashmakkar/Documents/Project/code_rag/temp_dir/test_samples/agent_to_agent/agent_1/agent1.py"
    
    try:
        nodes, relationships = parser.parse_file(file_path)
        
        # Save results
        parser.save_results("/Users/yashmakkar/Documents/Project/code_rag/src/notebooks", "test")
        
        print(f"Parsed {len(nodes)} nodes and {len(relationships)} relationships")
        
        # Print summary
        node_types = {}
        for node in nodes:
            labels = node.get('labels', [])
            for label in labels:
                node_types[label] = node_types.get(label, 0) + 1
        
        print("Node types found:")
        for node_type, count in node_types.items():
            print(f"  {node_type}: {count}")
            
    except FileNotFoundError:
        print("Please update the file_path variable with a valid Python file")
    except Exception as e:
        print(f"Error: {e}")


