"""カスタム Swagger UI（/docs）— 英語・日本語 OpenAPI の切り替え。"""

from __future__ import annotations

# GET /docs で返す HTML（CDN の Swagger UI 5 を利用）
DOCS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Reception Breakthrough — API docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" crossorigin="anonymous" />
  <style>
    .rb-docs-bar {
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      padding: 10px 16px;
      background: #1b1b1b;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .rb-docs-bar button {
      cursor: pointer;
      border: 1px solid #444;
      background: #2a2a2a;
      color: #eee;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 13px;
    }
    .rb-docs-bar button.rb-active {
      background: #fff;
      color: #1b1b1b;
      border-color: #fff;
    }
    .rb-docs-hint {
      font-size: 12px;
      opacity: 0.78;
    }
    .rb-howto {
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      margin: 0;
      padding: 14px 18px 16px;
      background: #f4f6fb;
      border-bottom: 1px solid #d8dee9;
      color: #1a1a2e;
      font-size: 14px;
      line-height: 1.55;
    }
    .rb-howto h2 {
      margin: 0 0 8px;
      font-size: 16px;
      font-weight: 700;
    }
    .rb-howto h3 {
      margin: 14px 0 6px;
      font-size: 14px;
      font-weight: 700;
      color: #242442;
    }
    .rb-howto .rb-lead {
      font-size: 15px;
      margin-bottom: 12px;
      padding: 10px 12px;
      background: #fff;
      border-radius: 8px;
      border-left: 4px solid #0b5fff;
    }
    .rb-howto p {
      margin: 0 0 10px;
    }
    .rb-howto ol {
      margin: 0 0 10px;
      padding-left: 1.35em;
    }
    .rb-howto li {
      margin-bottom: 6px;
    }
    .rb-howto details {
      margin-top: 12px;
      padding: 8px 10px;
      background: #fff;
      border-radius: 6px;
      border: 1px solid #e0e4ef;
      font-size: 13px;
    }
    .rb-howto summary {
      cursor: pointer;
      font-weight: 600;
    }
    .rb-howto dl {
      margin: 8px 0 0;
    }
    .rb-howto dt {
      font-weight: 600;
      margin-top: 6px;
    }
    .rb-howto dd {
      margin: 2px 0 0 0.8em;
    }
    .rb-howto table {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid #e0e4ef;
      border-radius: 8px;
      overflow: hidden;
      margin: 8px 0 10px;
      font-size: 13px;
    }
    .rb-howto th,
    .rb-howto td {
      padding: 8px 10px;
      border-bottom: 1px solid #eef1f7;
      vertical-align: top;
      text-align: left;
    }
    .rb-howto th {
      background: #f8f9ff;
      font-weight: 700;
      color: #23234a;
      width: 32%;
    }
    .rb-howto tr:last-child td,
    .rb-howto tr:last-child th {
      border-bottom: none;
    }
    .rb-howto .rb-tip {
      margin: 10px 0 0;
      padding: 8px 10px;
      background: #fff;
      border-radius: 6px;
      border: 1px solid #e0e4ef;
      font-size: 13px;
    }
    .rb-howto a {
      color: #0b5fff;
    }
    .rb-howto-panel {
      display: none;
    }
    .rb-howto-panel.rb-visible {
      display: block;
    }
    #swagger-ui {
      min-height: calc(100vh - 48px);
    }
  </style>
</head>
<body>
  <div class="rb-docs-bar">
    <span><strong>Reception Breakthrough</strong> — API docs</span>
    <span class="rb-docs-hint">Language / 言語:</span>
    <button type="button" id="rb-lang-en">English</button>
    <button type="button" id="rb-lang-ja" class="rb-active">日本語</button>
    <span id="rb-docs-note" class="rb-docs-hint" style="display: none"></span>
  </div>
  <aside class="rb-howto" aria-label="How to use this page">
    <div id="rb-howto-ja" class="rb-howto-panel rb-visible">
      <h2>まずこれだけ読む</h2>
      <p class="rb-lead">
        下の画面は「<strong>サーバーにお願いを送って、返ってきた結果を見る</strong>」ための練習場です。
        プログラムを書かなくても、ボタンだけで試せます。
      </p>
      <h3>ここでできること（ざっくり）</h3>
      <table aria-label="できること一覧">
        <tr>
          <th>health</th>
          <td>サーバーが生きているか確認する</td>
        </tr>
        <tr>
          <th>leads</th>
          <td>「次にかける相手（モック）」を 1 件もらう（開発用の仮 CRM）</td>
        </tr>
        <tr>
          <th>sessions（POST）</th>
          <td>架電セッションを開始する（内部で状態マシンが動き始める）</td>
        </tr>
        <tr>
          <th>sessions（GET など）</th>
          <td>過去や現在のセッションを一覧・詳細・遷移ログ・アウトカムで見る</td>
        </tr>
        <tr>
          <th>sessions（POST step）</th>
          <td>「こういうイベント／インテントが起きた」として 1 手進める（人手モード向け）</td>
        </tr>
        <tr>
          <th>sessions（POST step_text）</th>
          <td>受付の発話テキストを入れると、分類して 1 手進める（AI っぽい流れ）</td>
        </tr>
        <tr>
          <th>metrics</th>
          <td>日次の集計っぽい数値を DB から読む</td>
        </tr>
      </table>
      <h3>いちばんかんたん（まず動くか確認）</h3>
      <ol>
        <li>この説明の<strong>すぐ下</strong>までスクロールする。</li>
        <li><code>GET</code> と <code>/health</code> と書かれた<strong>横長の枠</strong>をクリックする（中身が開く）。</li>
        <li>青い <strong>Try it out</strong>（日本語にすると <strong>試す</strong>）を押す。</li>
        <li>青い <strong>Execute</strong>（<strong>実行</strong>）を押す。</li>
        <li>もう少し下までスクロールすると、<strong>Server response</strong> のところに <code>200</code> と <code>{"status":"ok"}</code> のような文字が出れば成功です。</li>
      </ol>
      <h3>架電の流れをちょっと試すとき</h3>
      <ol>
        <li>同じ要領で <code>GET /leads/next</code> を開いて Try it out → Execute（次にかける相手の情報が返ります）。</li>
        <li>次に <code>POST /sessions</code> を開く → Try it out → 真ん中の JSON を
          <code>{"lead_id":"LEAD-001","mode":"AI"}</code> のまま（またはリード ID を変えて）→ Execute。</li>
        <li>返ってきた JSON の <code>session_id</code> をメモすると、そのあと <code>POST .../step</code> などで続きを試せます。</li>
      </ol>
      <p class="rb-tip">
        <strong>上の「English」「日本語」</strong>は、<strong>説明文の言語</strong>だけ切り替わります。ボタン名は英語のままのことが多いです。<br />
        仕様ファイルだけ欲しいとき：<a href="/openapi-ja.json" target="_blank" rel="noopener">openapi-ja.json</a> ／
        <a href="/openapi-en.json" target="_blank" rel="noopener">openapi-en.json</a>
      </p>
      <details>
        <summary>用語がわからないとき（クリックで開く）</summary>
        <dl>
          <dt>API</dt>
          <dd>「この URL にこの形でお願いすると、決まった形で返事が返る」という約束の一覧です。</dd>
          <dt>GET / POST</dt>
          <dd>GET は主に「見る・取る」、POST は主に「新しく作る・送る」お願いです。</dd>
          <dt>JSON</dt>
          <dd><code>{ }</code> で囲まれた、コンマ区切りのデータの書き方です。</dd>
          <dt>レスポンス</dt>
          <dd>サーバーから返ってきた結果（この画面では下の方に表示されます）。</dd>
        </dl>
      </details>
    </div>
    <div id="rb-howto-en" class="rb-howto-panel">
      <h2>Start here</h2>
      <p class="rb-lead">
        Below is a <strong>click-to-call</strong> playground: you send a real HTTP request to this server from your browser
        and read the JSON response — <strong>no code required</strong>.
      </p>
      <h3>What you can do here (quick map)</h3>
      <table aria-label="What you can do">
        <tr>
          <th>health</th>
          <td>Check if the server is alive</td>
        </tr>
        <tr>
          <th>leads</th>
          <td>Get one “next lead” (mock CRM, for development)</td>
        </tr>
        <tr>
          <th>sessions (POST)</th>
          <td>Start a dialing session (state machine begins)</td>
        </tr>
        <tr>
          <th>sessions (GET etc.)</th>
          <td>View sessions: list / detail / transition log / outcome</td>
        </tr>
        <tr>
          <th>sessions (POST step)</th>
          <td>Advance one step by explicit event/intent id (human mode)</td>
        </tr>
        <tr>
          <th>sessions (POST step_text)</th>
          <td>Send receptionist utterance text; it classifies and advances one step</td>
        </tr>
        <tr>
          <th>metrics</th>
          <td>Read daily aggregated-looking numbers from the DB</td>
        </tr>
      </table>
      <h3>Easiest check (“is the server alive?”)</h3>
      <ol>
        <li>Scroll down to the big list <strong>right under this box</strong>.</li>
        <li>Click the bar that shows <code>GET</code> and <code>/health</code> to <strong>expand</strong> it.</li>
        <li>Click the blue <strong>Try it out</strong> button.</li>
        <li>Click the blue <strong>Execute</strong> button.</li>
        <li>Scroll further down inside that block: under <strong>Server response</strong> you should see <code>200</code> and JSON like <code>{"status":"ok"}</code>.</li>
      </ol>
      <h3>Try a tiny outbound flow</h3>
      <ol>
        <li>Same pattern for <code>GET /leads/next</code> (Try it out → Execute) to fetch a mock lead.</li>
        <li>Then open <code>POST /sessions</code> → Try it out → keep or edit the JSON body
          <code>{"lead_id":"LEAD-001","mode":"AI"}</code> → Execute.</li>
        <li>Copy <code>session_id</code> from the response to continue with <code>POST .../step</code> endpoints.</li>
      </ol>
      <p class="rb-tip">
        <strong>English / 日本語</strong> switches the <strong>description text</strong> in the spec; some button labels may stay English.<br />
        Raw OpenAPI files: <a href="/openapi-en.json" target="_blank" rel="noopener">openapi-en.json</a> /
        <a href="/openapi-ja.json" target="_blank" rel="noopener">openapi-ja.json</a>
      </p>
      <details>
        <summary>Quick glossary</summary>
        <dl>
          <dt>API</dt>
          <dd>A catalog of “if you call this URL with this shape, you get this kind of response.”</dd>
          <dt>GET / POST</dt>
          <dd>GET mostly reads data; POST mostly creates or submits data.</dd>
          <dt>JSON</dt>
          <dd>Text in curly braces with quoted keys — the usual format for request/response bodies here.</dd>
          <dt>Response</dt>
          <dd>What the server sends back (shown under “Server response” after Execute).</dd>
        </dl>
      </details>
    </div>
  </aside>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js" crossorigin="anonymous"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js" crossorigin="anonymous"></script>
  <script>
    const SPEC = { en: "/openapi-en.json", ja: "/openapi-ja.json" };
    const JA_LABELS = [
      ["Try it out", "試す"],
      ["Cancel", "キャンセル"],
      ["Execute", "実行"],
      ["Clear", "クリア"],
      ["Authorize", "認証"],
      ["Close", "閉じる"],
      ["Allowed values", "許可値"],
      ["Request body", "リクエスト本文"],
      ["Responses", "レスポンス"],
      ["Parameters", "パラメータ"],
      ["Schemas", "スキーマ"],
    ];
    let ui = null;
    let labelTimer = null;

    function translateUiLabelsJa() {
      document.querySelectorAll("#swagger-ui button, #swagger-ui a").forEach((el) => {
        const t = (el.textContent || "").trim();
        for (const [en, ja] of JA_LABELS) {
          if (t === en) el.textContent = ja;
        }
      });
    }

    function startJaLabelSync() {
      stopJaLabelSync();
      labelTimer = setInterval(translateUiLabelsJa, 500);
    }

    function stopJaLabelSync() {
      if (labelTimer) {
        clearInterval(labelTimer);
        labelTimer = null;
      }
    }

    function mount(lang) {
      stopJaLabelSync();
      const dom = document.getElementById("swagger-ui");
      dom.innerHTML = "";
      ui = SwaggerUIBundle({
        url: SPEC[lang],
        dom_id: "#swagger-ui",
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        layout: "StandaloneLayout",
      });
      document.getElementById("rb-lang-en").classList.toggle("rb-active", lang === "en");
      document.getElementById("rb-lang-ja").classList.toggle("rb-active", lang === "ja");
      document.getElementById("rb-howto-ja").classList.toggle("rb-visible", lang === "ja");
      document.getElementById("rb-howto-en").classList.toggle("rb-visible", lang === "en");
      const note = document.getElementById("rb-docs-note");
      if (lang === "ja") {
        note.style.display = "inline";
        note.textContent = "説明は日本語／ボタンは英語のことが多いです。";
        startJaLabelSync();
      } else {
        note.style.display = "none";
        note.textContent = "";
      }
    }

    document.getElementById("rb-lang-en").addEventListener("click", () => mount("en"));
    document.getElementById("rb-lang-ja").addEventListener("click", () => mount("ja"));
    mount("ja");
  </script>
</body>
</html>"""
