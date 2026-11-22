"""
ALL Instagram-specific rules live in this file.

How Instagram data is collected, and why:

  * Instagram is never fetched by this project. Scraping runs on Apify's hosted
    Instagram actor, which does the fetching on their infrastructure and hands
    back JSON. That is the standalone scraper's approach, kept exactly.
  * Only publicly viewable content is read. No Instagram login is performed, no
    private profile is opened, and no authentication or rate limit is worked
    around.

Two actor runs per profile: one for the posts, one for their comments. When the
actor's output shape changes, edit THIS FILE ONLY.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Where the data comes from
# ---------------------------------------------------------------------------
#: Overridable with APIFY_INSTAGRAM_ACTOR_ID.
DEFAULT_ACTOR_ID = "apify/instagram-scraper"

#: What each run asks the actor for.
#: "details" returns the profile (followers, bio, name) with its latest posts nested in it -- but Instagram only ever
#: nests the newest 12 there, whatever limit is asked for. "posts" returns the posts themselves, up to the limit.
RESULTS_TYPE_POSTS = "details"
RESULTS_TYPE_MORE_POSTS = "posts"
RESULTS_TYPE_COMMENTS = "comments"
#: How many posts a "details" run nests at most (Instagram's own page size).
DETAILS_POSTS_CAP = 12

# ---------------------------------------------------------------------------
# 2. Links
# ---------------------------------------------------------------------------
ALLOWED_HOST_SUFFIX = "instagram.com"
CANONICAL_PROFILE_URL = "https://www.instagram.com/{username}/"

#: Instagram's own routes: none of these is a profile.
RESERVED_PATH_SEGMENTS = {
    "p", "reel", "reels", "tv", "stories", "explore", "accounts", "directory",
    "about", "developer", "legal", "privacy", "terms", "directory", "direct",
    "challenge", "emails", "session", "web", "graphql", "api",
}

#: A username is what Instagram allows: letters, digits, dots, underscores.
USERNAME_PATTERN = r"^[A-Za-z0-9._]{1,30}$"

# ---------------------------------------------------------------------------
# 3. The actor's output
# ---------------------------------------------------------------------------
#: A profile run returns one item per profile with its posts nested here.
NESTED_POSTS_KEY = "latestPosts"

#: Keys that only ever appear on a PROFILE item, never on a post. Used to tell
#: the two apart, because a comments/posts run returns posts at the top level
#: and a profile's own fields must never be read off one of those.
PROFILE_MARKER_KEYS = ("latestPosts", "followersCount", "biography", "fullName")

#: Dotted paths inside one profile object.
#:
#: The username lives HERE and nowhere else. A post's ``ownerUsername`` is the
#: post's author, and on a collaboration post -- two accounts publishing the
#: same post together -- that is the other account. Reading the profile name
#: off the first post is what made a profile display a stranger's handle.
PROFILE_PATHS = {
    "username": ["username"],
    "full_name": ["fullName"],
    "biography": ["biography"],
    "followers_count": ["followersCount"],
    "posts_count": ["postsCount"],
    "profile_picture": ["profilePicUrlHD", "profilePicUrl"],
    "is_verified": ["verified", "isVerified"],
    # Read for the engagement model (app/analysis/instagram/).
    "following_count": ["followsCount", "followingCount"],
    "external_url": ["externalUrl"],
    "highlights_count": ["highlightReelCount"],
    "category": ["businessCategoryName", "categoryName"],
}

#: Dotted paths inside one post object. First non-empty wins.
POST_PATHS = {
    "post_url": ["url"],
    "owner_username": ["ownerUsername", "owner.username"],
    "caption": ["caption"],
    "hashtags": ["hashtags"],
    "like_count": ["likesCount"],
    "comment_count": ["commentsCount"],
    "posted_at": ["timestamp"],
    "media_type": ["type"],
    "media_url": ["videoUrl", "displayUrl"],
    # The still picture Instagram shows for a post; for a video, its cover frame.
    "thumbnail_url": ["displayUrl"],
    "location": ["locationName"],
    "is_sponsored": ["isSponsored"],
    "video_views": ["videoViewCount", "videoPlayCount"],
}

#: Dotted paths inside one comment object.
COMMENT_PATHS = {
    "commenter_username": ["ownerUsername", "owner.username"],
    "comment_text": ["text"],
    "like_count": ["likesCount"],
    "posted_at": ["timestamp"],
}

#: Which post a comment belongs to.
COMMENT_POST_URL_PATHS = ["postUrl", "inputUrl", "parentUrl"]

#: A carousel post carries its slides here.
CHILD_POSTS_KEY = "childPosts"

# ---------------------------------------------------------------------------
# 4. Limits
# ---------------------------------------------------------------------------
#: Hard ceilings, whatever the settings ask for: one comparison must not turn
#: into an unbounded Apify bill.
MAX_POSTS_PER_PROFILE = 50
MAX_COMMENTS_PER_POST = 50
#: Media rows stored per post (a carousel can be long).
MAX_MEDIA_PER_POST = 10
#: Captions longer than this are truncated in the stored excerpt only.
EXCERPT_LENGTH = 400

# ---------------------------------------------------------------------------
# 5. Serving a post's media
# ---------------------------------------------------------------------------
# Instagram's CDN sends Cross-Origin-Resource-Policy: same-origin, so a browser
# will not render its images from this app's origin however they are linked.
# media.py fetches them server-side instead; these are the limits on that.

#: The only hosts the media proxy will fetch from. Everything else is refused
#: before a request is made, which is what stops it being an open proxy.
MEDIA_HOST_SUFFIXES = ("cdninstagram.com", "fbcdn.net")

#: Redirect hops followed, each one re-checked against the rules above.
MEDIA_MAX_REDIRECTS = 3
MEDIA_TIMEOUT_SECONDS = 20
#: Nothing larger is relayed: a post's photo or short video, not a film.
MEDIA_MAX_BYTES = 25 * 1024 * 1024
MEDIA_CHUNK_BYTES = 64 * 1024
#: How long a browser may keep one. The URLs are signed and expire anyway.
MEDIA_CACHE_SECONDS = 3600
MEDIA_USER_AGENT = "OptiStratixAI-Scout/1.0 (+https://github.com/OptiStratix-AI/Development)"
