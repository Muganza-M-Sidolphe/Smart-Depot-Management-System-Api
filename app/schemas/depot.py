from pydantic import BaseModel, ConfigDict, Field


class DepotBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    location: str | None = Field(default=None, max_length=255)
    manager_name: str | None = Field(default=None, max_length=120)
    is_active: bool = True


class DepotCreate(DepotBase):
    pass


class DepotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    location: str | None = Field(default=None, max_length=255)
    manager_name: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None


class DepotRead(DepotBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
