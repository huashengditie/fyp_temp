import json
from langchain.tools import tool
from pydantic import BaseModel, Field
from app.config import Config
from app.tools.base import post_request

class EquilibratorInput(BaseModel):
    """
    Input definition for the eQuilibrator tool.
    """
    reaction_formula: str = Field(
        ...,
        description="Reaction equation strictly using KEGG IDs with 'kegg:' prefix. Example: 'kegg:C00002 + kegg:C00001 <=> kegg:C00008 + kegg:C00009'"
    )
    ph: float = Field(default=7.3, description="pH value (default: 7.3)")
    p_mg: float = Field(default=3.0, description="pMg value (default: 3.0)")
    ionic_strength: float = Field(default=0.25, description="Ionic strength in Molar (default: 0.25)")

import re

@tool("equilibrator_tool", args_schema=EquilibratorInput)
def equilibrator_tool(reaction_formula: str, ph: float = 7.3, p_mg: float = 3.0, ionic_strength: float = 0.25) -> str:
    """Calculates Delta G'0 using eQuilibrator. Automatically handles KEGG ID formatting."""
    processed_formula = re.sub(r'(?<!kegg:)\b([CR]\d{5})\b', r'kegg:\1', reaction_formula)
    
    payload = {
        "reaction_formula": processed_formula,
        "ph": ph, 
        "p_mg": p_mg, 
        "ionic_strength": ionic_strength
    }
    return post_request(Config.EQUILIBRATOR_URL, payload)