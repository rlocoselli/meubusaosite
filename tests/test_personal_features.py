import copy
import os
import time
import unittest
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import app
from data_health import DataHealth
from journey import Network
from passenger_features import compare_journeys,last_scheduled_services
from test_journeys import tables,DAY

CITY='Grenoble_France'

class PersonalFeaturesTests(unittest.TestCase):
    def setUp(self):self.client=app.app.test_client()

    def test_comparison_exposes_fastest_and_less_walking(self):
        data=tables();data['stops'][2]['stop_lat']=45.0201;data['stop_times'][2]['stop_id']='C'
        data['trips'].append(dict(trip_id='direct',route_id='r3',service_id='daily',wheelchair_accessible='1'))
        data['routes'].append(dict(route_id='r3',route_short_name='3'))
        for i,(sid,clock) in enumerate([('A','10:01:00'),('D','10:40:00')]):data['stop_times'].append(dict(trip_id='direct',stop_id=sid,stop_sequence=i,arrival_time=clock,departure_time=clock))
        result=compare_journeys(Network(data),'A','D',DAY,9*3600+55*60)
        direct=next(item for item in result['items'] if item['transfers']==0)
        fast=next(item for item in result['items'] if item['arrival']=='10:30:00')
        self.assertIn('fastest',fast['highlights']);self.assertGreater(fast['walking_meters'],0)
        self.assertIn('less_walking',direct['highlights']);self.assertIn('fewest_transfers',direct['highlights']);self.assertEqual(direct['walking_meters'],0)

    def test_last_scheduled_service_respects_calendar_and_frequencies(self):
        data=tables();trip=copy.deepcopy(data['trips'][0]);trip['trip_id']='last';data['trips'].append(trip)
        for i,(sid,clock) in enumerate([('A','25:00:00'),('B','25:10:00')]):data['stop_times'].append(dict(trip_id='last',stop_id=sid,stop_sequence=i,arrival_time=clock,departure_time=clock))
        result=last_scheduled_services(Network(data),'A',DAY,ZoneInfo('Europe/Paris'))
        self.assertEqual(result[0]['time'],'01:00');self.assertEqual(result[0]['day_offset'],1)
        self.assertTrue(result[0]['scheduled'])
        data['calendar_dates']=[dict(service_id='daily',date=DAY.strftime('%Y%m%d'),exception_type='2')]
        self.assertEqual(last_scheduled_services(Network(data),'A',DAY,ZoneInfo('Europe/Paris')),[])
        data['calendar_dates']=[];data['frequencies']=[dict(trip_id='last')]
        self.assertEqual(last_scheduled_services(Network(data),'A',DAY,ZoneInfo('Europe/Paris')),[])

    def test_last_service_does_not_guess_from_next_departures(self):
        with patch.object(app,'planner_network',return_value=None):
            value=self.client.get(f'/api/{CITY}/last-service?stop=A').json
            self.assertFalse(value['supported']);self.assertEqual(value['items'],[])
        self.assertEqual(self.client.get(f'/api/{CITY}/last-service').status_code,400)

    def test_stop_alerts_exclude_unrelated_routes_and_stops(self):
        alerts={'items':[{'title':'Global'},{'title':'My route','route_ids':['r1']},{'title':'Other route','route_ids':['r2']},{'title':'Other stop','stop_ids':['B']}]}
        def api(path,params=None,max_age=180):return [{'route_id':'r1'}] if path.startswith('getRouteByStopId') else alerts
        with patch.object(app,'api_get',side_effect=api):
            value=self.client.get(f'/api/{CITY}/alerts?stop=A').json
            self.assertEqual([a['title'] for a in value['items']],['Global','My route'])

    def test_health_is_private_and_login_checks_token(self):
        with patch.dict(os.environ,{'MEUBUSAO_ADMIN_TOKEN':'test-admin-token'}):
            self.assertEqual(self.client.get('/api/admin/data-health').status_code,401)
            page=self.client.get('/admin/data-health');self.assertIn('no-store',page.headers['Cache-Control'])
            with self.client.session_transaction() as session:csrf=session['health_csrf']
            self.assertEqual(self.client.post('/admin/data-health',data={'csrf':csrf,'token':'wrong'}).status_code,401)
            self.assertEqual(self.client.post('/admin/data-health',data={'csrf':csrf,'token':'test-admin-token'}).status_code,302)
            response=self.client.get('/api/admin/data-health');self.assertEqual(response.status_code,200)
            self.assertEqual(len(response.json['items']),13)
            self.assertNotIn('test-admin-token',response.get_data(as_text=True))
            self.assertEqual(self.client.post(f'/api/admin/data-health/check/{CITY}').status_code,403)
            with patch.object(app,'api_get',return_value=[]):
                response=self.client.post(f'/api/admin/data-health/check/{CITY}',headers={'X-CSRF-Token':csrf});self.assertEqual(response.status_code,200);self.assertEqual(response.json['items'][0]['status'],'empty')

    def test_health_staleness_and_expired_coverage(self):
        health=DataHealth();cities={CITY:{'name':'Grenoble'}};meta=lambda _:{}
        self.assertEqual(health.snapshot(cities,meta,True)[0]['status'],'not_checked')
        health.record(CITY,'routes',True,5);health.record(CITY,'stops',True,10)
        self.assertEqual(health.snapshot(cities,meta,True)[0]['status'],'ok')
        health.record(CITY,'departures',False)
        self.assertEqual(health.snapshot(cities,meta,True)[0]['status'],'unavailable')
        health.record(CITY,'departures',True,0)
        with patch('data_health.time.time',return_value=time.time()+1000):self.assertEqual(health.snapshot(cities,meta,True)[0]['status'],'stale')
        self.assertEqual(health.snapshot(cities,lambda _:{'coverage_end':'2000-01-01'},True)[0]['status'],'expired')

    def test_new_controls_render_in_every_locale(self):
        with patch.object(app,'api_get',return_value=[]):
            for language in app.LANGUAGES:
                with self.client.session_transaction() as session:session['lang']=language
                for path in ('/','/my-space',f'/city/{CITY}/plan','/admin/data-health'):
                    page=self.client.get(path);self.assertEqual(page.status_code,200,(language,path));self.assertIn(b'data-reading="large"',page.data)
                page=self.client.get('/');self.assertIn(b'personalHome',page.data);self.assertEqual(page.get_data(as_text=True).count('class="review-card"'),3)
        with self.client.get('/sw.js') as response:worker=response.get_data(as_text=True)
        self.assertIn("url.pathname.startsWith('/admin/')",worker)
        self.assertIn("request.headers.get('X-Meubusao-Refresh')==='1'",worker)

if __name__=='__main__':unittest.main()
