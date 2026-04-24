from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from dangdang_kgqa.config import PROJECT_ROOT, settings
from dangdang_kgqa.graphdb import graphdb_query
from dangdang_kgqa.qa import build_sparql, classify_question


WEB_DIR = PROJECT_ROOT / "web"

app = FastAPI(title="Dangdang KGQA", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=50)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "service": "dangdang-kgqa",
        "graphdb_base_url": settings.graphdb_base_url,
        "graphdb_repo": settings.graphdb_repo,
    }


@app.post("/api/ask")
def ask(payload: AskRequest) -> dict[str, Any]:
    classified = classify_question(payload.question)
    sparql = build_sparql(classified, limit=payload.limit)
    graphdb_available = True
    error: str | None = None
    results: list[dict[str, Any]] = []
    try:
        results = graphdb_query(sparql)
    except Exception as exc:  # GraphDB may not be running during local UI/API testing.
        graphdb_available = False
        error = str(exc)
    return {
        "question": payload.question,
        "intent": classified.intent,
        "slots": classified.slots,
        "sparql": sparql,
        "answer": summarize_answer(classified.intent, results, graphdb_available),
        "results": results,
        "graphdb_available": graphdb_available,
        "error": error,
    }


@app.get("/api/search")
def search(q: str, limit: int = 10) -> dict[str, Any]:
    return ask(AskRequest(question=q, limit=limit))


def summarize_answer(intent: str, results: list[dict[str, Any]], graphdb_available: bool) -> str:
    if not graphdb_available:
        return "GraphDB 当前不可用；已生成可执行的 SPARQL，可在 GraphDB 启动并导入数据后查询。"
    if not results:
        return "没有查询到匹配书籍，可以尝试缩短关键词或换一个类别。"
    if intent == "cheapest_by_category":
        first = results[0]
        return f"最低价结果是《{first.get('title', '未知书名')}》，价格 {first.get('price', '未知')}。"
    if intent == "author_books":
        titles = "、".join(row.get("title", "未知书名") for row in results[:5])
        return f"查询到这些作品：{titles}。"
    return f"查询到 {len(results)} 条结果，已按相关性或评论数排序。"

