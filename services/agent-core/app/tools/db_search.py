import requests
import logging
import re
from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Literal
from app.config import Config

logger = logging.getLogger(__name__)

# --- Helper Function for Name Cleaning ---

def preprocess_kegg_query(query: str) -> str:
    """
    Cleans the query string to improve KEGG search hit rates.
    1. Removes charge states like (2-), (3+), (+), (-).
    2. Replaces hyphens with spaces (KEGG find API prefers spaces).
    3. Trims extra whitespace.
    """
    # Remove parentheses containing charge info, e.g., "fumarate(2-)" -> "fumarate"
    query = re.sub(r'\(\d?[-+]\)', '', query)
    # Replace hyphens with spaces, e.g., "menaquinol-8" -> "menaquinol 8"
    query = query.replace("-", " ")
    return query.strip()

# --- 1. Search Tool ---

class SearchInput(BaseModel):
    query: str = Field(..., description="The common name to search for (e.g., 'Glucose', 'Pyruvate', 'Hexokinase').")
    category: Literal["compound", "reaction"] = Field(
        "compound", 
        description="What to search for: 'compound' for chemicals, 'reaction' for enzymes/reactions."
    )

@tool("entity_search_tool", args_schema=SearchInput)
def entity_search_tool(query: str, category: str = "compound") -> str:
    """
    Search for KEGG IDs by common name. 
    - Use category='compound' for metabolites (Cxxxxx).
    - Use category='reaction' for enzymatic reactions (Rxxxxx).
    This tool automatically cleans charge states and formatting to improve results.
    """
    # Pre-process the query for better matching
    clean_name = preprocess_kegg_query(query)
    
    print(f"?? DEBUG: invoking entity_search_tool | Original: '{query}' | Cleaned: '{clean_name}' | Category: '{category}'")
    logger.info(f"Searching KEGG for '{clean_name}' (Original: {query})")

    try:
        api_target = "reaction" if category.lower() == "reaction" else "compound"
        # Using the cleaned name for the API call
        kegg_url = f"https://rest.kegg.jp/find/{api_target}/{clean_name}"
        
        res = requests.get(kegg_url, timeout=10)
        
        if res.status_code == 200 and res.text.strip():
            lines = res.text.strip().split('\n')
            top_results = lines[:5] 
            formatted_list = []
            
            for line in top_results:
                parts = line.split('\t')
                if len(parts) >= 2:
                    raw_id = parts[0]
                    # Extract ID from 'cpd:C00001' or 'rn:R00001'
                    clean_id = raw_id.split(':')[1] if ':' in raw_id else raw_id
                    name_desc = parts[1]

                    if category == "reaction":
                        formatted_list.append(f"Reaction ID: {clean_id} | Desc: {name_desc}")
                    else:
                        formatted_list.append(f"Compound ID: {clean_id} | Name: {name_desc}")
            
            if not formatted_list:
                return f"No parsable results found for {category} '{clean_name}'."

            formatted_str = "\n".join(formatted_list)
            print(f"? DEBUG: Search found {len(formatted_list)} matches for '{clean_name}'.")
            return (
                f"Found potential KEGG {category} matches for '{query}':\n"
                f"{formatted_str}\n"
                f"DECISION: Please choose the most relevant ID. Generic matches are acceptable."
            )
            
        elif res.status_code == 200:
            return f"No matches found for {category} '{query}' (Search: '{clean_name}') in KEGG."

    except Exception as e:
        print(f"? DEBUG: Search Tool Error: {e}")
        return f"Search error: {str(e)}"
    
    return f"No matches found for {category} '{query}' in KEGG."


# --- 2. Validation Tool ---

class ValidationInput(BaseModel):
    entity_id: str = Field(..., description="The ID to validate (e.g., C00022, R00235, P12345).")
    db_type: str = Field("KEGG", description="Database type: 'KEGG' (default), 'Rhea', or 'UniProt'")

@tool("entity_validation_tool", args_schema=ValidationInput)
def entity_validation_tool(entity_id: str, db_type: str = "KEGG") -> str:
    """
    Validates a specific ID and returns its metadata (Official Name, Formula, or Reaction Equation).
    Use this to confirm the identity of an ID before proceeding with calculations.
    """
    print(f"?? DEBUG: invoking entity_validation_tool | ID: '{entity_id}' | DB: '{db_type}'")
    logger.info(f"Validating ID: {entity_id} in {db_type}")

    try:
        db_type_clean = db_type.strip().upper()

        # --- KEGG Validation ---
        if db_type_clean == "KEGG":
            clean_id = entity_id.strip()
            prefix = ""
            
            if not ":" in clean_id:
                if clean_id.startswith("C"): prefix = "cpd:"
                elif clean_id.startswith("R"): prefix = "rn:"
            
            url = f"{Config.KEGG_API_URL}/get/{prefix}{clean_id}"
            res = requests.get(url, timeout=10)
            
            if res.status_code == 200:
                content = res.text
                name_info = "Unknown"
                extra_info = "" 

                lines = content.split('\n')
                for line in lines:
                    if line.startswith("NAME") and name_info == "Unknown":
                        name_info = line.replace("NAME", "").strip().split(';')[0]

                    if line.startswith("FORMULA"):
                        extra_info = f"Formula: {line.replace('FORMULA', '').strip()}"

                    if line.startswith("EQUATION"):
                        extra_info = f"Equation: {line.replace('EQUATION', '').strip()}"

                    if line.startswith("ENZYME"):
                         enzyme_val = line.replace('ENZYME', '').strip()
                         extra_info += f" | EC: {enzyme_val}"

                print(f"? DEBUG: KEGG Validated -> {name_info}")
                return (
                    f"? VALID KEGG ID: {entity_id}\n"
                    f"Name: {name_info}\n"
                    f"{extra_info}\n"
                    f"Status: Verified."
                )
            else:
                return f"? INVALID KEGG ID: {entity_id}. API returned status {res.status_code}."
        
        # --- Rhea Validation ---
        elif db_type_clean == "RHEA":
            url = f"{Config.RHEA_API_URL}?query={entity_id}&format=json"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get('results') and len(data['results']) > 0:
                    eq = data['results'][0].get('equationString', 'Equation not found')
                    rhea_id = data['results'][0].get('id', entity_id)
                    return f"? VALID Rhea ID: {rhea_id}\nEquation: {eq}"
                return f"? ID not found in Rhea: {entity_id}"
            return f"Rhea API Error: {res.status_code}"

        # --- UniProt Validation ---
        elif db_type_clean == "UNIPROT":
            url = f"{Config.UNIPROT_API_URL}/search?query={entity_id}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get('results') and len(data['results']) > 0:
                    try:
                        name = data['results'][0]['proteinDescription']['recommendedName']['fullName']['value']
                        return f"? VALID UniProt ID: {entity_id}\nProtein: {name}"
                    except KeyError:
                        return f"? VALID UniProt ID: {entity_id} (Official name parsing failed)"
                return f"? Invalid UniProt ID: {entity_id}"
            return f"UniProt API Error: {res.status_code}"
            
        return f"Unsupported database type: {db_type}"

    except Exception as e:
        print(f"? DEBUG: Validation Tool Exception: {e}")
        return f"Tool Execution Error: {str(e)}"