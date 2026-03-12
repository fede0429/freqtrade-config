import json
from pathlib import Path
from datetime import datetime, timezone

def utc_now_iso(): return datetime.now(timezone.utc).isoformat()
class DecisionAggregator:
    def __init__(self, cache_ttl_seconds=90, shadow_mode=True): self.cache_ttl_seconds=cache_ttl_seconds; self.shadow_mode=shadow_mode
    def build_pair_decision(self,pair,snapshots):
        c=round(sum(float(getattr(s,'score',0.0)) for s in snapshots)/len(snapshots),4) if snapshots else 0.0
        return {'agent_enabled':bool(snapshots),'pair_enabled':True,'governance_gate':'passed','trading_mode':'paper_candidate','rollout_state':'paper','confidence':c,'risk_score':0.0,'providers':{getattr(s,'provider'):{'status':getattr(s,'status'),'score':getattr(s,'score'),'ts':getattr(s,'ts'),'stale':getattr(s,'stale')} for s in snapshots},'entry':{'entry_allowed':c>=0.75,'entry_min_confidence':0.75},'stake':{'stake_multiplier':1.15 if c>=0.75 else 1.0},'exit':{'exit_signal':False},'stoploss':{'stoploss_mode':'tighten_only','agent_stoploss':-0.045},'roi':{'target_rr':1.8},'entry_allowed':c>=0.75,'stake_multiplier':1.15 if c>=0.75 else 1.0,'exit_signal':False,'stoploss_mode':'tighten_only','agent_stoploss':-0.045,'target_rr':1.8}
    def build_decision_cache(self,pair_snapshots): return {'schema_version':'2.0','ts':utc_now_iso(),'source':'decision_aggregator','env':'dry-run','global':{'shadow_mode':self.shadow_mode,'governance_gate':'passed','cache_ttl_seconds':self.cache_ttl_seconds,'aggregator_health':'ok','fallback_mode':'base_strategy_only'},'pairs':{p:self.build_pair_decision(p,s) for p,s in pair_snapshots.items()}}
    def write_decision_cache(self,pair_snapshots, output_path='user_data/agent_runtime/state/decision_cache.json'):
        out=Path(output_path); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(self.build_decision_cache(pair_snapshots),indent=2,ensure_ascii=False),encoding='utf-8'); return out
