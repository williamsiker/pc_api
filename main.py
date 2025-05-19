# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from scraper import AtCoderScraper
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

app = FastAPI(title="AtCoder API",
             description="API for fetching and caching AtCoder contests and problems")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Asegurar que existe el directorio de storage
Path("storage").mkdir(exist_ok=True)

def load_cached_data() -> List[Dict[str, Any]]:
    """Cargar datos del cache"""
    try:
        with open('storage/contests.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.get("/sync")
async def sync_data(force: bool = False):
    """
    Sincronizar datos de AtCoder usando web scraping
    """
    try:
        scraper = AtCoderScraper()
        data = scraper.fetch_and_save_all()
        return {
            "status": "success",
            "message": "Data synchronized successfully",
            "contests_count": len(data),
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/contests")
async def get_contests():
    """
    Obtener todos los concursos con sus problemas
    """
    data = load_cached_data()
    if not data:
        raise HTTPException(status_code=404, detail="No cached data found. Run /sync first.")
    return data

@app.get("/contests/{contest_id}")
async def get_contest(contest_id: str):
    """
    Obtener un concurso específico con sus problemas
    """
    data = load_cached_data()
    for contest in data:
        if contest["id"] == contest_id:
            return contest
    raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")

@app.get("/contests/{contest_id}/problems/{problem_id}")
async def get_problem(contest_id: str, problem_id: str, force_refresh: bool = False):
    """
    Obtener los detalles de un problema específico incluyendo el contenido del problema
    """
    data = load_cached_data()
    # print(data)
    for contest in data:
        if contest["id"] == contest_id:
            for problem in contest["problems"]:
                if problem["id"] == problem_id:
                    # Si el problema ya tiene contenido y no se fuerza refresh, devolverlo
                    if not force_refresh and "content" in problem:
                        return problem
                    
                    # Si no tiene contenido o se fuerza refresh, obtenerlo
                    try:
                        scraper = AtCoderScraper()
                        problem_detail = scraper.get_problem_detail(contest_id, problem_id)
                        # print(f"Problem detail fetched: {problem_detail}")
                        # Actualizar el problema con el contenido detallado
                        problem.update({
                            "content": {
                                "statement": problem_detail.statement,
                                "constraints": problem_detail.constraints,
                                "input_format": problem_detail.input_format,
                                "output_format": problem_detail.output_format,
                                "samples": [s.dict() for s in problem_detail.samples]
                            },
                            "time_limit": problem_detail.time_limit,
                            "memory_limit": problem_detail.memory_limit,
                            "last_updated": datetime.now().isoformat()
                        })

                        
                        # Guardar los cambios en el archivo
                        with open('storage/contests.json', 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                            
                        return problem
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"Error fetching problem details: {str(e)}")
                        
            raise HTTPException(status_code=404, detail=f"Problem {problem_id} not found")
    raise HTTPException(status_code=404, detail=f"Contest {contest_id} not found")


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", port=8000, log_level="debug", reload=True)
