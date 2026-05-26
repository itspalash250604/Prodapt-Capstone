# Course Finder AI

This repository contains the backend course recommendation pipeline and the React frontend.

## Optional Retrieval Cache

The semantic course search now supports caching repeated searches. By default it uses an in-memory cache, and it can automatically switch to Redis when `REDIS_URL` is set.

Recommended environment variables:

```bash
REDIS_URL=redis://localhost:6379/0
COURSE_SEARCH_CACHE_TTL_SECONDS=3600
COURSE_SEARCH_CACHE_PREFIX=course_search
```

Notes:
- If Redis is available, it will be used for shared cache storage.
- If Redis is unavailable, the app falls back to an in-memory cache automatically.
- Cached entries are keyed by query, `top_k`, filters, collection name, and embedding model name.
