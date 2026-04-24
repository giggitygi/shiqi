# 当当小说知识图谱问答系统

这是一个 Python + GraphDB 的知识图谱问答系统原型，面向当当网图书小说栏目。

## 能力范围

- 从当当小说频道抽取小说分类。
- 爬取分类页商品和详情页字段：类别、书名、价格、作者、出版社、出版时间、百分比评分、评论数、详情页链接。
- 每本书保存为一个 XML 文件。
- 将 XML 批量转换为 N-Triples，供 GraphDB 导入。
- 通过 GraphDB SPARQL 查询支持作者作品、类别推荐、最低价、出版社、年份和模糊查询。
- FastAPI 提供问答接口，静态前端提供专业知识问答页面。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

启动 API 和前端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn dangdang_kgqa.api:app --reload
```

浏览器访问：

```text
http://127.0.0.1:8000
```

## 采样爬取

默认采样模式限制页数和详情数，适合先验证流程。

```powershell
.\.venv\Scripts\python.exe scripts/crawl_dangdang.py --sample --max-pages-per-category 1 --max-books 50
.\.venv\Scripts\python.exe scripts/export_nt.py --xml-dir data/xml --out data/nt/books.nt
```

## 20 万本全量爬取命令

不要带 `--sample`，否则会限制为最多 50 本。目标 20 万本可以这样跑：

```powershell
.\.venv\Scripts\python.exe scripts/crawl_dangdang.py --max-pages-per-category 100 --max-books 200000 --xml-dir data/xml
.\.venv\Scripts\python.exe scripts/export_nt.py --xml-dir data/xml --out data/nt/books.nt
```

如果想把当前页面发现的全部小说分类都尽量跑满，不设图书数量上限：

```powershell
.\.venv\Scripts\python.exe scripts/crawl_dangdang.py --full --max-books 0 --xml-dir data/xml
```

全量爬取会产生大量网络请求，并且详情页字段需要逐本访问商品页。建议先确认 GraphDB、磁盘空间和网络稳定性，再长时间运行。

## GraphDB

1. 在 GraphDB Workbench 创建仓库，建议 ruleset 选择 `owl2-rl`；如果机器资源紧张可先用 `rdfsplus`。
2. 先导入 `ontology/dangdang-books.ttl`，再导入 `data/nt/books.nt`。
3. 也可以使用脚本导入：

```powershell
.\.venv\Scripts\python.exe scripts/import_graphdb.py --repo dangdang-books --file ontology/dangdang-books.ttl --content-type text/turtle
.\.venv\Scripts\python.exe scripts/import_graphdb.py --repo dangdang-books --file data/nt/books.nt --content-type application/n-triples
```

## 20 万实体策略

当当分类页会显示远超 20 万的商品总量，但单一分类常见分页上限为 100 页。全量任务不要只按一个分类翻页，应启用：

- 多小说子类别扩展。
- 分类内排序维度扩展。
- 价格区间或关键词分片。
- 商品 ID 去重。
- 断点缓存和失败重试。

本项目的 CLI 已预留分片参数，建议先采样验证，再逐步放大。
