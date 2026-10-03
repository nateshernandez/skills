#!/usr/bin/env python3
"""Search Reddit for product research through Arctic Shift, a free community archive.

Usage:
  reddit_search.py subreddits NAME [NAME ...]          subscribers and description of each;
                                                       `NAME*` lists subreddits starting NAME
  reddit_search.py posts SUBREDDIT QUERY [--since=12m] [--max=100]
  reddit_search.py comments SUBREDDIT QUERY [--since=12m] [--max=100]
  reddit_search.py thread POST_ID [--max=20]

--since is a date (2025-10-01) or an age: 30d, 12m (30-day months), 2y. --max caps what's fetched.
Posts and comments print most engaged first, after a summary line and a `cite:` URL that reruns
the search. `[builder?]` marks text that reads like someone selling or validating a product.
Keyword search needs a subreddit, so find the customer's subreddits first. Scores and comment
counts settle about 36 hours after posting. Arctic Shift isn't affiliated with Reddit and has no
uptime promise. When it's busy, this waits as told for up to 3 minutes, then gives up; answers
from the last day come from a cache in the temp dir.
"""

import hashlib
import json
import re
import statistics
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

BASE_URL = "https://arctic-shift.photon-reddit.com"
POSTS_PATH = "/api/posts/search"
COMMENTS_PATH = "/api/comments/search"
POST_FIELDS = "id,subreddit,title,selftext,score,num_comments,created_utc"
COMMENT_FIELDS = "id,link_id,subreddit,body,score,created_utc"
USER_AGENT = "kit-product-research (+https://github.com/nateshernandez/skills)"
PAGE_SIZE = 100
PAGE_PAUSE_SECONDS = 1.0
DEFAULT_WAIT_SECONDS = 10
MAX_WAIT_SECONDS = 60
MAX_RUN_SECONDS = 180
RUN_DEADLINE = time.monotonic() + MAX_RUN_SECONDS
CACHE_DIR = Path(tempfile.gettempdir()) / "kit-arctic-shift"
CACHE_SECONDS = 24 * 60 * 60
BUSY_WORDS = ("slow down", "timeout", "timed out")
TIMEOUT_SECONDS = 60
THREAD_FETCH_LIMIT = 500
EXCERPT_CHARS = 280
ENGAGED_COMMENTS = 20
DEFAULT_SINCE = "12m"
DEFAULT_MAX = {"posts": 100, "comments": 100, "thread": 20}
DAYS_PER_UNIT = {"d": 1, "m": 30, "y": 365}

AGE_RE = re.compile(r"(?P<count>\d+)(?P<unit>[dmy])")
FLAG_RE = re.compile(r"--(?P<name>since|max)=(?P<value>\S+)")
POST_ID_RE = re.compile(r"(?:t3_)?(?P<post_id>[a-z0-9]+)")
BUILDER_RE = re.compile(
    r"\b(?:disclosure|i built|founder|dm me|waitlist"
    r"|(?:i'?m|we'?re|i am|we are|thinking of|ended up|been) building"
    r"|building (?:a|an|something|my|this)\b|built (?:a|an|something) to"
    r"|my (?:app|startup|tool|saas|product|side project)|our (?:app|tool|product|platform)"
    r"|beta testers?|quick survey|not selling anything|validat(?:e|ing) (?:an|my|this) idea)",
    re.IGNORECASE,
)
REMOVED_TEXTS = frozenset(("[removed]", "[deleted]"))


class UsageError(Exception):
    pass


class ArchiveError(Exception):
    pass


class ArchiveBusyError(Exception):
    def __init__(self, message: str, wait_seconds: int) -> None:
        super().__init__(message)
        self.wait_seconds = wait_seconds


class Post(NamedTuple):
    post_id: str
    subreddit: str
    title: str
    text: str
    score: int
    comment_count: int
    created: date


class Comment(NamedTuple):
    comment_id: str
    post_id: str
    subreddit: str
    text: str
    score: int
    created: date


class Subreddit(NamedTuple):
    name: str
    subscribers: int
    description: str


class Search(NamedTuple):
    subreddit: str
    query: str
    since: date
    max_results: int


def main() -> int:
    if not sys.argv[1:]:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        print(run(sys.argv[1], sys.argv[2:]))
    except UsageError as error:
        print(f"{error}\n\n{__doc__}", file=sys.stderr)
        return 1
    except ArchiveError as error:
        print(f"Arctic Shift: {error}", file=sys.stderr)
        return 1
    return 0


def run(command: str, arguments: list[str]) -> str:
    flags, positionals = split_flags(arguments)
    if command == "subreddits" and positionals and not flags:
        return format_subreddits(fetch_subreddits(positionals))
    if command in ("posts", "comments") and len(positionals) == 2:
        search = Search(
            subreddit=positionals[0].removeprefix("r/"),
            query=positionals[1],
            since=parse_since(flags.get("since", DEFAULT_SINCE), datetime.now(UTC).date()),
            max_results=parse_max(flags.get("max"), command),
        )
        if command == "posts":
            return format_posts(search, search_posts(search))
        return format_comments(search, search_comments(search))
    if command == "thread" and len(positionals) == 1 and "since" not in flags:
        post_id = parse_post_id(positionals[0])
        return format_thread(
            fetch_post(post_id), fetch_thread(post_id), parse_max(flags.get("max"), command)
        )
    raise UsageError(f"can't run `{' '.join([command, *arguments])}`")


def split_flags(arguments: list[str]) -> tuple[dict[str, str], list[str]]:
    flags: dict[str, str] = {}
    positionals: list[str] = []
    for argument in arguments:
        flag_match = FLAG_RE.fullmatch(argument)
        if flag_match:
            flags[flag_match.group("name")] = flag_match.group("value")
        elif argument.startswith("--"):
            raise UsageError(f"unknown flag `{argument}`")
        else:
            positionals.append(argument)
    return flags, positionals


def parse_since(since_text: str, today: date) -> date:
    age_match = AGE_RE.fullmatch(since_text)
    if age_match:
        days = int(age_match.group("count")) * DAYS_PER_UNIT[age_match.group("unit")]
        return today - timedelta(days=days)
    try:
        return date.fromisoformat(since_text)
    except ValueError:
        raise UsageError(f"--since=`{since_text}` should be a date or an age like 12m") from None


def parse_max(max_text: str | None, command: str) -> int:
    if max_text is None:
        return DEFAULT_MAX[command]
    if not max_text.isdigit() or int(max_text) < 1:
        raise UsageError(f"--max=`{max_text}` should be a whole number above 0")
    return int(max_text)


def parse_post_id(post_text: str) -> str:
    """Takes a bare ID, a `t3_` ID, or a reddit.com link to the post."""
    link_match = re.search(r"/comments/([a-z0-9]+)", post_text)
    if link_match:
        return link_match.group(1)
    id_match = POST_ID_RE.fullmatch(post_text)
    if not id_match:
        raise UsageError(f"`{post_text}` isn't a post ID or link")
    return id_match.group("post_id")


def fetch_subreddits(names: list[str]) -> list[Subreddit]:
    subreddits: list[Subreddit] = []
    for name in names:
        bare_name = name.removeprefix("r/")
        match_field = "subreddit_prefix" if bare_name.endswith("*") else "subreddit"
        rows = fetch(
            "/api/subreddits/search",
            {
                match_field: bare_name.rstrip("*"),
                "limit": "25",
                "fields": "display_name,subscribers,public_description",
            },
        )
        subreddits += [parse_subreddit(row) for row in rows]
    return sorted(set(subreddits), key=lambda subreddit: -subreddit.subscribers)


def search_posts(search: Search) -> list[Post]:
    rows = fetch_pages(POSTS_PATH, post_params(search), POST_FIELDS, search.max_results)
    return [parse_post(row) for row in rows]


def search_comments(search: Search) -> list[Comment]:
    rows = fetch_pages(COMMENTS_PATH, comment_params(search), COMMENT_FIELDS, search.max_results)
    return [parse_comment(row) for row in rows]


def post_params(search: Search) -> dict[str, str]:
    return {"subreddit": search.subreddit, "query": search.query, "after": search.since.isoformat()}


def comment_params(search: Search) -> dict[str, str]:
    return {"subreddit": search.subreddit, "body": search.query, "after": search.since.isoformat()}


def fetch_post(post_id: str) -> Post:
    rows = fetch("/api/posts/ids", {"ids": post_id})
    if not rows:
        raise ArchiveError(f"no post with ID `{post_id}`")
    return parse_post(rows[0])


def fetch_thread(post_id: str) -> list[Comment]:
    rows = fetch_pages(COMMENTS_PATH, {"link_id": post_id}, COMMENT_FIELDS, THREAD_FETCH_LIMIT)
    return [parse_comment(row) for row in rows]


def fetch_pages(path: str, params: dict[str, str], fields: str, max_results: int) -> list[dict]:
    """Pages newest first by moving `before` to the oldest result seen."""
    rows: list[dict] = []
    seen_ids: set[str] = set()
    page_params = {**params, "sort": "desc", "fields": fields}
    while len(rows) < max_results:
        page_size = min(PAGE_SIZE, max_results - len(rows))
        page = fetch(path, {**page_params, "limit": str(page_size)})
        new_rows = [row for row in page if row["id"] not in seen_ids]
        rows += new_rows
        seen_ids.update(row["id"] for row in new_rows)
        if len(page) < page_size or not new_rows:
            break
        page_params["before"] = str(min(row["created_utc"] for row in page))
        time.sleep(PAGE_PAUSE_SECONDS)
    return rows[:max_results]


def fetch(path: str, params: dict[str, str]) -> list[dict]:
    url = archive_url(path, params)
    cache_path = CACHE_DIR / f"{hashlib.sha1(url.encode()).hexdigest()}.json"
    if cache_path.exists() and time.time() - cache_path.stat().st_mtime < CACHE_SECONDS:
        return json.loads(cache_path.read_text())
    while True:
        try:
            rows = ask(url)
        except ArchiveBusyError as busy:
            wait_out(busy)
            continue
        CACHE_DIR.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(rows))
        return rows


def wait_out(busy: ArchiveBusyError) -> None:
    if time.monotonic() + busy.wait_seconds > RUN_DEADLINE:
        raise ArchiveError(
            f"still busy after {MAX_RUN_SECONDS // 60} minutes ({busy}); "
            "try again later, or say so under Unknown"
        )
    print(f"Arctic Shift is busy; waiting {busy.wait_seconds}s", file=sys.stderr)
    time.sleep(busy.wait_seconds)


def archive_url(path: str, params: dict[str, str]) -> str:
    return f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"


def ask(url: str) -> list[dict]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = json.load(response)
    except urllib.error.HTTPError as error:
        message = error.read().decode(errors="replace")[:200]
        if error.code != 429 and not (error.code == 422 and is_busy(message)):
            raise ArchiveError(f"HTTP {error.code} for {url}: {message}") from error
        reset_header = error.headers.get("X-RateLimit-Reset")
        raise ArchiveBusyError(message, wait_seconds(reset_header)) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise ArchiveError(f"unreachable ({error}); say so under Unknown") from error
    if body.get("error"):
        if not is_busy(body["error"]):
            raise ArchiveError(f"{body['error']} ({url})")
        raise ArchiveBusyError(body["error"], DEFAULT_WAIT_SECONDS)
    return body["data"] or []


def is_busy(message: str) -> bool:
    return any(word in message.lower() for word in BUSY_WORDS)


def wait_seconds(reset_header: str | None) -> int:
    reset_seconds = int(reset_header) + 1 if reset_header and reset_header.isdigit() else 0
    return min(reset_seconds or DEFAULT_WAIT_SECONDS, MAX_WAIT_SECONDS)


def parse_post(row: dict) -> Post:
    return Post(
        post_id=row["id"],
        subreddit=row["subreddit"],
        title=row["title"],
        text=clean_text(row.get("selftext") or ""),
        score=int(row["score"]),
        comment_count=int(row["num_comments"]),
        created=datetime.fromtimestamp(row["created_utc"], UTC).date(),
    )


def parse_comment(row: dict) -> Comment:
    return Comment(
        comment_id=row["id"],
        post_id=row["link_id"].removeprefix("t3_"),
        subreddit=row["subreddit"],
        text=clean_text(row["body"]),
        score=int(row["score"]),
        created=datetime.fromtimestamp(row["created_utc"], UTC).date(),
    )


def parse_subreddit(row: dict) -> Subreddit:
    return Subreddit(
        name=row["display_name"],
        subscribers=int(row["subscribers"] or 0),
        description=clean_text(row.get("public_description") or ""),
    )


def clean_text(text: str) -> str:
    return "" if text.strip() in REMOVED_TEXTS else " ".join(text.split())


def format_subreddits(subreddits: list[Subreddit]) -> str:
    if not subreddits:
        return "no subreddits found; try a shorter prefix, like `bookkeep*`"
    return "\n".join(
        f"r/{subreddit.name}  {subreddit.subscribers:,} subscribers  "
        f"{excerpt(subreddit.description)}"
        for subreddit in subreddits
    )


def format_posts(search: Search, posts: list[Post]) -> str:
    ranked = sorted(posts, key=lambda post: (post.comment_count, post.score), reverse=True)
    comment_counts = [post.comment_count for post in posts]
    engaged_count = sum(count >= ENGAGED_COMMENTS for count in comment_counts)
    summary = [
        f"{len(posts)} posts{capped_note(len(posts), search.max_results)}",
        f"median {statistics.median(comment_counts) if posts else 0:g} comments",
        f"{engaged_count} with {ENGAGED_COMMENTS}+ comments",
        f"{sum(looks_like_builder(full_text(post)) for post in posts)} [builder?]",
    ]
    lines = [header(search, summary, archive_url(POSTS_PATH, post_params(search)))]
    for post in ranked:
        lines.append(
            f"{post.created}  {post.score} pts  {post.comment_count} comments"
            f"{builder_marker(full_text(post))}  {post.title}  {post_link(post)}"
        )
        if post.text:
            lines.append(f"    {excerpt(post.text)}")
    return "\n".join(lines)


def format_comments(search: Search, comments: list[Comment]) -> str:
    ranked = sorted(comments, key=lambda comment: comment.score, reverse=True)
    summary = [
        f"{len(comments)} comments{capped_note(len(comments), search.max_results)}",
        f"in {len({comment.post_id for comment in comments})} threads",
        f"{sum(looks_like_builder(comment.text) for comment in comments)} [builder?]",
    ]
    lines = [header(search, summary, archive_url(COMMENTS_PATH, comment_params(search)))]
    lines += [format_comment(comment) for comment in ranked]
    return "\n".join(lines)


def format_thread(post: Post, comments: list[Comment], max_comments: int) -> str:
    ranked = sorted(comments, key=lambda comment: comment.score, reverse=True)[:max_comments]
    lines = [
        f"r/{post.subreddit} · {post.created} · {post.score} pts · "
        f"{post.comment_count} comments{builder_marker(full_text(post))}",
        post.title,
        post_link(post),
    ]
    if post.text:
        lines.append(f"    {excerpt(post.text)}")
    lines.append(f"top {len(ranked)} of {len(comments)} archived comments by score:")
    lines += [format_comment(comment) for comment in ranked]
    return "\n".join(lines)


def format_comment(comment: Comment) -> str:
    link = (
        f"https://www.reddit.com/r/{comment.subreddit}/comments/{comment.post_id}/_/"
        f"{comment.comment_id}"
    )
    marker = builder_marker(comment.text)
    return f"{comment.created}  {comment.score} pts{marker}  {link}\n    {excerpt(comment.text)}"


def header(search: Search, summary: list[str], cite_url: str) -> str:
    heading = f'r/{search.subreddit} · "{search.query}" · since {search.since}: '
    return f"{heading}{' · '.join(summary)}\ncite: {cite_url}\n"


def capped_note(found: int, max_results: int) -> str:
    is_capped = found >= max_results
    return f" (stopped at --max={max_results}; raise it for a full count)" if is_capped else ""


def post_link(post: Post) -> str:
    return f"https://www.reddit.com/r/{post.subreddit}/comments/{post.post_id}/"


def full_text(post: Post) -> str:
    return f"{post.title} {post.text}"


def builder_marker(text: str) -> str:
    return " [builder?]" if looks_like_builder(text) else ""


def looks_like_builder(text: str) -> bool:
    return BUILDER_RE.search(text) is not None


def excerpt(text: str) -> str:
    return text if len(text) <= EXCERPT_CHARS else text[: EXCERPT_CHARS - 1].rstrip() + "…"


if __name__ == "__main__":
    sys.exit(main())
