class EventDeduper:
    def dedupe(self, events):
        seen_ids=set(); seen_titles=set(); out=[]
        for event in events:
            title_key = event.headline.strip().lower()
            if event.event_id in seen_ids or title_key in seen_titles:
                continue
            seen_ids.add(event.event_id)
            seen_titles.add(title_key)
            out.append(event)
        return out
