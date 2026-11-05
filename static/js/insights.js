const insightsSection = document.querySelector('[data-insights-city]');
if (insightsSection) {
  const copy = JSON.parse(document.getElementById('insightsCopy').textContent);
  const city = insightsSection.dataset.insightsCity;
  const route = insightsSection.dataset.insightsRoute;
  const number = value => new Intl.NumberFormat(document.documentElement.lang).format(value);
  const date = value => {
    if (!value) return '—';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? '—' : new Intl.DateTimeFormat(document.documentElement.lang, {dateStyle:'medium',timeStyle:'short'}).format(parsed);
  };
  const node = (tag, className, value) => {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (value !== undefined) item.textContent = value;
    return item;
  };
  const metric = (label, value) => {
    const item = node('div','insight-kpi');
    item.append(node('small','',label),node('strong','',value));
    return item;
  };
  const showInsights = data => {
    const kpis = insightsSection.querySelector('[data-insights-kpis]');
    const list = insightsSection.querySelector('[data-insights-routes]');
    kpis.replaceChildren(); list.replaceChildren();
    if (!data.connected || !data.available) { list.append(node('p','insights-empty',copy.unavailable)); return; }
    const items = data.items || [];
    if (!items.length) { list.append(node('p','insights-empty',copy.no_data)); return; }
    const withBoardings = items.filter(item => item.boardingSampleCount > 0);
    const withAlightings = items.filter(item => item.alightingSampleCount > 0);
    kpis.append(
      metric(copy.observations, number(items.reduce((total,item) => total + (item.eventCount || 0), 0))),
      metric(copy.boardings, withBoardings.length ? number(withBoardings.reduce((total,item) => total + (item.totalBoardings || 0), 0)) : '—'),
      metric(copy.alightings, withAlightings.length ? number(withAlightings.reduce((total,item) => total + (item.totalAlightings || 0), 0)) : '—'),
      metric(copy.last, date(items.map(item => item.lastObservedAt).filter(Boolean).sort().at(-1)))
    );
    const sorted = [...items].sort((a,b) => (b.totalBoardings || 0) - (a.totalBoardings || 0) || (b.eventCount || 0) - (a.eventCount || 0));
    sorted.slice(0, route ? 12 : 6).forEach(item => {
      const card = node('article','insight-route-card');
      const head = node('div','insight-route-head');
      const badge = node('span','insight-route-badge',item.routeId || '•');
      const title = node('div','');
      title.append(node('strong','',item.lineName || item.routeId || '—'),node('small','',item.direction ? `${copy.direction}: ${item.direction}` : ''));
      head.append(badge,title);
      if (!route && item.routeId) {
        const link = node('a','insight-route-link',`${copy.view_line} ↗`);
        link.href = `/city/${encodeURIComponent(city)}/line/${encodeURIComponent(item.routeId)}`;
        head.append(link);
      }
      const details = node('div','insight-route-metrics');
      details.append(
        metric(copy.boardings, item.boardingSampleCount ? number(item.totalBoardings) : '—'),
        metric(copy.alightings, item.alightingSampleCount ? number(item.totalAlightings) : '—'),
        metric(copy.occupancy, item.occupancySampleCount ? number(Number(item.averageOccupancy).toFixed(1)) : '—'),
        metric(copy.trips, item.observedTripCount ? number(item.observedTripCount) : '—')
      );
      card.append(head,details);
      list.append(card);
    });
  };
  const showRealtime = data => {
    const target = insightsSection.querySelector('[data-realtime-feeds]');
    target.replaceChildren();
    if (!data.connected || !data.feeds?.length) {
      target.append(node('span','realtime-pill muted',data.status === 'not_configured' ? copy.not_configured : copy.unavailable));
      return;
    }
    data.feeds.forEach(feed => {
      const pill = node('span',`realtime-pill ${feed.status === 'ok' ? 'is-live' : 'muted'}`,
        `${copy[feed.type] || feed.type} · ${copy[feed.status] || copy.error}`);
      pill.title = feed.feedTimestamp ? `${copy.refresh}: ${date(feed.feedTimestamp)}` : '';
      target.append(pill);
    });
  };
  const get = async path => {
    const response = await fetch(path);
    if (!response.ok) throw new Error('service');
    return response.json();
  };
  const query = route ? `?route=${encodeURIComponent(route)}` : '';
  get(`/api/${encodeURIComponent(city)}/insights${query}`).then(showInsights).catch(() => showInsights({connected:false}));
  get(`/api/${encodeURIComponent(city)}/realtime-status`).then(showRealtime).catch(() => showRealtime({connected:false}));
}
