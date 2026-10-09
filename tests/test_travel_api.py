import unittest
import time
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo
import app
from journey import Network
from test_journeys import tables

class TravelApiTests(unittest.TestCase):
    def setUp(self): self.client=app.app.test_client()

    def test_journeys_have_calendar_epoch_and_invalid_input(self):
        with patch.object(app,'planner_network',return_value=Network(tables())):
            data=self.client.get('/api/Grenoble_France/journeys?from=A&to=D&date=2026-10-09&time=09:55&accessible=1').get_json()
            self.assertEqual(data['items'][0]['legs'][0]['departure_at'],int(datetime(2026,10,9,10,tzinfo=ZoneInfo('Europe/Paris')).timestamp()*1000))
            self.assertEqual(self.client.get('/api/Grenoble_France/journeys?from=invalid&to=D&time=09:00').status_code,400)
        self.assertEqual(self.client.get('/api/Grenoble_France/journeys?from=A&to=D&time=25:00').status_code,400)

    def test_vehicle_feed_only_includes_fresh_valid_route_positions(self):
        now=time.time()
        values=[dict(vehicle_id='valid',lat=45,lon=5,route_id='12',timestamp=now),dict(vehicle_id='old',lat=45,lon=5,route_id='12',timestamp=now-180),dict(vehicle_id='bad',lat=float('nan'),lon=5,route_id='12',timestamp=now),dict(vehicle_id='other',lat=45,lon=5,route_id='13',timestamp=now)]
        with patch.dict(app.os.environ,{'MEUBUSAO_VEHICLES_PATH':'vehicles/{city}'}),patch.object(app,'api_get',return_value={'vehicles':values}) as api:
            response=self.client.get('/api/Grenoble_France/vehicles?route=12')
            self.assertEqual([item['id'] for item in response.get_json()['items']],['valid'])
            self.assertEqual(api.call_args.kwargs['max_age'],10)
            self.assertEqual(response.headers['Cache-Control'],'no-store')

    def test_map_aggregates_a_large_network_and_filters_viewport(self):
        values=[dict(stop_id=str(index),stop_lat=45+index*.000001,stop_lon=5,stop_name=str(index)) for index in range(10000)]
        values.append(dict(stop_id='outside',stop_lat=30,stop_lon=3))
        with patch.object(app,'api_get',return_value=values):
            data=self.client.get('/api/Grenoble_France/map-stops?bounds=44,4,46,6&zoom=12').get_json()
            self.assertLess(len(data['items']),20)
            self.assertEqual(data['total'],10000)
            self.assertTrue(any(item['count']>1 for item in data['items']))
        self.assertEqual(self.client.get('/api/Grenoble_France/map-stops?bounds=nan,1,2,3').status_code,400)

    def test_stop_search_and_accessibility_unknown(self):
        with patch.object(app,'api_get',return_value=[dict(stop_id='1',stop_name='São Paulo',wheelchair_boarding=1),dict(stop_id='2',stop_name='Elsewhere')]):
            data=self.client.get('/api/Grenoble_France/stops?q=sao').get_json()
            self.assertEqual(len(data['items']),1)
            self.assertEqual(data['items'][0]['wheelchair'],'1')
        self.assertEqual(app.departure_view({})['wheelchair'],'0')

    def test_worker_scope_and_offline_shell(self):
        response=self.client.get('/sw.js')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['Service-Worker-Allowed'],'/')
        response.close()
        self.assertEqual(self.client.get('/offline').status_code,200)

    def test_live_api_snapshot_joins_trip_metadata(self):
        data=tables()
        def upstream(path,params=None):
            for prefix,key in [('getStopsTime','stop_times'),('getStops','stops'),('getCalendarDates','calendar_dates'),('getCalendar','calendar'),('getRoutes','routes')]:
                if path.startswith(prefix):return data[key]
            if path.startswith('getTrips'):
                route=path.split('/')[-1]
                return [trip for trip in data['trips'] if trip['route_id']==route]
            return None
        with patch.object(app,'_planner_cache',{}),patch.object(app,'api_get',side_effect=upstream):
            network=app.planner_network('Grenoble_France')
            self.assertTrue(network.plan('A','D',datetime(2026,10,9).date(),9*3600)['items'])

if __name__=='__main__':unittest.main()
