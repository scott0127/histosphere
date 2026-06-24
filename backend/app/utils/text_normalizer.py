"""Text normalization utilities.

本模組負責將後端要呈現給前端的中文文字統一為繁體中文。
OpenCC 是主要轉換工具；fallback 只處理常見字詞，避免缺少套件時整個後端無法啟動。
"""

from typing import Any

try:
    from opencc import OpenCC
except Exception:  # pragma: no cover - fallback only runs when optional dependency is missing.
    OpenCC = None


_OPENCC = OpenCC("s2t") if OpenCC else None

_FALLBACK_REPLACEMENTS = {
    "法国": "法國",
    "战争": "戰爭",
    "会议": "會議",
    "国民": "國民",
    "共和国": "共和國",
    "阶级": "階級",
    "经济": "經濟",
    "政治": "政治",
    "社会": "社會",
    "历史": "歷史",
    "时期": "時期",
    "革命": "革命",
    "影响": "影響",
    "发": "發",
    "国": "國",
    "会": "會",
    "战": "戰",
    "后": "後",
    "为": "為",
    "与": "與",
    "门": "門",
    "级": "級",
    "处": "處",
    "导": "導",
    "义": "義",
    "体": "體",
    "权": "權",
    "时": "時",
    "动": "動",
    "应": "應",
    "统": "統",
    "实": "實",
    "质": "質",
}


def normalize_display_text(value: str | None) -> str | None:
    """將單一展示文字轉為繁體中文；英文與數字會原樣保留。"""
    if value is None:
        return None
    normalized = value
    if _OPENCC:
        # OpenCC 對少數混合詞需要不只一次才會穩定，例如「核准新税」。
        for _ in range(3):
            converted = _OPENCC.convert(normalized)
            if converted == normalized:
                break
            normalized = converted
        return normalized
    for source, target in _FALLBACK_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)
    return normalized


def normalize_display_payload(value: Any) -> Any:
    """遞迴正規化 dict/list 中會被前端顯示的字串。"""
    if isinstance(value, str):
        return normalize_display_text(value)
    if isinstance(value, list):
        return [normalize_display_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_display_payload(item) for key, item in value.items()}
    return value
