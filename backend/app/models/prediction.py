"""Invoer voor de voorspel- en opslagroutes."""
from pydantic import BaseModel, Field, StrictBool, StrictInt


class PredictionRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    scan_number: StrictInt = Field(ge=1)


class SaveRequest(PredictionRequest):
    clear_old: StrictBool
