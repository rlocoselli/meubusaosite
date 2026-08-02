from __future__ import annotations

import os
import base64
import binascii
import json
import threading
import time
from datetime import date
from functools import lru_cache

import requests
from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, session, url_for


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-change-me")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
if os.environ.get("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True
API_BASE = os.environ.get("MEUBUSAO_API_URL", "https://mybusaoservice.audeladedonnees.fr").rstrip("/")
# Despite its historical name, this value is the legacy login identifier sent
# to /login. The API response token is kept in memory and never exposed.
API_LOGIN_ID = os.environ.get("MEUBUSAO_API_TOKEN", "")
LANGUAGES = ("pt-br", "fr", "it", "es")

CITIES = {
    "Grenoble_France": {"name": "Grenoble", "country": "France", "lat": 45.1885, "lon": 5.7245, "photo": "/static/img/cities/grenoble.jpg", "accent": "#3267e3"},
    "Fortaleza_Brazil": {"name": "Fortaleza", "country": "Brasil", "lat": -3.7319, "lon": -38.5267, "photo": "/static/img/cities/fortaleza.jpg", "accent": "#f59e0b"},
    "SaoPaulo_Brazil": {"name": "São Paulo", "country": "Brasil", "lat": -23.5505, "lon": -46.6333, "photo": "/static/img/cities/sao-paulo.jpg", "accent": "#e63946"},
    "Managua_Nicaragua": {"name": "Managua", "country": "Nicaragua", "lat": 12.114, "lon": -86.2362, "photo": "/static/img/cities/managua.jpg", "accent": "#06a77d"},
    "PortoAlegre_Brazil": {"name": "Porto Alegre", "country": "Brasil", "lat": -30.0346, "lon": -51.2177, "photo": "/static/img/cities/porto-alegre.jpg", "accent": "#7c3aed"},
    "Brisbane_Australia": {"name": "Brisbane", "country": "Australia", "lat": -27.4698, "lon": 153.0251, "photo": "/static/img/cities/brisbane.jpg", "accent": "#0ea5e9"},
    "Perpignan_France": {"name": "Perpignan", "country": "France", "lat": 42.6887, "lon": 2.8948, "photo": "/static/img/cities/perpignan.png", "accent": "#ef4444"},
    "Paris_France": {"name": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522, "photo": "/static/img/cities/paris.jpg", "accent": "#8b5cf6"},
    "Curitiba_Brazil": {"name": "Curitiba", "country": "Brasil", "lat": -25.4284, "lon": -49.2733, "photo": "/static/img/cities/curitiba.jpg", "accent": "#16a34a"},
    "Montreal_Canada": {"name": "Montréal", "country": "Canada", "lat": 45.5019, "lon": -73.5674, "photo": "/static/img/cities/montreal.jpg", "accent": "#dc2626"},
    "Turin_Italy": {"name": "Torino", "country": "Italia", "lat": 45.0703, "lon": 7.6869, "photo": "/static/img/cities/turin.png", "accent": "#2563eb"},
    "Nice_France": {"name": "Nice", "country": "France", "lat": 43.7102, "lon": 7.262, "photo": "/static/img/cities/nice.jpg", "accent": "#0891b2"},
    "BuenosAires_Argentina": {"name": "Buenos Aires", "country": "Argentina", "lat": -34.6037, "lon": -58.3816, "photo": "/static/img/cities/buenos-aires.jpg", "accent": "#0284c7"},
}

COPY = {
    "pt-br": {"nav_cities":"Cidades", "nav_plan":"Planejar viagem", "nav_docs":"Documentação API", "hero_kicker":"Mobilidade urbana, sem complicação", "hero_title":"Sua cidade. Suas linhas. Seu próximo ônibus.", "hero_text":"Explore linhas, pontos, mapas e horários de transporte público em 13 cidades pelo mundo.", "explore":"Explorar cidades", "plan":"Consultar horários", "cities_title":"Escolha sua cidade", "cities_text":"Informação local, mapas claros e as linhas que movem cada lugar.", "routes":"linhas", "open_city":"Ver transporte", "live":"Dados da API", "search_routes":"Buscar linha ou destino", "all_routes":"Todas as linhas", "stops":"Pontos", "map":"Mapa da rede", "timetable":"Horários", "direction":"Sentido", "today":"Hoje", "find_departures":"Buscar partidas", "stop_placeholder":"Nome ou código do ponto", "next_departures":"Próximas partidas", "no_data":"Nenhum dado disponível agora.", "api_missing":"Conecte MEUBUSAO_API_TOKEN para carregar dados ao vivo.", "back":"Voltar", "line":"Linha", "network":"Rede de transporte", "hero_stat_cities":"cidades", "hero_stat_languages":"idiomas", "hero_stat_access":"acesso gratuito"},
    "fr": {"nav_cities":"Villes", "nav_plan":"Planifier", "nav_docs":"Documentation API", "hero_kicker":"La mobilité urbaine, simplement", "hero_title":"Votre ville. Vos lignes. Votre prochain bus.", "hero_text":"Explorez les lignes, arrêts, cartes et horaires de transport public dans 13 villes du monde.", "explore":"Explorer les villes", "plan":"Consulter les horaires", "cities_title":"Choisissez votre ville", "cities_text":"Des informations locales, des cartes lisibles et les lignes qui font vivre chaque ville.", "routes":"lignes", "open_city":"Voir le réseau", "live":"Données de l’API", "search_routes":"Rechercher une ligne ou destination", "all_routes":"Toutes les lignes", "stops":"Arrêts", "map":"Carte du réseau", "timetable":"Horaires", "direction":"Direction", "today":"Aujourd’hui", "find_departures":"Rechercher", "stop_placeholder":"Nom ou code de l’arrêt", "next_departures":"Prochains départs", "no_data":"Aucune donnée disponible pour le moment.", "api_missing":"Configurez MEUBUSAO_API_TOKEN pour charger les données en direct.", "back":"Retour", "line":"Ligne", "network":"Réseau de transport", "hero_stat_cities":"villes", "hero_stat_languages":"langues", "hero_stat_access":"accès gratuit"},
    "it": {"nav_cities":"Città", "nav_plan":"Pianifica", "nav_docs":"Documentazione API", "hero_kicker":"Mobilità urbana, senza complicazioni", "hero_title":"La tua città. Le tue linee. Il tuo prossimo bus.", "hero_text":"Esplora linee, fermate, mappe e orari del trasporto pubblico in 13 città del mondo.", "explore":"Esplora le città", "plan":"Consulta gli orari", "cities_title":"Scegli la tua città", "cities_text":"Informazioni locali, mappe chiare e le linee che fanno muovere ogni luogo.", "routes":"linee", "open_city":"Vedi trasporti", "live":"Dati API", "search_routes":"Cerca linea o destinazione", "all_routes":"Tutte le linee", "stops":"Fermate", "map":"Mappa della rete", "timetable":"Orari", "direction":"Direzione", "today":"Oggi", "find_departures":"Cerca partenze", "stop_placeholder":"Nome o codice fermata", "next_departures":"Prossime partenze", "no_data":"Nessun dato disponibile al momento.", "api_missing":"Configura MEUBUSAO_API_TOKEN per caricare dati in tempo reale.", "back":"Indietro", "line":"Linea", "network":"Rete di trasporto", "hero_stat_cities":"città", "hero_stat_languages":"lingue", "hero_stat_access":"accesso gratuito"},
    "es": {"nav_cities":"Ciudades", "nav_plan":"Planificar", "nav_docs":"Documentación API", "hero_kicker":"Movilidad urbana, sin complicaciones", "hero_title":"Tu ciudad. Tus líneas. Tu próximo bus.", "hero_text":"Explora líneas, paradas, mapas y horarios de transporte público en 13 ciudades del mundo.", "explore":"Explorar ciudades", "plan":"Consultar horarios", "cities_title":"Elige tu ciudad", "cities_text":"Información local, mapas claros y las líneas que mueven cada lugar.", "routes":"líneas", "open_city":"Ver transporte", "live":"Datos de la API", "search_routes":"Buscar línea o destino", "all_routes":"Todas las líneas", "stops":"Paradas", "map":"Mapa de la red", "timetable":"Horarios", "direction":"Dirección", "today":"Hoy", "find_departures":"Buscar salidas", "stop_placeholder":"Nombre o código de la parada", "next_departures":"Próximas salidas", "no_data":"No hay datos disponibles ahora.", "api_missing":"Configura MEUBUSAO_API_TOKEN para cargar datos en vivo.", "back":"Volver", "line":"Línea", "network":"Red de transporte", "hero_stat_cities":"ciudades", "hero_stat_languages":"idiomas", "hero_stat_access":"acceso gratuito"},
}

_cache: dict[str, tuple[float, object]] = {}
_auth = {"token": "", "expires_at": 0.0}
_auth_lock = threading.Lock()

LEGAL_COPY = {
    "pt-br": {"nav_more":"Mais", "about":"Sobre", "team":"Equipe", "faq":"Perguntas frequentes", "contact":"Contato", "terms":"Termos", "privacy":"Privacidade", "cookies":"Cookies", "cookie_title":"Sua privacidade, sua escolha", "cookie_text":"Usamos armazenamento essencial para lembrar o idioma e suas preferências. Recursos opcionais só serão ativados com sua autorização.", "cookie_accept":"Aceitar todos", "cookie_reject":"Somente essenciais", "cookie_settings":"Personalizar", "cookie_save":"Salvar escolhas", "cookie_essential":"Essenciais", "cookie_essential_info":"Necessários para idioma, segurança e funcionamento do site. Sempre ativos.", "cookie_optional":"Experiência externa", "cookie_optional_info":"Permite mapas e outros conteúdos fornecidos por serviços externos."},
    "fr": {"nav_more":"Plus", "about":"À propos", "team":"Équipe", "faq":"FAQ", "contact":"Contact", "terms":"Conditions", "privacy":"Confidentialité", "cookies":"Cookies", "cookie_title":"Votre vie privée, votre choix", "cookie_text":"Nous utilisons le stockage essentiel pour mémoriser la langue et vos préférences. Les fonctionnalités optionnelles ne sont activées qu’avec votre accord.", "cookie_accept":"Tout accepter", "cookie_reject":"Essentiels uniquement", "cookie_settings":"Personnaliser", "cookie_save":"Enregistrer mes choix", "cookie_essential":"Essentiels", "cookie_essential_info":"Nécessaires à la langue, la sécurité et au fonctionnement du site. Toujours actifs.", "cookie_optional":"Expérience externe", "cookie_optional_info":"Autorise les cartes et autres contenus fournis par des services externes."},
    "it": {"nav_more":"Altro", "about":"Chi siamo", "team":"Team", "faq":"Domande frequenti", "contact":"Contatti", "terms":"Termini", "privacy":"Privacy", "cookies":"Cookie", "cookie_title":"La tua privacy, la tua scelta", "cookie_text":"Usiamo lo spazio di archiviazione essenziale per ricordare lingua e preferenze. Le funzioni opzionali vengono attivate solo con il tuo consenso.", "cookie_accept":"Accetta tutto", "cookie_reject":"Solo essenziali", "cookie_settings":"Personalizza", "cookie_save":"Salva le scelte", "cookie_essential":"Essenziali", "cookie_essential_info":"Necessari per lingua, sicurezza e funzionamento del sito. Sempre attivi.", "cookie_optional":"Esperienza esterna", "cookie_optional_info":"Consente mappe e altri contenuti forniti da servizi esterni."},
    "es": {"nav_more":"Más", "about":"Acerca de", "team":"Equipo", "faq":"Preguntas frecuentes", "contact":"Contacto", "terms":"Términos", "privacy":"Privacidad", "cookies":"Cookies", "cookie_title":"Tu privacidad, tu elección", "cookie_text":"Usamos almacenamiento esencial para recordar el idioma y tus preferencias. Las funciones opcionales solo se activan con tu consentimiento.", "cookie_accept":"Aceptar todo", "cookie_reject":"Solo esenciales", "cookie_settings":"Personalizar", "cookie_save":"Guardar opciones", "cookie_essential":"Esenciales", "cookie_essential_info":"Necesarios para el idioma, la seguridad y el funcionamiento del sitio. Siempre activos.", "cookie_optional":"Experiencia externa", "cookie_optional_info":"Permite mapas y otros contenidos proporcionados por servicios externos."},
}

PAGE_CONTENT = {
    "pt-br": {"testimonials_kicker":"Histórias reais", "testimonials_title":"Quem usa, recomenda", "testimonials_text":"Avaliações compartilhadas por passageiros que usam o Meu Busão para organizar seus trajetos.", "reviews":[("Muito útil. Ajuda bastante na hora de planejar qual itinerário escolher.", "M. Reis", "Brasil"), ("Excelente, bem explicado e muito detalhado. Recomendo para usar em Manágua, Nicarágua.", "Sr. Herrera", "Manágua"), ("Um ótimo aplicativo de horários de ônibus em Manágua. Funciona muito bem.", "Sr. Perez", "Manágua")], "team_kicker":"As pessoas por trás das rotas", "team_title":"Uma pequena equipe com uma missão em movimento", "team_intro":"Criamos ferramentas simples a partir de dados abertos para tornar o transporte público mais compreensível e acessível.", "team_story_title":"Tecnologia que começa no ponto de ônibus", "team_story":"O Meu Busão nasceu de uma necessidade cotidiana: saber qual ônibus pegar e quando ele chegaria. Unimos desenvolvimento, engenharia e análise de dados para transformar informações GTFS complexas em uma experiência clara para passageiros de diferentes cidades.", "team_value_1":"Dados abertos", "team_value_1_text":"Transformamos dados públicos de mobilidade em informação útil.", "team_value_2":"Acesso para todos", "team_value_2_text":"O serviço é gratuito, inclusivo e disponível em vários idiomas.", "team_value_3":"Feito com cuidado", "team_value_3_text":"Mapas, horários e interfaces pensados para a vida real.", "join_title":"Quer ajudar a melhorar a mobilidade?", "join_text":"Fale conosco sobre dados, novas cidades, traduções ou colaboração.", "join_button":"Entrar em contato", "roles":["Usuário de ônibus e desenvolvedor", "Engenheiro de software", "Analista de dados"]},
    "fr": {"testimonials_kicker":"Histoires vécues", "testimonials_title":"Ils l’utilisent, ils le recommandent", "testimonials_text":"Des avis de voyageurs qui utilisent Meu Busão pour mieux organiser leurs déplacements.", "reviews":[("Très utile. L’application aide beaucoup à choisir le bon itinéraire.", "M. Reis", "Brésil"), ("Excellent, bien expliqué et très détaillé. Je le recommande pour Managua, au Nicaragua.", "M. Herrera", "Managua"), ("Une très bonne application pour les horaires de bus à Managua. Elle fonctionne très bien.", "M. Perez", "Managua")], "team_kicker":"Derrière chaque trajet", "team_title":"Une petite équipe, une mission en mouvement", "team_intro":"Nous créons des outils simples à partir de données ouvertes pour rendre les transports publics plus lisibles et accessibles.", "team_story_title":"Une technologie née à l’arrêt de bus", "team_story":"Meu Busão est né d’un besoin quotidien : savoir quel bus prendre et quand il arrivera. Nous réunissons développement, ingénierie et analyse de données pour transformer des données GTFS complexes en une expérience claire dans chaque ville.", "team_value_1":"Données ouvertes", "team_value_1_text":"Nous transformons les données publiques de mobilité en informations utiles.", "team_value_2":"Accessible à tous", "team_value_2_text":"Le service est gratuit, inclusif et disponible en plusieurs langues.", "team_value_3":"Conçu avec soin", "team_value_3_text":"Des cartes, horaires et interfaces pensés pour la vie réelle.", "join_title":"Vous souhaitez améliorer la mobilité ?", "join_text":"Contactez-nous pour les données, de nouvelles villes, les traductions ou une collaboration.", "join_button":"Nous contacter", "roles":["Usager du bus et développeur", "Ingénieur logiciel", "Analyste de données"]},
    "it": {"testimonials_kicker":"Storie reali", "testimonials_title":"Chi lo usa, lo consiglia", "testimonials_text":"Recensioni di passeggeri che usano Meu Busão per organizzare meglio i propri spostamenti.", "reviews":[("Molto utile. Aiuta davvero a scegliere l’itinerario giusto.", "M. Reis", "Brasile"), ("Eccellente, ben spiegato e molto dettagliato. Consigliato per Managua, Nicaragua.", "Sig. Herrera", "Managua"), ("Un’ottima app per gli orari degli autobus a Managua. Funziona molto bene.", "Sig. Perez", "Managua")], "team_kicker":"Le persone dietro le linee", "team_title":"Un piccolo team, una missione in movimento", "team_intro":"Creiamo strumenti semplici a partire da dati aperti per rendere il trasporto pubblico più chiaro e accessibile.", "team_story_title":"Tecnologia nata alla fermata", "team_story":"Meu Busão nasce da un’esigenza quotidiana: sapere quale autobus prendere e quando arriverà. Uniamo sviluppo, ingegneria e analisi dei dati per trasformare complessi dati GTFS in un’esperienza chiara per ogni città.", "team_value_1":"Dati aperti", "team_value_1_text":"Trasformiamo i dati pubblici sulla mobilità in informazioni utili.", "team_value_2":"Accesso per tutti", "team_value_2_text":"Il servizio è gratuito, inclusivo e disponibile in più lingue.", "team_value_3":"Progettato con cura", "team_value_3_text":"Mappe, orari e interfacce pensati per la vita reale.", "join_title":"Vuoi contribuire a una mobilità migliore?", "join_text":"Contattaci per dati, nuove città, traduzioni o collaborazioni.", "join_button":"Contattaci", "roles":["Utente del bus e sviluppatore", "Ingegnere software", "Analista dati"]},
    "es": {"testimonials_kicker":"Historias reales", "testimonials_title":"Quienes lo usan, lo recomiendan", "testimonials_text":"Opiniones de pasajeros que utilizan Meu Busão para organizar mejor sus recorridos.", "reviews":[("Muy útil. Ayuda mucho a elegir el itinerario adecuado.", "M. Reis", "Brasil"), ("Excelente, bien explicado y muy detallado. Recomendado para Managua, Nicaragua.", "Sr. Herrera", "Managua"), ("Una gran aplicación de horarios de autobús en Managua. Funciona muy bien.", "Sr. Perez", "Managua")], "team_kicker":"Las personas detrás de las rutas", "team_title":"Un pequeño equipo con una misión en movimiento", "team_intro":"Creamos herramientas sencillas a partir de datos abiertos para que el transporte público sea más comprensible y accesible.", "team_story_title":"Tecnología que nació en la parada", "team_story":"Meu Busão nació de una necesidad cotidiana: saber qué autobús tomar y cuándo llegaría. Unimos desarrollo, ingeniería y análisis de datos para convertir complejos datos GTFS en una experiencia clara para cada ciudad.", "team_value_1":"Datos abiertos", "team_value_1_text":"Convertimos datos públicos de movilidad en información útil.", "team_value_2":"Acceso para todos", "team_value_2_text":"El servicio es gratuito, inclusivo y está disponible en varios idiomas.", "team_value_3":"Creado con cuidado", "team_value_3_text":"Mapas, horarios e interfaces pensados para la vida real.", "join_title":"¿Quieres ayudar a mejorar la movilidad?", "join_text":"Contáctanos para hablar de datos, nuevas ciudades, traducciones o colaboración.", "join_button":"Contactar", "roles":["Usuario de autobús y desarrollador", "Ingeniero de software", "Analista de datos"]},
}

TEAM = [
    {"name": "Rodrigo Locoselli", "photo": "/images/rodrigo.jpg"},
    {"name": "Pedro Marcondes", "photo": "/images/pedro.jpg"},
    {"name": "Lisiane Von Ahn", "photo": "/images/lisiane-von-ahn.jpg"},
]

def current_lang():
    lang = session.get("lang", "pt-br")
    return lang if lang in LANGUAGES else "pt-br"

def tr(key):
    return COPY[current_lang()].get(key, LEGAL_COPY[current_lang()].get(key, key))

def api_get(path, params=None):
    cache_key = path + repr(sorted((params or {}).items()))
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < 180:
        return cached[1]
    token = api_token()
    if not token:
        return None
    for attempt in range(2):
        try:
            response = requests.get(f"{API_BASE}/{path.lstrip('/')}", params=params, headers={"token": token}, timeout=12)
            if response.status_code in (401, 403) and attempt == 0:
                token = api_token(force=True)
                if token:
                    continue
            response.raise_for_status()
            data = response.json()
            _cache[cache_key] = (time.time(), data)
            return data
        except (requests.RequestException, ValueError):
            return None
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

def _extract_login_token(payload):
    """Accept the response shapes used by both legacy and current login APIs."""
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return ""
    for key in ("token", "access_token", "accessToken", "jwt"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    for key in ("data", "result"):
        value = payload.get(key)
        token = _extract_login_token(value)
        if token:
            return token
    return ""

def _token_expiry(token):
    """Use the JWT expiry when available, otherwise renew after 50 minutes."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        expires_at = float(json.loads(base64.urlsafe_b64decode(payload))["exp"])
        return max(time.time() + 30, expires_at - 30)
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError, binascii.Error):
        return time.time() + 3000

def api_token(force=False):
    if not API_LOGIN_ID:
        return ""
    if not force and _auth["token"] and time.time() < _auth["expires_at"]:
        return _auth["token"]
    with _auth_lock:
        if not force and _auth["token"] and time.time() < _auth["expires_at"]:
            return _auth["token"]
        try:
            response = requests.get(f"{API_BASE}/login", headers={"id": API_LOGIN_ID}, timeout=12)
            response.raise_for_status()
            token = _extract_login_token(response.json())
        except (requests.RequestException, ValueError):
            token = ""
        _auth["token"] = token
        _auth["expires_at"] = _token_expiry(token) if token else 0.0
        return token

@app.context_processor
def template_context():
    return {"t": tr, "content": PAGE_CONTENT[current_lang()], "lang": current_lang(), "languages": LANGUAGES, "api_docs": f"{API_BASE}/apidocs/", "api_connected": bool(API_LOGIN_ID)}

@app.get("/lang/<lang>")
def set_language(lang):
    if lang in LANGUAGES: session["lang"] = lang
    return redirect(request.referrer or url_for("home"))

@app.get("/")
def home():
    return render_template("home.html", cities=CITIES)

@app.get("/index.html")
def legacy_index():
    return redirect(url_for("home"), code=301)

@app.get("/team.html")
def team_page():
    members = [{**member, "role": PAGE_CONTENT[current_lang()]["roles"][index]} for index, member in enumerate(TEAM)]
    return render_template("team.html", members=members)

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
    direction_rows = rows(api_get(f"getDirectionByRoute/{city_id}/{route_id}"))
    directions = []
    for item in direction_rows:
        value = item.get("trip_headsign", item.get("tripHeadsign", item.get("direction", "")))
        if value and value not in directions:
            directions.append(str(value))
    selected_direction = request.args.get("direction", "").strip()
    if selected_direction not in directions:
        selected_direction = directions[0] if directions else ""

    weekday = date.today().strftime("%A").lower()
    stop_params = {"direction": selected_direction} if selected_direction else None
    stops = rows(api_get(f"getStopsByRouteAndDirection/{city_id}/{weekday}/{route_id}", stop_params))
    if not stops and selected_direction:
        stops = rows(api_get(f"getStopsByRouteAndDirection/{city_id}/{weekday}/{route_id}"))

    shape_id = ""
    for stop in stops:
        shape_id = str(stop.get("shape_id", stop.get("shapeId", "")) or "")
        if shape_id:
            break
    shape = rows(api_get(f"getShapeById/{city_id}", {"shapeId": shape_id})) if shape_id else []

    if not stops:
        trips = rows(api_get(f"getTrips/{city_id}/{route_id}"))
        trip_id = str((trips[0] if trips else {}).get("trip_id", (trips[0] if trips else {}).get("tripId", "")))
        stops = rows(api_get(f"getStopsByTrip/{city_id}/{trip_id}")) if trip_id else []
        shape = rows(api_get(f"getShapeByTripId/{city_id}", {"tripId": trip_id})) if trip_id else []
    return render_template("line.html", city_id=city_id, city=city_info, route=route, stops=stops, shape=shape, directions=directions, selected_direction=selected_direction)

@app.get("/api/<city_id>/departures")
def departures(city_id):
    if city_id not in CITIES: abort(404)
    stop_id = request.args.get("stop", "").strip()
    if not stop_id: return jsonify({"items": [], "error": "stop_required"}), 400
    data = api_get(f"getNextDepartures/{city_id}/{stop_id}", {"date": request.args.get("date", date.today().isoformat()), "limit": 12})
    return jsonify({"items": rows(data), "connected": bool(data is not None)})

@app.get("/health")
def health():
    return {"status": "ok", "api_configured": bool(API_LOGIN_ID), "api_authenticated": bool(_auth["token"] and time.time() < _auth["expires_at"])}

LEGACY_PAGES = {"about.html", "faqs.html", "contacts.html", "terms.html", "privacy.html", "app-ads.txt"}

@app.get("/<folder>/<path:filename>")
def legacy_asset(folder, filename):
    if folder not in {"css", "js", "images", "fonts"}:
        abort(404)
    return send_from_directory(os.path.join(app.root_path, folder), filename, max_age=86400)

@app.get("/<path:page>")
def legacy_page(page):
    if page not in LEGACY_PAGES:
        abort(404)
    return send_from_directory(app.root_path, page)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
