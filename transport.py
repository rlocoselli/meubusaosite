"""Passenger-facing transport normalization; provider data remains authoritative."""
import json
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

TIMEZONES = {
    'Grenoble_France': 'Europe/Paris', 'Paris_France': 'Europe/Paris',
    'Perpignan_France': 'Europe/Paris', 'Nice_France': 'Europe/Paris',
    'Turin_Italy': 'Europe/Rome', 'Fortaleza_Brazil': 'America/Fortaleza',
    'SaoPaulo_Brazil': 'America/Sao_Paulo', 'PortoAlegre_Brazil': 'America/Sao_Paulo',
    'Curitiba_Brazil': 'America/Sao_Paulo', 'Managua_Nicaragua': 'America/Managua',
    'Brisbane_Australia': 'Australia/Brisbane', 'Montreal_Canada': 'America/Toronto',
    'BuenosAires_Argentina': 'America/Argentina/Buenos_Aires',
}

def city_now(city_id):
    return datetime.now(ZoneInfo(TIMEZONES[city_id]))

def city_metadata(city_id):
    path = os.environ.get('MEUBUSAO_CITY_DATA_FILE')
    if not path:
        return {}
    try:
        with open(path, encoding='utf-8') as source:
            value = json.load(source).get(city_id, {})
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}

def safe_url(value):
    return value if isinstance(value, str) and urlparse(value).scheme in ('https', 'http') else ''

def public_metadata(city_id):
    data = city_metadata(city_id)
    alerts = []
    for alert in data.get('alerts', []):
        if not isinstance(alert, dict) or not alert.get('title'):
            continue
        try:
            start = datetime.fromisoformat(alert['start']) if alert.get('start') else None
            end = datetime.fromisoformat(alert['end']) if alert.get('end') else None
            local_now = city_now(city_id)
            if (start and local_now < start) or (end and local_now > end):
                continue
        except (ValueError, TypeError):
            continue
        alerts.append({'title': str(alert['title']), 'description': str(alert.get('description', '')), 'url': safe_url(alert.get('url')), 'routes': [str(x) for x in alert.get('routes', [])], 'stops': [str(x) for x in alert.get('stops', [])]})
    return {'agency': str(data.get('agency', '')), 'source_url': safe_url(data.get('source_url')), 'coverage_start': str(data.get('coverage_start', '')), 'coverage_end': str(data.get('coverage_end', '')), 'source_updated_at': str(data.get('source_updated_at', '')), 'fare': str(data.get('fare', '')), 'service_hours': str(data.get('service_hours', '')), 'tickets_url': safe_url(data.get('tickets_url')), 'alerts': alerts, 'timezone': TIMEZONES[city_id]}

def service_weekday(city_id, day):
    overrides = city_metadata(city_id).get('service_calendar', {})
    weekday = overrides.get(day.isoformat())
    allowed = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    return weekday if weekday in allowed else day.strftime('%A').lower()

def clean_color(value, default='2563eb'):
    value = str(value or '').lstrip('#')
    return '#' + (value if re.fullmatch(r'[0-9a-fA-F]{6}', value) else default)

def stop_view(item):
    def number(*keys):
        try:
            return float(next(item[k] for k in keys if item.get(k) is not None))
        except (ValueError, TypeError, StopIteration):
            return None
    return {**item, 'id': str(item.get('stop_id', item.get('stopId', item.get('id', '')))), 'name': str(item.get('stop_name', item.get('stopName', item.get('name', '')))), 'lat': number('stop_lat', 'stopLat', 'lat'), 'lon': number('stop_lon', 'stopLon', 'lon', 'lng'), 'platform': str(item.get('platform_code') or ''), 'wheelchair': str(item.get('wheelchair_boarding', '0'))}

def departure_view(item, city_id, service_date):
    scheduled = item.get('scheduled_departure_time') or item.get('departure_time') or item.get('departureTime') or item.get('time') or ''
    predicted = item.get('predicted_departure_time') or item.get('estimated_departure_time') or ''
    cancelled = item.get('cancelled') is True or str(item.get('schedule_relationship', '')).upper() == 'CANCELED'
    status = 'cancelled' if cancelled else ('predicted' if predicted else 'scheduled')
    value = str(predicted or scheduled)
    minutes = None
    day_offset = 0
    try:
        if re.fullmatch(r'\d{1,3}:\d{2}(:\d{2})?', value):
            hours, mins, *secs = map(int, value.split(':'))
            if mins > 59 or (secs and secs[0] > 59):
                raise ValueError('Invalid time')
            moment = datetime.combine(service_date, datetime.min.time(), ZoneInfo(TIMEZONES[city_id])) + timedelta(hours=hours, minutes=mins, seconds=secs[0] if secs else 0)
        else:
            moment = datetime.fromisoformat(value)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=ZoneInfo(TIMEZONES[city_id]))
        day_offset = (moment.astimezone(ZoneInfo(TIMEZONES[city_id])).date() - service_date).days
        minutes = round((moment - city_now(city_id)).total_seconds() / 60)
        value = moment.astimezone(ZoneInfo(TIMEZONES[city_id])).strftime('%H:%M')
    except (ValueError, TypeError, OverflowError):
        pass
    return {'line': str(item.get('route_short_name') or item.get('routeShortName') or item.get('route_id') or '•'), 'destination': str(item.get('trip_headsign') or item.get('headsign') or item.get('route_long_name') or ''), 'time': value, 'scheduled_time': str(scheduled), 'minutes': minutes, 'day_offset': day_offset, 'status': status, 'platform': str(item.get('platform_code') or ''), 'updated_at': str(item.get('updated_at') or item.get('timestamp') or ''), 'color': clean_color(item.get('route_color'), '0c7662')}
