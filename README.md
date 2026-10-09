# Meu Busão website

Multilingual Flask website for the Meu Busão public-transport API.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export FLASK_SECRET_KEY='replace-this'
export MEUBUSAO_API_TOKEN='your-login-id'
flask --app app run
```

Despite its historical variable name, `MEUBUSAO_API_TOKEN` contains the legacy login identifier (username), not the API token returned by the service. Flask sends it as the `id` header to `/login`, stores the resulting token in server memory, renews it automatically when it expires or is rejected, and never exposes either value to the browser. The login identifier is optional for previewing the city experience but required for live routes, stops, shapes, and departures. Override the API with `MEUBUSAO_API_URL` if needed.

Line and stop pages support a service date, and departures use each city's local time zone. Nearby-stop location is requested only when the visitor selects **Find nearby**; distances are straight-line measurements and walking times are estimates. Saved lines and stops remain in the visitor's browser.

The default API does not publish service alerts. To connect an authenticated alert endpoint on the configured API host, set `MEUBUSAO_ALERTS_PATH`, for example `alerts/{city}`. The endpoint should return a JSON list (or `{"alerts": [...]}`) with `title`, `description`, and optional `route_ids` (citywide alerts omit this field). The UI distinguishes unsupported alerts, unavailable feeds, and an empty feed. Canceled departures are labeled when their payload supplies `cancelled: true` or a cancellation status.

Run regression checks with `.venv/bin/python -m unittest discover -s tests -v`.

City pages prioritize departure times, lines, and maps. Journey planning has its own URL, `/city/<city_id>/plan`; older city links containing journey inputs redirect there while preserving the query.

Travel tools now include share links (city, route, direction, stop, service date, and planner inputs), stop/vehicle accessibility, saved schedules, and departure reminders. The planner searches direct rides and up to two transfers over a 12-hour horizon. It respects calendars, date exceptions, pickup/drop-off restrictions, and a minimum two-minute connection buffer. Coordinate approaches (up to 800 m) and transfers between stops (up to 250 m) use approximate straight-line walking distances. Wheelchair-only searches require explicitly accessible boarding/alighting stops and trips, and exclude unverified walking paths. Frequency-based trips and trip-specific transfer rules are not inferred; feeds using the latter report planning as unavailable.

Journey data comes from the API's stops, routes, trips, calendar, calendar exceptions, and stop times, cached for 15 minutes. A cold city snapshot loads trip metadata concurrently. Alternatively configure a local GTFS zip with `MEUBUSAO_GTFS_<CITY_ID_UPPERCASE>`, for example `MEUBUSAO_GTFS_GRENOBLE_FRANCE=/srv/gtfs/grenoble.zip`. The bundled Managua feed is used only without API credentials, and its expired 2023 calendar never produces current-day journeys. Missing/invalid feeds are reported as unavailable.

For live vehicle positions, set `MEUBUSAO_VEHICLES_PATH=vehicles/{city}` on the configured API host. Return a JSON list or `{"vehicles": [...]}` with `vehicle_id`, `route_id`, `lat`, `lon`, `timestamp` (Unix seconds), and optional `label` and `wheelchair_accessible` (GTFS 0/1/2). Polling runs every 15 seconds while the page is visible; cached responses last at most 10 seconds and positions older than two minutes are discarded. Raw protobuf feeds need a JSON adapter. Live positions, location searches, and alerts are never served from offline storage.

Offline support uses a service worker on HTTPS (or localhost), with bounded caches for visited pages and timetable responses. Leaflet is bundled locally so saved route diagrams work offline; external basemap tiles are not downloaded for offline use. Cached schedules show their save time and suppress live countdowns. **My space** lists saved pages and provides a cache-clear control while retaining favorites.

Reminders are stored in the browser and can display a notification five minutes before departure while a Meu Busão page remains open. Notification permission is requested only after selecting a reminder. Calendar downloads include a five-minute alarm for use in a calendar app when the site is closed; server-side push scheduling is not configured.
