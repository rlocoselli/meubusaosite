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

### Suggestion email

The contact page sends suggestions to `admin@audeladedonnees.fr` and `locoselli2016@gmail.com`. Configure `SMTP_HOST`, `SMTP_PORT` (default `587`), `SMTP_USERNAME`, `SMTP_PASSWORD`, and optionally `SMTP_FROM` (defaults to `SMTP_USERNAME`) on the server. The SMTP server must support STARTTLS and permit the configured sender. Until these are set, the form displays a delivery error and sends no message. Keep credentials in server environment variables, outside the repository.

### Passenger experience and optional operator data

The homepage searches lines, stops, and destination names within the selected city. Favorites and the last city stay on the visitor's device. Nearby stops use location only after the visitor asks; walking minutes are explicitly approximate and use straight-line distance. Maps load only after **Open map** is selected, so the main search and stop lists work without downloading map tiles. Leaflet is bundled locally.

Departures use each city's local date and time zone. Scheduled times stay labelled as scheduled; only explicit `predicted_departure_time` or `estimated_departure_time` fields enable the live prediction label. `cancelled: true` or `schedule_relationship: CANCELED` marks cancellations. Empty results never claim that service has ended. `checked_at` reports when this app retrieved data, not the operator's update time. The upstream API cache currently lasts three minutes, so this is not a continuously refreshed vehicle tracker.

Optional operator information can be supplied with `MEUBUSAO_CITY_DATA_FILE`, an absolute path to a JSON object keyed by city ID. Start from [docs/city-data.example.json](docs/city-data.example.json). Only publish verified operator information; leaving fields absent shows an explicit unknown state. Alerts support route/stop IDs and optional start/end timestamps including a UTC offset. Outdated alerts are omitted. Fares are displayed as source text, with an optional official ticket link. Stop wheelchair access uses GTFS `wheelchair_boarding` values 1/2; absent information remains unknown.

The date-specific line-stop endpoint is used first. When only the weekday endpoint is available, `service_calendar` can map verified holiday exceptions to a weekday schedule. The journey planner supports GTFS calendars and exceptions through API snapshots or a GTFS archive set with `MEUBUSAO_GTFS_<CITY_ID_IN_UPPERCASE>`. It retains the upstream reminders, offline pages, vehicle feeds, insights, and scoped alerts. The **Find transport** search is a quick line/stop search; the separate **Plan your journey** page handles origins and destinations. Feed availability still depends on the operator and server configuration. Optional proxy paths remain available through `MEUBUSAO_ALERTS_PATH` and `MEUBUSAO_VEHICLES_PATH`.

Run checks with `python3 -m unittest discover -s tests -v`. No real email is sent by these checks. A live API login and SMTP credentials must be configured on the deployment to verify transport retrieval and suggestion delivery end to end.

### Stop selection and nearby departures

The city timetable uses an explicit stop picker with paginated, accent-insensitive name/code search. Stops with the same name keep separate IDs, codes, and platforms. Selecting a stop loads its departures and provides a full-day timetable link. Current stop departures refresh every minute while the page is visible; the upstream next-departure cache lasts at most 30 seconds.

**Use my location** asks the browser for permission, ranks nearby stops by straight-line distance, and supports 1, 2, or 5 km radii. Location is held in tab session storage for five minutes and passed to the read-only nearby endpoint in a POST body. The stop inventory supplies a fallback when the provider lacks nearby search or distance fields. Maps are optional for selecting a nearby stop and viewing departures. Walking minutes remain estimates, and real location requires HTTPS or localhost. Development verification uses synthetic geolocation and stops; production retrieval still requires API credentials.

### Personal transport tools and reading settings

Returning visitors see their last city, recent stops, up to six favorite cards, and saved Home/Work journeys above the illustrated welcome section. Saved stop favorites show upcoming departures. Line favorites ask the visitor to choose a boarding stop before showing times. Data refreshes while the page is visible. Recent stops, boarding stops, commute shortcuts, and reading settings are stored only in the browser. Favorite alerts are scoped by route or stop; an unavailable feed is never presented as a disruption-free service.

Journey results compare the alternatives found for arrival time, walking distance, and transfers. The algorithm retains schedule and accessibility checks. Home/Work shortcuts can be saved after a successful journey search and use the current service date/time when reopened. The reading controls offer larger text and stronger contrast without relying on color alone.

Last-service badges use the complete planner network, service calendar, pickup restrictions, and after-midnight GTFS times. Frequency-based services without a confirmed final departure are excluded. A limited next-departure response never establishes that a trip is the last bus. These are **scheduled** final trips; operator changes and cancellations can still affect actual service.

Saved offline pages show their save time, service date, and a warning after 24 hours. Individual or bulk refresh preserves the previous copy if the page or associated timetable cannot be fetched successfully. Browser offline storage availability still depends on the browser and device.

### Private data health dashboard

Set a strong `MEUBUSAO_ADMIN_TOKEN` in the server environment, then open `/admin/data-health`. Sign in with that token; it is not embedded in URLs or source files. The JSON endpoints also accept `Authorization: Bearer <token>`. Browser checks require the page's CSRF token. Admin pages and endpoints use `Cache-Control: no-store` and are excluded from service-worker caching.

The dashboard shows the last route/stop/calendar checks observed by the current server process, failed or empty sources, old checks, and optional GTFS coverage dates from the city metadata file. Checking a city explicitly fetches its route and stop inventories. It does not run background monitoring or combine observations across server workers. It never returns API credentials, private URLs, or passenger locations.
