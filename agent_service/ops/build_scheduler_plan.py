import json
from pathlib import Path

def main():
    payload = {"kind":"scheduler_plan","profiles":{"light_shadow":{"description":"低频影子运行，适合刚接入真实 RSS/API 时","schedule":{"smoke_test":"every 30 minutes","shadow_cycle":"every 4 hours","daily_summary":"daily 23:30","weekly_summary":"sunday 23:45"}},"standard_shadow":{"description":"标准影子运行，适合稳定运行期","schedule":{"smoke_test":"every 15 minutes","shadow_cycle":"every 2 hours","daily_summary":"daily 23:15","weekly_summary":"sunday 23:30"}},"intensive_shadow":{"description":"高频校准期，适合参数收敛与事件频发阶段","schedule":{"smoke_test":"every 10 minutes","shadow_cycle":"every 1 hour","daily_summary":"daily 23:00","weekly_summary":"sunday 23:15"}}},"recommended_profile":"standard_shadow"}
    out = Path("agent_service/reports/scheduler_plan.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); print(out)

if __name__ == "__main__":
    main()
