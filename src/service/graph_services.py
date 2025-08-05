from src.models.graph_models import FileProps, ClassProps, MethodProps, PROP_TYPE
from src.utils.db_connections import driver
from cymple.builder import QueryBuilder
from pydantic import ValidationError

def add_node(properties: PROP_TYPE) -> None:
    label = None
    if isinstance(properties, FileProps):
        label = "File"
    elif isinstance(properties, ClassProps):
        label = "Class"
    elif isinstance(properties, MethodProps):
        label = "Method"
    else:
        raise TypeError(f"Unsupported properties type: {type(properties)}")

    try:
        props_dict = properties.model_dump()
    except ValidationError as e:
        print(f"Validation error: {e}")
        return

    with driver.session() as session:
        builder = (
            QueryBuilder()
            .create()
            .node(labels=label, properties=props_dict)
        )
        query = str(builder)
        try:
            session.run(query)
        except Exception as e:
            print(f"Failed to run query: {e}")