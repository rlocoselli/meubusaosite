"""In-memory source checks. No credentials, request URLs or passenger locations."""
import threading
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

class DataHealth:
    def __init__(self):
        self.checks={}
        self.lock=threading.Lock()

    def record(self,city,kind,ok,count=None):
        with self.lock:
            previous=self.checks.get((city,kind),{})
            self.checks[(city,kind)]={'checked_at':time.time(),'ok':bool(ok),'count':count if ok else previous.get('count'),'last_success':time.time() if ok else previous.get('last_success')}

    def snapshot(self,cities,metadata,configured):
        with self.lock:checks=dict(self.checks)
        items=[]
        for city,info in cities.items():
            meta=metadata(city)
            samples={kind:checks.get((city,kind)) for kind in ('routes','stops','calendar','departures')}
            required=[samples[k] for k in ('routes','stops')]
            status='not_configured' if not configured else 'not_checked'
            known=[x for x in required if x]
            if known:
                status='unavailable' if any(not x['ok'] for x in known) else 'empty' if any(x['count']==0 for x in known) else 'stale' if any(time.time()-x['checked_at']>900 for x in known) else 'ok' if len(known)==2 else 'partial'
            departure=samples['departures']
            if departure and not departure['ok']:status='unavailable'
            try:
                if meta.get('coverage_end') and date.fromisoformat(meta['coverage_end'])<datetime.now(ZoneInfo(meta.get('timezone','UTC'))).date():status='expired'
            except ValueError:pass
            items.append(dict(city=city,name=info['name'],status=status,checks=samples,source_updated_at=meta.get('source_updated_at'),coverage_start=meta.get('coverage_start'),coverage_end=meta.get('coverage_end')))
        return items
