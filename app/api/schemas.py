from pydantic import BaseModel, field_validator

class UpgdInput(BaseModel):
    semana: int
    nom_upgd: str
    
    @field_validator('semana', mode='before')
    @classmethod
    def convertir_semana(cls, v):
        """Convierte semana a int automáticamente si viene como string"""
        if isinstance(v, str):
            return int(v)
        return v
    
    class Config:
        str_strip_whitespace = True

class ExplainRequest(BaseModel):
    semana: int
    nom_upgd: str
    
    @field_validator('semana', mode='before')
    @classmethod
    def convertir_semana(cls, v):
        """Convierte semana a int automáticamente si viene como string"""
        if isinstance(v, str):
            return int(v)
        return v
    
    class Config:
        str_strip_whitespace = True