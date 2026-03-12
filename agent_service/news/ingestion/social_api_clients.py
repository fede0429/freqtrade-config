class XApiClient:
    def __init__(self, bearer_token): self.bearer_token = bearer_token
    def search_recent(self, query, max_results=10):
        return [{"id":"x_sample_1","text":f"sample x result for {query}","created_at":"2026-03-12T09:00:00Z","url":"https://example.com/x/sample1"}]

class RedditApiClient:
    def __init__(self, client_id, client_secret): self.client_id = client_id; self.client_secret = client_secret
    def search_posts(self, query, limit=10):
        return [{"id":"reddit_sample_1","title":f"sample reddit result for {query}","selftext":"sample reddit body","created_at":"2026-03-12T09:05:00Z","url":"https://example.com/reddit/sample1"}]
