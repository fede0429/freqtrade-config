from datetime import datetime, timezone
from user_data.strategies.bridge_loader import BridgeLoader
from user_data.strategies.shadow_audit_writer import ShadowAuditWriter
try:
    from user_data.strategies.AdaptiveMetaStrategy import AdaptiveMetaStrategy as BaseStrategy
except Exception:
    class BaseStrategy:
        timeframe='5m'; stoploss=-0.10; process_only_new_candles=True; use_custom_stoploss=True; use_exit_signal=True
        def bot_loop_start(self, current_time, **kwargs): return None
        def custom_stake_amount(self, *args, **kwargs): return kwargs.get('proposed_stake')
        def custom_exit(self, *args, **kwargs): return None
        def custom_stoploss(self, *args, **kwargs): return None
        def custom_roi(self, *args, **kwargs): return None
        def confirm_trade_entry(self, *args, **kwargs): return True
class AgentBridgeStrategy(BaseStrategy):
    agent_overlay_path='user_data/config/agent_overlay.json'; decision_cache_path='user_data/agent_runtime/state/decision_cache.json'; use_custom_stoploss=True; use_exit_signal=True
    def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs); self.loader=BridgeLoader(self.agent_overlay_path,self.decision_cache_path); self.audit=ShadowAuditWriter(); self._overlay={}; self._cache={}; self._refresh()
    def _utc_now(self): return datetime.now(timezone.utc)
    def _refresh(self): self._overlay=self.loader.load_overlay(); self._cache=self.loader.load_decision_cache()
    @property
    def shadow_mode(self): return bool(self._overlay.get('shadow_mode', True))
    @property
    def enabled_callbacks(self): return self._overlay.get('enabled_callbacks', {'stake':False,'exit':False,'stoploss':False,'roi':False,'entry_confirm':False})
    def _pair_decision(self,pair): return self._cache.get('pairs', {}).get(pair.upper(), {})
    def _pair_allowed(self,pair): allowed=[p.upper() for p in self._overlay.get('enabled_pairs', [])]; return (not allowed) or pair.upper() in allowed
    def _cache_is_fresh(self): return True if self._cache.get('ts') else False
    def _providers_healthy(self, decision): return True
    def _decision_value(self, decision, nested_key, flat_key, default=None):
        group, _, subkey=nested_key.partition('.')
        if group and subkey and isinstance(decision.get(group), dict) and subkey in decision[group]: return decision[group][subkey]
        return decision.get(flat_key, default)
    def _agent_enabled_for_pair(self,pair): d=self._pair_decision(pair); return bool(d) and self._pair_allowed(pair) and self._cache_is_fresh() and d.get('governance_gate')=='passed'
    def _trace(self, filename, payload): self.audit.append_event(filename, payload)
    def bot_loop_start(self, current_time, **kwargs): self._refresh(); self._trace('bridge_runtime_trace.jsonl', {'shadow_mode': self.shadow_mode, 'enabled_callbacks': self.enabled_callbacks, 'cache_fresh': self._cache_is_fresh(), 'pair_count': len(self._cache.get('pairs', {}))}); parent=getattr(super(),'bot_loop_start',None); return parent(current_time, **kwargs) if callable(parent) else None
    def custom_stake_amount(self,pair,current_time,current_rate,proposed_stake,min_stake,max_stake,leverage,entry_tag,side,**kwargs): d=self._pair_decision(pair); self._trace('stake_decision_trace.jsonl', {'pair':pair,'mode':'shadow' if self.shadow_mode else 'live','proposed_stake':proposed_stake,'decision':d}); return proposed_stake if self.shadow_mode else min(proposed_stake*float(self._decision_value(d,'stake.stake_multiplier','stake_multiplier',1.0)), max_stake or proposed_stake)
    def custom_exit(self,pair,trade,current_time,current_rate,current_profit,**kwargs): d=self._pair_decision(pair); self._trace('exit_shadow_trace.jsonl', {'pair':pair,'mode':'shadow' if self.shadow_mode else 'live','current_profit':current_profit,'decision':d}); return None if self.shadow_mode else (self._decision_value(d,'exit.exit_reason','exit_reason','agent_exit_signal') if bool(self._decision_value(d,'exit.exit_signal','exit_signal',False)) else None)
    def custom_stoploss(self,pair,trade,current_time,current_rate,current_profit,after_fill,**kwargs): d=self._pair_decision(pair); self._trace('stoploss_shadow_trace.jsonl', {'pair':pair,'mode':'shadow' if self.shadow_mode else 'live','current_profit':current_profit,'decision':d}); return None if self.shadow_mode else self._decision_value(d,'stoploss.agent_stoploss','agent_stoploss',None)
    def custom_roi(self,pair,trade,current_time,trade_duration,entry_tag,side,**kwargs): d=self._pair_decision(pair); self._trace('roi_shadow_trace.jsonl', {'pair':pair,'mode':'shadow' if self.shadow_mode else 'live','trade_duration':trade_duration,'decision':d}); return None if self.shadow_mode else self._decision_value(d,'roi.target_rr','target_rr',None)
    def confirm_trade_entry(self,pair,order_type,amount,rate,time_in_force,current_time,entry_tag,side,**kwargs): d=self._pair_decision(pair); self._trace('entry_confirm_trace.jsonl', {'pair':pair,'mode':'shadow' if self.shadow_mode else 'live','amount':amount,'rate':rate,'decision':d}); return True if self.shadow_mode else bool(self._decision_value(d,'entry.entry_allowed','entry_allowed',True))
