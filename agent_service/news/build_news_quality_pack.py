import json
from pathlib import Path
from agent_service.news.reports.news_quality_metrics_report import write_news_quality_metrics_report
from agent_service.news.reports.news_module_health_report import write_news_module_health_report

DECISION_CACHE_PATH = "user_data/agent_runtime/state/decision_cache.json"
NEWS_EVENT_PACK_PATH = "agent_service/reports/news_event_pack.json"
NEWS_AGG_REPORT_PATH = "agent_service/reports/news_aggregation_report.json"
NEWS_PROVIDER_HEALTH_PATH = "agent_service/reports/news_provider_health_report.json"
NEWS_RISK_EVENT_PATH = "agent_service/reports/news_risk_event_report.json"
NEWS_REVIEW_QUEUE_PATH = "agent_service/reports/news_review_queue.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def build_quality_metrics(decision_cache, event_pack, agg_report, risk_report, review_queue):
    metrics = {"pairs": {}, "source_tiers": {}}
    for event in event_pack.get("events", []):
        tier = event.get("source_tier", "unknown")
        row = metrics["source_tiers"].setdefault(tier, {"event_count": 0, "review_required_count": 0})
        row["event_count"] += 1
        if bool(event.get("review_required", False)):
            row["review_required_count"] += 1
    for pair, meta in decision_cache.get("pairs", {}).items():
        agg = agg_report.get("pairs", {}).get(pair, {})
        risk = risk_report.get("pairs", {}).get(pair, {})
        review = review_queue.get("pairs", {}).get(pair, {})
        metrics["pairs"][pair] = {
            "news_snapshot_count": int(agg.get("news_snapshot_count", 0)),
            "news_event_count": int(agg.get("news_event_count", 0)),
            "high_priority_trigger_count": len(risk.get("triggered_events", [])),
            "review_required": bool(review.get("review_required", False)),
            "review_item_count": len(review.get("items", [])),
            "trading_mode": meta.get("trading_mode"),
            "governance_gate": meta.get("governance_gate"),
            "news_governance_present": "news_governance" in meta,
        }
    return metrics

def build_health_summary(provider_health, quality_metrics):
    providers = provider_health.get("providers", {})
    pair_rows = quality_metrics.get("pairs", {})
    source_tiers = quality_metrics.get("source_tiers", {})
    enabled_provider_count = sum(1 for _, row in providers.items() if bool(row.get("enabled", False)))
    review_pairs = sum(1 for _, row in pair_rows.items() if bool(row.get("review_required", False)))
    return {"providers": {"total": len(providers), "enabled": enabled_provider_count}, "pairs": {"total": len(pair_rows), "review_required": review_pairs}, "source_tiers": source_tiers, "module_status": "ok" if enabled_provider_count > 0 else "degraded"}

def main():
    decision_cache = load_json(DECISION_CACHE_PATH, {"pairs": {}})
    event_pack = load_json(NEWS_EVENT_PACK_PATH, {"events": []})
    agg_report = load_json(NEWS_AGG_REPORT_PATH, {"pairs": {}})
    provider_health = load_json(NEWS_PROVIDER_HEALTH_PATH, {"providers": {}})
    risk_report = load_json(NEWS_RISK_EVENT_PATH, {"pairs": {}})
    review_queue = load_json(NEWS_REVIEW_QUEUE_PATH, {"pairs": {}})
    quality_metrics = build_quality_metrics(decision_cache, event_pack, agg_report, risk_report, review_queue)
    write_news_quality_metrics_report(quality_metrics)
    health_summary = build_health_summary(provider_health, quality_metrics)
    write_news_module_health_report(health_summary)
    out = Path("agent_service/reports/news_quality_pack_summary.json")
    out.write_text(json.dumps({"quality_metrics": quality_metrics, "health_summary": health_summary}, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
