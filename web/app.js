const questionInput = document.querySelector("#question");
const askButton = document.querySelector("#askButton");
const limitSelect = document.querySelector("#limit");
const statusNode = document.querySelector("#status");
const answerNode = document.querySelector("#answer");
const intentNode = document.querySelector("#intent");
const resultsNode = document.querySelector("#results");
const sparqlNode = document.querySelector("#sparql");
const toggleSparql = document.querySelector("#toggleSparql");

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    ask();
  });
});

askButton.addEventListener("click", ask);
questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") ask();
});

toggleSparql.addEventListener("click", () => {
  sparqlNode.hidden = !sparqlNode.hidden;
  toggleSparql.textContent = sparqlNode.hidden ? "查看 SPARQL" : "隐藏 SPARQL";
});

async function ask() {
  const question = questionInput.value.trim();
  if (!question) return;
  statusNode.textContent = "正在查询 GraphDB...";
  askButton.disabled = true;
  resultsNode.innerHTML = "";
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, limit: Number(limitSelect.value) }),
    });
    const payload = await response.json();
    renderPayload(payload);
  } catch (error) {
    statusNode.textContent = "查询失败";
    answerNode.textContent = "前端无法连接 API。";
    intentNode.textContent = String(error);
  } finally {
    askButton.disabled = false;
  }
}

function renderPayload(payload) {
  statusNode.textContent = payload.graphdb_available
    ? `GraphDB 已返回 ${payload.results.length} 条结果`
    : "GraphDB 未连接，已生成 SPARQL";
  answerNode.textContent = payload.answer;
  intentNode.textContent = `意图：${payload.intent}；槽位：${JSON.stringify(payload.slots)}`;
  sparqlNode.textContent = payload.sparql;
  if (!payload.results.length) {
    resultsNode.innerHTML = `<article class="result"><div><h3>暂无结果</h3><p>${
      payload.error ? escapeHtml(payload.error) : "请确认 GraphDB 已启动且已导入 ontology 与 NT 数据。"
    }</p></div></article>`;
    return;
  }
  resultsNode.innerHTML = payload.results.map(renderResult).join("");
}

function renderResult(row) {
  const title = row.title || "未知书名";
  const author = row.authorLabel || "作者未知";
  const publisher = row.publisherLabel || "出版社未知";
  const price = row.price ? `¥${row.price}` : "价格未知";
  const rating = row.rating ? `评分 ${row.rating}%` : "评分未知";
  const comments = row.comments ? `${row.comments} 条评论` : "评论数未知";
  const url = row.url || row.book || "#";
  return `
    <article class="result">
      <div>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(author)} · ${escapeHtml(publisher)} · ${escapeHtml(price)} · ${escapeHtml(rating)} · ${escapeHtml(comments)}</p>
      </div>
      <a href="${escapeAttr(url)}" target="_blank" rel="noreferrer">详情页</a>
    </article>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}

ask();
