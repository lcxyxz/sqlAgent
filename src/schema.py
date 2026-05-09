from pydantic import BaseModel, Field
from typing import Dict, List

class ColumnModel(BaseModel):
    type: str
    nullable: bool
    primary_key: bool
    description: str

class TableModel(BaseModel):
    columns: Dict[str, ColumnModel]
    description: str

class RelationshipModel(BaseModel):
    from_: str = Field(..., alias='from') # 处理 'from' 关键字
    to: str

class SchemaModel(BaseModel):
    tables: Dict[str, TableModel]
    relationships: List[RelationshipModel]
