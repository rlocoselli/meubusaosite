# Meu Busão website

Multilingual Flask website for the Meu Busão public-transport API.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export FLASK_SECRET_KEY='replace-this'
export MEUBUSAO_API_TOKEN='your-api-token'
flask --app app run
```

The API token is optional for previewing the city experience, but required for live routes, stops, shapes, and departure times. It is only used by Flask and is never exposed to the browser. Override the API with `MEUBUSAO_API_URL` if needed.
