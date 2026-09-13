"""A tiny stand-in for the two GitHub endpoints this gate needs.

It speaks real HTTP on a real socket, so the adapter under test does real
requests, real JSON parsing and real error handling. That is what makes the
offline end-to-end run meaningful rather than a mock rehearsal.
"""
import json
import re
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

COMMENTS_PATH = re.compile(r"^/repos/([^/]+/[^/]+)/issues/(\d+)/comments")


class FakeGitHub:
    def __init__(self, repo, issue, comments=None, post_author="pipeline-bot"):
        self.repo = repo
        self.issue = int(issue)
        self.comments = list(comments or [])
        # Real pipelines often post with the owner's own personal token, so
        # their comments arrive under the approver's login.
        self.post_author = post_author
        self.auth_headers = []
        self.get_count = 0
        self._next_id = 1000
        self._server = HTTPServer(("127.0.0.1", 0), _make_handler(self))
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    # -- lifecycle -----------------------------------------------------
    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()

    @property
    def api_base(self):
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    # -- test-side helpers ---------------------------------------------
    def add_comment(self, body, author, created_at=None):
        self._next_id += 1
        self.comments.append(
            {
                "id": self._next_id,
                "user": {"login": author},
                "body": body,
                "created_at": (
                    created_at or datetime.now(timezone.utc)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
        return self._next_id

    def bodies_by(self, author):
        return [c["body"] for c in self.comments if c["user"]["login"] == author]


def _make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def _route(self):
            m = COMMENTS_PATH.match(self.path)
            if not m or m.group(1) != state.repo or int(m.group(2)) != state.issue:
                return None
            return m

        def _send(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            state.auth_headers.append(self.headers.get("Authorization"))
            if not self._route():
                return self._send(404, {"message": "Not Found"})
            state.get_count += 1
            self._send(200, state.comments)

        def do_POST(self):
            state.auth_headers.append(self.headers.get("Authorization"))
            if not self._route():
                return self._send(404, {"message": "Not Found"})
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            cid = state.add_comment(payload.get("body", ""), author=state.post_author)
            self._send(201, {"id": cid})

        def log_message(self, *args):
            pass  # keep verify.sh output readable

    return Handler


def minutes_ago(n):
    return datetime.now(timezone.utc) - timedelta(minutes=n)
