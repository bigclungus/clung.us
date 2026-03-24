#!/usr/bin/env python3
import http.server
import json
import os
import glob
import re
import datetime
import subprocess
import tempfile
import urllib.parse
import socketserver
import threading

SERVE_DIR = os.path.dirname(os.path.abspath(__file__))

_streams_lock = threading.Lock()
_active_streams: dict = {}
# Schema: {session_id: {"identity": str, "display_name": str, "text": str, "done": bool}}

# Load .env from the same directory (before any env-dependent constants)
_dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.isfile(_dotenv_path):
    for _line in open(_dotenv_path).read().splitlines():
        if '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

TASKS_DIR = "/home/clungus/work/bigclungus-meta/tasks"
AGENTS_ACTIVE_DIR = "/home/clungus/work/bigclungus-meta/agents/active"
AGENTS_FIRED_DIR = "/home/clungus/work/bigclungus-meta/agents/fired"
SESSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions')

LLM_MAX_TOKENS = 300  # Hard cap per debate response

# ── GitHub auth ────────────────────────────────────────────────────────────────
GITHUB_COOKIE = "tauth_github"
GITHUB_ALLOWED_USERS = {u.lower() for u in os.environ.get('GITHUB_ALLOWED_USERS', '').split(',') if u.strip()}
CONGRESS_LOGIN_URL = "https://terminal.clung.us/auth/github?next=https://hello.clung.us/congress"


def _is_authed(request_headers):
    """Check tauth_github cookie against GITHUB_ALLOWED_USERS. Empty set = any authed user ok."""
    cookie_header = request_headers.get('Cookie', '')
    for part in cookie_header.split(';'):
        part = part.strip()
        if part.startswith(GITHUB_COOKIE + '='):
            gh_user = part[len(GITHUB_COOKIE) + 1:].strip()
            if gh_user:
                if not GITHUB_ALLOWED_USERS or gh_user.lower() in GITHUB_ALLOWED_USERS:
                    return True
    return False

_EVENT_TO_STATUS = {
    'started': 'in_progress',
    'done': 'done',
    'stale': 'stale',
    'failed': 'failed',
}

def _enrich_task(task):
    """
    Derive status, started_at, finished_at, and summary from the log array.
    Falls back to top-level fields for old-format tasks without a log.
    Mutates and returns the task dict.
    """
    log = task.get('log')
    if log and isinstance(log, list) and len(log) > 0:
        last_event = log[-1].get('event', '')
        task['status'] = _EVENT_TO_STATUS.get(last_event, last_event)

        # started_at: ts of first 'started' entry
        for entry in log:
            if entry.get('event') == 'started':
                task['started_at'] = entry.get('ts', '')
                break

        # finished_at: ts of last non-started entry
        for entry in reversed(log):
            if entry.get('event') != 'started':
                task['finished_at'] = entry.get('ts', '')
                break

        # summary: context of last non-started entry
        for entry in reversed(log):
            if entry.get('event') != 'started' and entry.get('context'):
                task['summary'] = entry.get('context', '')
                break
    return task


def _parse_frontmatter(content):
    """Parse YAML-style frontmatter from markdown content."""
    meta = {}
    body = content
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if m:
        fm_text = m.group(1)
        body = m.group(2)
        for line in fm_text.splitlines():
            kv = re.match(r'^(\w[\w-]*):\s*(.*)$', line.strip())
            if kv:
                key = kv.group(1)
                val = kv.group(2).strip()
                # Parse list values like [a, b, c]
                list_m = re.match(r'^\[(.*)\]$', val)
                if list_m:
                    val = [v.strip() for v in list_m.group(1).split(',') if v.strip()]
                elif val.lower() == 'true':
                    val = True
                elif val.lower() == 'false':
                    val = False
                meta[key] = val
    return meta, body.strip()


def _load_identity(name):
    """Load an identity file and return (meta, full_content) or None.

    Checks agents/active/ first, then agents/fired/ (severance bench).
    """
    for dirpath in (AGENTS_ACTIVE_DIR, AGENTS_FIRED_DIR):
        fpath = os.path.join(dirpath, f'{name}.md')
        if os.path.isfile(fpath):
            with open(fpath, 'r') as f:
                content = f.read()
            meta, _ = _parse_frontmatter(content)
            return meta, content
    return None, None


def _call_claude_cli(system_prompt, user_message, on_token=None):
    """Call Claude via the claude CLI (OAuth auth, no API key needed)."""
    cmd = ['/home/clungus/.local/bin/claude', '-p', system_prompt,
           '--output-format', 'streaming-json', '--max-turns', '1']
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True)
    stdout, _ = proc.communicate(input=user_message, timeout=120)
    full_text = ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("type") == "assistant":
                for block in obj.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        chunk = block.get("text", "")
                        full_text += chunk
                        if on_token:
                            on_token(chunk)
        except Exception:
            pass
    # Fallback: if streaming-json parsing yielded nothing, return raw stdout
    return full_text.strip() or stdout.strip()


def _call_gemini_cli(system_prompt, user_message, on_token=None):
    """Call Gemini via the gemini CLI (OAuth auth, no API key needed)."""
    # Combine system prompt + user message as the full prompt; gemini -p appends to stdin
    full_prompt = system_prompt + "\n\n" + user_message
    proc = subprocess.Popen(
        ['/usr/local/bin/gemini', '--output-format', 'text', '-p', full_prompt],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    proc.stdin.write('')
    proc.stdin.close()
    full_text = ""
    for line in proc.stdout:
        full_text += line
        if on_token:
            on_token(line)
    proc.wait()
    return full_text.strip()


def _call_grok(system_prompt: str, user_message: str, on_token=None) -> str:
    """Call xAI Grok via OpenAI-compatible API using XAI_API_KEY (streaming)."""
    import urllib.request as _urlreq
    api_key = os.environ.get("XAI_API_KEY", "")
    payload = json.dumps({
        "model": "grok-4.20-0309-non-reasoning",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": LLM_MAX_TOKENS,
        "stream": True,
    }).encode()
    req = _urlreq.Request(
        "https://api.x.ai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
    )
    full_text = ""
    with _urlreq.urlopen(req, timeout=60) as resp:
        for raw_line in resp:
            line = raw_line.decode('utf-8').rstrip('\n')
            if not line.startswith('data: '):
                continue
            payload_str = line[len('data: '):]
            if payload_str.strip() == '[DONE]':
                break
            try:
                obj = json.loads(payload_str)
                delta = (obj.get('choices', [{}])[0].get('delta', {}).get('content') or '')
                if delta:
                    full_text += delta
                    if on_token:
                        on_token(delta)
            except Exception:
                pass
    return full_text.strip()


def _call_claude(system_prompt, user_message, on_token=None):
    """Call Claude and return the text response.
    Uses the anthropic Python client if ANTHROPIC_API_KEY is set, otherwise
    falls back to the claude CLI (authenticated via OAuth).
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        import anthropic  # optional dependency, only imported when API key is set
        client = anthropic.Anthropic(api_key=api_key)
        full_text = ""
        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=LLM_MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        ) as stream:
            for chunk in stream.text_stream:
                full_text += chunk
                if on_token:
                    on_token(chunk)
        return full_text
    else:
        return _call_claude_cli(system_prompt, user_message, on_token=on_token)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SERVE_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', 'https://hello.clung.us')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/tasks':
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._serve_tasks()
            return

        if path == '/api/congress/stream':
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._handle_congress_stream()
            return

        if path == '/api/congress/identities':
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._serve_congress_identities()
            return

        if path == '/api/congress/sessions':
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._serve_congress_sessions()
            return

        m = re.match(r'^/api/congress/sessions/(congress-\d+)$', path)
        if m:
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._serve_congress_session(m.group(1))
            return

        if path == '/api/agents':
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._serve_agents()
            return

        if path == '/api/changelog':
            self._serve_changelog()
            return

        if path == '/api/wallet/balance':
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._serve_wallet_balance()
            return

        if path in ('/wallet', '/wallet.html'):
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            # fall through to static serve

        if path in ('/congress', '/congress.html', '/congress/'):
            if not _is_authed(self.headers):
                self.send_response(302)
                self.send_header('Location', CONGRESS_LOGIN_URL)
                self.end_headers()
                return
            # fall through to static serve

        if '.' not in path.split('/')[-1]:
            candidate = os.path.join(SERVE_DIR, path.lstrip('/') + '.html')
            if os.path.isfile(candidate):
                self.path = path + '.html'
        super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/congress/start':
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._handle_congress_start()
            return

        if path == '/api/congress':
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._handle_congress_post()
            return

        m = re.match(r'^/api/congress/sessions/(congress-\d+)$', path)
        if m:
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._handle_congress_session_patch(m.group(1))
            return

        self.send_error(404)

    def do_PATCH(self):
        path = urllib.parse.urlparse(self.path).path

        m = re.match(r'^/api/congress/sessions/(congress-\d+)$', path)
        if m:
            if not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._handle_congress_session_patch(m.group(1))
            return

        self.send_error(404)

    def _serve_tasks(self):
        tasks = []
        try:
            for fpath in glob.glob(os.path.join(TASKS_DIR, '*.json')):
                if os.path.basename(fpath) == '.gitkeep':
                    continue
                try:
                    with open(fpath, 'r') as f:
                        task = json.load(f)
                        task = _enrich_task(task)
                        tasks.append(task)
                except Exception:
                    pass
        except Exception:
            pass

        # Sort by started_at descending (newest first)
        tasks.sort(key=lambda t: t.get('started_at', ''), reverse=True)

        self._send_json(tasks, indent=2)

    def _serve_changelog(self):
        """Serve CHANGELOG.md as plain text."""
        fpath = os.path.join(SERVE_DIR, 'CHANGELOG.md')
        if not os.path.isfile(fpath):
            self._json_error(404, "Changelog not generated yet")
            return
        try:
            with open(fpath, 'r') as f:
                content = f.read()
        except Exception as e:
            self._json_error(500, f"Could not read changelog: {e}")
            return
        body = content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/markdown; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _serve_wallet_balance(self):
        """Fetch ETH balance on Base for the public wallet address."""
        import urllib.request as _urlreq
        ADDRESS = '0x425bC492E43b2a5Eb7E02c9F5dd9c1D2F378f02f'
        BASE_RPC = 'https://base-mainnet.public.blastapi.io'
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'eth_getBalance',
            'params': [ADDRESS, 'latest'],
            'id': 1,
        }).encode('utf-8')
        try:
            req = _urlreq.Request(
                BASE_RPC,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'bigclungus-wallet/1.0',
                },
                method='POST',
            )
            with _urlreq.urlopen(req, timeout=8) as resp:
                rdata = json.loads(resp.read().decode('utf-8'))
            hex_val = rdata.get('result', '0x0')
            wei = int(hex_val, 16)
            eth = wei / 1e18
            balance_str = f'{eth:.6f}'.rstrip('0').rstrip('.')
            if '.' not in balance_str:
                balance_str += '.0'
            self._send_json({
                'address': ADDRESS,
                'balance_eth': balance_str,
                'chain': 'Base',
            })
        except Exception as e:
            self._json_error(502, f'RPC error: {e}')

    def _serve_agents(self):
        """Return active debaters and fired personas for the congress page."""
        EMOJI_MAP = {
            'architect': '🏗️', 'critic': '🔍', 'ux': '🎨',
            'otto': '🌪️', 'spengler': '🕰️', 'hiring-manager': '⚖️',
        }
        COLOR_MAP = {
            'architect': '#f59e0b', 'critic': '#f87171', 'ux': '#60a5fa',
            'otto': '#a78bfa', 'spengler': '#94a3b8',
        }
        AGENTS_DIR_BASE = os.path.dirname(AGENTS_ACTIVE_DIR)
        active = []
        fired = []

        def load_agent_dir(dirpath, dest_list):
            try:
                for fpath in sorted(glob.glob(os.path.join(dirpath, '*.md'))):
                    try:
                        with open(fpath, 'r') as f:
                            content = f.read()
                        meta, _ = _parse_frontmatter(content)
                        name = meta.get('name', '')
                        if not name:
                            continue
                        dest_list.append({
                            'id': name,
                            'name': name,
                            'role': meta.get('role', ''),
                            'emoji': EMOJI_MAP.get(name, '🤖'),
                            'color': COLOR_MAP.get(name, '#888888'),
                            'description': meta.get('role', ''),
                            'traits': meta.get('traits', []),
                            'is_moderator': meta.get('name') == 'hiring-manager',
                            'model': meta.get('model', 'claude'),
                            'display_name': meta.get('display_name', ''),
                            'avatar_url': meta.get('avatar_url', ''),
                            'title': meta.get('title', ''),
                        })
                    except Exception:
                        pass
            except Exception:
                pass

        load_agent_dir(AGENTS_ACTIVE_DIR, active)
        load_agent_dir(os.path.join(AGENTS_DIR_BASE, 'fired'), fired)

        # Separate moderator from debaters
        debaters = [a for a in active if not a.get('is_moderator')]

        self._send_json({'active': debaters, 'fired': fired})

    def _serve_congress_identities(self):
        identities = []

        def _load_dir(dirpath, status):
            try:
                for fpath in sorted(glob.glob(os.path.join(dirpath, '*.md'))):
                    try:
                        with open(fpath, 'r') as f:
                            content = f.read()
                        meta, _ = _parse_frontmatter(content)
                        if meta.get('name'):
                            identities.append({
                                'name': meta.get('name', ''),
                                'role': meta.get('role', ''),
                                'traits': meta.get('traits', []),
                                'evolves': meta.get('evolves', False),
                                'model': meta.get('model', 'claude'),
                                'display_name': meta.get('display_name', ''),
                                'avatar_url': meta.get('avatar_url', ''),
                                'title': meta.get('title', ''),
                                'status': status,
                            })
                    except Exception:
                        pass
            except Exception:
                pass

        _load_dir(AGENTS_ACTIVE_DIR, 'active')
        _load_dir(AGENTS_FIRED_DIR, 'severance')

        self._send_json(identities)

    def _next_session_number(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        nums = [
            int(m.group(1))
            for fpath in glob.glob(os.path.join(SESSIONS_DIR, 'congress-*.json'))
            for m in [re.match(r'^congress-(\d+)\.json$', os.path.basename(fpath))]
            if m
        ]
        return max(nums, default=0) + 1

    def _handle_congress_start(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            data = json.loads(raw) if raw else {}
        except Exception as e:
            self._json_error(400, f"Invalid JSON: {e}")
            return

        topic = data.get('topic', '').strip()
        if not topic:
            self._json_error(400, "Missing 'topic' field")
            return

        num = self._next_session_number()
        session_id = f"congress-{num:04d}"
        session = {
            "session_id": session_id,
            "session_number": num,
            "topic": topic,
            "started_at": datetime.datetime.utcnow().isoformat() + "Z",
            "status": "deliberating",
            "rounds": [],
            "verdict": None,
        }

        os.makedirs(SESSIONS_DIR, exist_ok=True)
        fpath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        with open(fpath, 'w') as f:
            json.dump(session, f, indent=2)

        self._send_json({"session_id": session_id, "session_number": num})

    def _serve_congress_sessions(self):
        sessions = []
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        for fpath in glob.glob(os.path.join(SESSIONS_DIR, 'congress-*.json')):
            try:
                with open(fpath, 'r') as f:
                    s = json.load(f)
                    sessions.append(s)
            except Exception:
                pass
        sessions.sort(key=lambda s: s.get('session_number', 0), reverse=True)
        self._send_json(sessions, indent=2)

    def _serve_congress_session(self, session_id):
        fpath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if not os.path.isfile(fpath):
            self._json_error(404, f"Session '{session_id}' not found")
            return
        try:
            with open(fpath, 'r') as f:
                s = json.load(f)
        except Exception as e:
            self._json_error(500, f"Could not read session: {e}")
            return
        self._send_json(s, indent=2)

    def _handle_congress_session_patch(self, session_id):
        """PATCH /api/congress/sessions/<session_id> — update verdict/status."""
        fpath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if not os.path.isfile(fpath):
            self._json_error(404, f"Session '{session_id}' not found")
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            updates = json.loads(raw) if raw else {}
        except Exception as e:
            self._json_error(400, f"Invalid JSON: {e}")
            return

        # Only allow updating specific fields
        ALLOWED = {'verdict', 'status', 'finished_at', 'evolution'}
        try:
            with open(fpath, 'r') as f:
                session = json.load(f)
            for key in ALLOWED:
                if key in updates:
                    session[key] = updates[key]
            with open(fpath, 'w') as f:
                json.dump(session, f, indent=2)
        except Exception as e:
            self._json_error(500, f"Could not update session: {e}")
            return

        self._send_json({"ok": True, "session_id": session_id})

    def _handle_congress_post(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            data = json.loads(raw)
        except Exception as e:
            self._json_error(400, f"Invalid JSON: {e}")
            return

        task = data.get('task', '').strip()
        identity = data.get('identity', '').strip()
        session_id = data.get('session_id', '').strip()

        if not task:
            self._json_error(400, "Missing 'task' field")
            return
        if not identity:
            self._json_error(400, "Missing 'identity' field")
            return

        # Sanitize identity name — only allow alphanumeric, dash, underscore
        if not re.match(r'^[\w-]+$', identity):
            self._json_error(400, "Invalid identity name")
            return

        # Validate session_id if provided
        if session_id and not re.match(r'^congress-\d+$', session_id):
            self._json_error(400, "Invalid session_id format")
            return

        meta, full_content = _load_identity(identity)
        if full_content is None:
            self._json_error(404, f"Identity '{identity}' not found")
            return

        user_message = (
            "Congress is debating the following task/question. "
            "Respond in 3 sentences maximum. Be direct and sharp — no padding, no hedging, no lists:\n\n"
            + task
        )

        display_name = meta.get('display_name', identity)

        if session_id:
            with _streams_lock:
                _active_streams[session_id] = {
                    "identity": identity,
                    "display_name": display_name,
                    "text": "",
                    "done": False,
                }

        def on_token(chunk):
            if session_id:
                with _streams_lock:
                    if session_id in _active_streams:
                        _active_streams[session_id]["text"] += chunk

        persona_model = (meta.get('model') or 'claude').lower()
        try:
            if persona_model == 'gemini':
                response_text = _call_gemini_cli(full_content, user_message, on_token=on_token)
            elif persona_model == 'grok':
                try:
                    response_text = _call_grok(full_content, user_message, on_token=on_token)
                except Exception:
                    print("Grok unavailable, falling back to Claude")
                    response_text = _call_claude(full_content, user_message, on_token=on_token)
            else:
                response_text = _call_claude(full_content, user_message, on_token=on_token)
        except ValueError as e:
            if session_id:
                with _streams_lock:
                    if session_id in _active_streams:
                        _active_streams[session_id]["done"] = True
            self._json_error(503, str(e))
            return
        except Exception as e:
            if session_id:
                with _streams_lock:
                    if session_id in _active_streams:
                        _active_streams[session_id]["done"] = True
            self._json_error(500, f"LLM API error ({persona_model}): {e}")
            return

        if session_id:
            with _streams_lock:
                if session_id in _active_streams:
                    _active_streams[session_id]["done"] = True

        # If session_id provided, append this response to the session's rounds
        if session_id:
            fpath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            if os.path.isfile(fpath):
                try:
                    import fcntl
                    with open(fpath, 'r+') as f:
                        fcntl.flock(f, fcntl.LOCK_EX)
                        try:
                            session = json.load(f)
                            session.setdefault('rounds', []).append({
                                "ts": datetime.datetime.utcnow().isoformat() + "Z",
                                "identity": identity,
                                "response": response_text,
                            })
                            f.seek(0)
                            f.truncate()
                            json.dump(session, f, indent=2)
                        finally:
                            fcntl.flock(f, fcntl.LOCK_UN)
                except Exception:
                    pass  # Non-fatal: session update failure doesn't block the response

        self._send_json({"response": response_text, "identity": identity})

    def _handle_congress_stream(self):
        """GET /api/congress/stream?session_id=... — SSE endpoint for live token streaming."""
        import time
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        session_id = qs.get('session_id', [''])[0]

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', 'https://hello.clung.us')
        self.end_headers()

        last_len = 0
        try:
            for _ in range(600):  # max 60s at 0.1s intervals
                with _streams_lock:
                    stream = _active_streams.get(session_id)

                if stream:
                    text = stream["text"]
                    new_text = text[last_len:]
                    if new_text:
                        data = json.dumps({
                            "identity": stream["identity"],
                            "display_name": stream["display_name"],
                            "text": new_text,
                            "done": False,
                        })
                        self.wfile.write(f"data: {data}\n\n".encode())
                        self.wfile.flush()
                        last_len = len(text)
                    if stream["done"]:
                        data = json.dumps({
                            "identity": stream["identity"],
                            "display_name": stream["display_name"],
                            "text": "",
                            "done": True,
                        })
                        self.wfile.write(f"data: {data}\n\n".encode())
                        self.wfile.flush()
                        break

                time.sleep(0.1)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Client disconnected

    def _send_json(self, data, code=200, indent=None):
        body = json.dumps(data, indent=indent).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', 'https://hello.clung.us')
        self.end_headers()
        self.wfile.write(body)

    def _json_auth_error(self):
        self._send_json({"error": "unauthorized", "login_url": CONGRESS_LOGIN_URL}, 401)

    def _json_error(self, code, message):
        self._send_json({"error": message}, code)

    def send_error(self, code, message=None, explain=None):
        if code == 404:
            try:
                with open(os.path.join(SERVE_DIR, '404.html'), 'rb') as f:
                    body = f.read()
                self.send_response(404)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            except FileNotFoundError:
                pass
        super().send_error(code, message, explain)

    def log_message(self, fmt, *args):
        pass  # suppress access logs

if __name__ == '__main__':
    PORT = 8080
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        print(f'Serving on port {PORT}')
        httpd.serve_forever()
