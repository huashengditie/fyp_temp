from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from equilibrator_api import ComponentContribution, Q_
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="eQuilibrator Microservice")

logger.info("Initializing ComponentContribution (Loading database...)")
cc = ComponentContribution()
logger.info("Database loaded successfully.")

class EquilibratorReq(BaseModel):
    reaction_formula: str
    ph: float = 7.3
    p_mg: float = 3.0
    ionic_strength: float = 0.25

@app.post("/calculate")
def calculate_dg(req: EquilibratorReq):
    logger.info(f"Received request: {req.reaction_formula}")
    try:
        cc.p_h = Q_(req.ph)
        cc.p_mg = Q_(req.p_mg)
        cc.ionic_strength = Q_(f"{req.ionic_strength} M")
        
        rxn = cc.parse_reaction_formula(req.reaction_formula)
        if not rxn:
            raise HTTPException(status_code=400, detail="Failed to parse reaction formula. Ensure you use format like 'kegg:C00002 + kegg:C00001 <=> kegg:C00008 + kegg:C00009'")
            
        cg = cc.standard_dg_prime(rxn)
        
        return {
            "status": "success",
            "reaction": req.reaction_formula,
            "dG_prime_molar": f"{cg.value.m:.2f}",
            "dG_error": f"{cg.error.m:.2f}",
            "units": str(cg.units),
            "conditions": {
                "pH": req.ph,
                "pMg": req.p_mg,
                "ionic_strength": req.ionic_strength
            }
        }
    except Exception as e:
        logger.error(f"eQuilibrator Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))