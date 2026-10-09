import os
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import app as transit

CITY = 'Grenoble_France'
NOW = datetime(2026, 10, 9, 10, 0, 0, tzinfo=ZoneInfo('Europe/Paris'))

class TransitTests(unittest.TestCase):
    def setUp(self):
        self.client = transit.app.test_client()

    def test_line_uses_selected_service_date_and_direction(self):
        def upstream(path, params=None):
            if path.startswith('getDirection'): return [{'trip_headsign': 'Station'}, {'trip_headsign': 'Centre'}]
            if path.startswith('getStopsByRouteAndDirectionDate'):
                self.assertIn('/20261010/', path)
                self.assertEqual(params, {'direction': 'Centre'})
                return [{'stop_id': 'b', 'stop_sequence': 2}, {'stop_id': 'a', 'stop_sequence': 1}]
            return []
        with patch.object(transit, 'api_get', side_effect=upstream):
            response = self.client.get(f'/api/{CITY}/line/12?date=2026-10-10&direction=Centre')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['selected_direction'], 'Centre')
        self.assertEqual([item['stop_id'] for item in data['stops']], ['a', 'b'])

    def test_empty_dated_service_does_not_invent_stops(self):
        def upstream(path, params=None):
            if path.startswith('getStopsByRouteAndDirectionDate'): return []
            if path.startswith('getStopsByTrip'): self.fail('Must not substitute an inactive trip')
            if path.startswith('getTrips'): return [{'trip_id': 'demo'}]
            return []
        with patch.object(transit, 'api_get', side_effect=upstream):
            self.assertEqual(self.client.get(f'/api/{CITY}/line/12?date=2026-10-10').get_json()['stops'], [])

    def test_next_three_city_local_departures_and_cancellation(self):
        raw = [{'departure_time': time, 'trip_headsign': 'Station', 'status': status} for time, status in [('10:15:00','scheduled'), ('09:59:00','scheduled'), ('10:05:00','cancelled'), ('10:10:00','scheduled'), ('10:20:00','scheduled')]]
        with patch.object(transit, 'city_now', return_value=NOW), patch.object(transit, 'api_get', return_value=raw) as api:
            data = self.client.get(f'/api/{CITY}/departures?stop=a&route=12&direction=Station').get_json()
            self.assertEqual([item['minutes'] for item in data['items']], [5, 10, 15])
            self.assertTrue(data['items'][0]['cancelled'])
            self.assertIn('/20261009/', api.call_args.args[0])
            self.assertEqual(api.call_args.args[1], {'direction':'Station'})

    def test_future_date_has_no_today_countdown(self):
        with patch.object(transit, 'city_now', return_value=NOW), patch.object(transit, 'api_get', return_value=[{'departure_time':'08:00:00'}]) as api:
            data = self.client.get(f'/api/{CITY}/departures?stop=a&date=2026-10-10').get_json()
            self.assertIsNone(data['items'][0]['minutes'])
            self.assertEqual(api.call_args.args[1]['date'], '20261010')
            self.assertEqual(api.call_args.args[1]['time'], '00:00:00')

    def test_invalid_dates_and_coordinates(self):
        for path in [f'/api/{CITY}/departures?stop=a&date=wrong', f'/api/{CITY}/nearby?lat=nan&lon=1', f'/api/{CITY}/nearby?lat=91&lon=1']:
            self.assertEqual(self.client.get(path).status_code,400)

    def test_nearby_distance_order_and_estimate(self):
        raw = [{'stop_id':'b','distance_meters':300}, {'stop_id':'a','distance_meters':75}, {'stop_id':'bad','distance_meters':float('nan')}]
        with patch.object(transit, 'api_get', return_value=raw):
            data = self.client.get(f'/api/{CITY}/nearby?lat=45&lon=5').get_json()
        self.assertEqual([item['id'] for item in data['items']], ['a','b'])
        self.assertEqual(data['items'][1]['walk_minutes'],4)

    def test_alert_feed_optional_and_route_scoped(self):
        with patch.dict(os.environ, {'MEUBUSAO_ALERTS_PATH':''}):
            self.assertFalse(self.client.get(f'/api/{CITY}/alerts').get_json()['supported'])
        with patch.dict(os.environ, {'MEUBUSAO_ALERTS_PATH':'alerts/{city}'}), patch.object(transit, 'api_get', return_value={'alerts':[{'title':'Diversion','route_ids':['12']}, {'title':'Other','route_ids':['13']}]}) as api:
            data = self.client.get(f'/api/{CITY}/alerts?route=12').get_json()
            self.assertEqual([item['title'] for item in data['items']],['Diversion'])
            self.assertEqual(api.call_args.args[0],f'alerts/{CITY}')

    def test_all_languages_render(self):
        with patch.object(transit, 'api_get', return_value=[]):
            for language in transit.LANGUAGES:
                with self.client.session_transaction() as session: session['lang']=language
                for path in ['/', f'/city/{CITY}', f'/city/{CITY}/line/12', f'/city/{CITY}/stop/a','/my-space']:
                    self.assertEqual(self.client.get(path).status_code,200,(language,path))

if __name__ == '__main__': unittest.main()
