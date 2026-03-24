#!/usr/bin/env python3
"""Simple static file server with custom 404 page support."""
import http.server
import json
import os
import glob
import re

SERVE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_DIR = "/home/clungus/work/bigclungus-meta/tasks"
AGENTS_ACTIVE_DIR = "/home/clungus/work/bigclungus-meta/agents/active"

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
    else:
        # Old format: status/started_at/finished_at/summary already at top level
        pass

    # Pass through new metadata fields (present in newer task files)
    task.setdefault('run_in_background', task.get('run_in_background', None))
    task.setdefault('isolation', task.get('isolation', None))
    task.setdefault('model', task.get('model', None))

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
    """Load an identity file and return (meta, full_content) or None."""
    fpath = os.path.join(AGENTS_ACTIVE_DIR, f'{name}.md')
    if not os.path.isfile(fpath):
        return None, None
    with open(fpath, 'r') as f:
        content = f.read()
    meta, _ = _parse_frontmatter(content)
    return meta, content


def _call_claude(system_prompt, user_message):
    """Call Claude claude-haiku-4-5-20251001 and return the text response."""
    import anthropic
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    return message.content[0].text


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SERVE_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        import urllib.parse
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/tasks':
            self._serve_tasks()
            return

        if path == '/api/congress/identities':
            self._serve_congress_identities()
            return

        if path == '/api/agents':
            self._serve_agents()
            return

        if '.' not in path.split('/')[-1]:
            candidate = os.path.join(SERVE_DIR, path.lstrip('/') + '.html')
            if os.path.isfile(candidate):
                self.path = path + '.html'
        super().do_GET()

    def do_POST(self):
        import urllib.parse
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/congress':
            self._handle_congress_post()
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

        body = json.dumps(tasks, indent=2).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _serve_agents(self):
        """Return active debaters and fired personas for the congress page."""
        EMOJI_MAP = {
            'architect': '🏗️', 'critic': '🔍', 'ux': '🎨',
            'pragmatist': '🔧', 'devil': '😈',
        }
        COLOR_MAP = {
            'architect': '#f59e0b', 'critic': '#f87171', 'ux': '#60a5fa',
            'pragmatist': '#4ecca3', 'devil': '#c084fc',
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
                        })
                    except Exception:
                        pass
            except Exception:
                pass

        load_agent_dir(AGENTS_ACTIVE_DIR, active)
        load_agent_dir(os.path.join(AGENTS_DIR_BASE, 'fired'), fired)

        # Separate moderator from debaters
        debaters = [a for a in active if not a.get('is_moderator')]

        body = json.dumps({'active': debaters, 'fired': fired}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _serve_congress_identities(self):
        identities = []
        try:
            for fpath in sorted(glob.glob(os.path.join(AGENTS_ACTIVE_DIR, '*.md'))):
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
                        })
                except Exception:
                    pass
        except Exception:
            pass

        body = json.dumps(identities).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

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

        meta, full_content = _load_identity(identity)
        if full_content is None:
            self._json_error(404, f"Identity '{identity}' not found")
            return

        user_message = (
            "Congress is debating the following task/question. "
            "Respond as your persona in 2-4 sentences, focused and direct:\n\n"
            + task
        )

        try:
            response_text = _call_claude(full_content, user_message)
        except ValueError as e:
            self._json_error(503, str(e))
            return
        except Exception as e:
            self._json_error(500, f"Claude API error: {e}")
            return

        body = json.dumps({"response": response_text, "identity": identity}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, code, message):
        body = json.dumps({"error": message}).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

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
    import socketserver
    PORT = 8080
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        print(f'Serving on port {PORT}')
        httpd.serve_forever()
