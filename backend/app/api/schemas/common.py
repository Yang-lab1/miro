from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalizedText(StrictModel):
    en: str
    zh: str
