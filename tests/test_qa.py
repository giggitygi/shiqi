from dangdang_kgqa.qa import build_sparql, classify_question


def test_classify_author_books_question():
    question = classify_question("余华写过哪些书")

    assert question.intent == "author_books"
    assert question.slots["author"] == "余华"


def test_classify_cheapest_category_question():
    question = classify_question("最便宜的中国当代小说是哪本书")

    assert question.intent == "cheapest_by_category"
    assert question.slots["category"] == "中国当代小说"


def test_build_sparql_for_author_books_contains_fuzzy_filter():
    classified = classify_question("余华写过哪些书")

    sparql = build_sparql(classified)

    assert "kg:authoredBy" in sparql
    assert "kg:ratingPercent" in sparql
    assert "CONTAINS" in sparql
    assert "余华" in sparql


def test_build_sparql_for_cheapest_category_orders_by_price():
    classified = classify_question("最便宜的中国当代小说是哪本书")

    sparql = build_sparql(classified)

    assert "kg:inCategory" in sparql
    assert "kg:ratingPercent" in sparql
    assert "ORDER BY ASC(?price)" in sparql
    assert "LIMIT 1" in sparql


def test_build_sparql_for_recommendation_uses_category_hierarchy():
    classified = classify_question("推荐几本世界名著")

    sparql = build_sparql(classified)

    assert classified.slots["category"] == "世界名著"
    assert "kg:subCategoryOf*" in sparql
    assert "?matchedCategory rdfs:label ?categoryLabel" in sparql
