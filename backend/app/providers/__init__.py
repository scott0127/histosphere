"""External data providers package.

匯出外部資料來源 provider:
    - ``WikipediaProvider``: 從 Wikipedia API 擷取歷史事件來源資料。

LLM providers 位於 ``providers.llm`` 子套件。
"""

from .wikipedia_provider import WikipediaProvider

__all__ = ["WikipediaProvider"]
