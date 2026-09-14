"""The GitHub adapter, exercised over real HTTP against a fake API."""
import unittest
from datetime import timezone

from src.github_comments import ApiError, GitHubComments
from tests.fake_github import FakeGitHub, minutes_ago

REPO = "owner/repo"
ISSUE = 7


class ReadingComments(unittest.TestCase):
    def test_maps_the_github_payload_onto_comments(self):
        with FakeGitHub(REPO, ISSUE) as gh:
            gh.add_comment("go 3", author="repo-owner", created_at=minutes_ago(2))
            source = GitHubComments(REPO, ISSUE, api_base=gh.api_base)

            (c,) = source.list_comments()

            self.assertEqual(c.author, "repo-owner")
            self.assertEqual(c.body, "go 3")
            self.assertIsNotNone(c.created_at.tzinfo)
            self.assertEqual(c.created_at.tzinfo, timezone.utc)

    def test_sends_the_token_as_a_bearer_header(self):
        with FakeGitHub(REPO, ISSUE) as gh:
            GitHubComments(REPO, ISSUE, token="s3cret", api_base=gh.api_base).list_comments()
            self.assertEqual(gh.auth_headers, ["Bearer s3cret"])

    def test_omits_the_header_when_there_is_no_token(self):
        with FakeGitHub(REPO, ISSUE) as gh:
            GitHubComments(REPO, ISSUE, api_base=gh.api_base).list_comments()
            self.assertEqual(gh.auth_headers, [None])

    def test_a_wrong_repo_raises_instead_of_looking_unapproved(self):
        """Silently returning nothing would read as 'no approval yet' and the
        pipeline would wait out its timeout on a typo."""
        with FakeGitHub(REPO, ISSUE) as gh:
            source = GitHubComments("owner/typo", ISSUE, api_base=gh.api_base)
            with self.assertRaises(ApiError):
                source.list_comments()


class WritingComments(unittest.TestCase):
    def test_post_comment_lands_on_the_issue(self):
        with FakeGitHub(REPO, ISSUE) as gh:
            source = GitHubComments(REPO, ISSUE, token="t", api_base=gh.api_base)

            source.post_comment("could not read that as a decision")

            self.assertEqual(
                gh.bodies_by("pipeline-bot"), ["could not read that as a decision"]
            )


if __name__ == "__main__":
    unittest.main()
