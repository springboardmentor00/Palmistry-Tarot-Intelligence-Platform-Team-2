from pydantic import BaseModel


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: str