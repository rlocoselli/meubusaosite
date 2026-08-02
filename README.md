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
