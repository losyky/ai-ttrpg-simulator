"""Standalone debug/monitoring dashboard server.

Runs on port 8001, proxies /api/debug/* to the main backend (port 8000),
and serves a self-contained HTML dashboard.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

app = FastAPI(title="AI TTRPG Debug Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TTRPG Debug Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0d17;--card:#111827;--card2:#1a2235;--border:#1f2937;--text:#e5e7eb;--dim:#6b7280;--primary:#818cf8;--green:#34d399;--yellow:#fbbf24;--red:#f87171;--blue:#60a5fa;--purple:#c084fc;--cyan:#22d3ee;--orange:#fb923c}
body{background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,sans-serif;font-size:13px}

/* Header */
.header{background:var(--card);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:100}
.header h1{font-size:15px;font-weight:700;color:var(--primary);white-space:nowrap}
.badge{font-size:10px;padding:2px 8px;border-radius:9999px;font-weight:600}
.badge-live{background:var(--green);color:#000}
.badge-paused{background:var(--yellow);color:#000}
.tab-bar{display:flex;gap:2px;margin-left:20px}
.tab-bar button{padding:6px 14px;border-radius:8px 8px 0 0;border:1px solid transparent;border-bottom:none;background:transparent;color:var(--dim);cursor:pointer;font-size:12px;font-weight:500;transition:all .2s}
.tab-bar button:hover{color:var(--text);background:var(--card2)}
.tab-bar button.active{background:var(--bg);color:var(--primary);border-color:var(--border)}
.header .actions{margin-left:auto;display:flex;gap:6px;align-items:center}
.header .actions button{padding:5px 12px;border-radius:6px;border:1px solid var(--border);background:var(--card);color:var(--text);cursor:pointer;font-size:11px}
.header .actions button:hover{border-color:var(--primary)}
.header .actions button.danger{border-color:var(--red);color:var(--red)}

/* Layout */
.page{display:none;height:calc(100vh - 45px);overflow:hidden}
.page.active{display:flex}

/* ==== Overview Page ==== */
.overview{display:grid;grid-template-columns:300px 1fr 320px;gap:0;height:100%}
.panel{border-right:1px solid var(--border);overflow-y:auto;padding:14px}
.panel:last-child{border-right:none}

/* Sections */
.section{margin-bottom:16px}
.section-title{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--dim);margin-bottom:8px;font-weight:700;display:flex;align-items:center;gap:6px}
.section-title .count{background:var(--border);color:var(--text);padding:1px 6px;border-radius:9999px;font-size:9px}

/* Stat cards */
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px}
.stat .value{font-size:22px;font-weight:700;color:var(--primary);font-variant-numeric:tabular-nums}
.stat .label{font-size:10px;color:var(--dim);margin-top:2px}
.stat.green .value{color:var(--green)} .stat.yellow .value{color:var(--yellow)}
.stat.red .value{color:var(--red)} .stat.blue .value{color:var(--blue)}
.stat.wide{grid-column:1/-1}

/* DB table */
.db-table{width:100%;font-size:11px;border-collapse:collapse}
.db-table th,.db-table td{padding:5px 6px;text-align:left;border-bottom:1px solid var(--border)}
.db-table th{color:var(--dim);font-weight:500;font-size:10px;text-transform:uppercase}
.db-table td.num{text-align:right;font-family:monospace;color:var(--primary)}
.db-table tr:hover td{background:var(--card2)}

/* Events */
.filter-bar{display:flex;gap:4px;margin-bottom:10px;flex-wrap:wrap}
.filter-bar button{padding:2px 8px;border-radius:5px;border:1px solid var(--border);background:transparent;color:var(--dim);cursor:pointer;font-size:10px;transition:all .15s}
.filter-bar button:hover{color:var(--text)}
.filter-bar button.active{border-color:var(--primary);color:var(--primary);background:rgba(129,140,248,0.1)}

.event{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 10px;margin-bottom:4px;font-size:11px;cursor:pointer;transition:border-color .15s}
.event:hover{border-color:var(--primary)}
.event .meta{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.event .time{color:var(--dim);font-family:monospace;font-size:10px;margin-left:auto}
.event .cat{padding:1px 5px;border-radius:3px;font-size:9px;font-weight:700;text-transform:uppercase}
.cat-agent{background:#312e81;color:#a5b4fc} .cat-chat{background:#064e3b;color:#6ee7b7}
.cat-tool{background:#78350f;color:#fcd34d} .cat-session{background:#1e3a5f;color:#93c5fd}
.cat-data{background:#3b0764;color:#c084fc} .cat-error{background:#7f1d1d;color:#fca5a5}
.cat-interactive{background:#4a1d7f;color:#d8b4fe} .cat-llm{background:#164e63;color:#67e8f9}
.event .detail{color:var(--dim);margin-top:3px;white-space:pre-wrap;max-height:60px;overflow:hidden;font-size:10px;line-height:1.4}
@keyframes fadeIn{from{opacity:0;transform:translateY(-3px)}to{opacity:1;transform:translateY(0)}}
.event.new{animation:fadeIn .25s ease}

/* Session / detail cards */
.info-card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px;margin-bottom:6px;cursor:pointer;transition:border-color .15s}
.info-card:hover{border-color:var(--primary)}
.info-card .title{font-size:12px;font-weight:600;color:var(--text)}
.info-card .sub{font-size:10px;color:var(--dim);margin-top:3px}
.info-card .mono{font-family:monospace;font-size:10px;color:var(--primary)}
.data-json{font-family:monospace;font-size:10px;color:var(--dim);background:#0d1117;padding:6px 8px;border-radius:6px;max-height:200px;overflow-y:auto;white-space:pre-wrap;word-break:break-all;margin-top:6px}

/* ==== Data page ==== */
.data-page{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;height:100%}

/* ==== Chat preview page ==== */
.chat-preview-page{display:grid;grid-template-columns:250px 1fr;gap:0;height:100%}
.chat-msg{padding:8px 10px;margin-bottom:4px;border-radius:8px;font-size:12px;line-height:1.5;max-height:150px;overflow:hidden}
.chat-msg.user{background:#1e3a5f;border:1px solid #2563eb30}
.chat-msg.narrator{background:#1a2e1a;border:1px solid #16a34a30}
.chat-msg.referee{background:#2a1a1a;border:1px solid #dc262630}
.chat-msg.teammate{background:#1a1a2e;border:1px solid #7c3aed30}
.chat-msg.system{background:var(--card);border:1px solid var(--border);color:var(--dim)}
.chat-msg .role{font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:3px}
.chat-msg .role.user{color:var(--blue)} .chat-msg .role.narrator{color:var(--green)}
.chat-msg .role.referee{color:var(--red)} .chat-msg .role.teammate{color:var(--purple)}
.chat-msg .role.system{color:var(--dim)}
.empty-state{color:var(--dim);font-size:12px;padding:20px;text-align:center}
</style>
</head>
<body>
<div class="header">
  <h1>🔍 TTRPG Debug Dashboard</h1>
  <span class="badge badge-live" id="status-badge">● LIVE</span>
  <div class="tab-bar">
    <button class="active" onclick="switchPage('overview')">总览</button>
    <button onclick="switchPage('data')">数据</button>
    <button onclick="switchPage('chat')">聊天记录</button>
  </div>
  <div class="actions">
    <span style="font-size:10px;color:var(--dim)" id="auto-label">每 2s 刷新</span>
    <button onclick="refresh()">刷新</button>
    <button onclick="toggleAuto()" id="toggle-btn">暂停</button>
    <button class="danger" onclick="clearEvents()">清除日志</button>
  </div>
</div>

<!-- ===== Page: Overview ===== -->
<div class="page active" id="page-overview">
  <div class="overview">
    <!-- Left: Stats -->
    <div class="panel">
      <div class="section">
        <div class="section-title">系统概览</div>
        <div class="stat-grid" id="stats-grid"></div>
      </div>
      <div class="section">
        <div class="section-title">智能体调用统计</div>
        <div id="agent-stats"></div>
      </div>
      <div class="section">
        <div class="section-title">活跃会话</div>
        <div id="sessions-list"></div>
      </div>
      <div class="section">
        <div class="section-title">角色卡</div>
        <div id="characters-list"></div>
      </div>
    </div>

    <!-- Center: Events -->
    <div class="panel">
      <div class="section-title">事件日志 <span class="count" id="event-count">0</span></div>
      <div class="filter-bar" id="filter-bar"></div>
      <div id="events-list"></div>
    </div>

    <!-- Right: Detail -->
    <div class="panel">
      <div class="section-title">详情</div>
      <div id="detail-content"><div class="empty-state">点击事件或会话查看详情</div></div>
    </div>
  </div>
</div>

<!-- ===== Page: Data ===== -->
<div class="page" id="page-data">
  <div class="data-page">
    <div class="panel">
      <div class="section">
        <div class="section-title">数据库</div>
        <div id="db-summary"></div>
      </div>
    </div>
    <div class="panel">
      <div class="section">
        <div class="section-title">文档资料</div>
        <div id="docs-list"></div>
      </div>
    </div>
    <div class="panel">
      <div class="section">
        <div class="section-title">兼容性设置</div>
        <div id="compat-info"></div>
      </div>
      <div class="section">
        <div class="section-title">文件统计</div>
        <div id="files-summary"></div>
      </div>
    </div>
  </div>
</div>

<!-- ===== Page: Chat Preview ===== -->
<div class="page" id="page-chat">
  <div class="chat-preview-page">
    <div class="panel">
      <div class="section-title">会话列表</div>
      <div id="chat-sessions"></div>
    </div>
    <div class="panel" id="chat-content">
      <div class="empty-state">选择左侧会话查看聊天记录</div>
    </div>
  </div>
</div>

<script>
const API='http://localhost:8000/api/debug';
let autoRefresh=true,timer=null,lastTs=0,activeFilter='',allEvents=[],currentPage='overview';
const CATS=['agent','chat','tool','session','data','error','interactive','llm'];
const CAT_LABELS={agent:'智能体',chat:'聊天',tool:'工具',session:'会话',data:'数据',error:'错误',interactive:'交互',llm:'LLM'};

function $(id){return document.getElementById(id)}
function escHtml(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function catClass(c){return 'cat-'+(CATS.includes(c)?c:'agent')}
async function fetchJSON(url){try{const r=await fetch(url);if(!r.ok)return null;return await r.json()}catch{return null}}
function fmtTime(ts){if(!ts)return'';const p=ts.split('T');return p[1]?p[1].split('.')[0]:''}

function switchPage(name){
  currentPage=name;
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  $('page-'+name).classList.add('active');
  document.querySelectorAll('.tab-bar button').forEach((b,i)=>{
    b.classList.toggle('active',['overview','data','chat'][i]===name);
  });
  if(name==='data')refreshDataPage();
  if(name==='chat')refreshChatPage();
}

// ===== Overview =====
function renderStats(s,sessions){
  if(!s)return;
  const cc=s.category_counts||{};
  $('stats-grid').innerHTML=`
    <div class="stat"><div class="value">${s.total_events}</div><div class="label">总事件</div></div>
    <div class="stat green"><div class="value">${sessions?sessions.length:s.active_sessions}</div><div class="label">活跃会话</div></div>
    <div class="stat yellow"><div class="value">${cc.agent||0}</div><div class="label">智能体</div></div>
    <div class="stat blue"><div class="value">${cc.chat||0}</div><div class="label">聊天</div></div>
    <div class="stat"><div class="value">${cc.tool||0}</div><div class="label">工具调用</div></div>
    <div class="stat red"><div class="value">${cc.error||0}</div><div class="label">错误</div></div>
  `;
  $('event-count').textContent=s.total_events;
}

function renderAgentStats(s){
  if(!s||!s.agent_counts)return;
  const ac=s.agent_counts;
  const entries=Object.entries(ac).sort((a,b)=>b[1]-a[1]);
  if(!entries.length){$('agent-stats').innerHTML='<div class="empty-state">暂无数据</div>';return}
  let html='<table class="db-table"><thead><tr><th>智能体</th><th>调用次数</th></tr></thead><tbody>';
  entries.forEach(([name,cnt])=>{html+=`<tr><td>${escHtml(name)}</td><td class="num">${cnt}</td></tr>`});
  html+='</tbody></table>';
  $('agent-stats').innerHTML=html;
}

function renderSessions(list){
  if(!list||!list.length){$('sessions-list').innerHTML='<div class="empty-state">暂无活跃会话</div>';return}
  $('sessions-list').innerHTML=list.map(s=>`
    <div class="info-card" onclick="showSessionDetail('${s.session_id}')">
      <div class="title">${escHtml(s.label||'未命名冒险')}</div>
      <div class="sub">${s.phase} · R${s.round_number} · ${s.message_count} 消息${s.player?' · '+escHtml(s.player.name):''}</div>
      <div class="mono">${s.session_id.slice(0,12)}...</div>
    </div>
  `).join('');
}

function renderCharacters(list){
  if(!list||!list.length){$('characters-list').innerHTML='<div class="empty-state">暂无角色卡</div>';return}
  $('characters-list').innerHTML=list.map(c=>`
    <div class="info-card">
      <div class="title">${escHtml(c.name)}</div>
      <div class="sub">Lv.${c.level} ${escHtml(c.ancestry)} ${escHtml(c.character_class)} · HP ${c.hp}/${c.max_hp}</div>
    </div>
  `).join('');
}

function renderFilters(){
  let html=`<button class="${activeFilter===''?'active':''}" onclick="setFilter('')">全部</button>`;
  CATS.forEach(c=>{html+=`<button class="${activeFilter===c?'active':''}" onclick="setFilter('${c}')">${CAT_LABELS[c]||c}</button>`});
  $('filter-bar').innerHTML=html;
}

function renderEvents(events){
  const filtered=activeFilter?events.filter(e=>e.category===activeFilter):events;
  if(!filtered.length){$('events-list').innerHTML='<div class="empty-state">暂无事件</div>';return}
  $('events-list').innerHTML=filtered.slice(0,300).map(e=>`
    <div class="event" onclick='showEvent(${JSON.stringify(e).replace(/'/g,"&#39;").replace(/\\/g,"\\\\")})'>
      <div class="meta">
        <span class="cat ${catClass(e.category)}">${CAT_LABELS[e.category]||e.category}</span>
        <span style="color:var(--text);font-weight:500;font-size:11px">${escHtml(e.action)}</span>
        ${e.agent?`<span style="color:var(--primary);font-size:10px">${escHtml(e.agent)}</span>`:''}
        <span class="time">${fmtTime(e.timestamp)}</span>
      </div>
      ${e.detail?`<div class="detail">${escHtml(e.detail.slice(0,200))}</div>`:''}
    </div>
  `).join('');
}

function showEvent(e){
  let html=`<div style="margin-bottom:10px"><span class="cat ${catClass(e.category)}" style="font-size:11px">${CAT_LABELS[e.category]||e.category}</span> <b style="font-size:13px">${escHtml(e.action)}</b></div>`;
  html+=`<div style="font-size:10px;color:var(--dim);margin-bottom:10px">${escHtml(e.timestamp)}</div>`;
  if(e.session_id)html+=`<div style="font-size:11px;margin-bottom:4px">会话: <span class="mono">${escHtml(e.session_id)}</span></div>`;
  if(e.agent)html+=`<div style="font-size:11px;margin-bottom:4px">智能体: <span style="color:var(--primary)">${escHtml(e.agent)}</span></div>`;
  if(e.detail)html+=`<div style="font-size:12px;margin:10px 0;color:var(--text);white-space:pre-wrap;line-height:1.6;background:var(--card);padding:10px;border-radius:8px;border:1px solid var(--border);max-height:300px;overflow-y:auto">${escHtml(e.detail)}</div>`;
  if(e.data&&Object.keys(e.data).length){html+=`<div class="section-title" style="margin-top:12px">附加数据</div><div class="data-json">${escHtml(JSON.stringify(e.data,null,2))}</div>`}
  $('detail-content').innerHTML=html;
}

async function showSessionDetail(sid){
  const[history,memories]=await Promise.all([
    fetchJSON(`${API}/sessions/${sid}/history`),
    fetchJSON(`${API}/memories/${sid}`),
  ]);
  let html=`<div style="font-size:14px;font-weight:700;margin-bottom:4px">会话详情</div>`;
  html+=`<div class="mono" style="margin-bottom:12px">${sid}</div>`;

  // Chat history summary
  html+=`<div class="section-title">聊天记录 <span class="count">${history?history.length:0}</span></div>`;
  if(history&&history.length){
    const recent=history.slice(-8);
    recent.forEach((m,i)=>{
      const rc={'user':'var(--blue)','narrator':'var(--green)','referee':'var(--red)','teammate':'var(--purple)'}[m.role]||'var(--dim)';
      html+=`<div style="margin-bottom:6px;padding:6px 8px;background:var(--card);border-radius:6px;border:1px solid var(--border)">
        <div style="font-size:9px;color:${rc};font-weight:700;text-transform:uppercase;margin-bottom:2px">${escHtml(m.role)}</div>
        <div style="font-size:11px;max-height:60px;overflow:hidden">${escHtml((m.content||'').slice(0,200))}</div>
      </div>`;
    });
    if(history.length>8)html+=`<div style="font-size:10px;color:var(--dim);text-align:center">... 还有 ${history.length-8} 条消息</div>`;
  }

  // Memories
  if(memories&&memories.total>0){
    html+=`<div class="section-title" style="margin-top:14px">记忆层 <span class="count">${memories.total}</span></div>`;
    for(const[cat,items]of Object.entries(memories.categories)){
      html+=`<div style="font-size:10px;color:var(--dim);margin:4px 0">${escHtml(cat)}: ${items} 条</div>`;
    }
  }

  $('detail-content').innerHTML=html;
}

function setFilter(f){activeFilter=f;renderFilters();renderEvents(allEvents)}

// ===== Data Page =====
async function refreshDataPage(){
  const[data,docs,strategy]=await Promise.all([
    fetchJSON(`${API}/data/summary`),
    fetchJSON(`${API}/documents`),
    fetchJSON(`${API}/reasoning-strategy`),
  ]);

  // DB summary
  if(data){
    let html=`<div class="stat-grid" style="margin-bottom:12px">
      <div class="stat"><div class="value">${data.db_size_mb||0}</div><div class="label">数据库 (MB)</div></div>
      <div class="stat green"><div class="value">${data.uploads?data.uploads.file_count:0}</div><div class="label">上传文件</div></div>
      <div class="stat"><div class="value">${data.skills_count||0}</div><div class="label">Skills</div></div>
      <div class="stat"><div class="value">${data.custom_tools_count||0}</div><div class="label">自定义工具</div></div>
    </div>`;
    if(data.tables){
      html+='<table class="db-table"><thead><tr><th>数据表</th><th>行数</th></tr></thead><tbody>';
      for(const[t,c]of Object.entries(data.tables)){html+=`<tr><td>${escHtml(t)}</td><td class="num">${c}</td></tr>`}
      html+='</tbody></table>';
    }
    $('db-summary').innerHTML=html;

    // Files summary
    let fhtml='<table class="db-table"><thead><tr><th>项目</th><th>数量</th></tr></thead><tbody>';
    if(data.uploads)fhtml+=`<tr><td>上传文件</td><td class="num">${data.uploads.file_count} (${data.uploads.total_size_mb} MB)</td></tr>`;
    fhtml+=`<tr><td>Skills</td><td class="num">${data.skills_count||0}</td></tr>`;
    fhtml+=`<tr><td>自定义工具</td><td class="num">${data.custom_tools_count||0}</td></tr>`;
    fhtml+=`<tr><td>存档</td><td class="num">${data.saves_count||0}</td></tr>`;
    fhtml+=`<tr><td>工作区文件</td><td class="num">${data.workspace_files||0}</td></tr>`;
    fhtml+=`<tr><td>ChromaDB</td><td class="num">${data.chroma_exists?'✓':'✗'}</td></tr>`;
    fhtml+='</tbody></table>';
    $('files-summary').innerHTML=fhtml;
  }

  // Documents
  if(docs&&docs.length){
    $('docs-list').innerHTML=docs.map(d=>`
      <div class="info-card">
        <div class="title">${escHtml(d.filename||d.doc_id)}</div>
        <div class="sub">${escHtml(d.doc_type)} · ${d.chunk_count} 片段</div>
        <div class="mono">${escHtml(d.doc_id)}</div>
      </div>
    `).join('');
  }else{
    $('docs-list').innerHTML='<div class="empty-state">暂无文档</div>';
  }

  // Compat
  if(strategy){
    const labels={auto:'自动 (推荐)',keep:'始终保留',strip:'始终移除'};
    $('compat-info').innerHTML=`
      <div class="info-card">
        <div class="title">reasoning_content 策略</div>
        <div class="sub">${labels[strategy.strategy]||strategy.strategy}</div>
      </div>
    `;
  }
}

// ===== Chat Preview Page =====
async function refreshChatPage(){
  const sessions=await fetchJSON(`${API}/sessions`);
  if(!sessions||!sessions.length){$('chat-sessions').innerHTML='<div class="empty-state">暂无会话</div>';return}
  $('chat-sessions').innerHTML=sessions.map(s=>`
    <div class="info-card" onclick="loadChatHistory('${s.session_id}')">
      <div class="title">${escHtml(s.label||'未命名')}</div>
      <div class="sub">${s.message_count} 消息 · ${s.phase}</div>
    </div>
  `).join('');
}

async function loadChatHistory(sid){
  const history=await fetchJSON(`${API}/sessions/${sid}/history`);
  if(!history||!history.length){$('chat-content').innerHTML='<div class="empty-state">该会话暂无消息</div>';return}
  $('chat-content').innerHTML='<div style="padding:14px;overflow-y:auto;height:100%">'+
    history.map(m=>`
      <div class="chat-msg ${m.role}">
        <div class="role ${m.role}">${m.role}</div>
        <div>${escHtml(m.content)}</div>
      </div>
    `).join('')+'</div>';
  $('chat-content').scrollTop=$('chat-content').scrollHeight;
}

// ===== Refresh =====
async function refresh(){
  const[stats,sessions,events,chars]=await Promise.all([
    fetchJSON(`${API}/stats`),
    fetchJSON(`${API}/sessions`),
    fetchJSON(`${API}/events?limit=300`),
    fetchJSON(`${API}/characters`),
  ]);
  renderStats(stats,sessions);
  renderAgentStats(stats);
  renderSessions(sessions);
  renderCharacters(chars);
  if(events){allEvents=events;renderEvents(events)}
  renderFilters();
}

async function pollNew(){
  if(!autoRefresh)return;
  const[events,stats]=await Promise.all([
    fetchJSON(`${API}/events?limit=50${lastTs?'&since='+lastTs:''}`),
    fetchJSON(`${API}/stats`),
  ]);
  if(events&&events.length){
    if(lastTs>0){events.forEach(e=>{allEvents.unshift(e)});allEvents=allEvents.slice(0,500)}
    else{allEvents=events}
    lastTs=Math.max(...allEvents.map(e=>e.ts_unix||0));
    renderEvents(allEvents);
  }
  renderStats(stats);
  renderAgentStats(stats);
}

function toggleAuto(){
  autoRefresh=!autoRefresh;
  $('toggle-btn').textContent=autoRefresh?'暂停':'继续';
  $('auto-label').textContent=autoRefresh?'每 2s 刷新':'已暂停';
  $('status-badge').textContent=autoRefresh?'● LIVE':'⏸ PAUSED';
  $('status-badge').className='badge '+(autoRefresh?'badge-live':'badge-paused');
}

async function clearEvents(){
  if(!confirm('确定清除所有事件日志？'))return;
  await fetch(`${API}/events`,{method:'DELETE'});
  allEvents=[];renderEvents([]);refresh();
}

// Init
refresh();
setInterval(()=>{if(autoRefresh)pollNew()},2000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
