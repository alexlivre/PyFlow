from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
import httpx
from pydantic import BaseModel
from pyflow.api.deps import require_token

router = APIRouter()

class ModelInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    context_length: Optional[int] = None
    pricing: Optional[dict] = None

class ModelsResponse(BaseModel):
    data: List[ModelInfo]

@router.get("/models/openrouter", response_model=ModelsResponse, dependencies=[Depends(require_token)])
async def list_openrouter_models(api_key: str = Header(..., alias="X-OpenRouter-API-Key")):
    """
    Lista os modelos disponíveis no OpenRouter.
    Requer uma chave de API válida do OpenRouter.
    """
    # Use the standard models endpoint to list all available models
    url = "https://openrouter.ai/api/v1/models"
    
    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # OpenRouter returns { data: [ ... models ... ] }
            models = []
            for item in data.get("data", []):
                # Map OpenRouter model structure to our simple structure
                models.append(ModelInfo(
                    id=item.get("id"),
                    name=item.get("name"),
                    description=item.get("description"),
                    context_length=item.get("context_length"),
                    pricing=item.get("pricing")
                ))
            
            # Sort by name
            models.sort(key=lambda x: x.name)
            
            return ModelsResponse(data=models)
            
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"OpenRouter API Error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")
