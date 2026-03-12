import json
from pathlib import Path
from agent_service.news.news_policy import NewsPolicy
from agent_service.news.news_governance_bridge import NewsGovernanceBridge
from agent_service.news.reports.news_risk_event_report import write_news_risk_event_report

DECISION_CACHE_PATH = "user_data/agent_runtime/state/decision_cache.json"
NEWS_POLICY_PATH = "user_data/config/news_policy.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))

def classify_news_risk(pair, pair_meta, news_policy):
    bridge = NewsGovernanceBridge()
    high_priority = set(news_policy.high_priority_event_types(pair))
    block_on = set(news_policy.block_on_event_types(pair))
    review_on = set(news_policy.review_on_event_types(pair))
    cfg = news_policy.config_for_pair(pair)
    min_cred = float(cfg.get("minimum_credibility_for_action", 0.70))
    providers = pair_meta.get("providers", {})
    triggered=[]; block=False; review=False; escalate=False
    for provider_name, provider_meta in providers.items():
        if not bridge.is_news_provider(provider_name): continue
        raw_ref = provider_meta.get("raw_ref", {})
        signals = raw_ref.get("signals", {})
        event_type = raw_ref.get("event_type") or signals.get("event_type")
        credibility = raw_ref.get("credibility_score") or signals.get("credibility_score") or 0.0
        source_tier = raw_ref.get("source_tier") or signals.get("source_tier") or "unknown"
        if float(credibility) < min_cred and source_tier not in {"exchange_status","official"}: continue
        if event_type in high_priority:
            triggered.append({"provider": provider_name, "event_type": event_type, "credibility_score": credibility, "source_tier": source_tier})
        if event_type in block_on: block = True
        if event_type in review_on: review = True
        if event_type == "exchange_incident" and bool(cfg.get("escalate_on_exchange_status", True)): escalate = True
        if event_type == "regulatory_action" and bool(cfg.get("escalate_on_regulatory", True)): escalate = True
    return {"triggered_events": triggered, "block": block, "review": review, "escalate": escalate}

def apply_news_overlay(decision_cache, news_policy):
    report = {"pairs": {}}
    for pair, pair_meta in decision_cache.get("pairs", {}).items():
        news_risk = classify_news_risk(pair, pair_meta, news_policy)
        pair_meta["news_governance"] = news_risk
        if news_risk["block"]:
            pair_meta["governance_gate"] = "blocked"; pair_meta["agent_enabled"] = False; pair_meta["entry_allowed"] = False
            if isinstance(pair_meta.get("entry"), dict):
                pair_meta["entry"]["entry_allowed"] = False
                pair_meta["entry"]["entry_reason"] = "news_governance_blocked"
        if news_risk["review"]:
            pair_meta["trading_mode"] = "review_shadow"
        report["pairs"][pair] = news_risk
    return report

def main():
    decision_cache = load_json(DECISION_CACHE_PATH, {"pairs": {}})
    policy_raw = load_json(NEWS_POLICY_PATH, {"global_defaults": {}, "pair_overrides": {}})
    report = apply_news_overlay(decision_cache, NewsPolicy(policy_raw))
    write_news_risk_event_report(report)
    out = Path(DECISION_CACHE_PATH); out.write_text(json.dumps(decision_cache, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
