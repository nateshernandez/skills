# Researching Reddit

Reddit is where customers describe their problems in their own words, unprompted. kit reaches it through `reddit_search.py`, which queries Arctic Shift, a free community archive of Reddit. Claude's web tools can't reach reddit.com, and Reddit refuses requests without approved API access.

## The script

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/reddit_search.py subreddits Bookkeeping "bookkeep*" Accounting
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/reddit_search.py posts Bookkeeping "chasing clients" --since=12m
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/reddit_search.py comments Bookkeeping "hubdoc" --since=6m --max=50
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/reddit_search.py thread https://www.reddit.com/r/Bookkeeping/comments/1run75a/
```

- **Output** → a summary line, a `cite:` URL that reruns the search, then results most engaged first
- **`[builder?]`** → the text reads like someone building, selling, or validating a product
- **A small budget** → Arctic Shift allows only a few searches a minute when it's busy, and keyword searches cost the most
  - Plan about ten calls: `subreddits` once, `posts` and `comments` for the strongest pain phrases, `thread` for the top two or three
  - Run them one at a time; the script waits as told for up to 3 minutes, then exits with `still busy`
  - Repeating a call within a day is free: answers are cached
- **Freshness** → scores and comment counts settle about 36 hours after posting

## Find where the customer talks

- **Search needs a subreddit** → Arctic Shift's keyword search runs within one subreddit, so find them first
- **Candidates** → the customer's job title, trade, and tools: `bookkeep*`, `Accounting`, `QuickBooks`
- **Web search** → "subreddit for <customer>" finds communities a prefix won't
- **Pick by size and fit** → `subreddits` prints subscribers and descriptions; a 50,000-member trade subreddit beats ten tiny ones
- **Founder subreddits** → r/SaaS, r/startups, r/Entrepreneur, and r/SideProject are builders talking to builders; never count them as demand

## Search for pain

- **The customers' words** → "how do you handle", "chasing", "I hate", "nightmare", "is there a tool", "spreadsheet"
- **Alternatives** → "alternative to <leader>", "<leader>" in comments, "switched from"
- **Money** → "we pay", "worth it", "too expensive", "per month"
- **One idea per query** → two or three words; Arctic Shift matches words, not meaning

## Read what comes back

- **Engagement over volume** → a thread with 69 comments is a real conversation; twelve posts with one comment each are not
- **Founders asking** → low-engagement posts phrased as surveys ("how much of your month goes to…", "talk me out of building") are usually builders validating; set them apart even without a `[builder?]` mark
- **Vendors answering** → comments that end in a product link or a disclosure are marketing; their complaints about rivals are still signal
- **Read the top threads** → `thread` on the two or three most engaged posts; the comments hold the workarounds and the money
- **Count, don't collect** → "22 posts in 12 months, 2 with 20+ comments, most by builders" with the `cite:` URL as the source
- **Quote sparingly** → 25 words or fewer, no usernames, linked to the thread or comment

## Limits

- **Arctic Shift** → not affiliated with Reddit, no uptime promise; `still busy` or `unreachable` means do the web research, retry Reddit once at the end, then say so under Unknown
- **Keep nothing raw** → write counts, short quotes, and links into market.md; leave search output out of the repo
