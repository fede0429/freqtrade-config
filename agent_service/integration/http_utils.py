import json
import urllib.request

def http_get_json(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_get_text(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")

def http_post_json(url, payload, headers=None, timeout=30):
    body = json.dumps(payload).encode("utf-8")
    merged_headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=body, headers=merged_headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
