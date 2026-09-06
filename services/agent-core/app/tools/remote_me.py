import json
import requests
import logging
from langchain.tools import tool
from pydantic import BaseModel, Field
from app.config import Config

logger = logging.getLogger(__name__)

class SearchMEInput(BaseModel):
    product: str = Field(
        ..., 
        description="The common name or ID of the chemical product to search for (e.g., '3-hydroxybutyrate', 'bhb', 'succinate')."
    )
    host: str = Field(
        "iJN1463", 
        description="The host organism model ID. Default is 'iJN1463'. Other examples: 'iML1515', 'W3110'."
    )
    carbon: str = Field(
        "D-glucose", 
        description="The primary carbon source used in the production process. Default is 'D-glucose'."
    )

@tool("search_me_resource_tool", args_schema=SearchMEInput)
def search_me_resource_tool(product: str, host: str = "iJN1463", carbon: str = "D-glucose") -> str:
    """
    Query the MEResource database for metabolic engineering data. 
    Use this tool when:
    1. The user asks for the 'maximum yield', 'theoretical yield', or 'YA' of a chemical.
    2. The user wants to know the 'best host' or 'optimal pathway' for producing a compound.
    3. The user needs the specific heterologous reactions (BiGG/Rhea) and equations required to synthesize a product.
    
    Returns: A JSON string containing yield rankings, target reactions, and net equations.
    """
    url = f"{Config.MERESOURCE_URL}/query"
    
    payload = {
        "product": product,
        "host": host,
        "carbon": carbon
    }
    
    logger.info(f"Invoking SearchME Tool for product: {product} in host: {host}")

    try:
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("status") == "success":
                return json.dumps(data, indent=2)
            else:
                msg = data.get("message", "No specific results found.")
                return f"MEResource Search Result: {msg}. Suggest trying a different product name or host."
        
        elif response.status_code == 404:
            return f"Error: The MEResource service endpoint was not found (404). Check if the service is running on port 8004."
        
        else:
            return f"Error: MEResource service returned status code {response.status_code}. Details: {response.text}"

    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to the SearchMEResource service. Ensure the Apptainer instance is running on port 8004."
    except Exception as e:
        logger.error(f"Unexpected error in SearchME tool: {str(e)}")
        return f"Tool Execution Error: {str(e)}"