import unittest
from unittest.mock import patch

import app

CITY='Grenoble_France'

class StopFinderTests(unittest.TestCase):
    def setUp(self):
        self.client=app.app.test_client()
        self.stops=[
            {'stop_id':'NORTH','stop_code':'101','stop_name':'École Centrale','stop_lat':45.1802,'stop_lon':5.72,'platform_code':'A'},
            {'stop_id':'SOUTH','stop_code':'102','stop_name':'École Centrale','stop_lat':45.181,'stop_lon':5.72,'platform_code':'B'},
            {'stop_id':'FAR','stop_code':'103','stop_name':'École Nord','stop_lat':45.25,'stop_lon':5.72},
        ]

    def test_search_matches_accents_codes_and_keeps_opposite_platforms(self):
        with patch.object(app,'api_get',return_value=self.stops):
            data=self.client.get(f'/api/{CITY}/stops?q=ecole%20centrale').json
            self.assertEqual({s['id'] for s in data['items']},{'NORTH','SOUTH'})
            self.assertEqual({s['platform'] for s in data['items']},{'A','B'})
            exact=self.client.get(f'/api/{CITY}/stops?q=102').json
            self.assertEqual(exact['items'][0]['id'],'SOUTH')

    def test_stop_pagination_and_duplicates(self):
        with patch.object(app,'api_get',return_value=self.stops+[self.stops[0]]):
            first=self.client.get(f'/api/{CITY}/stops?limit=2').json
            next_page=self.client.get(f'/api/{CITY}/stops?limit=2&offset=2').json
            self.assertEqual(first['total'],3)
            self.assertTrue(first['has_more'])
            self.assertFalse(next_page['has_more'])
            self.assertEqual(len(first['items'])+len(next_page['items']),3)
        for suffix in ('limit=0','offset=-1','limit=no','limit=51'):
            self.assertEqual(self.client.get(f'/api/{CITY}/stops?{suffix}').status_code,400)

    def test_nearby_falls_back_to_stop_inventory_and_sorts_distance(self):
        def upstream(path,params=None):
            return None if path.startswith('getNearbyStops') else list(reversed(self.stops))
        with patch.object(app,'api_get',side_effect=upstream):
            response=self.client.post(f'/api/{CITY}/nearby',json={'lat':45.18,'lon':5.72,'radius':1000})
            self.assertEqual(response.status_code,200)
            self.assertEqual([s['id'] for s in response.json['items']],['NORTH','SOUTH'])
            self.assertLess(response.json['items'][0]['distance'],response.json['items'][1]['distance'])
            self.assertEqual(response.headers['Cache-Control'],'no-store')

    def test_nearby_missing_distance_uses_coordinates_and_radius(self):
        with patch.object(app,'api_get',return_value=self.stops):
            small=self.client.post(f'/api/{CITY}/nearby',json={'lat':45.18,'lon':5.72,'radius':1000}).json
            self.assertEqual(len(small['items']),2)
            self.assertTrue(small['connected'])
        with patch.object(app,'api_get',return_value=[{'stop_id':'NO','stop_lat':None,'stop_lon':None}]):
            self.assertEqual(self.client.post(f'/api/{CITY}/nearby',json={'lat':45.18,'lon':5.72}).json['items'],[])

    def test_nearby_invalid_payload_and_unavailable(self):
        for payload in (None,[],{'lat':91,'lon':5},{'lat':45,'lon':5,'radius':100000},{'lat':'bad','lon':5}):
            self.assertEqual(self.client.post(f'/api/{CITY}/nearby',json=payload).status_code,400)
        with patch.object(app,'api_get',return_value=None):
            self.assertFalse(self.client.post(f'/api/{CITY}/nearby',json={'lat':45,'lon':5}).json['connected'])

    def test_iso_predictions_are_not_lost_from_upcoming_departures(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now=datetime(2026,11,13,12,0,tzinfo=ZoneInfo('Europe/Paris'))
        raw=[{'departure_time':'12:08:00','predicted_departure_time':'2026-11-13T11:05:00Z','route_short_name':'12'}]
        with patch.object(app,'city_now',return_value=now),patch.object(app,'api_get',return_value=raw):
            data=self.client.get(f'/api/{CITY}/departures?stop=NORTH').json
            self.assertEqual(len(data['items']),1)
            self.assertEqual(data['items'][0]['minutes'],5)
            self.assertEqual(data['items'][0]['status'],'predicted')
            self.assertEqual(data['items'][0]['time'],'12:05:00')

    def test_city_exposes_explicit_stop_selection_in_all_languages(self):
        with patch.object(app,'api_get',return_value=[]):
            for language in app.LANGUAGES:
                with self.client.session_transaction() as session: session['lang']=language
                response=self.client.get(f'/city/{CITY}')
                self.assertEqual(response.status_code,200)
                text=response.get_data(as_text=True)
                self.assertIn('id="departureStopOptions"',text)
                self.assertIn('aria-autocomplete="list"',text)
                self.assertIn('id="findNearby"',text)
                self.assertEqual(text.count('id="findNearby"'),1)
                self.assertNotIn('list="stopList"',text)
                self.assertLess(text.index('id="departures"'),text.index('id="insightsTitle"'))

if __name__=='__main__':unittest.main()
