import json
from langchain.tools import tool
from pydantic import BaseModel, Field
from app.config import Config
from app.tools.base import post_request
import uuid

class ChemicalReactionInput(BaseModel):
    reaction_equation: str = Field(
        ...,
        description="The chemical reaction equation string (e.g. 'C00002 + C00001 <=> C00008'). MUST contain both reactants and products."
    )

def _validate_equation(eq: str) -> str:
    """
    Validates if the reaction equation is structurally correct.
    Returns None if valid, otherwise returns an error message string.
    """
    eq = eq.strip()
    
    separator = None
    if "<=>" in eq: separator = "<=>"
    elif "<->" in eq: separator = "<->"
    elif "->" in eq: separator = "->"
    elif "=" in eq: separator = "="
    
    if not separator:
        return f"Invalid Format: The reaction string '{eq}' is missing a valid separator (e.g., '<=>')."

    parts = eq.split(separator)
    if len(parts) != 2:
        return f"Invalid Format: Could not parse reactants and products from '{eq}'."
        
    left_side = parts[0].strip()
    right_side = parts[1].strip()
    
    if not left_side:
        return "Invalid Reaction: Missing reactants (left side is empty)."
    if not right_side:
        return "Invalid Reaction: Missing products (right side is empty). Please check the input."

    return None # Valid

@tool("dg_predictor_tool", args_schema=ChemicalReactionInput)
def dg_predictor_tool(reaction_equation: str) -> str:
    """
    Calculates Delta G for a reaction. Returns result in kJ/mol.
    Validates input before calling the backend.
    """
    error_msg = _validate_equation(reaction_equation)
    if error_msg:
        return f"Tool Rejection: {error_msg}. Please ask the user to provide the full reaction."

    reaction_id = f"R_{uuid.uuid4().hex[:4]}"
    payload = {
        "data": { 
            reaction_id: reaction_equation 
        }
    }

    try:
        raw_response = post_request(Config.DG_PREDICTOR_URL, payload)
        
        data = json.loads(raw_response)
        
        result_item = None
        if isinstance(data, dict) and "data" in data:
            result_item = list(data["data"].values())[0]
        elif isinstance(data, list) and data:
            result_item = data[0]

        if result_item:
            dg_val = result_item.get("dG")
            std_val = result_item.get("std")
            unit = "kJ/mol" 

            if dg_val is not None:
                return (
                    f"Success. Delta G = {dg_val:.2f} {unit} "
                    f"(Std Dev: {std_val:.2f})."
                )
        
        return f"Error: Backend returned unexpected format: {raw_response}"

    except Exception as e:
        return f"Tool Execution Error: {str(e)}"