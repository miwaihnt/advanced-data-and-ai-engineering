import polars as pl
from typing import Type

from pydantic import BaseModel

def pydantic_to_polars(model: Type[BaseModel]) -> dict[str, pl.DataType]:

    temp_map = {
        int: pl.Int64,
        float: pl.Float64,
        str: pl.String,
        bool: pl.Boolean
    }

    schema = {}

    for field_name, field_info in model.model_fields.items():
       annotation = field_info.annotation
       pl_type = temp_map.get(annotation, pl.String)
       schema[field_name] = pl_type

    return schema



class Transaction(BaseModel):
    transaction_id: int
    user_id: int 
    product_id: int 
    amount: int
    timestamp: str
    status: str



