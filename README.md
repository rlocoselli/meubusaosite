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
