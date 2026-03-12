import json
from pathlib import Path
from agent_service.news.review_queue import NewsReviewQueue
from agent_service.news.reports.news_escalation_summary_report import write_news_escalation_summary_report
from agent_service.news.reports.news_source_incident_report import write_news_source_incident_report

DECISION_CACHE_PATH = "user_data/agent_runtime/state/decision_cache.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def build_review_summary(decision_cache):
    review_queue = {"pairs": {}}
    escalation_summary = {"pairs": {}}
    source_incidents = {"pairs": {}}
    for pair, meta in decision_cache.get("pairs", {}).items():
        news_governance = meta.get("news_governance", {})
        triggered = news_governance.get("triggered_events", [])
        review_items=[]; escalations=[]; source_rows=[]
        for event in triggered:
            event_type = event.get("event_type"); provider = event.get("provider"); cred = event.get("credibility_score"); tier = event.get("source_tier")
            review_items.append({"provider": provider, "event_type": event_type, "credibility_score": cred, "source_tier": tier, "recommended_action": "manual_review"})
            if event_type in {"regulatory_action","exchange_incident"}:
                escalations.append({"provider": provider, "event_type": event_type, "severity": "high", "recommended_action": "escalate_to_operator"})
            if event_type == "exchange_incident":
                source_rows.append({"provider": provider, "incident_type": "exchange_status_incident", "severity": "high"})
        review_queue["pairs"][pair] = {"review_required": bool(review_items) or bool(news_governance.get("review", False)), "items": review_items}
        escalation_summary["pairs"][pair] = {"escalate": bool(escalations) or bool(news_governance.get("escalate", False)), "items": escalations}
        source_incidents["pairs"][pair] = {"incident_count": len(source_rows), "items": source_rows}
    return {"review_queue": review_queue, "escalation_summary": escalation_summary, "source_incidents": source_incidents}

def main():
    decision_cache = load_json(DECISION_CACHE_PATH, {"pairs": {}})
    payload = build_review_summary(decision_cache)
    NewsReviewQueue().write(payload["review_queue"])
    write_news_escalation_summary_report(payload["escalation_summary"])
    write_news_source_incident_report(payload["source_incidents"])
    out = Path("agent_service/reports/news_operator_handoff_pack.json"); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
