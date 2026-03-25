#!/usr/bin/env python3
import http.server
import hmac
import hashlib
import json
import os
import glob
import re
import datetime
import subprocess
import fcntl
import secrets
import sqlite3
import time
import urllib.parse
import urllib.request
import socketserver
import threading
import asyncio

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
PERSONAS_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'personas.db')

LLM_MAX_TOKENS = 300  # Hard cap per debate response

EMOJI_MAP = {
    'architect': '🏗️', 'critic': '🔍', 'ux': '🎨',
    'otto': '🌪️', 'spengler': '🕰️', 'hiring-manager': '⚖️',
    'wolf': '🐺', 'hume': '🔬', 'adelbert': '🗡️', 'nemesis': '⚡',
}
COLOR_MAP = {
    'architect': '#f59e0b', 'critic': '#f87171', 'ux': '#60a5fa',
    'otto': '#a78bfa', 'spengler': '#94a3b8',
    'wolf': '#f97316', 'hume': '#38bdf8', 'adelbert': '#e879f9', 'nemesis': '#f43f5e',
}

# ── GitHub auth ────────────────────────────────────────────────────────────────
GITHUB_COOKIE = "tauth_github"
GITHUB_ALLOWED_USERS = {u.lower() for u in os.environ.get('GITHUB_ALLOWED_USERS', '').split(',') if u.strip()}
COOKIE_SECRET = os.environ.get('COOKIE_SECRET', '')
GITHUB_CLIENT_ID     = os.environ.get('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '')
COOKIE_MAX_AGE = 86400  # 24 hours
CONGRESS_LOGIN_URL = "https://clung.us/auth/github?next=https://clung.us/congress"
INTERNAL_TOKEN = os.environ.get('INTERNAL_TOKEN', '')


def _verify_cookie(value: str) -> str:
    """Verify a signed cookie value. Returns the username on success, '' on failure."""
    if not COOKIE_SECRET or '.' not in value:
        return ''
    username, _, sig = value.rpartition('.')
    expected = hmac.new(COOKIE_SECRET.encode(), username.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, expected):
        return username
    return ''


def _sign_cookie(username: str) -> str:
    """Return a signed cookie value: username.hmac_hex"""
    if not COOKIE_SECRET:
        return username
    sig = hmac.new(COOKIE_SECRET.encode(), username.encode(), hashlib.sha256).hexdigest()
    return f'{username}.{sig}'


def _is_safe_redirect(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ''
        return (host == 'clung.us' or host.endswith('.clung.us')) and parsed.scheme == 'https'
    except Exception:
        return False


_LOCALHOST_ADDRS = frozenset(('127.0.0.1', '::1'))


def _is_localhost(client_address):
    """Return True if the request originates from localhost (internal service-to-service calls)."""
    return client_address[0] in _LOCALHOST_ADDRS


# ── Persona metadata DB ────────────────────────────────────────────────────────

def _get_personas_db() -> sqlite3.Connection:
    """Open and return a sqlite3 connection to personas.db (row_factory set)."""
    conn = sqlite3.connect(PERSONAS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _load_persona_meta() -> dict:
    """
    Load all persona rows from personas.db into a dict keyed by name.
    Returns an empty dict if the DB doesn't exist yet (graceful degradation).
    Each value is a plain dict of column→value.
    """
    if not os.path.isfile(PERSONAS_DB_PATH):
        import logging
        logging.warning("personas.db not found at %s — persona meta unavailable", PERSONAS_DB_PATH)
        return {}
    try:
        conn = _get_personas_db()
        rows = conn.execute("SELECT * FROM personas").fetchall()
        conn.close()
        return {row['name']: dict(row) for row in rows}
    except Exception as e:
        import logging
        logging.warning("Failed to load personas.db: %s", e)
        return {}


# Module-level persona metadata cache with 60-second TTL.
# Keyed by persona name (e.g. 'critic', 'architect').
# Use _get_persona_meta() for reads; direct mutation is still fine for
# write paths that already hold fresh data from the DB.
_PERSONA_META: dict = _load_persona_meta()
_PERSONA_META_LOADED_AT: float = time.monotonic()
_PERSONA_META_TTL: float = 60.0  # seconds


def _get_persona_meta() -> dict:
    """Return the persona metadata dict, reloading from DB if the TTL has expired."""
    global _PERSONA_META, _PERSONA_META_LOADED_AT
    if time.monotonic() - _PERSONA_META_LOADED_AT > _PERSONA_META_TTL:
        _PERSONA_META = _load_persona_meta()
        _PERSONA_META_LOADED_AT = time.monotonic()
    return _PERSONA_META


def _is_authed(request_headers, client_address=None):
    """Check auth via tauth_github cookie or X-Internal-Token header.

    Cookie path: HMAC-signed tauth_github cookie checked against GITHUB_ALLOWED_USERS.
    Token path: X-Internal-Token header must match INTERNAL_TOKEN and request must be from localhost.
    Empty GITHUB_ALLOWED_USERS set = any authed user ok.
    """
    # Internal service-to-service auth via X-Internal-Token (localhost only)
    if INTERNAL_TOKEN and client_address is not None and _is_localhost(client_address):
        token_header = request_headers.get('X-Internal-Token', '')
        if token_header and hmac.compare_digest(token_header, INTERNAL_TOKEN):
            return True

    # Browser cookie auth path
    cookie_header = request_headers.get('Cookie', '')
    for part in cookie_header.split(';'):
        part = part.strip()
        if part.startswith(GITHUB_COOKIE + '='):
            raw = part[len(GITHUB_COOKIE) + 1:].strip()
            gh_user = _verify_cookie(raw) if raw else ''
            if gh_user:
                if not GITHUB_ALLOWED_USERS or gh_user.lower() in GITHUB_ALLOWED_USERS:
                    return True
    return False


# ── GitHub OAuth state store (in-memory; short-lived) ──────────────────────────
_oauth_states: dict = {}  # state_token -> next_url
_oauth_states_lock = threading.Lock()


def _oauth_state_new(next_url: str = '') -> str:
    state = secrets.token_urlsafe(16)
    with _oauth_states_lock:
        _oauth_states[state] = next_url
        # Prune old entries (keep last 100)
        if len(_oauth_states) > 100:
            oldest = list(_oauth_states.keys())[:50]
            for k in oldest:
                _oauth_states.pop(k, None)
    return state


def _oauth_state_consume(state: str):
    """Return next_url for state token and remove it, or None if invalid."""
    with _oauth_states_lock:
        return _oauth_states.pop(state, None)


_EVENT_TO_STATUS = {
    'started': 'in_progress',
    'milestone': 'in_progress',
    'user_feedback': 'in_progress',
    'blocked': 'in_progress',
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


def _call_claude_cli(system_prompt, user_message, on_token=None, model=None):
    """Call Claude via the claude CLI (OAuth auth, no API key needed)."""
    # Strip YAML frontmatter before passing via -p — the CLI treats '---' as
    # an unknown option flag if the prompt starts with it.
    _, system_prompt_body = _parse_frontmatter(system_prompt)
    cmd = ['/home/clungus/.local/bin/claude', '-p', system_prompt_body,
           '--output-format', 'stream-json', '--verbose', '--max-turns', '1']
    if model:
        cmd += ['--model', model]
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
            # Skip system/init events and any non-assistant events — only extract
            # text from assistant message blocks. This prevents the Claude CLI's
            # {"type":"system","subtype":"init",...} blob from leaking into output.
            if obj.get("type") in ("system", "result"):
                continue
            if obj.get("type") == "assistant":
                for block in obj.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        chunk = block.get("text", "")
                        full_text += chunk
                        if on_token:
                            on_token(chunk)
        except Exception:
            pass
    # Never fall back to raw stdout — it contains stream-json protocol events
    # (including {"type":"system","subtype":"init",...}) that must not leak into responses.
    result = full_text.strip()
    if not result:
        import logging
        logging.warning("_call_claude_cli: no assistant text extracted (exit=%s)", proc.returncode)
    return result



def _call_grok(system_prompt: str, user_message: str, on_token=None, model: str = "grok-3-mini") -> str:
    """Call xAI Grok via OpenAI-compatible API using XAI_API_KEY (streaming)."""
    api_key = os.environ.get("XAI_API_KEY", "")
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": LLM_MAX_TOKENS,
        "stream": True,
    }).encode()
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
    )
    full_text = ""
    with urllib.request.urlopen(req, timeout=60) as resp:
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


def _call_claude(system_prompt, user_message, on_token=None, model=None):
    """Call Claude and return the text response.
    Uses the anthropic Python client if ANTHROPIC_API_KEY is set, otherwise
    falls back to the claude CLI (authenticated via OAuth).
    model: override the Claude model (e.g. 'claude-opus-4-6'); defaults to haiku via API key path.
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        import anthropic  # optional dependency, only imported when API key is set
        client = anthropic.Anthropic(api_key=api_key)
        full_text = ""
        with client.messages.stream(
            model=model or "claude-haiku-4-5-20251001",
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
        return _call_claude_cli(system_prompt, user_message, on_token=on_token, model=model)


_MODEL_ALIASES = {
    'gemini': 'gemini-3-pro-preview',
    'grok': 'grok-3-mini',
    'opus': 'claude-opus-4-6',
    'claude': 'claude-haiku-4-5-20251001',
}


def _call_llm(model: str, system_prompt: str, user_message: str, on_token=None) -> str:
    """Unified LLM dispatch layer. Routes to the appropriate backend based on model name.

    Routing rules:
      - grok-* or xai/* → xAI API via _call_grok
      - gemini-* or google/* → Gemini CLI via _call_gemini_cli_with_model
      - claude-* → Anthropic via _call_claude
      - anything else → RuntimeError

    Raises a RuntimeError with model name and cause on failure — never swallows errors silently.
    """
    model_lower = (model or '').lower().strip()

    try:
        if model_lower.startswith('grok-') or model_lower.startswith('xai/'):
            # Normalize xai/ prefix to plain grok model name
            grok_model = model_lower[len('xai/'):] if model_lower.startswith('xai/') else model_lower
            return _call_grok(system_prompt, user_message, on_token=on_token, model=grok_model)

        elif model_lower.startswith('gemini-') or model_lower.startswith('google/'):
            # Gemini uses CLI (OAuth auth), ignore model routing for now — CLI uses its configured default
            # unless -m flag is passed; pass the model name through
            gemini_model = model_lower[len('google/'):] if model_lower.startswith('google/') else model_lower
            return _call_gemini_cli_with_model(system_prompt, user_message, model=gemini_model, on_token=on_token)

        elif model_lower.startswith('claude-'):
            return _call_claude(system_prompt, user_message, on_token=on_token, model=model_lower)

        else:
            raise RuntimeError(f"Unknown model: {model!r}")

    except Exception as e:
        raise RuntimeError(f"[{model}] {type(e).__name__}: {e}") from e


def _call_gemini_cli_with_model(system_prompt, user_message, model=None, on_token=None):
    """Call Gemini CLI with an explicit model flag (-m)."""
    _, system_prompt_body = _parse_frontmatter(system_prompt)
    full_prompt = system_prompt_body + "\n\n" + user_message
    cmd = ['/usr/local/bin/gemini', '--yolo', '-p', full_prompt, '--output-format', 'text']
    if model:
        cmd += ['-m', model]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    chunks = []
    for line in proc.stdout:
        chunks.append(line)
        if on_token:
            on_token(line)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"gemini CLI exited with code {proc.returncode}")
    return "".join(chunks).strip()


def _inc_verdict(vh: dict, display_name: str, verdict_type: str):
    """Increment verdict counters for a persona identified by display_name."""
    if not display_name:
        return
    if display_name not in vh:
        vh[display_name] = {'retained': 0, 'evolved': 0, 'fired': 0, 'last_verdict': ''}
    vh[display_name][verdict_type] = vh[display_name].get(verdict_type, 0) + 1
    vh[display_name]['last_verdict'] = verdict_type.upper()


DISCORD_INJECT_URL = 'http://127.0.0.1:9876/inject'
DISCORD_MAIN_CHAT_ID = '1485343472952148008'


def _start_github_webhook_workflow(params: dict):
    """Fire a GitHubWebhookWorkflow in Temporal. Runs in a daemon thread so it
    doesn't block the synchronous HTTP handler. Uses asyncio.run() since
    serve.py is fully synchronous (http.server based)."""

    async def _run():
        try:
            from temporalio.client import Client
            from temporalio.common import WorkflowIDReusePolicy
            host = os.environ.get('TEMPORAL_HOST', 'localhost:7233')
            client = await Client.connect(host)
            wf_id = (
                f"github-webhook-{params.get('event_type','unknown')}-"
                f"{params.get('repo','').replace('/', '-')}-"
                f"{params.get('number', 0)}-{int(time.time())}"
            )
            await client.start_workflow(
                'GitHubWebhookWorkflow',
                params,
                id=wf_id,
                task_queue='listings-queue',
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
            )
        except Exception as e:
            print(f'[webhook] failed to start GitHubWebhookWorkflow: {e}', flush=True)

    def _thread_target():
        asyncio.run(_run())

    t = threading.Thread(target=_thread_target, daemon=True)
    t.start()


def _github_comment(repo_full_name, issue_number, body):
    """Post a comment on a GitHub issue or PR."""
    token = os.environ.get('GITHUB_TOKEN', '')
    if not token:
        print('[webhook] GITHUB_TOKEN not set — skipping comment', flush=True)
        return
    url = f'https://api.github.com/repos/{repo_full_name}/issues/{issue_number}/comments'
    data = json.dumps({'body': body}).encode()
    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'token {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'BigClungus',
    })
    urllib.request.urlopen(req, timeout=10)


def _discord_inject(message):
    """Inject a notification into the bot's Discord session via the local inject endpoint."""
    try:
        secret_path = os.path.expanduser('~/.claude/channels/discord/.env')
        secret = ''
        if os.path.isfile(secret_path):
            for line in open(secret_path).read().splitlines():
                if line.startswith('DISCORD_INJECT_SECRET='):
                    secret = line.split('=', 1)[1].strip()
                    break
        if not secret:
            secret = os.environ.get('DISCORD_INJECT_SECRET', '')
        payload = json.dumps({
            'content': message,
            'chat_id': DISCORD_MAIN_CHAT_ID,
            'user': 'github-webhook',
        }).encode()
        req = urllib.request.Request(
            DISCORD_INJECT_URL,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-inject-secret': secret,
            },
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f'[webhook] discord inject failed: {e}', flush=True)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SERVE_DIR, **kwargs)

    def end_headers(self):
        # Inject Cache-Control: no-cache for JS and CSS so browsers always
        # revalidate rather than serving stale files from disk cache.
        path = urllib.parse.urlparse(self.path).path
        if path.endswith('.js') or path.endswith('.css'):
            self.send_header('Cache-Control', 'no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', 'https://clung.us')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/auth/github':
            self._handle_github_auth()
            return

        if path == '/auth/callback':
            self._handle_github_callback()
            return

        if path == '/terminal':
            self.send_response(302)
            self.send_header('Location', 'https://terminal.clung.us/')
            self.end_headers()
            return

        if path == '/api/tasks':
            if not _is_authed(self.headers, self.client_address):
                self._json_auth_error()
                return
            self._serve_tasks()
            return

        if path == '/api/congress/stream':
            self._handle_congress_stream()
            return

        if path == '/api/congress/identities':
            self._serve_congress_identities()
            return

        if path == '/api/congress/sessions':
            self._serve_congress_sessions()
            return

        m = re.match(r'^/api/congress/sessions/(congress-\d+)$', path)
        if m:
            self._serve_congress_session(m.group(1))
            return

        if path == '/api/agents':
            self._serve_agents()
            return

        if path == '/api/personas':
            if not _is_localhost(self.client_address):
                self._json_auth_error()
                return
            self._serve_personas_list()
            return

        m = re.match(r'^/api/personas/([\w-]+)$', path)
        if m:
            if not _is_localhost(self.client_address):
                self._json_auth_error()
                return
            self._serve_persona_detail(m.group(1))
            return

        if path == '/api/wallet/balance':
            if not _is_authed(self.headers, self.client_address):
                self._json_auth_error()
                return
            self._serve_wallet_balance()
            return

        if path in ('/wallet', '/wallet.html'):
            if not _is_authed(self.headers, self.client_address):
                self._json_auth_error()
                return
            # fall through to static serve

        if path in ('/congress', '/congress.html', '/congress/'):
            pass  # public page — fall through to static serve

        if path in ('/personas', '/personas/'):
            self.send_response(302)
            self.send_header('Location', '/congress#personas')
            self.end_headers()
            return

        if '.' not in path.split('/')[-1]:
            candidate = os.path.join(SERVE_DIR, path.lstrip('/') + '.html')
            if os.path.isfile(candidate):
                self.path = path + '.html'
        super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/congress/start':
            if not _is_localhost(self.client_address) and not _is_authed(self.headers, self.client_address):
                self._json_auth_error()
                return
            self._handle_congress_start()
            return

        if path == '/api/congress':
            if not _is_localhost(self.client_address) and not _is_authed(self.headers, self.client_address):
                self._json_auth_error()
                return
            self._handle_congress_post()
            return

        m = re.match(r'^/api/congress/sessions/(congress-\d+)$', path)
        if m:
            if not _is_localhost(self.client_address) and not _is_authed(self.headers, self.client_address):
                self._json_auth_error()
                return
            self._handle_congress_session_patch(m.group(1))
            return

        if path == '/webhook/github':
            self._handle_github_webhook()
            return

        if path == '/api/personas':
            if not _is_localhost(self.client_address):
                self._json_auth_error()
                return
            self._handle_persona_create()
            return

        m = re.match(r'^/api/personas/([\w-]+)/verdict$', path)
        if m:
            if not _is_localhost(self.client_address):
                self._json_auth_error()
                return
            self._handle_persona_verdict(m.group(1))
            return

        self.send_error(404)

    def do_PATCH(self):
        path = urllib.parse.urlparse(self.path).path

        m = re.match(r'^/api/congress/sessions/(congress-\d+)$', path)
        if m:
            if not _is_localhost(self.client_address) and not _is_authed(self.headers, self.client_address):
                self._json_auth_error()
                return
            self._handle_congress_session_patch(m.group(1))
            return

        m = re.match(r'^/api/personas/([\w-]+)$', path)
        if m:
            if not _is_localhost(self.client_address):
                self._json_auth_error()
                return
            self._handle_persona_update(m.group(1))
            return

        self.send_error(404)

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path

        m = re.match(r'^/api/personas/([\w-]+)$', path)
        if m:
            if not _is_localhost(self.client_address):
                self._json_auth_error()
                return
            self._handle_persona_delete(m.group(1))
            return

        self.send_error(404)

    # ── Personas CRUD ─────────────────────────────────────────────────────────

    def _persona_md_path(self, name, status='active'):
        """Return the md file path for a persona given its status."""
        dirpath = AGENTS_ACTIVE_DIR if status == 'active' else AGENTS_FIRED_DIR
        return os.path.join(dirpath, f'{name}.md')

    def _find_persona_md_path(self, name):
        """Find existing md file for persona name, checking active then fired. Returns (path, status) or (None, None)."""
        for status, dirpath in (('active', AGENTS_ACTIVE_DIR), ('fired', AGENTS_FIRED_DIR)):
            fpath = os.path.join(dirpath, f'{name}.md')
            if os.path.isfile(fpath):
                return fpath, status
        return None, None

    def _write_persona_md(self, fpath, meta, prompt):
        """Write a persona md file given frontmatter dict and prose prompt body."""
        lines = ['---']
        for key, val in meta.items():
            if isinstance(val, bool):
                lines.append(f'{key}: {str(val).lower()}')
            elif isinstance(val, list):
                items = ', '.join(str(v) for v in val)
                lines.append(f'{key}: [{items}]')
            elif val is None:
                pass  # skip None fields
            else:
                lines.append(f'{key}: {val}')
        lines.append('---')
        lines.append('')
        lines.append(prompt.strip() if prompt else '')
        content = '\n'.join(lines) + '\n'
        with open(fpath, 'w') as f:
            f.write(content)

    def _sync_persona_to_db(self, name, meta, status, md_path):
        """Upsert a single persona row in personas.db and refresh _PERSONA_META cache."""
        global _PERSONA_META
        conn = _get_personas_db()
        try:
            existing = conn.execute('SELECT name FROM personas WHERE name=?', (name,)).fetchone()
            congress_val = 1 if meta.get('congress', True) else 0
            evolves_val = 1 if meta.get('evolves', True) else 0
            now = datetime.datetime.utcnow().isoformat() + '+00:00'
            if existing:
                conn.execute('''
                    UPDATE personas SET
                        display_name=?, model=?, role=?, title=?, sex=?,
                        congress=?, evolves=?, status=?, md_path=?, avatar_url=?,
                        updated_at=?
                    WHERE name=?
                ''', (
                    meta.get('display_name', name),
                    meta.get('model', 'claude'),
                    meta.get('role', ''),
                    meta.get('title') or None,
                    meta.get('sex') or None,
                    congress_val,
                    evolves_val,
                    status,
                    md_path,
                    meta.get('avatar_url') or None,
                    now,
                    name,
                ))
            else:
                conn.execute('''
                    INSERT INTO personas
                        (name, display_name, model, role, title, sex, congress, evolves,
                         special_seat, stakeholder_only, status, md_path, avatar_url,
                         prompt_hash, total_congresses, times_evolved, times_fired,
                         times_reinstated, last_verdict, last_verdict_date, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,0,0,?,?,?,NULL,0,0,0,0,NULL,NULL,?)
                ''', (
                    name,
                    meta.get('display_name', name),
                    meta.get('model', 'claude'),
                    meta.get('role', ''),
                    meta.get('title') or None,
                    meta.get('sex') or None,
                    congress_val,
                    evolves_val,
                    status,
                    md_path,
                    meta.get('avatar_url') or None,
                    now,
                ))
            conn.commit()
            # Refresh cache entry
            row = conn.execute('SELECT * FROM personas WHERE name=?', (name,)).fetchone()
            if row:
                _PERSONA_META[name] = dict(row)
        finally:
            conn.close()

    def _serve_personas_list(self):
        """GET /api/personas — return all personas from DB."""
        conn = _get_personas_db()
        try:
            rows = conn.execute('SELECT * FROM personas ORDER BY name').fetchall()
            personas = [dict(r) for r in rows]
        finally:
            conn.close()
        self._send_json({'personas': personas})

    def _serve_persona_detail(self, name):
        """GET /api/personas/{name} — return one persona plus prompt body."""
        conn = _get_personas_db()
        try:
            row = conn.execute('SELECT * FROM personas WHERE name=?', (name,)).fetchone()
        finally:
            conn.close()

        if not row:
            self._json_error(404, f"Persona '{name}' not found")
            return

        persona = dict(row)

        # Read the prompt body from the md file
        fpath, _ = self._find_persona_md_path(name)
        prompt = ''
        if fpath and os.path.isfile(fpath):
            with open(fpath, 'r') as f:
                content = f.read()
            _, prompt = _parse_frontmatter(content)

        persona['prompt'] = prompt
        self._send_json({'persona': persona})

    def _handle_persona_create(self):
        """POST /api/personas — create a new persona."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            data = json.loads(raw) if raw else {}
        except Exception as e:
            self._json_error(400, f'Invalid JSON: {e}')
            return

        name = (data.get('name') or '').strip()
        if not name or not re.match(r'^[\w-]+$', name):
            self._json_error(400, "Missing or invalid 'name' field (alphanumeric + dash/underscore only)")
            return

        # Check for existing
        fpath_existing, _ = self._find_persona_md_path(name)
        if fpath_existing:
            self._json_error(409, f"Persona '{name}' already exists")
            return

        prompt = data.get('prompt', '')
        meta = {
            'name': name,
            'display_name': data.get('display_name', name),
            'model': data.get('model', 'claude-sonnet-4-6'),
            'role': data.get('role', ''),
            'title': data.get('title') or None,
            'sex': data.get('sex') or None,
            'congress': data.get('congress', True),
            'evolves': data.get('evolves', True),
            'avatar_url': data.get('avatar_url') or None,
        }

        fpath = self._persona_md_path(name, 'active')
        try:
            self._write_persona_md(fpath, meta, prompt)
        except Exception as e:
            self._json_error(500, f'Failed to write md file: {e}')
            return

        try:
            self._sync_persona_to_db(name, meta, 'active', fpath)
        except Exception as e:
            self._json_error(500, f'Failed to sync to DB: {e}')
            return

        conn = _get_personas_db()
        try:
            row = conn.execute('SELECT * FROM personas WHERE name=?', (name,)).fetchone()
            persona = dict(row) if row else {}
        finally:
            conn.close()
        persona['prompt'] = prompt

        self._send_json({'persona': persona}, code=201)

    def _handle_persona_update(self, name):
        """PATCH /api/personas/{name} — update fields on an existing persona."""
        fpath, current_status = self._find_persona_md_path(name)
        if not fpath:
            self._json_error(404, f"Persona '{name}' not found")
            return

        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            updates = json.loads(raw) if raw else {}
        except Exception as e:
            self._json_error(400, f'Invalid JSON: {e}')
            return

        # Read current md
        with open(fpath, 'r') as f:
            content = f.read()
        meta, current_prompt = _parse_frontmatter(content)

        # Apply frontmatter updates
        frontmatter_fields = {'model', 'role', 'title', 'sex', 'congress', 'evolves',
                               'avatar_url', 'display_name'}
        for field in frontmatter_fields:
            if field in updates:
                meta[field] = updates[field]

        prompt = updates.get('prompt', current_prompt)

        # Handle status change (file move)
        new_status = updates.get('status', current_status)
        if new_status not in ('active', 'fired'):
            self._json_error(400, f"Invalid status '{new_status}' — must be 'active' or 'fired'")
            return

        new_fpath = self._persona_md_path(name, new_status)

        try:
            if new_status != current_status:
                # Move the file
                os.makedirs(os.path.dirname(new_fpath), exist_ok=True)
                self._write_persona_md(new_fpath, meta, prompt)
                os.remove(fpath)
            else:
                self._write_persona_md(fpath, meta, prompt)
        except Exception as e:
            self._json_error(500, f'Failed to write md file: {e}')
            return

        try:
            self._sync_persona_to_db(name, meta, new_status, new_fpath)
        except Exception as e:
            self._json_error(500, f'Failed to sync to DB: {e}')
            return

        conn = _get_personas_db()
        try:
            row = conn.execute('SELECT * FROM personas WHERE name=?', (name,)).fetchone()
            persona = dict(row) if row else {}
        finally:
            conn.close()
        persona['prompt'] = prompt

        self._send_json({'persona': persona})

    def _handle_persona_delete(self, name):
        """DELETE /api/personas/{name} — remove md file and db row."""
        global _PERSONA_META

        fpath, _ = self._find_persona_md_path(name)
        if not fpath:
            self._json_error(404, f"Persona '{name}' not found")
            return

        try:
            os.remove(fpath)
        except Exception as e:
            self._json_error(500, f'Failed to remove md file: {e}')
            return

        conn = _get_personas_db()
        try:
            conn.execute('DELETE FROM personas WHERE name=?', (name,))
            conn.commit()
        except Exception as e:
            conn.close()
            self._json_error(500, f'Failed to remove from DB: {e}')
            return
        conn.close()

        _PERSONA_META.pop(name, None)

        self._send_json({'ok': True, 'deleted': name})

    def _handle_persona_verdict(self, name):
        """POST /api/personas/{name}/verdict — record a congress verdict in personas.db.

        Body: {"verdict": "FIRE"|"EVOLVE"|"RETAIN", "date": "YYYY-MM-DD"}

        For FIRE: increments times_fired, sets status='fired', moves md file to agents/fired/
          (if not already there — Option A: skip move if already in fired/).
        For EVOLVE: increments times_evolved.
        For RETAIN: no counter change beyond last_verdict fields.
        Always: sets last_verdict and last_verdict_date, refreshes _PERSONA_META.
        """
        global _PERSONA_META

        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            data = json.loads(raw) if raw else {}
        except Exception as e:
            self._json_error(400, f'Invalid JSON: {e}')
            return

        verdict = (data.get('verdict') or '').strip().upper()
        date_str = (data.get('date') or datetime.datetime.utcnow().strftime('%Y-%m-%d')).strip()

        if verdict not in ('FIRE', 'EVOLVE', 'RETAIN'):
            self._json_error(400, "Invalid verdict — must be FIRE, EVOLVE, or RETAIN")
            return

        conn = _get_personas_db()
        try:
            row = conn.execute('SELECT * FROM personas WHERE name=?', (name,)).fetchone()
            if not row:
                conn.close()
                self._json_error(404, f"Persona '{name}' not found")
                return

            now_iso = datetime.datetime.utcnow().isoformat() + '+00:00'

            if verdict == 'FIRE':
                conn.execute('''
                    UPDATE personas
                    SET last_verdict=?, last_verdict_date=?, times_fired=times_fired+1,
                        status='fired', updated_at=?
                    WHERE name=?
                ''', (verdict, date_str, now_iso, name))
                # Move md file to agents/fired/ unless already there
                active_path = os.path.join(AGENTS_ACTIVE_DIR, f'{name}.md')
                fired_path = os.path.join(AGENTS_FIRED_DIR, f'{name}.md')
                if os.path.isfile(active_path) and not os.path.isfile(fired_path):
                    import shutil as _shutil
                    _shutil.move(active_path, fired_path)
                # Update md_path in db to reflect new location
                final_path = fired_path if os.path.isfile(fired_path) else active_path
                conn.execute('UPDATE personas SET md_path=? WHERE name=?', (final_path, name))

            elif verdict == 'EVOLVE':
                conn.execute('''
                    UPDATE personas
                    SET last_verdict=?, last_verdict_date=?, times_evolved=times_evolved+1,
                        updated_at=?
                    WHERE name=?
                ''', (verdict, date_str, now_iso, name))

            else:  # RETAIN
                conn.execute('''
                    UPDATE personas
                    SET last_verdict=?, last_verdict_date=?, updated_at=?
                    WHERE name=?
                ''', (verdict, date_str, now_iso, name))

            conn.commit()
            # Refresh cache
            updated_row = conn.execute('SELECT * FROM personas WHERE name=?', (name,)).fetchone()
            if updated_row:
                _PERSONA_META[name] = dict(updated_row)
        finally:
            conn.close()

        self._send_json({'ok': True})

    # ── Tasks ─────────────────────────────────────────────────────────────────

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

    def _serve_wallet_balance(self):
        """Fetch ETH balance on Base for the public wallet address."""
        ADDRESS = '0x425bC492E43b2a5Eb7E02c9F5dd9c1D2F378f02f'
        BASE_RPC = 'https://base-mainnet.public.blastapi.io'
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'eth_getBalance',
            'params': [ADDRESS, 'latest'],
            'id': 1,
        }).encode('utf-8')
        try:
            req = urllib.request.Request(
                BASE_RPC,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'bigclungus-wallet/1.0',
                },
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
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
        active = []
        fired = []

        # Pre-compute verdict history from session files so the UI can show last verdict per persona
        verdict_history = {}  # name -> {retained: int, evolved: int, fired: int, last_verdict: str}
        try:
            for sfpath in glob.glob(os.path.join(SESSIONS_DIR, 'congress-*.json')):
                try:
                    with open(sfpath, 'r') as sf:
                        sdata = json.load(sf)
                    evo = sdata.get('evolution') or {}
                    for pname in evo.get('retained', []):
                        # retained is a list of display_names — match by display_name
                        _inc_verdict(verdict_history, pname, 'retained')
                    for item in evo.get('evolved', []):
                        _inc_verdict(verdict_history, item.get('display_name', ''), 'evolved')
                    for item in evo.get('fired', []):
                        _inc_verdict(verdict_history, item.get('display_name', ''), 'fired')
                except Exception:
                    pass
        except Exception:
            pass

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
                        dname = meta.get('display_name', '') or name
                        vh = verdict_history.get(dname, {})
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
                            'display_name': dname,
                            'avatar_url': meta.get('avatar_url', ''),
                            'title': meta.get('title', ''),
                            'sex': meta.get('sex', ''),
                            'stats_retained': vh.get('retained', 0),
                            'stats_evolved': vh.get('evolved', 0),
                            'stats_fired': vh.get('fired', 0),
                            'last_verdict': vh.get('last_verdict', ''),
                        })
                    except Exception:
                        pass
            except Exception:
                pass

        load_agent_dir(AGENTS_ACTIVE_DIR, active)
        load_agent_dir(AGENTS_FIRED_DIR, fired)

        # Separate moderator from debaters
        debaters = [a for a in active if not a.get('is_moderator')]
        moderator = next((a for a in active if a.get('is_moderator')), None)

        self._send_json({'active': debaters, 'fired': fired, 'moderator': moderator})

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
                            # Exclude personas with congress: false from congress seat selection
                            if meta.get('congress') is False:
                                continue
                            identities.append({
                                'name': meta.get('name', ''),
                                'role': meta.get('role', ''),
                                'traits': meta.get('traits', []),
                                'evolves': meta.get('evolves', False),
                                'model': meta.get('model', 'claude'),
                                'display_name': meta.get('display_name', ''),
                                'avatar_url': meta.get('avatar_url', ''),
                                'title': meta.get('title', ''),
                                'sex': meta.get('sex', ''),
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
        discord_user = data.get('discord_user', '') or ''

        num = self._next_session_number()
        session_id = f"congress-{num:04d}"

        # Snapshot the current persona roster so historical sessions show who existed then
        roster = []
        for dirpath, status in ((AGENTS_ACTIVE_DIR, 'active'), (AGENTS_FIRED_DIR, 'severance')):
            try:
                for fpath_agent in sorted(glob.glob(os.path.join(dirpath, '*.md'))):
                    try:
                        with open(fpath_agent, 'r') as _af:
                            content = _af.read()
                        meta, _ = _parse_frontmatter(content)
                        name = meta.get('name', '')
                        if not name or name == 'hiring-manager':
                            continue
                        if meta.get('congress') is False:
                            continue
                        roster.append({
                            'id': name,
                            'name': name,
                            'display_name': meta.get('display_name', ''),
                            'title': meta.get('title', ''),
                            'avatar_url': meta.get('avatar_url', ''),
                            'status': status,
                            'emoji': EMOJI_MAP.get(name, '🤖'),
                            'color': COLOR_MAP.get(name, '#888888'),
                            'description': meta.get('role', ''),
                            'role': meta.get('role', ''),
                            'model': meta.get('model', ''),
                        })
                    except Exception:
                        pass
            except Exception:
                pass

        session = {
            "session_id": session_id,
            "session_number": num,
            "topic": topic,
            "discord_user": discord_user or None,
            "started_at": datetime.datetime.utcnow().isoformat() + "Z",
            "status": "deliberating",
            "rounds": [],
            "verdict": None,
            "roster": roster,
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
        ALLOWED = {'verdict', 'status', 'finished_at', 'evolution', 'thread_id'}
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

        if identity == 'hiring-manager':
            length_instruction = (
                "Congress is debating the following task/question. "
                "Respond in 5-8 sentences maximum. Be direct and authoritative — "
                "no preamble, no padding, no lists. Deliver your synthesis or judgment plainly:\n\n"
            )
        else:
            length_instruction = (
                "Congress is debating the following task/question. "
                "Be concise — 3-4 sentences maximum. No preamble, no hedging, just your position:\n\n"
            )
        user_message = length_instruction + task

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

        # Model lookup: prefer personas.db (single authoritative source), fall
        # back to YAML frontmatter meta if the DB entry is missing.
        _db_entry = _get_persona_meta().get(identity)
        if _db_entry:
            persona_model = (_db_entry.get('model') or 'claude').strip()
        else:
            persona_model = (meta.get('model') or 'claude').strip()
        # Normalize legacy shorthand model names to canonical routing names
        routed_model = _MODEL_ALIASES.get(persona_model.lower(), persona_model)

        try:
            response_text = _call_llm(routed_model, full_content, user_message, on_token=on_token)
        except Exception as e:
            if session_id:
                with _streams_lock:
                    if session_id in _active_streams:
                        _active_streams[session_id]["done"] = True
                threading.Timer(60, _active_streams.pop, args=[session_id, None]).start()
            # Extract a short reason from the exception message
            reason = str(e)
            print(f"[congress] LLM error for {identity} ({routed_model}): {reason}", flush=True)
            self._send_json({
                "error": "Persona failed to respond",
                "persona": identity,
                "model": routed_model,
                "reason": reason,
            }, code=503)
            return

        if session_id:
            with _streams_lock:
                if session_id in _active_streams:
                    _active_streams[session_id]["done"] = True
            threading.Timer(60, _active_streams.pop, args=[session_id, None]).start()

        # If session_id provided, append this response to the session's rounds
        if session_id:
            fpath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            if os.path.isfile(fpath):
                try:
                    with open(fpath, 'r+') as f:
                        fcntl.flock(f, fcntl.LOCK_EX)
                        try:
                            session = json.load(f)
                            session.setdefault('rounds', []).append({
                                "ts": datetime.datetime.utcnow().isoformat() + "Z",
                                "identity": identity,
                                "response": response_text,
                                "model": routed_model,
                            })
                            f.seek(0)
                            f.truncate()
                            json.dump(session, f, indent=2)
                        finally:
                            fcntl.flock(f, fcntl.LOCK_UN)
                except Exception:
                    pass  # Non-fatal: session update failure doesn't block the response

        # Increment total_congresses for this persona in personas.db
        if identity and identity != 'hiring-manager':
            try:
                now_iso = datetime.datetime.utcnow().isoformat() + '+00:00'
                conn = _get_personas_db()
                try:
                    conn.execute(
                        'UPDATE personas SET total_congresses = total_congresses + 1, updated_at = ? WHERE name = ?',
                        (now_iso, identity)
                    )
                    conn.commit()
                    row = conn.execute('SELECT * FROM personas WHERE name=?', (identity,)).fetchone()
                    if row:
                        _PERSONA_META[identity] = dict(row)
                finally:
                    conn.close()
            except Exception as _e:
                import logging
                logging.warning("Failed to increment total_congresses for %s: %s", identity, _e)

        self._send_json({"response": response_text, "identity": identity})

    def _handle_congress_stream(self):
        """GET /api/congress/stream?session_id=... — SSE endpoint for live token streaming."""
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        session_id = qs.get('session_id', [''])[0]

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', 'https://clung.us')
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

    def _handle_github_webhook(self):
        # 1. Read body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # 2. Verify HMAC-SHA256 signature
        secret = os.environ.get('GITHUB_WEBHOOK_SECRET', '').encode()
        sig_header = self.headers.get('X-Hub-Signature-256', '')
        expected = 'sha256=' + hmac.new(secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            self._json_error(401, 'invalid signature')
            return

        # 3. Parse event
        event_type = self.headers.get('X-GitHub-Event', '')
        try:
            payload = json.loads(body)
        except Exception as e:
            self._json_error(400, f'invalid JSON: {e}')
            return

        action = payload.get('action', '')
        repo = payload.get('repository', {}).get('full_name', '')

        # 4. Handle each event type — dispatch to Temporal for ack/notify, return fast
        try:
            if event_type == 'ping':
                self._send_json({'ok': True, 'zen': payload.get('zen', '')})
                return

            elif event_type == 'issues' and action == 'opened':
                issue = payload.get('issue', {})
                _start_github_webhook_workflow({
                    'event_type': 'issues',
                    'action': 'opened',
                    'repo': repo,
                    'number': issue.get('number', 0),
                    'title': issue.get('title', ''),
                    'url': issue.get('html_url', ''),
                    'user': issue.get('user', {}).get('login', ''),
                })
                self._send_json({'ok': True, 'action': 'workflow_started'})

            elif event_type == 'issue_comment' and action == 'created':
                comment = payload.get('comment', {})
                commenter = comment.get('user', {}).get('login', '')
                # Skip ack for our own bot comments to avoid comment loops
                if commenter.lower() == 'bigclungus':
                    self._send_json({'ok': True, 'action': 'ignored (own comment)'})
                    return
                issue = payload.get('issue', {})
                _start_github_webhook_workflow({
                    'event_type': 'issue_comment',
                    'action': 'created',
                    'repo': repo,
                    'number': issue.get('number', 0),
                    'title': issue.get('title', ''),
                    'url': comment.get('html_url', ''),
                    'user': commenter,
                })
                self._send_json({'ok': True, 'action': 'workflow_started'})

            elif event_type == 'pull_request' and action == 'opened':
                pr = payload.get('pull_request', {})
                _start_github_webhook_workflow({
                    'event_type': 'pull_request',
                    'action': 'opened',
                    'repo': repo,
                    'number': pr.get('number', 0),
                    'title': pr.get('title', ''),
                    'url': pr.get('html_url', ''),
                    'user': pr.get('user', {}).get('login', ''),
                })
                self._send_json({'ok': True, 'action': 'workflow_started'})

            else:
                # All other events silently acknowledged
                self._send_json({'ok': True, 'action': 'ignored', 'event': event_type, 'action_type': action})

        except Exception as e:
            # Non-fatal: log but still return 200 to avoid GitHub retries spamming
            print(f'[webhook] error handling {event_type}/{action}: {e}', flush=True)
            self._send_json({'ok': False, 'error': str(e)})

    def _send_json(self, data, code=200, indent=None):
        body = json.dumps(data, indent=indent).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', 'https://clung.us')
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

    # ── GitHub OAuth handlers ──────────────────────────────────────────────────

    def _handle_github_auth(self):
        """Redirect to GitHub OAuth. Accepts ?next=<url> for post-auth redirect."""
        if not GITHUB_CLIENT_ID:
            self._send_html(500, '<h1>GitHub OAuth not configured</h1>')
            return
        qs = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(qs)
        next_url = params.get('next', [''])[0]
        state = _oauth_state_new(next_url)
        redirect_uri = 'https://clung.us/auth/callback'
        gh_url = (
            f'https://github.com/login/oauth/authorize'
            f'?client_id={urllib.parse.quote(GITHUB_CLIENT_ID)}'
            f'&scope=read:user'
            f'&state={urllib.parse.quote(state)}'
            f'&redirect_uri={urllib.parse.quote(redirect_uri)}'
        )
        self.send_response(302)
        self.send_header('Location', gh_url)
        # Store state in cookie for CSRF validation
        self.send_header('Set-Cookie',
            f'gh_oauth_state={state}; Max-Age=600; HttpOnly; SameSite=Lax; Path=/')
        self.end_headers()

    def _handle_github_callback(self):
        """Handle GitHub OAuth callback: exchange code, validate user, set cookie."""
        qs = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(qs)
        code = params.get('code', [''])[0]
        state = params.get('state', [''])[0]

        # Validate state (CSRF check via in-memory store + cookie fallback)
        next_url = _oauth_state_consume(state)
        if next_url is None:
            # Fallback: if service was restarted and in-memory state was lost,
            # validate against the gh_oauth_state cookie the browser sent back.
            cookie_header = self.headers.get('Cookie', '')
            cookie_state = ''
            for part in cookie_header.split(';'):
                part = part.strip()
                if part.startswith('gh_oauth_state='):
                    cookie_state = part[len('gh_oauth_state='):].strip()
                    break
            if cookie_state and cookie_state == state:
                # State matches cookie — treat next_url as empty (root redirect)
                next_url = ''
                print(f'[auth] OAuth state validated via cookie fallback (in-memory store was empty — service may have restarted)', flush=True)
            else:
                self._send_html(403, '<h1>Invalid OAuth state — please try again.</h1>')
                return

        if not code:
            self._send_html(403, '<h1>Missing OAuth code.</h1>')
            return

        try:
            # Exchange code for access token
            token_payload = json.dumps({
                'client_id':     GITHUB_CLIENT_ID,
                'client_secret': GITHUB_CLIENT_SECRET,
                'code':          code,
                'redirect_uri':  'https://clung.us/auth/callback',
            }).encode()
            token_req = urllib.request.Request(
                'https://github.com/login/oauth/access_token',
                data=token_payload,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'User-Agent': 'BigClungus',
                },
                method='POST',
            )
            with urllib.request.urlopen(token_req, timeout=10) as resp:
                token_data = json.loads(resp.read().decode())
            access_token = token_data.get('access_token', '')
            if not access_token:
                self._send_html(403, '<h1>Failed to obtain GitHub access token.</h1>')
                return

            # Get GitHub username
            user_req = urllib.request.Request(
                'https://api.github.com/user',
                headers={
                    'Authorization': f'token {access_token}',
                    'Accept': 'application/json',
                    'User-Agent': 'BigClungus',
                },
            )
            with urllib.request.urlopen(user_req, timeout=10) as resp:
                user_data = json.loads(resp.read().decode())
            username = user_data.get('login', '')
        except Exception as e:
            print(f'[auth] GitHub OAuth error: {e}', flush=True)
            self._send_html(502, f'<h1>GitHub OAuth error: {e}</h1>')
            return

        if not username:
            self._send_html(403, '<h1>Could not determine GitHub username.</h1>')
            return

        if GITHUB_ALLOWED_USERS and username.lower() not in GITHUB_ALLOWED_USERS:
            self._send_html(403, f'<h1>GitHub user {username!r} is not allowed.</h1>')
            return

        # Sign and set cookie
        cookie_value = _sign_cookie(username)
        redirect_to = next_url if _is_safe_redirect(next_url) else '/'
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>body{{background:#0a0a0f;color:#4ecca3;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}}</style>
</head>
<body><div>authenticated — redirecting...</div>
<script>window.location.replace({json.dumps(redirect_to)});</script>
</body>
</html>"""
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Set-Cookie',
            f'{GITHUB_COOKIE}={cookie_value}; Max-Age={COOKIE_MAX_AGE}; '
            f'HttpOnly; Secure; SameSite=Lax; Domain=.clung.us; Path=/')
        # Clear state cookie
        self.send_header('Set-Cookie',
            'gh_oauth_state=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/')
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, code, html_body):
        body = f'<!DOCTYPE html><html><body>{html_body}</body></html>'.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress access logs

if __name__ == '__main__':
    PORT = 8080
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('', PORT), Handler) as httpd:
        print(f'Serving on port {PORT}')
        httpd.serve_forever()
