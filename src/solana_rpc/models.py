from typing import Any

from pydantic import BaseModel


class Err(BaseModel):
    Ok: Any | None


class Value(BaseModel):
    bundle_id: str
    transactions: list[str]
    slot: int
    confirmation_status: str
    err: Err


class Context(BaseModel):
    slot: int


class Result(BaseModel):
    context: Context
    value: list[Value | None]


class GetBundleStatusesResp(BaseModel):
    jsonrpc: str
    result: Result
    id: int


class SendBundleResp(BaseModel):
    jsonrpc: str
    result: str
    id: int
