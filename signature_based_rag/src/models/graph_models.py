from typing import Literal, TypeVar
from pydantic import BaseModel


# Node models
class FileProps(BaseModel):
    name: str
    extension: str

class ClassProps(BaseModel):
    name: str
    arguments: str
    description: str

class MethodProps(BaseModel):
    name: str
    parameters: str
    sync_type: Literal["sync", "async"]
    description: str

PROP_TYPE = TypeVar("PROP_TYPE", bound=BaseModel)