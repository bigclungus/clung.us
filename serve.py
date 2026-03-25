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

LLM_MAX_TOKENS = 300  # Hard cap per debate response

EMOJI_MAP = {
    'architect': '🏗️', 'critic': '🔍', 'ux': '🎨',
    'otto': '🌪️', 'spengler': '🕰️', 'hiring-manager': '⚖️',
}
COLOR_MAP = {
    'architect': '#f59e0b', 'critic': '#f87171', 'ux': '#60a5fa',
    'otto': '#a78bfa', 'spengler': '#94a3b8',
}

# ── GitHub auth ────────────────────────────────────────────────────────────────
GITHUB_COOKIE = "tauth_github"
GITHUB_ALLOWED_USERS = {u.lower() for u in os.environ.get('GITHUB_ALLOWED_USERS', '').split(',') if u.strip()}
COOKIE_SECRET = os.environ.get('COOKIE_SECRET', '')
GITHUB_CLIENT_ID     = os.environ.get('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '')
COOKIE_MAX_AGE = 86400  # 24 hours
CONGRESS_LOGIN_URL = "https://clung.us/auth/github?next=https://clung.us/congress"


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


def _is_authed(request_headers):
    """Check tauth_github cookie (HMAC-signed) against GITHUB_ALLOWED_USERS. Empty set = any authed user ok."""
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


def _call_gemini_cli(system_prompt, user_message, on_token=None):
    """Call Gemini via the gemini CLI (OAuth auth, no API key needed)."""
    # Strip YAML frontmatter (---\n...\n---\n) from system_prompt — gemini CLI fails if
    # the prompt passed via -p starts with '---'.
    _, system_prompt_body = _parse_frontmatter(system_prompt)
    # Combine system prompt body + user message as the full prompt; gemini -p appends to stdin
    full_prompt = system_prompt_body + "\n\n" + user_message
    proc = subprocess.Popen(
        ['/usr/local/bin/gemini', '--yolo', '-p', full_prompt],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    full_text = ""
    for line in proc.stdout:
        full_text += line
        if on_token:
            on_token(line)
    proc.wait()
    return full_text.strip()


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
            import time as _time

            host = os.environ.get('TEMPORAL_HOST', 'localhost:7233')
            client = await Client.connect(host)
            wf_id = (
                f"github-webhook-{params.get('event_type','unknown')}-"
                f"{params.get('repo','').replace('/', '-')}-"
                f"{params.get('number', 0)}-{int(_time.time())}"
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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
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
            if not _is_authed(self.headers):
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
            pass  # public page — fall through to static serve

        if '.' not in path.split('/')[-1]:
            candidate = os.path.join(SERVE_DIR, path.lstrip('/') + '.html')
            if os.path.isfile(candidate):
                self.path = path + '.html'
        super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/congress/start':
            if not _is_localhost(self.client_address) and not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._handle_congress_start()
            return

        if path == '/api/congress':
            if not _is_localhost(self.client_address) and not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._handle_congress_post()
            return

        m = re.match(r'^/api/congress/sessions/(congress-\d+)$', path)
        if m:
            if not _is_localhost(self.client_address) and not _is_authed(self.headers):
                self._json_auth_error()
                return
            self._handle_congress_session_patch(m.group(1))
            return

        if path == '/webhook/github':
            self._handle_github_webhook()
            return

        self.send_error(404)

    def do_PATCH(self):
        path = urllib.parse.urlparse(self.path).path

        m = re.match(r'^/api/congress/sessions/(congress-\d+)$', path)
        if m:
            if not _is_localhost(self.client_address) and not _is_authed(self.headers):
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
        load_agent_dir(AGENTS_FIRED_DIR, fired)

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
            elif persona_model == 'grok' or persona_model.startswith('grok-'):
                # Route to xAI Grok; use specific model name if given (e.g. grok-3-mini), else default
                grok_model = persona_model if persona_model.startswith('grok-') else 'grok-3-mini'
                try:
                    response_text = _call_grok(full_content, user_message, on_token=on_token, model=grok_model)
                except Exception as e:
                    print(f"Grok error for {identity}: {type(e).__name__}: {e}", flush=True)
                    print("Grok unavailable, falling back to Claude")
                    response_text = _call_claude(full_content, user_message, on_token=on_token)
            elif persona_model == 'opus':
                response_text = _call_claude(full_content, user_message, on_token=on_token, model='claude-opus-4-6')
            else:
                response_text = _call_claude(full_content, user_message, on_token=on_token)
        except ValueError as e:
            if session_id:
                with _streams_lock:
                    if session_id in _active_streams:
                        _active_streams[session_id]["done"] = True
                threading.Timer(60, _active_streams.pop, args=[session_id, None]).start()
            self._json_error(503, str(e))
            return
        except Exception as e:
            if session_id:
                with _streams_lock:
                    if session_id in _active_streams:
                        _active_streams[session_id]["done"] = True
                threading.Timer(60, _active_streams.pop, args=[session_id, None]).start()
            self._json_error(500, f"LLM API error ({persona_model}): {e}")
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
