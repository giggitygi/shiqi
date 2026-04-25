from __future__ import annotations

import re

from dangdang_kgqa.models import ClassifiedQuestion


PREFIXES = """PREFIX kg: <https://example.org/dangdang/kg/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


def classify_question(question: str) -> ClassifiedQuestion:
    normalized = re.sub(r"\s+", "", question)
    if "最便宜" in normalized:
        return ClassifiedQuestion(
            intent="cheapest_by_category",
            slots={"category": _category_from_question(normalized)},
            original=question,
        )
    if "推荐" in normalized:
        return ClassifiedQuestion(
            intent="recommend_by_category",
            slots={"category": _category_from_question(normalized)},
            original=question,
        )
    author_match = re.match(r"(.+?)(写过|有哪些作品|的书|作品)", normalized)
    if author_match and ("写过" in normalized or "作品" in normalized or "哪些书" in normalized):
        return ClassifiedQuestion(
            intent="author_books",
            slots={"author": author_match.group(1).replace("哪些书", "")},
            original=question,
        )
    publisher_match = re.match(r"(.+?出版社).*(哪些|有什么|出版)", normalized)
    if publisher_match:
        return ClassifiedQuestion(
            intent="publisher_books",
            slots={"publisher": publisher_match.group(1)},
            original=question,
        )
    year_match = re.search(r"(\d{4})年?", normalized)
    if year_match:
        return ClassifiedQuestion(
            intent="year_books",
            slots={"year": year_match.group(1), "category": _category_from_question(normalized)},
            original=question,
        )
    return ClassifiedQuestion(intent="fuzzy_search", slots={"keyword": question.strip()}, original=question)


def build_sparql(classified: ClassifiedQuestion, limit: int = 10) -> str:
    if classified.intent == "author_books":
        author = _escape_literal(classified.slots["author"])
        return (
            PREFIXES
            + f"""
SELECT ?book ?title ?price ?rating ?publisherLabel ?comments ?length ?brand ?novelType ?series ?discount ?url WHERE {{
  ?book a kg:Book ;
        kg:title ?title ;
        kg:authoredBy ?author .
  ?author rdfs:label ?authorLabel .
  OPTIONAL {{ ?book kg:price ?price . }}
  OPTIONAL {{ ?book kg:ratingPercent ?rating . }}
  OPTIONAL {{ ?book kg:commentsCount ?comments . }}
  OPTIONAL {{ ?book kg:length ?length . }}
  OPTIONAL {{ ?book kg:brand ?brand . }}
  OPTIONAL {{ ?book kg:novelType ?novelType . }}
  OPTIONAL {{ ?book kg:series ?series . }}
  OPTIONAL {{ ?book kg:discount ?discount . }}
  OPTIONAL {{ ?book kg:detailUrl ?url . }}
  OPTIONAL {{ ?book kg:publishedBy/rdfs:label ?publisherLabel . }}
  FILTER(CONTAINS(LCASE(STR(?authorLabel)), LCASE("{author}")))
}}
ORDER BY DESC(?comments)
LIMIT {limit}
"""
        ).strip()
    if classified.intent == "cheapest_by_category":
        category = _escape_literal(classified.slots["category"])
        return (
            PREFIXES
            + f"""
SELECT ?book ?title ?price ?rating ?authorLabel ?publisherLabel ?length ?brand ?novelType ?series ?discount ?url WHERE {{
  ?book a kg:Book ;
        kg:title ?title ;
        kg:price ?price ;
        kg:inCategory ?bookCategory .
  ?bookCategory kg:subCategoryOf* ?matchedCategory .
  ?matchedCategory rdfs:label ?categoryLabel .
  OPTIONAL {{ ?book kg:authoredBy/rdfs:label ?authorLabel . }}
  OPTIONAL {{ ?book kg:ratingPercent ?rating . }}
  OPTIONAL {{ ?book kg:length ?length . }}
  OPTIONAL {{ ?book kg:brand ?brand . }}
  OPTIONAL {{ ?book kg:novelType ?novelType . }}
  OPTIONAL {{ ?book kg:series ?series . }}
  OPTIONAL {{ ?book kg:discount ?discount . }}
  OPTIONAL {{ ?book kg:publishedBy/rdfs:label ?publisherLabel . }}
  OPTIONAL {{ ?book kg:detailUrl ?url . }}
  FILTER(CONTAINS(STR(?categoryLabel), "{category}"))
}}
ORDER BY ASC(?price)
LIMIT 1
"""
        ).strip()
    if classified.intent == "recommend_by_category":
        category = _escape_literal(classified.slots["category"])
        return (
            PREFIXES
            + f"""
SELECT ?book ?title ?price ?rating ?authorLabel ?comments ?length ?brand ?novelType ?series ?discount ?url WHERE {{
  ?book a kg:Book ;
        kg:title ?title ;
        kg:inCategory ?bookCategory .
  ?bookCategory kg:subCategoryOf* ?matchedCategory .
  ?matchedCategory rdfs:label ?categoryLabel .
  OPTIONAL {{ ?book kg:price ?price . }}
  OPTIONAL {{ ?book kg:ratingPercent ?rating . }}
  OPTIONAL {{ ?book kg:commentsCount ?comments . }}
  OPTIONAL {{ ?book kg:length ?length . }}
  OPTIONAL {{ ?book kg:brand ?brand . }}
  OPTIONAL {{ ?book kg:novelType ?novelType . }}
  OPTIONAL {{ ?book kg:series ?series . }}
  OPTIONAL {{ ?book kg:discount ?discount . }}
  OPTIONAL {{ ?book kg:authoredBy/rdfs:label ?authorLabel . }}
  OPTIONAL {{ ?book kg:detailUrl ?url . }}
  FILTER(CONTAINS(STR(?categoryLabel), "{category}"))
}}
ORDER BY DESC(?comments)
LIMIT {limit}
"""
        ).strip()
    if classified.intent == "publisher_books":
        publisher = _escape_literal(classified.slots["publisher"])
        return (
            PREFIXES
            + f"""
SELECT ?book ?title ?price ?rating ?authorLabel ?length ?brand ?novelType ?series ?discount ?url WHERE {{
  ?book a kg:Book ;
        kg:title ?title ;
        kg:publishedBy ?publisher .
  ?publisher rdfs:label ?publisherLabel .
  OPTIONAL {{ ?book kg:price ?price . }}
  OPTIONAL {{ ?book kg:ratingPercent ?rating . }}
  OPTIONAL {{ ?book kg:length ?length . }}
  OPTIONAL {{ ?book kg:brand ?brand . }}
  OPTIONAL {{ ?book kg:novelType ?novelType . }}
  OPTIONAL {{ ?book kg:series ?series . }}
  OPTIONAL {{ ?book kg:discount ?discount . }}
  OPTIONAL {{ ?book kg:authoredBy/rdfs:label ?authorLabel . }}
  OPTIONAL {{ ?book kg:detailUrl ?url . }}
  FILTER(CONTAINS(STR(?publisherLabel), "{publisher}"))
}}
ORDER BY ?title
LIMIT {limit}
"""
        ).strip()
    if classified.intent == "year_books":
        year = _escape_literal(classified.slots["year"])
        category = _escape_literal(classified.slots.get("category", "小说"))
        return (
            PREFIXES
            + f"""
SELECT ?book ?title ?publishedAt ?rating ?authorLabel ?length ?brand ?novelType ?series ?discount ?url WHERE {{
  ?book a kg:Book ;
        kg:title ?title ;
        kg:publishedAtText ?publishedAt .
  ?book kg:inCategory ?bookCategory .
  ?bookCategory kg:subCategoryOf* ?matchedCategory .
  ?matchedCategory rdfs:label ?categoryLabel .
  OPTIONAL {{ ?book kg:authoredBy/rdfs:label ?authorLabel . }}
  OPTIONAL {{ ?book kg:ratingPercent ?rating . }}
  OPTIONAL {{ ?book kg:length ?length . }}
  OPTIONAL {{ ?book kg:brand ?brand . }}
  OPTIONAL {{ ?book kg:novelType ?novelType . }}
  OPTIONAL {{ ?book kg:series ?series . }}
  OPTIONAL {{ ?book kg:discount ?discount . }}
  OPTIONAL {{ ?book kg:detailUrl ?url . }}
  FILTER(CONTAINS(STR(?publishedAt), "{year}") && CONTAINS(STR(?categoryLabel), "{category}"))
}}
ORDER BY ?title
LIMIT {limit}
"""
        ).strip()
    keyword = _escape_literal(classified.slots.get("keyword", classified.original))
    return (
        PREFIXES
        + f"""
SELECT ?book ?title ?price ?rating ?authorLabel ?categoryLabel ?length ?brand ?novelType ?series ?discount ?url WHERE {{
  ?book a kg:Book ;
        kg:title ?title .
  OPTIONAL {{ ?book kg:price ?price . }}
  OPTIONAL {{ ?book kg:ratingPercent ?rating . }}
  OPTIONAL {{ ?book kg:authoredBy/rdfs:label ?authorLabel . }}
  OPTIONAL {{ ?book kg:inCategory/rdfs:label ?categoryLabel . }}
  OPTIONAL {{ ?book kg:length ?length . }}
  OPTIONAL {{ ?book kg:brand ?brand . }}
  OPTIONAL {{ ?book kg:novelType ?novelType . }}
  OPTIONAL {{ ?book kg:series ?series . }}
  OPTIONAL {{ ?book kg:discount ?discount . }}
  OPTIONAL {{ ?book kg:detailUrl ?url . }}
  FILTER(
    CONTAINS(LCASE(STR(?title)), LCASE("{keyword}")) ||
    CONTAINS(LCASE(STR(?authorLabel)), LCASE("{keyword}")) ||
    CONTAINS(LCASE(STR(?categoryLabel)), LCASE("{keyword}"))
  )
}}
ORDER BY ?title
LIMIT {limit}
"""
    ).strip()


def _category_from_question(question: str) -> str:
    known = [
        "世界名著",
        "欧洲",
        "美洲",
        "亚洲",
        "其他地区",
        "四大名著",
        "红楼梦",
        "西游记",
        "水浒",
        "三国演义",
        "作品集",
        "美国",
        "德国",
        "英国",
        "法国",
        "日本",
        "俄罗斯",
        "韩国",
        "其他国家",
        "中国古典小说",
        "中国当代小说",
        "中国近现代小说",
        "外国小说",
        "科幻小说",
        "侦探/悬疑/推理",
        "情感小说",
        "魔幻小说",
        "社会小说",
        "武侠小说",
        "惊悚/恐怖",
        "历史小说",
        "影视小说",
        "官场小说",
        "职场小说",
        "财经小说",
        "军事小说",
    ]
    for category in known:
        if category.replace("/", "") in question.replace("/", "") or category in question:
            return category
    match = re.search(r"([\u4e00-\u9fa5/]+小说)", question)
    return match.group(1) if match else "小说"


def _escape_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
