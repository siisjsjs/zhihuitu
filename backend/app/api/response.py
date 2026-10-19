from typing import Any
from pydantic import BaseModel


class ResponseModel(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None


def ok(data: Any = None, message: str = "success") -> ResponseModel:
    return ResponseModel(code=200, message=message, data=data)


def err(message: str, code: int = 400) -> ResponseModel:
    return ResponseModel(code=code, message=message, data=None)
