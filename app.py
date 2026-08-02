from __future__ import annotations

import os
import time
from datetime import date
from functools import lru_cache

import requests
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-change-me")
API_BASE = os.environ.get("MEUBUSAO_API_URL", "https://mybusaoservice.audeladedonnees.fr").rstrip("/")
API_TOKEN = os.environ.get("MEUBUSAO_API_TOKEN", "")
LANGUAGES = ("pt-br", "fr", "it", "es")

CITIES = {
    "Grenoble_France": {"name": "Grenoble", "country": "France", "lat": 45.1885, "lon": 5.7245, "photo": "https://images.unsplash.com/photo-1593343559723-15f96a7a0a72?auto=format&fit=crop&w=1400&q=82", "accent": "#3267e3"},
    "Fortaleza_Brazil": {"name": "Fortaleza", "country": "Brasil", "lat": -3.7319, "lon": -38.5267, "photo": "https://images.unsplash.com/photo-1596395819057-e37f55a8516b?auto=format&fit=crop&w=1400&q=82", "accent": "#f59e0b"},
    "SaoPaulo_Brazil": {"name": "São Paulo", "country": "Brasil", "lat": -23.5505, "lon": -46.6333, "photo": "https://images.unsplash.com/photo-1543059080-f9b1272213d5?auto=format&fit=crop&w=1400&q=82", "accent": "#e63946"},
    "Managua_Nicaragua": {"name": "Managua", "country": "Nicaragua", "lat": 12.114, "lon": -86.2362, "photo": "https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?auto=format&fit=crop&w=1400&q=82", "accent": "#06a77d"},
    "PortoAlegre_Brazil": {"name": "Porto Alegre", "country": "Brasil", "lat": -30.0346, "lon": -51.2177, "photo": "https://images.unsplash.com/photo-1483729558449-99ef09a8c325?auto=format&fit=crop&w=1400&q=82", "accent": "#7c3aed"},
    "Brisbane_Australia": {"name": "Brisbane", "country": "Australia", "lat": -27.4698, "lon": 153.0251, "photo": "https://images.unsplash.com/photo-1524293581917-878a6d017c71?auto=format&fit=crop&w=1400&q=82", "accent": "#0ea5e9"},
    "Perpignan_France": {"name": "Perpignan", "country": "France", "lat": 42.6887, "lon": 2.8948, "photo": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1400&q=82", "accent": "#ef4444"},
    "Paris_France": {"name": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522, "photo": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1400&q=82", "accent": "#8b5cf6"},
    "Curitiba_Brazil": {"name": "Curitiba", "country": "Brasil", "lat": -25.4284, "lon": -49.2733, "photo": "https://images.unsplash.com/photo-1483729558449-99ef09a8c325?auto=format&fit=crop&w=1400&q=82", "accent": "#16a34a"},
    "Montreal_Canada": {"name": "Montréal", "country": "Canada", "lat": 45.5019, "lon": -73.5674, "photo": "https://images.unsplash.com/photo-1519178614-68673b201f36?auto=format&fit=crop&w=1400&q=82", "accent": "#dc2626"},
    "Turin_Italy": {"name": "Torino", "country": "Italia", "lat": 45.0703, "lon": 7.6869, "photo": "https://images.unsplash.com/photo-1515542622106-78bda8ba0e5b?auto=format&fit=crop&w=1400&q=82", "accent": "#2563eb"},
    "Nice_France": {"name": "Nice", "country": "France", "lat": 43.7102, "lon": 7.262, "photo": "https://images.unsplash.com/photo-1533104816931-20fa691ff6ca?auto=format&fit=crop&w=1400&q=82", "accent": "#0891b2"},
    "BuenosAires_Argentina": {"name": "Buenos Aires", "country": "Argentina", "lat": -34.6037, "lon": -58.3816, "photo": "https://images.unsplash.com/photo-1589909202802-8f4aadce1849?auto=format&fit=crop&w=1400&q=82", "accent": "#0284c7"},
}

COPY = {
    "pt-br": {"nav_cities":"Cidades", "nav_plan":"Planejar viagem", "nav_docs":"Documentação API", "hero_kicker":"Mobilidade urbana, sem complicação", "hero_title":"Sua cidade. Suas linhas. Seu próximo ônibus.", "hero_text":"Explore linhas, pontos, mapas e horários de transporte público em 13 cidades pelo mundo.", "explore":"Explorar cidades", "plan":"Consultar horários", "cities_title":"Escolha sua cidade", "cities_text":"Informação local, mapas claros e as linhas que movem cada lugar.", "routes":"linhas", "open_city":"Ver transporte", "live":"Dados da API", "search_routes":"Buscar linha ou destino", "all_routes":"Todas as linhas", "stops":"Pontos", "map":"Mapa da rede", "timetable":"Horários", "direction":"Sentido", "today":"Hoje", "find_departures":"Buscar partidas", "stop_placeholder":"Nome ou código do ponto", "next_departures":"Próximas partidas", "no_data":"Nenhum dado disponível agora.", "api_missing":"Conecte MEUBUSAO_API_TOKEN para carregar dados ao vivo.", "back":"Voltar", "line":"Linha", "network":"Rede de transporte", "hero_stat_cities":"cidades", "hero_stat_languages":"idiomas", "hero_stat_access":"acesso gratuito"},
    "fr": {"nav_cities":"Villes", "nav_plan":"Planifier", "nav_docs":"Documentation API", "hero_kicker":"La mobilité urbaine, simplement", "hero_title":"Votre ville. Vos lignes. Votre prochain bus.", "hero_text":"Explorez les lignes, arrêts, cartes et horaires de transport public dans 13 villes du monde.", "explore":"Explorer les villes", "plan":"Consulter les horaires", "cities_title":"Choisissez votre ville", "cities_text":"Des informations locales, des cartes lisibles et les lignes qui font vivre chaque ville.", "routes":"lignes", "open_city":"Voir le réseau", "live":"Données de l’API", "search_routes":"Rechercher une ligne ou destination", "all_routes":"Toutes les lignes", "stops":"Arrêts", "map":"Carte du réseau", "timetable":"Horaires", "direction":"Direction", "today":"Aujourd’hui", "find_departures":"Rechercher", "stop_placeholder":"Nom ou code de l’arrêt", "next_departures":"Prochains départs", "no_data":"Aucune donnée disponible pour le moment.", "api_missing":"Configurez MEUBUSAO_API_TOKEN pour charger les données en direct.", "back":"Retour", "line":"Ligne", "network":"Réseau de transport", "hero_stat_cities":"villes", "hero_stat_languages":"langues", "hero_stat_access":"accès gratuit"},
    "it": {"nav_cities":"Città", "nav_plan":"Pianifica", "nav_docs":"Documentazione API", "hero_kicker":"Mobilità urbana, senza complicazioni", "hero_title":"La tua città. Le tue linee. Il tuo prossimo bus.", "hero_text":"Esplora linee, fermate, mappe e orari del trasporto pubblico in 13 città del mondo.", "explore":"Esplora le città", "plan":"Consulta gli orari", "cities_title":"Scegli la tua città", "cities_text":"Informazioni locali, mappe chiare e le linee che fanno muovere ogni luogo.", "routes":"linee", "open_city":"Vedi trasporti", "live":"Dati API", "search_routes":"Cerca linea o destinazione", "all_routes":"Tutte le linee", "stops":"Fermate", "map":"Mappa della rete", "timetable":"Orari", "direction":"Direzione", "today":"Oggi", "find_departures":"Cerca partenze", "stop_placeholder":"Nome o codice fermata", "next_departures":"Prossime partenze", "no_data":"Nessun dato disponibile al momento.", "api_missing":"Configura MEUBUSAO_API_TOKEN per caricare dati in tempo reale.", "back":"Indietro", "line":"Linea", "network":"Rete di trasporto", "hero_stat_cities":"città", "hero_stat_languages":"lingue", "hero_stat_access":"accesso gratuito"},
    "es": {"nav_cities":"Ciudades", "nav_plan":"Planificar", "nav_docs":"Documentación API", "hero_kicker":"Movilidad urbana, sin complicaciones", "hero_title":"Tu ciudad. Tus líneas. Tu próximo bus.", "hero_text":"Explora líneas, paradas, mapas y horarios de transporte público en 13 ciudades del mundo.", "explore":"Explorar ciudades", "plan":"Consultar horarios", "cities_title":"Elige tu ciudad", "cities_text":"Información local, mapas claros y las líneas que mueven cada lugar.", "routes":"líneas", "open_city":"Ver transporte", "live":"Datos de la API", "search_routes":"Buscar línea o destino", "all_routes":"Todas las líneas", "stops":"Paradas", "map":"Mapa de la red", "timetable":"Horarios", "direction":"Dirección", "today":"Hoy", "find_departures":"Buscar salidas", "stop_placeholder":"Nombre o código de la parada", "next_departures":"Próximas salidas", "no_data":"No hay datos disponibles ahora.", "api_missing":"Configura MEUBUSAO_API_TOKEN para cargar datos en vivo.", "back":"Volver", "line":"Línea", "network":"Red de transporte", "hero_stat_cities":"ciudades", "hero_stat_languages":"idiomas", "hero_stat_access":"acceso gratuito"},
}

_cache: dict[str, tuple[float, object]] = {}

def current_lang():
    lang = session.get("lang", "pt-br")
    return lang if lang in LANGUAGES else "pt-br"

def tr(key):
    return COPY[current_lang()].get(key, key)

def api_get(path, params=None):
    if not API_TOKEN:
        return None
    cache_key = path + repr(sorted((params or {}).items()))
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < 180:
        return cached[1]
    try:
        response = requests.get(f"{API_BASE}/{path.lstrip('/')}", params=params, headers={"token": API_TOKEN}, timeout=12)
        response.raise_for_status()
        data = response.json()
        _cache[cache_key] = (time.time(), data)
        return data
    except (requests.RequestException, ValueError):
        return None

def rows(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for key in ("data", "results", "routes", "stops", "departures", "items"):
            if isinstance(data.get(key), list): return data[key]
    return []

def route_view(item):
    return {
        "id": str(item.get("route_id", item.get("routeId", item.get("id", "")))),
        "short": str(item.get("route_short_name", item.get("short_name", item.get("routeShortName", "•")))) or "•",
        "name": item.get("route_long_name", item.get("long_name", item.get("routeLongName", ""))) or "",
        "color": "#" + str(item.get("route_color", item.get("color", "2563eb"))).lstrip("#"),
        "text_color": "#" + str(item.get("route_text_color", item.get("text_color", "ffffff"))).lstrip("#"),
    }

@app.context_processor
def template_context():
    return {"t": tr, "lang": current_lang(), "languages": LANGUAGES, "api_docs": f"{API_BASE}/apidocs/", "api_connected": bool(API_TOKEN)}

@app.get("/lang/<lang>")
def set_language(lang):
    if lang in LANGUAGES: session["lang"] = lang
    return redirect(request.referrer or url_for("home"))

@app.get("/")
def home():
    return render_template("home.html", cities=CITIES)

@app.get("/city/<city_id>")
def city(city_id):
    city_info = CITIES.get(city_id)
    if not city_info: abort(404)
    routes = [route_view(x) for x in rows(api_get(f"getRoutes/{city_id}"))]
    stops = rows(api_get(f"getStops/{city_id}"))
    return render_template("city.html", city_id=city_id, city=city_info, routes=routes, stops=stops[:800])

@app.get("/city/<city_id>/line/<path:route_id>")
def line(city_id, route_id):
    city_info = CITIES.get(city_id)
    if not city_info: abort(404)
    all_routes = [route_view(x) for x in rows(api_get(f"getRoutes/{city_id}"))]
    route = next((x for x in all_routes if x["id"] == route_id), {"id": route_id, "short": route_id, "name": "", "color": city_info["accent"], "text_color": "#ffffff"})
    trips = rows(api_get(f"getTrips/{city_id}/{route_id}"))
    trip_id = str((trips[0] if trips else {}).get("trip_id", (trips[0] if trips else {}).get("tripId", "")))
    stops = rows(api_get(f"getStopsByTrip/{city_id}/{trip_id}")) if trip_id else []
    shape = rows(api_get(f"getShapeByTripId/{city_id}", {"tripId": trip_id})) if trip_id else []
    return render_template("line.html", city_id=city_id, city=city_info, route=route, stops=stops, shape=shape)

@app.get("/api/<city_id>/departures")
def departures(city_id):
    if city_id not in CITIES: abort(404)
    stop_id = request.args.get("stop", "").strip()
    if not stop_id: return jsonify({"items": [], "error": "stop_required"}), 400
    data = api_get(f"getNextDepartures/{city_id}/{stop_id}", {"date": request.args.get("date", date.today().isoformat()), "limit": 12})
    return jsonify({"items": rows(data), "connected": bool(data is not None)})

@app.get("/health")
def health():
    return {"status": "ok", "api_configured": bool(API_TOKEN)}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
