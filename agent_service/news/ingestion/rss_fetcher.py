import xml.etree.ElementTree as ET
from agent_service.integration.http_utils import http_get_text

class RSSFetcher:
    def __init__(self, timeout_seconds=30): self.timeout_seconds = timeout_seconds

    def fetch(self, url):
        text = http_get_text(url, timeout=self.timeout_seconds)
        root = ET.fromstring(text)
        items = []
        for item in root.findall(".//item"):
            items.append({"title": (item.findtext("title") or "").strip(), "link": (item.findtext("link") or "").strip(), "pubDate": (item.findtext("pubDate") or "").strip(), "description": (item.findtext("description") or "").strip()})
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//atom:entry", ns):
            link_el = entry.find("atom:link", ns)
            items.append({"title": (entry.findtext("atom:title", default="", namespaces=ns) or "").strip(), "link": (link_el.get("href", "") if link_el is not None else "").strip(), "pubDate": (entry.findtext("atom:updated", default="", namespaces=ns) or "").strip(), "description": (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()})
        return items
