from langchain.tools import tool
from pydantic import BaseModel, Field
from app.config import Config
from app.tools.base import post_request
from typing import List, Any, Union
import json
import ast


class EnzRankInput(BaseModel):
    data: Union[List[dict], Any] = Field(
        ...,
        description="List of enzyme-substrate pairs. Example: [{'enzyme': 'SEQ', 'substrate': 'ID'}]"
    )


@tool("enzrank_tool", args_schema=EnzRankInput)
def enzrank_tool(data: Union[List[dict], Any]) -> str:
    """
    Predict enzyme-substrate compatibility.
    """
    if isinstance(data, str):
        try:
            data = ast.literal_eval(data)
        except:
            pass

    if not isinstance(data, list):
        if isinstance(data, dict):
            data = [data]
        else:
            return "Error: Input format invalid. Expected a list of dictionaries."

    payload = {"data": data}

    return post_request(Config.ENZRANK_URL, payload)