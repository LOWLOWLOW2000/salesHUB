"""半自動オペ補助 UI（``/operator``）の最小 HTML。

依存（npm / フレームワーク）追加なしで動く 1 ページ HTML。/review/* API を
fetch で叩き、

  1. セッション一覧から 1 件選ぶ（または新規作成 → EV_PICKED_UP）
  2. 受付発話を入力 → /review/{id}/suggest で候補を取得
  3. 候補を選ぶ → /review/{id}/decide で採用 + state machine を進める
  4. オーバーライドしたい時は intent を上書きして decide

を画面上で行えるようにする。Tailwind は CDN を使い、外部依存をプロジェクトに
入れない方針。（/docs と同じ流儀）
"""

from __future__ import annotations

OPERATOR_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reception Breakthrough — Operator Assist</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { font-family: -apple-system, "Segoe UI", "Hiragino Sans", "Noto Sans JP", sans-serif; }
    .card { border: 1px solid rgb(229,231,235); border-radius: 8px; }
    .badge { display:inline-block; padding:2px 8px; border-radius:9999px; font-size:11px; }
    .badge-local { background:rgb(220,252,231); color:rgb(22,101,52); }
    .badge-cloud { background:rgb(224,231,255); color:rgb(55,48,163); }
    .conf-bar { height:6px; background:rgb(229,231,235); border-radius:3px; overflow:hidden; }
    .conf-fill { height:100%; background:rgb(59,130,246); }
    .lang-en .ja, .lang-ja .en { display: none; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 lang-ja">
  <header class="bg-white border-b border-slate-200">
    <div class="max-w-5xl mx-auto px-6 py-4 flex justify-between items-center">
      <div>
        <h1 class="text-xl font-semibold">
          <span class="ja">受付突破 — オペ補助</span>
          <span class="en">Reception Breakthrough — Operator Assist</span>
        </h1>
        <p class="text-xs text-slate-500 mt-1">
          <span class="ja">候補は AI 提案。最後はオペが決める（半自動）。</span>
          <span class="en">Suggestions come from the AI; the operator makes the final call.</span>
        </p>
      </div>
      <div class="space-x-2">
        <button id="btn-lang-ja" class="px-2 py-1 text-xs border border-slate-300 rounded">日本語</button>
        <button id="btn-lang-en" class="px-2 py-1 text-xs border border-slate-300 rounded">English</button>
      </div>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-6 py-6 space-y-6">

    <!-- 1. セッション選択 -->
    <section class="card bg-white p-4">
      <h2 class="text-sm font-semibold text-slate-700 mb-3">
        <span class="ja">1. セッションを選ぶ／作る</span>
        <span class="en">1. Pick or create a session</span>
      </h2>
      <div class="flex flex-wrap items-end gap-3">
        <div>
          <label class="block text-xs text-slate-500 mb-1">
            <span class="ja">セッション ID</span>
            <span class="en">Session ID</span>
          </label>
          <input id="session-id" type="text" class="border border-slate-300 rounded px-2 py-1 text-sm w-80" placeholder="UUID..." />
        </div>
        <button id="btn-new-session" class="px-3 py-1 text-sm border border-slate-300 rounded bg-slate-50 hover:bg-slate-100">
          <span class="ja">新規（モード HUMAN・S2 まで進める）</span>
          <span class="en">New (HUMAN mode, advance to S2)</span>
        </button>
        <span id="state-label" class="text-sm text-slate-600"></span>
      </div>
    </section>

    <!-- 2. 受付発話 -->
    <section class="card bg-white p-4">
      <h2 class="text-sm font-semibold text-slate-700 mb-3">
        <span class="ja">2. 受付の発話を入れる</span>
        <span class="en">2. Enter the receptionist's utterance</span>
      </h2>
      <div class="flex gap-2">
        <input id="utterance" type="text" class="flex-1 border border-slate-300 rounded px-2 py-1 text-sm"
               placeholder="例: ご担当の方にお繋ぎいただけますか / Sorry, no soliciting." />
        <button id="btn-suggest" class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
          <span class="ja">候補を取得</span>
          <span class="en">Get suggestions</span>
        </button>
      </div>
    </section>

    <!-- 3. 候補一覧 -->
    <section id="suggestions-section" class="card bg-white p-4 hidden">
      <h2 class="text-sm font-semibold text-slate-700 mb-3">
        <span class="ja">3. 候補から選ぶ（採用すると state が進む）</span>
        <span class="en">3. Pick a suggestion (state machine advances on click)</span>
      </h2>
      <ul id="suggestions" class="space-y-3"></ul>
    </section>

    <!-- 4. ターン履歴 -->
    <section class="card bg-white p-4">
      <h2 class="text-sm font-semibold text-slate-700 mb-3 flex justify-between items-center">
        <span>
          <span class="ja">4. このセッションの履歴</span>
          <span class="en">4. Turns in this session</span>
        </span>
        <button id="btn-refresh-turns" class="text-xs text-blue-600 hover:underline">
          <span class="ja">再読み込み</span>
          <span class="en">Reload</span>
        </button>
      </h2>
      <ol id="turns" class="space-y-2 text-sm text-slate-700"></ol>
    </section>

    <!-- 5. CSV 書き出し -->
    <section class="card bg-white p-4">
      <h2 class="text-sm font-semibold text-slate-700 mb-3">
        <span class="ja">5. ラベルを CSV で書き出す（オフライン改善用）</span>
        <span class="en">5. Export labels as CSV (for offline improvement)</span>
      </h2>
      <a href="/review/labels.csv" class="text-blue-600 hover:underline text-sm" download>
        <span class="ja">labels.csv をダウンロード</span>
        <span class="en">Download labels.csv</span>
      </a>
    </section>

    <p id="error" class="text-sm text-red-600"></p>
  </main>

  <script>
  (function () {
    const $ = (id) => document.getElementById(id);
    const html = document.documentElement.parentNode || document.body;
    const errorEl = $("error");

    function setError(msg) { errorEl.textContent = msg || ""; }

    function setLang(lang) {
      document.body.classList.remove("lang-ja", "lang-en");
      document.body.classList.add("lang-" + lang);
    }

    $("btn-lang-ja").addEventListener("click", () => setLang("ja"));
    $("btn-lang-en").addEventListener("click", () => setLang("en"));

    let lastLabelId = null;
    let lastSuggestions = [];

    async function jsonFetch(url, opts) {
      const resp = await fetch(url, opts);
      const text = await resp.text();
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch (_) { /* not JSON */ }
      if (!resp.ok) {
        const detail = data && data.detail ? data.detail : resp.statusText;
        throw new Error(resp.status + " " + detail);
      }
      return data;
    }

    async function pickNextLead() {
      const lead = await jsonFetch("/leads/next");
      return (lead && lead.lead_id) || ("DEMO-" + Date.now());
    }

    $("btn-new-session").addEventListener("click", async () => {
      setError("");
      try {
        const leadId = await pickNextLead();
        const created = await jsonFetch("/sessions", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({lead_id: leadId, mode: "HUMAN"})
        });
        const sid = created.session_id;
        await jsonFetch(`/sessions/${sid}/step`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({input_id: "EV_PICKED_UP"})
        });
        $("session-id").value = sid;
        $("state-label").textContent = "state: S2 (lead=" + leadId + ")";
        renderTurns();
      } catch (e) { setError(String(e)); }
    });

    $("btn-suggest").addEventListener("click", async () => {
      setError("");
      const sid = $("session-id").value.trim();
      const utt = $("utterance").value.trim();
      if (!sid || !utt) { setError("session_id と utterance を入れてね"); return; }
      try {
        const data = await jsonFetch(`/review/${sid}/suggest`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({utterance: utt, n: 3})
        });
        lastLabelId = data.label_id;
        lastSuggestions = data.suggestions || [];
        $("state-label").textContent = "state: " + data.current_state;
        renderSuggestions(data.suggestions);
        renderTurns();
      } catch (e) { setError(String(e)); }
    });

    function badgeForSource(src) {
      const cls = src === "cloud" ? "badge-cloud" : "badge-local";
      return `<span class="badge ${cls}">${src}</span>`;
    }

    function renderSuggestions(items) {
      const ul = $("suggestions");
      ul.innerHTML = "";
      if (!items || items.length === 0) {
        ul.innerHTML = '<li class="text-sm text-slate-500">候補なし</li>';
      } else {
        items.forEach((s, i) => {
          const li = document.createElement("li");
          li.className = "border border-slate-200 rounded p-3";
          const conf = Math.round((s.confidence || 0) * 100);
          li.innerHTML = `
            <div class="flex justify-between items-center mb-1">
              <div class="font-mono text-sm">
                ${s.intent_id} → ${s.next_state}
                ${badgeForSource(s.source)}
              </div>
              <div class="text-xs text-slate-500">${conf}%</div>
            </div>
            <div class="conf-bar mb-2"><div class="conf-fill" style="width:${conf}%"></div></div>
            <div class="text-sm text-slate-700 mb-1">
              <span class="text-slate-400">template:</span> ${s.template_id || "-"}
            </div>
            <div class="text-sm text-slate-700 mb-2">
              <span class="text-slate-400">say:</span> ${s.template_text || "<i class='text-slate-400'>(no utterance)</i>"}
            </div>
            <div class="text-xs text-slate-500 mb-2">${s.why}</div>
            <div class="flex flex-wrap gap-2">
              <button data-i="${i}" class="btn-accept px-2 py-1 text-xs border border-blue-600 text-blue-700 rounded hover:bg-blue-50">
                <span class="ja">この候補で進める</span>
                <span class="en">Use this</span>
              </button>
              <button data-i="${i}" class="btn-override px-2 py-1 text-xs border border-amber-500 text-amber-700 rounded hover:bg-amber-50">
                <span class="ja">違う intent で進める…</span>
                <span class="en">Override intent…</span>
              </button>
            </div>
          `;
          ul.appendChild(li);
        });
      }
      $("suggestions-section").classList.remove("hidden");
      ul.querySelectorAll(".btn-accept").forEach((b) => b.addEventListener("click", onAccept));
      ul.querySelectorAll(".btn-override").forEach((b) => b.addEventListener("click", onOverride));
    }

    async function onAccept(e) {
      const i = parseInt(e.currentTarget.dataset.i, 10);
      const s = lastSuggestions[i];
      const note = prompt("メモ（任意）／ Note (optional):") || null;
      const reviewer = prompt("レビュアー名（任意）／ Reviewer name (optional):") || null;
      await decide(s.intent_id, null, note, reviewer);
    }

    async function onOverride(e) {
      const i = parseInt(e.currentTarget.dataset.i, 10);
      const s = lastSuggestions[i];
      const corr = prompt(
        "正解とみなす intent_id を入れてね（例: A1_listening / C2_soft_reject）",
        s.intent_id
      );
      if (!corr) return;
      const note = prompt("なぜ訂正？／ Why correct?") || null;
      const reviewer = prompt("レビュアー名（任意）") || null;
      await decide(corr, corr, note, reviewer);
    }

    async function decide(chosen, correctIntent, note, reviewedBy) {
      setError("");
      const sid = $("session-id").value.trim();
      if (!sid || !lastLabelId) { setError("先に suggest を実行してね"); return; }
      try {
        const data = await jsonFetch(`/review/${sid}/decide`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            label_id: lastLabelId,
            chosen_input_id: chosen,
            correct_intent: correctIntent,
            note: note,
            reviewed_by: reviewedBy
          })
        });
        $("state-label").textContent =
          "state: " + data.to_state + (data.is_terminated ? " (terminated)" : "");
        $("utterance").value = "";
        $("suggestions-section").classList.add("hidden");
        lastLabelId = null;
        lastSuggestions = [];
        renderTurns();
      } catch (e) { setError(String(e)); }
    }

    async function renderTurns() {
      const sid = $("session-id").value.trim();
      const ol = $("turns");
      ol.innerHTML = "";
      if (!sid) return;
      try {
        const data = await jsonFetch(`/review/${sid}/turns`);
        (data.turns || []).forEach((t) => {
          const li = document.createElement("li");
          li.className = "border-l-4 pl-3 py-1 " +
            (t.speaker === "ai" ? "border-blue-400" : "border-emerald-400");
          const label = t.label
            ? ` <span class="text-xs text-slate-500">[${t.label.predicted_intent}` +
              (t.label.correct_intent && t.label.correct_intent !== t.label.predicted_intent
                ? ` → ${t.label.correct_intent}` : "") + `]</span>`
            : "";
          li.innerHTML =
            `<span class="text-xs text-slate-400">${t.speaker}</span> ${escapeHtml(t.text)}${label}`;
          ol.appendChild(li);
        });
      } catch (e) { /* セッションがまだなければ無視 */ }
    }

    $("btn-refresh-turns").addEventListener("click", renderTurns);

    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[c]));
    }
  })();
  </script>
</body>
</html>
"""
