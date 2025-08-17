from neo4j import GraphDatabase
from src.utils.config import graph_config
from typing import List, Optional, Dict, Any

class GraphDB:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            graph_config.uri,
            auth=(graph_config.username, graph_config.password)
        )

    def get_node(self, labels: List[str], filter_arguments: Dict[str, Any]) -> Optional[Dict]:
        label_str = ":" + ":".join(labels)
        where_clause = " AND ".join([f"n.{k} = ${k}" for k in filter_arguments])
        query = f"MATCH (n{label_str}) WHERE {where_clause} RETURN n LIMIT 1"

        with self.driver.session() as session:
            result = session.run(query, **filter_arguments)
            record = result.single()
            if record:
                return record["n"]
            return None

    def create_node(self, labels: List[str], properties: Dict[str, Any]) -> None:
        filters = {k: properties.get(k) for k in ["id"] if properties.get(k) is not None}
        label_str = ":" + ":".join(labels)
        existing_node = self.get_node(labels, filters)
        if existing_node:
            # Update labels and properties
            update_labels_query = (
                f"MATCH (n {{id: $id}}) "
                f"REMOVE n:{':'.join(existing_node.labels)} "
                f"SET n{label_str} "
            )
            update_props_query = (
                f"MATCH (n{label_str} {{id: $id}}) "
                f"SET n += $props"
            )
            with self.driver.session() as session:
                try:
                    # Remove old labels and set new ones
                    session.run(update_labels_query, id=properties["id"])
                    # Update properties
                    session.run(update_props_query, id=properties["id"], props=properties)
                    print(f"Node with id {properties['id']} updated with labels {labels} and properties {properties}")
                except Exception as e:
                    print(f"Error updating node: {e}")
            return
        
        properties["name"] = properties.get("name", properties["id"].split(":")[-1])
    
        create_query = f"CREATE (n{label_str} $props)"
        with self.driver.session() as session:
            try:
                session.run(create_query, props=properties)
            except Exception as e:
                print(f"Error creating node: {e}")

    def delete_all_nodes(self):
        query = "MATCH (n) DETACH DELETE n"
        with self.driver.session() as session:
            session.run(query)
            print("All nodes deleted.")
            

    def get_relationship(self, start_id: str, end_id: str, rel_label: str, properties: Optional[dict] = None):
        if properties is None:
            properties = {}
    
        # Build property filters for the relationship if any
        rel_filters = " AND ".join([f"rel.{k} = ${k}" for k in properties]) if properties else ""
        where_clause = f"start.id = $start_id AND end.id = $end_id"
        if rel_filters:
            where_clause += f" AND {rel_filters}"
    
        query = (
            f"MATCH (start)-[rel:{rel_label}]->(end) "
            f"WHERE {where_clause} "
            f"RETURN rel LIMIT 1"
        )
    
        params = {"start_id": start_id, "end_id": end_id, **properties}
    
        with self.driver.session() as session:
            result = session.run(query, **params)
            record = result.single()
            if record:
                return record["rel"]
            return None
        
    def create_node_and_relationship(self, start_id: str, end_id: str, rel_label: str, properties: Optional[dict] = None):
        if properties is None:
            properties = {}
    
        # Extract labels from IDs (e.g., "class:MyClass" -> "Class")
        def label_from_id(node_id):
            prefix = node_id.split(":")[0]
            return {
                "class": "Class",
                "method": "Method",
                "file": "File"
            }.get(prefix, prefix.capitalize())
    
        start_label = label_from_id(start_id)
        end_label = label_from_id(end_id)
    
        # Ensure start and end nodes exist
        self.create_node([start_label], {"id": start_id})
        self.create_node([end_label], {"id": end_id})

        existing_rel = self.get_relationship(start_id, end_id, rel_label, properties)
        if existing_rel is not None:
            print("Relationship already exist")
            return
    
        # Create relationship between nodes
        query = (
            f"MATCH (start:{start_label} {{id: $start_id}}), (end:{end_label} {{id: $end_id}}) "
            f"CREATE (start)-[rel:{rel_label} $props]->(end)"
        )
    
        with self.driver.session() as session:
            try:
                session.run(query, start_id=start_id, end_id=end_id, props=properties)
                print(f"Relationship '{rel_label}' created between {start_id} and {end_id}")
            except Exception as e:
                print(f"Error creating relationship: {e}")
        