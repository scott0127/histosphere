"""Helpers for recording compact, field-level Admin changes."""

from collections.abc import Iterable, Mapping
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel


def _as_json_dict(value: BaseModel | Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return jsonable_encoder(dict(value))


def build_change_payload(
    *,
    before: BaseModel | Mapping[str, Any] | None,
    after: BaseModel | Mapping[str, Any] | None,
    fields: Iterable[str] | None = None,
    subject: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """建立 research log 使用的欄位前後差異。

    只記錄實際改變的欄位，避免 Admin 畫面把未變更資料誤判為修改。
    結果放進既有 ``research_logs.payload``，不需要新增資料表欄位。
    """

    before_data = _as_json_dict(before)
    after_data = _as_json_dict(after)
    field_names = sorted(set(fields or (before_data.keys() | after_data.keys())))
    changes = {
        field: {
            "before": before_data.get(field),
            "after": after_data.get(field),
        }
        for field in field_names
        if before_data.get(field) != after_data.get(field)
    }
    return {
        **jsonable_encoder(dict(subject or {})),
        "updated_fields": list(changes.keys()),
        "changes": changes,
    }
