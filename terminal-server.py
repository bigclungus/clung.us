#!/usr/bin/env python3
"""
Live terminal stream server — streams /tmp/screenlog.txt to websocket clients,
served alongside an xterm.js HTML page.
"""
import asyncio
import json
import os
import time
from aiohttp import web

LOGFILE = "/tmp/screenlog.txt"
TASKS_DIR = "/tmp/claude-1001/-home-clungus/bb9407c6-0d39-400c-af71-7c6765df2c69/tasks"

HTML = r"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="icon" type="image/png" href="https://hello.clung.us/favicon.png">
  <title>BigClungus Live Terminal</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css" />
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #0d0d0d; display: flex; flex-direction: column; height: 100vh; font-family: monospace; }
    #header {
      background: #1a1a2e;
      color: #e94560;
      padding: 8px 16px;
      font-size: 14px;
      font-weight: bold;
      display: flex;
      align-items: center;
      gap: 12px;
      border-bottom: 1px solid #e94560;
      flex-shrink: 0;
    }
    #status { font-size: 11px; color: #888; margin-left: auto; }
    #status.connected { color: #4caf50; }
    #status.disconnected { color: #e94560; }
    #main {
      display: flex;
      flex: 1;
      overflow: hidden;
    }
    #terminal {
      width: 70%;
      padding: 4px;
      overflow: hidden;
      flex-shrink: 0;
    }
    #agents {
      width: 30%;
      background: #1a1a2e;
      border-left: 1px solid #2a2a4e;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    #agents-header {
      padding: 10px 14px;
      color: #e94560;
      font-size: 12px;
      font-weight: bold;
      border-bottom: 1px solid #2a2a4e;
      flex-shrink: 0;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    #agents-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
    }
    #agents-list::-webkit-scrollbar { width: 4px; }
    #agents-list::-webkit-scrollbar-track { background: #1a1a2e; }
    #agents-list::-webkit-scrollbar-thumb { background: #e94560; border-radius: 2px; }
    .task-card {
      background: #0d0d1a;
      border: 1px solid #2a2a4e;
      border-radius: 4px;
      padding: 8px 10px;
      margin-bottom: 6px;
      font-size: 11px;
    }
    .task-card:hover { border-color: #e94560; }
    .task-top {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 4px;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .dot.running { background: #f0c040; box-shadow: 0 0 4px #f0c040; }
    .dot.completed { background: #4caf50; }
    .task-id {
      color: #c0c0d0;
      font-weight: bold;
      font-size: 11px;
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .task-age {
      color: #555;
      font-size: 10px;
      flex-shrink: 0;
    }
    .task-description {
      color: #aaa;
      font-size: 11px;
      margin-bottom: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .task-summary {
      color: #777;
      font-size: 10px;
      line-height: 1.4;
      word-break: break-all;
      white-space: pre-wrap;
      max-height: 48px;
      overflow: hidden;
    }
    .task-card {
      cursor: pointer;
    }
    .task-card.expanded {
      border-color: #e94560;
    }
    .task-expand {
      display: none;
      margin-top: 8px;
      background: #060610;
      border: 1px solid #2a2a4e;
      border-radius: 3px;
      padding: 8px;
      max-height: 300px;
      overflow-y: auto;
      font-size: 10px;
      color: #bbb;
      white-space: pre-wrap;
      word-break: break-all;
      line-height: 1.5;
    }
    .task-expand::-webkit-scrollbar { width: 4px; }
    .task-expand::-webkit-scrollbar-track { background: #0d0d1a; }
    .task-expand::-webkit-scrollbar-thumb { background: #e94560; border-radius: 2px; }
    .task-expand.visible { display: block; }
    .task-expand-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      color: #e94560;
      font-size: 10px;
      font-weight: bold;
    }
    .task-expand-close {
      cursor: pointer;
      padding: 0 4px;
      color: #e94560;
      font-size: 13px;
      line-height: 1;
    }
    .task-expand-close:hover { color: #fff; }
    #agents-empty {
      color: #444;
      font-size: 11px;
      text-align: center;
      padding: 24px 8px;
    }
  </style>
</head>
<body>
  <div id="header">
    <span>&#x1F916; BigClungus Live Session</span>
    <span id="status" class="disconnected">&#x25CF; disconnected</span>
  </div>
  <div id="main">
    <div id="terminal"></div>
    <div id="agents">
      <div id="agents-header">&#x25A3; Subagent Tasks</div>
      <div id="agents-list">
        <div id="agents-empty">No recent tasks</div>
      </div>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
  <script>
    const term = new Terminal({
      theme: {
        background: '#0d0d0d',
        foreground: '#d4d4d4',
        cursor: '#e94560',
      },
      convertEol: true,
      scrollback: 5000,
      fontSize: 13,
      fontFamily: 'Consolas, "Courier New", monospace',
    });
    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(document.getElementById('terminal'));
    fitAddon.fit();
    window.addEventListener('resize', () => fitAddon.fit());

    const statusEl = document.getElementById('status');

    function connect() {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${proto}//${location.host}/ws`);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        statusEl.textContent = '\u25CF live';
        statusEl.className = 'connected';
      };
      ws.onmessage = (e) => {
        if (e.data instanceof ArrayBuffer) {
          term.write(new Uint8Array(e.data), () => term.scrollToBottom());
        } else {
          term.write(e.data, () => term.scrollToBottom());
        }
      };
      ws.onclose = () => {
        statusEl.textContent = '\u25CF disconnected \u2014 reconnecting...';
        statusEl.className = 'disconnected';
        setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
    }
    connect();

    // Agent task panel
    function relativeTime(mtime) {
      const secs = Math.floor(Date.now() / 1000) - mtime;
      if (secs < 60) return secs + 's ago';
      if (secs < 3600) return Math.floor(secs / 60) + 'm ago';
      return Math.floor(secs / 3600) + 'h ago';
    }

    function stripAnsi(str) {
      return str.replace(/\x1B\[[0-9;]*[mGKHF]/g, '').replace(/\x1B\][^\x07]*\x07/g, '');
    }

    const expandedCards = new Set();

    async function toggleCardExpand(card) {
      const agentId = card.dataset.id;
      const expandEl = card.querySelector('.task-expand');
      if (!expandEl) return;

      if (expandedCards.has(agentId)) {
        expandedCards.delete(agentId);
        card.classList.remove('expanded');
        expandEl.classList.remove('visible');
        return;
      }

      expandedCards.add(agentId);
      card.classList.add('expanded');
      expandEl.classList.add('visible');

      const contentEl = expandEl.querySelector('.task-expand-content');
      if (contentEl && contentEl.dataset.loaded !== 'true') {
        contentEl.textContent = 'Loading...';
        try {
          const resp = await fetch('/task-output/' + agentId);
          if (resp.ok) {
            const text = await resp.text();
            contentEl.textContent = stripAnsi(text).trim() || '(empty)';
          } else {
            contentEl.textContent = 'Error: ' + resp.status;
          }
        } catch (e) {
          contentEl.textContent = 'Fetch error: ' + e.message;
        }
        contentEl.dataset.loaded = 'true';
        // Scroll to bottom of output
        expandEl.scrollTop = expandEl.scrollHeight;
      }
    }

    function renderTasks(tasks) {
      const list = document.getElementById('agents-list');
      const empty = document.getElementById('agents-empty');
      if (!tasks || tasks.length === 0) {
        empty.style.display = '';
        // Remove any existing cards
        Array.from(list.querySelectorAll('.task-card')).forEach(c => c.remove());
        return;
      }
      empty.style.display = 'none';

      // Build a map of current task ids in DOM
      const existing = {};
      list.querySelectorAll('.task-card').forEach(c => { existing[c.dataset.id] = c; });

      const seen = new Set();
      tasks.forEach((task, idx) => {
        seen.add(task.id);
        let card = existing[task.id];
        const isNew = !card;
        if (isNew) {
          card = document.createElement('div');
          card.className = 'task-card';
          card.dataset.id = task.id;
        }
        const summary = stripAnsi(task.summary || '').trim();
        const desc = task.description ? `<div class="task-description">${task.description}</div>` : '';
        const wasExpanded = expandedCards.has(task.id);
        // Preserve loaded content across re-renders
        let loadedContent = null;
        let wasLoaded = false;
        if (!isNew) {
          const old = card.querySelector('.task-expand-content');
          if (old && old.dataset.loaded === 'true') {
            loadedContent = old.textContent;
            wasLoaded = true;
          }
        }
        card.innerHTML = `
          ${desc}
          <div class="task-top">
            <div class="dot ${task.status}"></div>
            <div class="task-id">${task.id.substring(0, 8)}</div>
            <div class="task-age">${relativeTime(task.mtime)}</div>
          </div>
          <div class="task-summary">${summary.substring(summary.length - 300)}</div>
          <div class="task-expand${wasExpanded ? ' visible' : ''}">
            <div class="task-expand-header">
              <span>Full Output</span>
              <span class="task-expand-close" title="Close">&times;</span>
            </div>
            <div class="task-expand-content"${wasLoaded ? ' data-loaded="true"' : ''}>${wasLoaded ? loadedContent.replace(/&/g,'&amp;').replace(/</g,'&lt;') : ''}</div>
          </div>
        `;
        if (wasExpanded) card.classList.add('expanded');

        // Close button
        card.querySelector('.task-expand-close').addEventListener('click', (e) => {
          e.stopPropagation();
          expandedCards.delete(task.id);
          card.classList.remove('expanded');
          card.querySelector('.task-expand').classList.remove('visible');
        });

        // Card click to expand
        if (isNew) {
          card.addEventListener('click', () => toggleCardExpand(card));
        }

        // Insert in order
        const cards = list.querySelectorAll('.task-card');
        if (cards.length === 0 || idx >= cards.length) {
          list.appendChild(card);
        } else if (cards[idx] !== card) {
          list.insertBefore(card, cards[idx]);
        }
      });

      // Remove stale cards
      Object.keys(existing).forEach(id => {
        if (!seen.has(id)) existing[id].remove();
      });
    }

    async function pollTasks() {
      try {
        const resp = await fetch('/tasks');
        if (resp.ok) {
          const tasks = await resp.json();
          renderTasks(tasks);
        }
      } catch (e) {
        // silently ignore
      }
    }

    pollTasks();
    setInterval(pollTasks, 3000);
  </script>
</body>
</html>
"""

async def index(request):
    return web.Response(text=HTML, content_type='text/html')

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Send existing log content first
    try:
        with open(LOGFILE, 'rb') as f:
            existing = f.read()
        if existing:
            await ws.send_bytes(existing)
    except FileNotFoundError:
        pass

    # Tail new content
    with open(LOGFILE, 'rb') as f:
        f.seek(0, 2)  # seek to end
        while not ws.closed:
            chunk = f.read(4096)
            if chunk:
                await ws.send_bytes(chunk)
            else:
                await asyncio.sleep(0.05)

    return ws

def get_task_description(agent_id, fpath):
    """Return a short human-readable description for a task.

    Priority:
    1. {agent_id}.meta.json in the same directory — use its 'description' field.
    2. First line of the output file parsed as JSONL — extract message.content,
       take the first line, truncate to 60 chars, strip 'You are BigClungus' prefix.
    """
    tasks_dir = os.path.dirname(fpath)
    meta_path = os.path.join(tasks_dir, agent_id + '.meta.json')
    try:
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        desc = meta.get('description', '').strip()
        if desc:
            return desc
    except (OSError, json.JSONDecodeError, KeyError):
        pass

    # Fall back to parsing first line of output file
    try:
        with open(fpath, 'r', errors='replace') as f:
            first_line = f.readline()
        obj = json.loads(first_line)
        content = obj.get('message', {}).get('content', '')
        if not isinstance(content, str):
            return ''
        # Take first non-empty line of the content
        first_content_line = ''
        for line in content.splitlines():
            if line.strip():
                first_content_line = line.strip()
                break
        if not first_content_line:
            return ''
        # Strip common prefix
        prefix = 'You are BigClungus'
        if first_content_line.startswith(prefix):
            remainder = first_content_line[len(prefix):].lstrip('., ')
            # Take up to first sentence end or just truncate
            for sep in ['. ', '! ', '? ']:
                idx = remainder.find(sep)
                if idx != -1:
                    remainder = remainder[:idx + 1]
                    break
            first_content_line = remainder
        return first_content_line[:60]
    except (OSError, json.JSONDecodeError, KeyError, StopIteration):
        return ''


async def tasks_handler(request):
    now = time.time()
    two_hours_ago = now - 7200
    thirty_secs_ago = now - 30

    tasks = []
    try:
        entries = os.listdir(TASKS_DIR)
    except FileNotFoundError:
        return web.Response(text='[]', content_type='application/json')

    for fname in entries:
        if not fname.endswith('.output'):
            continue
        fpath = os.path.join(TASKS_DIR, fname)
        try:
            stat = os.stat(fpath)
        except OSError:
            continue

        mtime = stat.st_mtime
        if mtime < two_hours_ago:
            continue

        # Read last 200 bytes for summary
        summary = ''
        try:
            with open(fpath, 'rb') as f:
                f.seek(max(0, stat.st_size - 200), 0)
                raw = f.read(200)
            summary = raw.decode('utf-8', errors='replace')
            # Get last non-empty line
            lines = [l for l in summary.splitlines() if l.strip()]
            summary = lines[-1] if lines else summary.strip()
        except OSError:
            pass

        agent_id = fname[:-7]  # strip .output
        status = 'running' if mtime >= thirty_secs_ago else 'completed'
        description = get_task_description(agent_id, fpath)

        tasks.append({
            'id': agent_id,
            'status': status,
            'summary': summary,
            'description': description,
            'mtime': int(mtime),
        })

    tasks.sort(key=lambda t: t['mtime'], reverse=True)
    return web.Response(text=json.dumps(tasks), content_type='application/json')


async def task_output_handler(request):
    agent_id = request.match_info['agentId']
    if not agent_id.replace('-', '').replace('_', '').isalnum():
        return web.Response(status=400, text='Invalid agentId')
    fpath = os.path.join(TASKS_DIR, agent_id + '.output')
    try:
        with open(fpath, 'r', errors='replace') as f:
            content = f.read()
    except FileNotFoundError:
        return web.Response(status=404, text='Task output not found')
    except OSError as e:
        return web.Response(status=500, text=str(e))
    return web.Response(text=content, content_type='text/plain')


async def meta_handler(request):
    agent_id = request.match_info['agentId']
    # Basic sanity check — agent IDs are hex strings
    if not agent_id.replace('-', '').replace('_', '').isalnum():
        return web.Response(status=400, text='Invalid agentId')
    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text='Invalid JSON')
    description = body.get('description', '').strip()
    if not description:
        return web.Response(status=400, text='Missing description field')
    meta_path = os.path.join(TASKS_DIR, agent_id + '.meta.json')
    try:
        os.makedirs(TASKS_DIR, exist_ok=True)
        with open(meta_path, 'w') as f:
            json.dump({'description': description}, f)
    except OSError as e:
        return web.Response(status=500, text=str(e))
    return web.Response(text=json.dumps({'ok': True, 'agentId': agent_id, 'description': description}),
                        content_type='application/json')

app = web.Application()
app.router.add_get('/', index)
app.router.add_get('/ws', websocket_handler)
app.router.add_get('/tasks', tasks_handler)
app.router.add_get('/task-output/{agentId}', task_output_handler)
app.router.add_post('/meta/{agentId}', meta_handler)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=7682)
