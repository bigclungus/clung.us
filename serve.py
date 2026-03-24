#!/usr/bin/env python3
"""Simple static file server with custom 404 page support."""
import http.server
import json
import os
import glob

SERVE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_DIR = "/home/clungus/work/bigclungus-meta/tasks"

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


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SERVE_DIR, **kwargs)

    def do_GET(self):
        import urllib.parse
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/tasks':
            self._serve_tasks()
            return

        if '.' not in path.split('/')[-1]:
            candidate = os.path.join(SERVE_DIR, path.lstrip('/') + '.html')
            if os.path.isfile(candidate):
                self.path = path + '.html'
        super().do_GET()

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
