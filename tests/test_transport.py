import json
import os
import tempfile
import unittest
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import app as site
from transport import departure_view, city_now, service_weekday, public_metadata, stop_view

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.client = site.app.test_client()
        site._cache.clear()

    def test_city_timezones(self):
        self.assertEqual(str(city_now('Brisbane_Australia').tzinfo), 'Australia/Brisbane')
        self.assertEqual(str(city_now('Managua_Nicaragua').tzinfo), 'America/Managua')

    def test_after_midnight_and_predictions(self):
        with patch('transport.city_now', return_value=datetime(2026,11,14,0,0,tzinfo=ZoneInfo('Europe/Paris'))):
            value=departure_view({'departure_time':'25:10:00'},'Grenoble_France',date(2026,11,13))
            self.assertEqual((value['time'],value['minutes'],value['status']),('01:10',70,'scheduled'))
            live=departure_view({'departure_time':'25:10:00','predicted_departure_time':'25:15:00'},'Grenoble_France',date(2026,11,13))
            self.assertEqual(live['status'],'predicted')
            self.assertEqual(live['minutes'],75)
        self.assertEqual(departure_view({'cancelled':True},'Grenoble_France',date.today())['status'],'cancelled')

    def test_metadata_and_holiday_override(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
            json.dump({'Grenoble_France':{'service_calendar':{'2026-12-25':'sunday'},'tickets_url':'javascript:alert(1)','alerts':[{'title':'Past','end':'2020-01-01T00:00:00+01:00'},{'title':'Diversion','routes':['12']}] }},f); f.flush()
            with patch.dict(os.environ,{'MEUBUSAO_CITY_DATA_FILE':f.name}):
                self.assertEqual(service_weekday('Grenoble_France',date(2026,12,25)),'sunday')
                meta=public_metadata('Grenoble_France')
                self.assertEqual(meta['tickets_url'],'')
                self.assertEqual([a['title'] for a in meta['alerts']],['Diversion'])

    def test_empty_and_unavailable_are_distinct(self):
        with patch('app.api_get',return_value=[]):
            value=self.client.get('/api/Grenoble_France/departures?stop=A').json
            self.assertTrue(value['connected']); self.assertEqual(value['items'],[])
        with patch('app.api_get',return_value=None):
            self.assertFalse(self.client.get('/api/Grenoble_France/departures?stop=A').json['connected'])
        self.assertEqual(self.client.get('/api/Grenoble_France/departures?stop=A&date=bad').status_code,400)

    def test_stop_shapes_and_local_api_date(self):
        self.assertEqual(stop_view({'stopId':'A','stopName':'Central','stopLat':45,'stopLon':5})['name'],'Central')
        fixed=datetime(2026,11,14,1,0,tzinfo=ZoneInfo('Australia/Brisbane'))
        with patch('app.city_now',return_value=fixed),patch('app.api_get',return_value=[]) as get:
            self.client.get('/api/Brisbane_Australia/departures?stop=A')
            self.assertEqual(get.call_args.args[1]['date'],'20261114')

    def test_pages_render_in_every_language(self):
        def fixture(path,params=None):
            if path.startswith('getRoutes'):return [{'route_id':'12','route_short_name':'12','route_long_name':'Central','route_type':3}]
            if path.startswith(('getStops','getStopsByRouteAndDirection')):return [{'stop_id':'A','stop_name':'Central','stop_lat':45.18,'stop_lon':5.7}]
            return []
        with patch('app.api_get',side_effect=fixture):
            for lang in site.LANGUAGES:
                with self.client.session_transaction() as session:session['lang']=lang
                for path in ('/','/my-space','/city/Grenoble_France','/city/Grenoble_France/line/12','/contacts.html'):
                    response=self.client.get(path)
                    self.assertEqual(response.status_code,200,(lang,path))
                    self.assertNotIn(b'LIVE',response.data)
                response=self.client.get('/city/Grenoble_France')
                self.assertIn(b'Central',response.data)
                self.assertNotIn(b'unpkg.com/leaflet',response.data)
                self.assertIn(b'passenger.js',response.data)
                self.assertIn(b'data-insights-city',response.data)

if __name__=='__main__':unittest.main()
