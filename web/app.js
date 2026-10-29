// Cliente mínimo del canal web: envía la pregunta a POST /api/chat y pinta
// la respuesta con sus fuentes. Toda la lógica de IA vive en el servidor.

const log = document.getElementById("log");
const form = document.getElementById("form");
const input = document.getElementById("input");
const send = document.getElementById("send");
const status = document.getElementById("status");

function addMessage(role, text, extraClass = "") {
  const article = document.createElement("article");
  article.className = `msg msg--${role} ${extraClass}`.trim();
  const p = document.createElement("p");
  p.textContent = text; // textContent: nunca se inyecta HTML del modelo
  article.appendChild(p);
  log.appendChild(article);
  log.scrollTop = log.scrollHeight;
  return article;
}

function addSources(article, sources) {
  if (!sources?.length) return;
  const details = document.createElement("details");
  details.className = "sources";
  const summary = document.createElement("summary");
  summary.textContent = `📄 ${sources.length} fuente(s)`;
  const list = document.createElement("ol");
  for (const s of sources) {
    const li = document.createElement("li");
    const page = s.page ? `, pág. ${s.page}` : "";
    li.textContent = `${s.source}${page} — similitud ${s.score}`;
    li.title = s.excerpt;
    list.appendChild(li);
  }
  details.append(summary, list);
  article.appendChild(details);
}

async function ask(question) {
  addMessage("user", question);
  const typing = addMessage("bot", "Buscando en los documentos…", "msg--typing");
  send.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question }),
    });
    const data = await res.json();
    typing.remove();

    if (!res.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "Error del servidor.";
      addMessage("bot", `⚠️ ${detail}`, "msg--ungrounded");
      status.textContent = "● sin índice / sin clave";
      status.classList.add("badge--off");
      return;
    }
    const article = addMessage("bot", data.answer, data.grounded ? "" : "msg--ungrounded");
    addSources(article, data.sources);
  } catch {
    typing.remove();
    addMessage("bot", "⚠️ No pude conectar con el servidor.", "msg--ungrounded");
  } finally {
    send.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  ask(question);
});

document.getElementById("chips").addEventListener("click", (event) => {
  if (event.target.tagName === "BUTTON") ask(event.target.textContent);
});
