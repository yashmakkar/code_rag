from neo4j import GraphDatabase
from src.utils.config import graph_config

driver = GraphDatabase.driver(graph_config.uri, auth=(graph_config.username, graph_config.password))