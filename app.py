from __future__ import annotations

import os
import base64
import binascii
import json
import threading
import time
import math
from zoneinfo import ZoneInfo
from datetime import date, datetime, timedelta
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zipfile import BadZipFile
from journey import Network, load_zip, seconds, distance

import requests
from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from page_content import PUBLIC_PAGES
from travel_copy import TRAVEL_COPY


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

# Geographic browsing uses stable region keys and localized labels.
for city_info in CITIES.values():
    city_info["continent"] = {"France": "europe", "Italia": "europe", "Brasil": "south_america", "Argentina": "south_america", "Canada": "north_america", "Nicaragua": "north_america", "Australia": "oceania"}[city_info["country"]]

EXPLORER_COPY = {
    "pt-br": ["Todas as cidades", "Europa", "América do Sul", "América do Norte", "Oceania", "Buscar cidade ou país", "Todos os países", "Trajeto", "Conexão entre pontos · trajeto aproximado", "Ver no mapa", "Horário previsto", "Escolha um ponto para consultar todos os horários", "Nenhuma cidade encontrada"],
    "fr": ["Toutes les villes", "Europe", "Amérique du Sud", "Amérique du Nord", "Océanie", "Rechercher une ville ou un pays", "Tous les pays", "Itinéraire", "Liaison entre arrêts · tracé approximatif", "Voir sur la carte", "Horaire prévu", "Choisissez un arrêt pour consulter tous les horaires", "Aucune ville trouvée"],
    "it": ["Tutte le città", "Europa", "Sud America", "Nord America", "Oceania", "Cerca città o paese", "Tutti i paesi", "Percorso", "Collegamento tra fermate · percorso approssimativo", "Vedi sulla mappa", "Orario previsto", "Scegli una fermata per consultare tutti gli orari", "Nessuna città trovata"],
    "es": ["Todas las ciudades", "Europa", "América del Sur", "América del Norte", "Oceanía", "Buscar ciudad o país", "Todos los países", "Recorrido", "Conexión entre paradas · recorrido aproximado", "Ver en el mapa", "Horario previsto", "Elige una parada para consultar todos los horarios", "No se encontraron ciudades"],
}
for language, labels in EXPLORER_COPY.items():
    COPY[language].update(zip(["all_cities", "europe", "south_america", "north_america", "oceania", "search_cities", "all_countries", "itinerary", "approximate_route", "show_on_map", "scheduled_time", "stop_hint", "no_cities"], labels))

CITY_ZONES = {
    "France": "Europe/Paris", "Italia": "Europe/Rome", "Brasil": "America/Sao_Paulo",
    "Argentina": "America/Argentina/Buenos_Aires", "Canada": "America/Toronto",
    "Nicaragua": "America/Managua", "Australia": "Australia/Brisbane",
}
def city_now(city_id):
    zone = "America/Fortaleza" if city_id == "Fortaleza_Brazil" else CITY_ZONES[CITIES[city_id]["country"]]
    return datetime.now(ZoneInfo(zone))

def service_date(city_id):
    value = request.args.get("date", "")
    try:
        return date.fromisoformat(value) if value else city_now(city_id).date()
    except ValueError:
        abort(400, description="Invalid date; use YYYY-MM-DD")

FEATURE_KEYS = ["service_date", "preview_route", "open_line", "nearby_stops", "find_nearby", "nearby_hint", "distance_hint", "no_nearby", "service_alerts", "alerts_unavailable", "no_alerts", "departure_stop", "minutes", "cancelled", "unavailable", "saved_stops", "saved_lines", "choose_stop", "expand_stops", "collapse_stops", "scheduled_notice", "past_date", "date_fallback"]
FEATURE_COPY = {
 "pt-br": ["Data da viagem", "Ver trajeto", "Abrir linha", "Pontos próximos", "Buscar perto de mim", "Encontre pontos em um raio de 1 km.", "Distância em linha reta · caminhada estimada", "Nenhum ponto a menos de 1 km.", "Alertas de serviço", "Alertas não disponíveis para esta rede.", "Nenhum alerta informado pelo serviço.", "Partidas deste ponto", "min", "Cancelado", "Serviço temporariamente indisponível", "Pontos favoritos", "Linhas favoritas", "Escolha um ponto", "Expandir pontos", "Recolher pontos", "Horários programados, sujeitos a alterações.", "Horários da data selecionada", "Trajeto habitual; serviço nesta data não confirmado"],
 "fr": ["Date du voyage", "Aperçu du trajet", "Ouvrir la ligne", "Arrêts à proximité", "Chercher autour de moi", "Trouvez des arrêts dans un rayon de 1 km.", "Distance à vol d’oiseau · marche estimée", "Aucun arrêt à moins de 1 km.", "Alertes du réseau", "Alertes indisponibles pour ce réseau.", "Aucune alerte signalée par le service.", "Départs à cet arrêt", "min", "Annulé", "Service temporairement indisponible", "Arrêts favoris", "Lignes favorites", "Choisissez un arrêt", "Développer les arrêts", "Réduire les arrêts", "Horaires prévus, susceptibles de changer.", "Horaires à la date sélectionnée", "Itinéraire habituel ; service à cette date non confirmé"],
 "it": ["Data del viaggio", "Anteprima percorso", "Apri linea", "Fermate vicine", "Cerca vicino a me", "Trova fermate entro 1 km.", "Distanza in linea d’aria · cammino stimato", "Nessuna fermata entro 1 km.", "Avvisi di servizio", "Avvisi non disponibili per questa rete.", "Nessun avviso segnalato dal servizio.", "Partenze da questa fermata", "min", "Cancellato", "Servizio temporaneamente non disponibile", "Fermate preferite", "Linee preferite", "Scegli una fermata", "Espandi fermate", "Riduci fermate", "Orari programmati, soggetti a modifiche.", "Orari della data selezionata", "Percorso abituale; servizio in questa data non confermato"],
 "es": ["Fecha del viaje", "Vista del recorrido", "Abrir línea", "Paradas cercanas", "Buscar cerca de mí", "Encuentra paradas en un radio de 1 km.", "Distancia en línea recta · caminata estimada", "Ninguna parada a menos de 1 km.", "Alertas del servicio", "Alertas no disponibles para esta red.", "Ninguna alerta indicada por el servicio.", "Salidas de esta parada", "min", "Cancelado", "Servicio temporalmente no disponible", "Paradas favoritas", "Líneas favoritas", "Elige una parada", "Expandir paradas", "Reducir paradas", "Horarios programados, sujetos a cambios.", "Horarios de la fecha seleccionada", "Recorrido habitual; servicio en esta fecha no confirmado"],
}
for language, labels in TRAVEL_COPY.items():
    COPY[language].update(labels)
for language, labels in FEATURE_COPY.items():
    COPY[language].update(zip(FEATURE_KEYS, labels))

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

MAP_COPY = {
    "pt-br": {"stop_details":"Detalhes da parada", "lines_here":"Linhas nesta parada", "upcoming":"Próximos ônibus", "getting_there":"Como chegar", "directions_text":"Abra uma rota de transporte público da sua localização até esta parada.", "open_directions":"Criar rota", "view_full_stop":"Ver horário completo", "stop_timetable":"Horário da parada", "departures_by_line":"Partidas por linha", "destination":"Destino", "hour":"Hora", "how_to_arrive":"Como chegar até aqui", "how_to_arrive_text":"Use sua localização atual ou abra o trajeto no Google Maps ou OpenStreetMap. A página já leva as coordenadas exatas da parada.", "open_google_maps":"Abrir no Google Maps", "open_osm":"Abrir no OpenStreetMap", "use_my_location":"Usar minha localização", "stop_code":"Código da parada", "no_upcoming":"Sem próximas partidas encontradas para hoje.", "all_day":"Grade completa do dia", "next_label":"Próximo", "loading":"Carregando informações…", "close":"Fechar", "minutes":"min", "scheduled":"Horário previsto", "location_error":"Não foi possível obter sua localização. Abriremos a rota usando seu ponto de partida escolhido no mapa.", "my_space":"Meu espaço", "favorites_title":"Suas linhas favoritas", "favorites_intro":"Acesse rapidamente as linhas que você usa. Tudo fica salvo somente neste dispositivo, sem cadastro.", "favorites_empty":"Você ainda não salvou nenhuma linha.", "favorites_empty_text":"Explore uma cidade e toque na estrela de uma linha para encontrá-la aqui.", "explore_lines":"Explorar linhas", "remove_favorite":"Remover favorito", "add_favorite":"Salvar nos favoritos", "local_note":"Armazenado neste dispositivo"},
    "fr": {"stop_details":"Détails de l’arrêt", "lines_here":"Lignes à cet arrêt", "upcoming":"Prochains bus", "getting_there":"Comment s’y rendre", "directions_text":"Ouvrez un itinéraire en transports publics depuis votre position jusqu’à cet arrêt.", "open_directions":"Créer l’itinéraire", "view_full_stop":"Voir l’horaire complet", "stop_timetable":"Horaire de l’arrêt", "departures_by_line":"Départs par ligne", "destination":"Destination", "hour":"Heure", "how_to_arrive":"Comment arriver jusqu’ici", "how_to_arrive_text":"Utilisez votre position actuelle ou ouvrez le trajet dans Google Maps ou OpenStreetMap. La page utilise déjà les coordonnées exactes de l’arrêt.", "open_google_maps":"Ouvrir dans Google Maps", "open_osm":"Ouvrir dans OpenStreetMap", "use_my_location":"Utiliser ma position", "stop_code":"Code de l’arrêt", "no_upcoming":"Aucun prochain départ trouvé pour aujourd’hui.", "all_day":"Programme complet du jour", "next_label":"Prochain", "loading":"Chargement des informations…", "close":"Fermer", "minutes":"min", "scheduled":"Horaire prévu", "location_error":"Votre position n’est pas disponible. Choisissez votre point de départ sur la carte.", "my_space":"Mon espace", "favorites_title":"Vos lignes favorites", "favorites_intro":"Retrouvez rapidement vos lignes habituelles. Elles restent uniquement sur cet appareil, sans compte.", "favorites_empty":"Vous n’avez encore enregistré aucune ligne.", "favorites_empty_text":"Explorez une ville et touchez l’étoile d’une ligne pour la retrouver ici.", "explore_lines":"Explorer les lignes", "remove_favorite":"Retirer des favoris", "add_favorite":"Ajouter aux favoris", "local_note":"Enregistré sur cet appareil"},
    "it": {"stop_details":"Dettagli fermata", "lines_here":"Linee a questa fermata", "upcoming":"Prossimi autobus", "getting_there":"Come arrivare", "directions_text":"Apri un percorso con il trasporto pubblico dalla tua posizione a questa fermata.", "open_directions":"Crea percorso", "view_full_stop":"Vedi orario completo", "stop_timetable":"Orario della fermata", "departures_by_line":"Partenze per linea", "destination":"Destinazione", "hour":"Ora", "how_to_arrive":"Come arrivare qui", "how_to_arrive_text":"Usa la tua posizione attuale oppure apri il percorso in Google Maps o OpenStreetMap. La pagina usa già le coordinate esatte della fermata.", "open_google_maps":"Apri in Google Maps", "open_osm":"Apri in OpenStreetMap", "use_my_location":"Usa la mia posizione", "stop_code":"Codice fermata", "no_upcoming":"Nessuna prossima partenza trovata per oggi.", "all_day":"Programma completo del giorno", "next_label":"Prossima", "loading":"Caricamento informazioni…", "close":"Chiudi", "minutes":"min", "scheduled":"Orario previsto", "location_error":"Posizione non disponibile. Scegli il punto di partenza sulla mappa.", "my_space":"Il mio spazio", "favorites_title":"Le tue linee preferite", "favorites_intro":"Accedi rapidamente alle linee che usi. I dati restano solo su questo dispositivo, senza account.", "favorites_empty":"Non hai ancora salvato nessuna linea.", "favorites_empty_text":"Esplora una città e tocca la stella di una linea per trovarla qui.", "explore_lines":"Esplora le linee", "remove_favorite":"Rimuovi dai preferiti", "add_favorite":"Aggiungi ai preferiti", "local_note":"Salvato su questo dispositivo"},
    "es": {"stop_details":"Detalles de la parada", "lines_here":"Líneas en esta parada", "upcoming":"Próximos autobuses", "getting_there":"Cómo llegar", "directions_text":"Abre una ruta en transporte público desde tu ubicación hasta esta parada.", "open_directions":"Crear ruta", "view_full_stop":"Ver horario completo", "stop_timetable":"Horario de la parada", "departures_by_line":"Salidas por línea", "destination":"Destino", "hour":"Hora", "how_to_arrive":"Cómo llegar hasta aquí", "how_to_arrive_text":"Usa tu ubicación actual o abre el trayecto en Google Maps u OpenStreetMap. La página ya incluye las coordenadas exactas de la parada.", "open_google_maps":"Abrir en Google Maps", "open_osm":"Abrir en OpenStreetMap", "use_my_location":"Usar mi ubicación", "stop_code":"Código de parada", "no_upcoming":"No se encontraron próximas salidas para hoy.", "all_day":"Programa completo del día", "next_label":"Próxima", "loading":"Cargando información…", "close":"Cerrar", "minutes":"min", "scheduled":"Horario previsto", "location_error":"No pudimos obtener tu ubicación. Elige el punto de partida en el mapa.", "my_space":"Mi espacio", "favorites_title":"Tus líneas favoritas", "favorites_intro":"Accede rápidamente a las líneas que utilizas. Todo se guarda solo en este dispositivo, sin cuenta.", "favorites_empty":"Todavía no has guardado ninguna línea.", "favorites_empty_text":"Explora una ciudad y toca la estrella de una línea para encontrarla aquí.", "explore_lines":"Explorar líneas", "remove_favorite":"Eliminar favorito", "add_favorite":"Guardar en favoritos", "local_note":"Guardado en este dispositivo"},
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
    return COPY[current_lang()].get(key, LEGAL_COPY[current_lang()].get(key, MAP_COPY[current_lang()].get(key, key)))

def api_get(path, params=None, max_age=180):
    cache_key = path + repr(sorted((params or {}).items()))
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < max_age:
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
        for key in ("data", "results", "routes", "stops", "departures", "items", "shapes", "points"):
            if isinstance(data.get(key), list): return data[key]
    return []

def stop_view(item):
    get = item.get
    stop_id = str(get("stop_id", get("stopId", get("id", ""))) or "")
    name = get("stop_name", get("stopName", get("name", ""))) or stop_id
    lat_raw = get("stop_lat", get("stopLat", get("lat", get("latitude"))))
    lon_raw = get("stop_lon", get("stopLon", get("lon", get("lng", get("longitude")))))
    try:
        lat = float(lat_raw)
    except (TypeError, ValueError):
        lat = None
    try:
        lon = float(lon_raw)
    except (TypeError, ValueError):
        lon = None
    if lat is not None and (not math.isfinite(lat) or abs(lat)>90): lat = None
    if lon is not None and (not math.isfinite(lon) or abs(lon)>180): lon = None
    return {"wheelchair": str(get("wheelchair_boarding", get("wheelchairBoarding", "0")) or "0"), "id": stop_id, "name": str(name), "lat": lat, "lon": lon, "code": str(get("stop_code", get("stopCode", get("code", stop_id))) or stop_id)}

def departure_view(item):
    get = item.get
    time_value = str(get("departure_time", get("departureTime", get("time", get("arrival_time", get("arrivalTime", ""))))) or "")
    return {
        "time": time_value,
        "hour": time_value[:2] if len(time_value) >= 5 and time_value[2] == ":" else "",
        "route": str(get("route_short_name", get("routeShortName", get("route_id", get("routeId", "")))) or ""),
        "headsign": str(get("trip_headsign", get("tripHeadsign", get("headsign", get("route_long_name", "")))) or ""),
        "wheelchair": str(get("wheelchair_accessible", get("wheelchairAccessible", "0")) or "0"),
        "raw": item,
    }

def minutes_of(time_value):
    text = str(time_value or "")
    if len(text) < 5 or text[2] != ":":
        return None
    try:
        hour, minute = int(text[:2]), int(text[3:5])
        return hour * 60 + minute if hour >= 0 and 0 <= minute < 60 else None
    except ValueError:
        return None

def next_departure_index(departures, now=None):
    """Index of the first departure still ahead, or -1 when the day is over."""
    if not departures:
        return -1
    current = now or datetime.now()
    reference = current.hour * 60 + current.minute
    for index, item in enumerate(departures):
        value = minutes_of(item.get("time") if isinstance(item, dict) else item)
        if value is not None and value >= reference:
            return index
    return -1

def group_timetable(departures):
    grouped: dict[str, list[dict]] = {}
    for item in departures:
        key = item.get("route") or "•"
        grouped.setdefault(key, []).append(item)
    return [{"route": route, "items": sorted(items, key=lambda x: x.get("time", ""))} for route, items in sorted(grouped.items())]

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
    return {"t": tr, "travel_copy": TRAVEL_COPY[current_lang()], "content": PAGE_CONTENT[current_lang()], "lang": current_lang(), "languages": LANGUAGES, "api_docs": f"{API_BASE}/apidocs/", "api_connected": bool(API_LOGIN_ID)}

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

@app.get("/my-space")
def my_space():
    return render_template("my_space.html")

@app.get("/about.html")
def about_page():
    return render_template("public/about.html", page=PUBLIC_PAGES[current_lang()]["about"])

@app.get("/faqs.html")
def faq_page():
    return render_template("public/faq.html", page=PUBLIC_PAGES[current_lang()]["faq"])

@app.get("/contacts.html")
def contact_page():
    return render_template("public/contact.html", page=PUBLIC_PAGES[current_lang()]["contact"])

@app.get("/terms.html")
def terms_page():
    return render_template("public/legal.html", page=PUBLIC_PAGES[current_lang()]["terms"])

@app.get("/privacy.html")
def privacy_page():
    return render_template("public/legal.html", page=PUBLIC_PAGES[current_lang()]["privacy"])

@app.get("/city/<city_id>")
def city(city_id):
    city_info = CITIES.get(city_id)
    if not city_info: abort(404)
    routes = [route_view(x) for x in rows(api_get(f"getRoutes/{city_id}"))]
    stops = rows(api_get(f"getStops/{city_id}"))
    return render_template("city.html", city_id=city_id, city=city_info, routes=routes, stops=stops[:100], stop_count=len(stops), selected_date=service_date(city_id).isoformat())

def line_data(city_id, route_id, selected_date, direction=""):
    city_info = CITIES[city_id]
    all_routes = [route_view(x) for x in rows(api_get(f"getRoutes/{city_id}"))]
    route = next((x for x in all_routes if x["id"] == route_id), {"id": route_id, "short": route_id, "name": "", "color": city_info["accent"], "text_color": "#ffffff"})
    direction_rows = rows(api_get(f"getDirectionByRoute/{city_id}/{route_id}"))
    directions = []
    for item in direction_rows:
        value = item.get("trip_headsign", item.get("tripHeadsign", item.get("direction", "")))
        if value and value not in directions:
            directions.append(str(value))
    selected_direction = direction.strip()
    if selected_direction not in directions:
        selected_direction = directions[0] if directions else ""

    weekday = selected_date.strftime("%A").lower()
    stop_params = {"direction": selected_direction} if selected_direction else None
    date_data = api_get(f"getStopsByRouteAndDirectionDate/{city_id}/{selected_date.strftime('%Y%m%d')}/{route_id}", stop_params)
    stops = rows(date_data)
    date_confirmed = date_data is not None
    if date_data is None:
        stops = rows(api_get(f"getStopsByRouteAndDirection/{city_id}/{weekday}/{route_id}", stop_params))

    shape_id = ""
    for stop in stops:
        shape_id = str(stop.get("shape_id", stop.get("shapeId", "")) or "")
        if shape_id:
            break
    shape = rows(api_get(f"getShapeById/{city_id}", {"shapeId": shape_id})) if shape_id else []

    if not stops or not shape:
        trips = rows(api_get(f"getTrips/{city_id}/{route_id}"))
        matching = [trip for trip in trips if not selected_direction or str(trip.get("trip_headsign", trip.get("tripHeadsign", ""))) == selected_direction]
        trips = matching if selected_direction else trips
        trip_id = str((trips[0] if trips else {}).get("trip_id", (trips[0] if trips else {}).get("tripId", "")))
        if not stops and not date_confirmed:
            stops = rows(api_get(f"getStopsByTrip/{city_id}/{trip_id}")) if trip_id else []
        shape = rows(api_get(f"getShapeByTripId/{city_id}", {"tripId": trip_id})) if trip_id else []
    def sequence(item):
        try:
            return float(item.get("stop_sequence", item.get("stopSequence", 0)))
        except (TypeError, ValueError):
            return 0
    stops = sorted(stops, key=sequence)
    return dict(city_id=city_id, city=city_info, route=route, stops=stops, shape=shape, directions=directions, selected_direction=selected_direction, selected_date=selected_date.isoformat(), date_confirmed=date_confirmed)

@app.get("/city/<city_id>/line/<path:route_id>")
def line(city_id, route_id):
    if city_id not in CITIES: abort(404)
    return render_template("line.html", **line_data(city_id, route_id, service_date(city_id), request.args.get("direction", "")))

@app.get("/api/<city_id>/line/<path:route_id>")
def line_preview(city_id, route_id):
    if city_id not in CITIES: abort(404)
    data = line_data(city_id, route_id, service_date(city_id), request.args.get("direction", ""))
    return jsonify(data)

@app.get("/city/<city_id>/stop/<path:stop_id>")
def stop_page(city_id, stop_id):
    city_info = CITIES.get(city_id)
    if not city_info: abort(404)
    all_stops = rows(api_get(f"getStops/{city_id}"))
    stop = None
    for raw in all_stops:
        view = stop_view(raw if isinstance(raw, dict) else {})
        if view["id"] == stop_id:
            stop = {**view, "raw": raw}
            break
    if stop is None:
        stop = {"id": stop_id, "name": stop_id, "lat": None, "lon": None, "code": stop_id, "wheelchair": "0"}
    selected_date = service_date(city_id)
    departures_raw = rows(api_get(f"getNextDepartures/{city_id}/{stop_id}", {"date": selected_date.strftime("%Y%m%d"), "time": "00:00:00", "limit": 200}))
    departures = normalized_departures(departures_raw, city_id, selected_date)
    departures.sort(key=lambda item: minutes_of(item["time"]) if minutes_of(item["time"]) is not None else float("inf"))
    upcoming = next_departure_index(departures, city_now(city_id)) if selected_date == city_now(city_id).date() else -1
    for position, item in enumerate(departures):
        item["is_next"] = position == upcoming
    grouped = group_timetable(departures)
    routes_here = [route_view(x) for x in rows(api_get(f"getRouteByStopId/{city_id}/{stop_id}"))]
    return render_template("stop.html", city_id=city_id, city=city_info, stop=stop, grouped=grouped, departures=departures, routes_here=routes_here, selected_date=selected_date.isoformat())


def normalized_departures(raw, city_id, selected_date):
    now = city_now(city_id)
    reference = now.hour * 60 + now.minute + now.second / 60
    items = []
    for value in rows(raw):
        if not isinstance(value, dict): continue
        item = departure_view(value)
        minute = minutes_of(item["time"])
        item["minutes"] = max(0, math.ceil(minute - reference)) if minute is not None and selected_date == now.date() and minute >= reference else None
        status = str(value.get("status", value.get("schedule_relationship", ""))).lower()
        item["cancelled"] = value.get("cancelled") is True or status in {"cancelled", "canceled", "canceled_trip", "3"}
        minute_seconds = seconds(item["time"])
        item["departure_at"] = int((datetime.combine(selected_date, datetime.min.time(), tzinfo=now.tzinfo) + timedelta(seconds=minute_seconds)).timestamp()*1000) if minute_seconds is not None else None
        items.append(item)
    return sorted(items, key=lambda item: minutes_of(item["time"]) if minutes_of(item["time"]) is not None else float("inf"))

@app.get("/api/<city_id>/departures")
def departures(city_id):
    if city_id not in CITIES: abort(404)
    stop_id = request.args.get("stop", "").strip()
    if not stop_id: return jsonify({"items": [], "error": "stop_required"}), 400
    selected_date = service_date(city_id)
    route_id = request.args.get("route", "")
    direction = request.args.get("direction", "")
    if route_id:
        data = api_get(f"getStopTimeByRouteAndDirectionAndDateAndStopId/{city_id}/{selected_date.strftime('%Y%m%d')}/{route_id}/{stop_id}", {"direction": direction})
    else:
        data = api_get(f"getNextDepartures/{city_id}/{stop_id}", {"date": selected_date.strftime("%Y%m%d"), "time": city_now(city_id).strftime("%H:%M:%S") if selected_date == city_now(city_id).date() else "00:00:00", "limit": 200})
    items = normalized_departures(data, city_id, selected_date)
    if selected_date == city_now(city_id).date():
        items = [item for item in items if item["minutes"] is not None]
    return jsonify({"items": items[:3] if route_id else items[:12], "connected": data is not None, "date": selected_date.isoformat(), "timezone": str(city_now(city_id).tzinfo)})

@app.get("/api/<city_id>/stop/<path:stop_id>")
def stop_details(city_id, stop_id):
    if city_id not in CITIES: abort(404)
    selected_date = service_date(city_id)
    routes_data = api_get(f"getRouteByStopId/{city_id}/{stop_id}")
    departures_data = api_get(f"getNextDepartures/{city_id}/{stop_id}", {"date": selected_date.strftime("%Y%m%d"), "time": "00:00:00", "limit": 200})
    departures = normalized_departures(departures_data, city_id, selected_date)
    return jsonify({"routes": [route_view(item) for item in rows(routes_data)], "items": departures,
        "times": [item["time"] for item in departures if item["time"]],
        "next": next_departure_index([item for item in departures if item["time"]], city_now(city_id)) if selected_date == city_now(city_id).date() else -1,
        "connected": departures_data is not None})

@app.get("/api/<city_id>/nearby")
def nearby_stops(city_id):
    if city_id not in CITIES: abort(404)
    try:
        lat, lon = float(request.args["lat"]), float(request.args["lon"])
        if not math.isfinite(lat) or not math.isfinite(lon) or abs(lat)>90 or abs(lon)>180: raise ValueError()
    except (KeyError, ValueError): abort(400)
    data = api_get(f"getNearbyStops/{city_id}", {"lat": lat, "lon": lon, "radiusMeters": 1000})
    items = []
    for raw in rows(data):
        stop = stop_view(raw)
        try: distance = float(raw["distance_meters"])
        except (KeyError, ValueError, TypeError): continue
        if not math.isfinite(distance) or distance < 0 or distance > 1000: continue
        items.append({**stop, "distance": round(distance), "walk_minutes": max(1, math.ceil(distance / 75))})
    return jsonify(items=sorted(items, key=lambda item:item["distance"]), connected=data is not None)

@app.get("/api/<city_id>/alerts")
def service_alerts(city_id):
    if city_id not in CITIES: abort(404)
    # Optional authenticated upstream endpoint; no alert endpoint exists in the default API.
    path = os.environ.get("MEUBUSAO_ALERTS_PATH", "")
    if not path: return jsonify(items=[], supported=False, connected=False)
    data = api_get(path.replace("{city}", city_id))
    alerts = data.get("alerts", []) if isinstance(data, dict) and isinstance(data.get("alerts"), list) else rows(data)
    route = request.args.get("route", "")
    items = []
    for alert in alerts:
        if not isinstance(alert, dict): continue
        route_ids = alert.get("route_ids", [])
        if isinstance(route_ids, (str, int)): route_ids = [route_ids]
        if not route_ids and alert.get("route_id") is not None: route_ids = [alert["route_id"]]
        if route and route_ids and route not in [str(value) for value in route_ids]: continue
        items.append({"title": str(alert.get("title", alert.get("header_text", ""))), "description": str(alert.get("description", alert.get("description_text", ""))), "severity": str(alert.get("severity", "info"))})
    return jsonify(items=items, supported=True, connected=data is not None)


_planner_cache = {}
_planner_lock = threading.Lock()

def planner_network(city_id):
    configured = os.environ.get("MEUBUSAO_GTFS_" + city_id.upper(), "")
    default = Path(app.root_path) / "gtfs" / "ni-managua-gtfs.zip" if city_id == "Managua_Nicaragua" and not API_LOGIN_ID else None
    path = Path(configured) if configured else default
    if configured and not path.is_file(): return None
    cache_key = (city_id, str(path), path.stat().st_mtime if path and path.is_file() else None)
    cached = _planner_cache.get(cache_key)
    if cached and time.time()-cached[0] < 900: return cached[1]
    # Serialize cold snapshots to avoid duplicate city-wide exports.
    with _planner_lock:
        cached = _planner_cache.get(cache_key)
        if cached and time.time()-cached[0]<900: return cached[1]
        try:
            if path and path.is_file():
                tables = load_zip(path)
            else:
                endpoints = {"stops":"getStops", "routes":"getRoutes", "stop_times":"getStopsTime", "calendar":"getCalendar", "calendar_dates":"getCalendarDates"}
                with ThreadPoolExecutor(max_workers=5) as pool:
                    futures = {key:pool.submit(api_get, f"{endpoint}/{city_id}") for key,endpoint in endpoints.items()}
                    responses = {key:future.result() for key,future in futures.items()}
                if any(responses[key] is None for key in ("stops","routes","stop_times","calendar","calendar_dates")): return None
                tables = {key:rows(value) for key,value in responses.items()}
                with ThreadPoolExecutor(max_workers=8) as pool:
                    trips = list(pool.map(lambda route: api_get(f"getTrips/{city_id}/{route.get('route_id',route.get('routeId',''))}"),tables['routes']))
                if any(value is None for value in trips): return None
                tables["trips"] = [trip for value in trips for trip in rows(value)]
                if not tables['stop_times'] or not tables['trips']: return None
            network = Network(tables)
        except (OSError, BadZipFile, ValueError, KeyError, TypeError):
            return None
        if len(_planner_cache)>=4: _planner_cache.pop(next(iter(_planner_cache)))
        _planner_cache[cache_key]=(time.time(),network)
        return network

@app.get("/api/<city_id>/journeys")
def journeys(city_id):
    if city_id not in CITIES: abort(404)
    day = service_date(city_id)
    start = seconds(request.args.get("time", city_now(city_id).strftime("%H:%M:%S")))
    origin,destination = request.args.get("from", ""),request.args.get("to", "")
    if start is None or start>=86400 or not origin or not destination: abort(400)
    network = planner_network(city_id)
    if network is None: return jsonify(items=[],connected=False,reason="unavailable")
    try: result = network.plan(origin,destination,day,start,request.args.get("accessible")=="1")
    except ValueError: abort(400)
    for item in result['items']:
        for leg in item['legs']:
            stamp = seconds(leg['departure'])
            leg['departure_at'] = int((datetime.combine(day,datetime.min.time(),tzinfo=city_now(city_id).tzinfo)+timedelta(seconds=stamp)).timestamp()*1000) if stamp is not None else None
    return jsonify(**result, connected=True, date=day.isoformat(), timezone=str(city_now(city_id).tzinfo))

@app.get("/api/<city_id>/stops")
def search_stops(city_id):
    if city_id not in CITIES: abort(404)
    data=api_get(f"getStops/{city_id}")
    query=request.args.get("q", "").casefold()
    import unicodedata
    normalize=lambda text: ''.join(char for char in unicodedata.normalize('NFD',text.casefold()) if not unicodedata.combining(char))
    items=[stop_view(raw) for raw in rows(data)]
    query=normalize(query)
    items=[stop for stop in items if query in normalize(stop['name']+' '+stop['id'])]
    return jsonify(items=items[:30],connected=data is not None)

@app.get("/api/<city_id>/map-stops")
def map_stops(city_id):
    if city_id not in CITIES: abort(404)
    try:
        south,west,north,east=map(float,request.args.get('bounds','-90,-180,90,180').split(','))
        zoom=int(request.args.get('zoom',12))
        if not all(math.isfinite(value) for value in (south,west,north,east)) or not -90<=south<=north<=90 or not -180<=west<=east<=180 or not 0<=zoom<=20: raise ValueError()
    except (ValueError,TypeError): abort(400)
    data=api_get(f"getStops/{city_id}")
    groups={}
    grid=360/(2**zoom)*.16
    for raw in rows(data):
        stop=stop_view(raw)
        if stop['lat'] is None or stop['lon'] is None or not south<=stop['lat']<=north or not west<=stop['lon']<=east: continue
        key=(int(stop['lat']/grid),int(stop['lon']/grid))
        groups.setdefault(key,[]).append(stop)
    items=[]
    for stops in groups.values():
        if len(stops)==1:items.append(dict(stops[0],count=1))
        else:items.append(dict(count=len(stops),lat=sum(stop['lat'] for stop in stops)/len(stops),lon=sum(stop['lon'] for stop in stops)/len(stops),members=stops[:20] if zoom>=18 else [],bounds=[[min(stop['lat'] for stop in stops),min(stop['lon'] for stop in stops)],[max(stop['lat'] for stop in stops),max(stop['lon'] for stop in stops)]]))
    # Bounded rendering even for unusual requests spanning very large networks.
    return jsonify(items=items[:800],connected=data is not None,total=sum(item['count'] for item in items),truncated=len(items)>800)

@app.get("/api/<city_id>/vehicles")
def vehicles(city_id):
    if city_id not in CITIES: abort(404)
    path=os.environ.get('MEUBUSAO_VEHICLES_PATH','')
    if not path:return jsonify(items=[],supported=False,connected=False)
    data=api_get(path.replace('{city}',city_id),max_age=10)
    vehicle_rows=data.get('vehicles',[]) if isinstance(data,dict) and isinstance(data.get('vehicles'),list) else rows(data)
    route=request.args.get('route','')
    items=[]
    for raw in vehicle_rows:
        if not isinstance(raw,dict):continue
        stop=stop_view(raw)
        rid=str(raw.get('route_id',raw.get('routeId','')))
        try: updated=float(raw.get('timestamp',0))
        except (ValueError,TypeError):continue
        age=time.time()-updated
        if stop['lat'] is None or stop['lon'] is None or not math.isfinite(updated) or age>120 or age < -30 or (route and rid!=route):continue
        items.append(dict(id=str(raw.get('vehicle_id',raw.get('id',''))),lat=stop['lat'],lon=stop['lon'],route=rid,label=str(raw.get('label',rid)),timestamp=updated,wheelchair=str(raw.get('wheelchair_accessible','0'))))
    response=jsonify(items=items,supported=True,connected=data is not None)
    response.headers['Cache-Control']='no-store'
    return response

@app.get('/sw.js')
def service_worker():
    response=send_from_directory(app.static_folder,'sw.js')
    response.headers['Cache-Control']='no-cache'
    response.headers['Service-Worker-Allowed']='/'
    return response

@app.get('/offline')
def offline_page():
    return render_template('offline.html')

@app.get("/health")
def health():
    return {"status": "ok", "api_configured": bool(API_LOGIN_ID), "api_authenticated": bool(_auth["token"] and time.time() < _auth["expires_at"])}

LEGACY_PAGES = {"app-ads.txt"}

RETIRED_DEMO_PAGES = {"blog-listing.html", "download.html", "features.html", "pricing.html", "project-details.html", "projects.html", "single-post.html"}

@app.get("/<page>.html")
def retired_demo_page(page):
    filename = f"{page}.html"
    if filename not in RETIRED_DEMO_PAGES:
        abort(404)
    return redirect(url_for("home"), code=301)

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

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
