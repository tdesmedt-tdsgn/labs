"""The only GitHub-specific code in the demo: read comments, post one back.

Standard library only, so `verify.sh` needs no install step. Swap this class
for a Slack or mail equivalent and the gate logic does not change.
"""
import json
import urllib.error
import urllib.request
from datetime import datetime

from .approval_gate import Comment

GITHUB_API = "https://api.github.com"


class ApiError(RuntimeError):
    """A failed call must be loud. An empty list would read as 'not approved
    yet' and the pipeline would sit out its whole timeout on a typo."""


class GitHubComments:
    def __init__(self, repo, issue, token=None, api_base=GITHUB_API, timeout=10):
        self.repo = repo
        self.issue = int(issue)
        self.token = token
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    @property
    def url(self):
        return f"{self.api_base}/repos/{self.repo}/issues/{self.issue}/comments"

    def _call(self, method, url, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "reply-to-approve-demo")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as e:
            raise ApiError(f"{method} {url} -> HTTP {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            raise ApiError(f"{method} {url} -> {e.reason}") from e

    def list_comments(self):
        # per_page=100 is enough for an approval thread; a busier thread would
        # need Link-header pagination.
        payload = self._call("GET", f"{self.url}?per_page=100")
        return [
            Comment(
                id=item["id"],
                author=item["user"]["login"],
                body=item.get("body") or "",
                created_at=datetime.fromisoformat(item["created_at"]),
            )
            for item in payload
        ]

    def post_comment(self, body):
        return self._call("POST", self.url, {"body": body})["id"]
