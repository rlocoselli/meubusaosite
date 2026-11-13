import unittest
from datetime import datetime,date
from unittest.mock import patch
from zoneinfo import ZoneInfo
import re
import app
from passenger_features import next_departures_by_line

CITY='Grenoble_France'
NOW=datetime(2026,11,13,10,0,0,tzinfo=ZoneInfo('Europe/Paris'))

class NextByLineTests(unittest.TestCase):
    def setUp(self):self.client=app.app.test_client()

    def test_one_next_per_line_and_direction_skips_past_and_cancelled(self):
        raw=[{'route_id':'r1','route_short_name':'1','trip_headsign':'Gare','departure_time':clock,'cancelled':cancelled} for clock,cancelled in [('09:50:00',False),('10:01:00',True),('10:05:00',False),('10:10:00',False)]]
        raw += [{'route_id':'r1','route_short_name':'1','trip_headsign':'Centre','departure_time':'10:07:00'},{'route_id':'r2','route_short_name':'2','trip_headsign':'Gare','departure_time':'10:06:00'}]
        with patch.object(app,'city_now',return_value=NOW),patch.object(app,'api_get',return_value=raw):
            response=self.client.get(f'/api/{CITY}/departures?stop=S').json
        self.assertEqual([(v['route'],v['headsign'],v['time']) for v in response['next_by_line']],[('1','Gare','10:05:00'),('2','Gare','10:06:00'),('1','Centre','10:07:00')])

    def test_grouping_precedes_global_limit(self):
        raw=[{'route_short_name':'1','departure_time':f'10:{minute:02d}:00'} for minute in range(1,20)]
        raw.append({'route_short_name':'2','departure_time':'10:25:00'})
        with patch.object(app,'city_now',return_value=NOW),patch.object(app,'api_get',return_value=raw):
            response=self.client.get(f'/api/{CITY}/departures?stop=S').json
        self.assertEqual(len(response['items']),12)
        self.assertEqual([v['route'] for v in response['next_by_line']],['1','2'])

    def test_future_date_returns_first_service_and_does_not_merge_distinct_route_ids(self):
        raw=[{'route_id':route,'route_short_name':'1','trip_headsign':'Gare','departure_time':'08:00:00'} for route in ('A','B')]
        with patch.object(app,'city_now',return_value=NOW),patch.object(app,'api_get',return_value=raw):
            values=self.client.get(f'/api/{CITY}/departures?stop=S&date=2026-11-14').json['next_by_line']
        self.assertEqual(len(values),2);self.assertTrue(all(v['minutes'] is None for v in values))

    def test_route_only_response_gets_route_and_direction_context(self):
        with patch.object(app,'city_now',return_value=NOW),patch.object(app,'api_get',return_value=[{'departure_time':'10:05:00'}]):
            item=self.client.get(f'/api/{CITY}/departures?stop=S&route=12&direction=Gare').json['next_by_line'][0]
        self.assertEqual((item['route_id'],item['route'],item['headsign']),('12','12','Gare'))

    def test_stop_page_shows_summary_and_keeps_full_day_collapsed(self):
        raw=[{'route_id':'12','route_short_name':'12','departure_time':clock,'trip_headsign':'Gare'} for clock in ('09:00:00','10:05:00','10:15:00')]
        def upstream(path,params=None):
            if path.startswith('getStops/'):return [{'stop_id':'S','stop_name':'Centre'}]
            if path.startswith('getNextDepartures/'):return raw
            return []
        with patch.object(app,'city_now',return_value=NOW),patch.object(app,'api_get',side_effect=upstream):
            response=self.client.get(f'/city/{CITY}/stop/S?route=12')
        html=response.get_data(as_text=True)
        summary=html.split('<section class="stop-next-departures"',1)[1].split('</section>',1)[0]
        self.assertEqual(summary.count('class="stop-next-card'),1)
        self.assertIn('10:05',summary);self.assertNotIn('09:00',summary)
        full_tag=re.search(r'<details[^>]*id="fullDayTimetable"[^>]*>',html).group()
        self.assertNotIn(' open',full_tag)
        self.assertEqual(len(re.findall(r'<tr class="is-next"',html)),1)

    def test_line_page_lists_stops_without_loading_geometry(self):
        def upstream(path,params=None):
            if path.startswith('getRoutes'):return [{'route_id':'12','route_short_name':'12'}]
            if path.startswith('getStopsByRouteAndDirectionDate'):return [{'stop_id':'S','stop_name':'Centre','stop_lat':45,'stop_lon':5},{'stop_id':'T','stop_name':'Gare','stop_lat':45.1,'stop_lon':5}]
            if path.startswith(('getShape','getTrips')):self.fail('Route geometry must not delay the stop list')
            return []
        with patch.object(app,'api_get',side_effect=upstream):response=self.client.get(f'/city/{CITY}/line/12')
        html=response.get_data(as_text=True)
        self.assertEqual(html.count('class="timeline-stop"'),2)
        self.assertLess(html.index('class="line-layout"'),html.index('id="lineDepartures"'))
        self.assertLess(html.index('class="line-layout"'),html.index('class="line-insights"'))
        insight_tag=re.search(r'<section class="line-insights"[^>]*>',html).group()
        self.assertIn(' hidden',insight_tag)
        insight_section=html.split('<section class="line-insights"',1)[1].split('</section>',1)[0]
        self.assertNotIn('indispon',insight_section.lower())
        self.assertNotIn('id="toggleStops"',html)
        self.assertIn('route=12',html);self.assertIn('#nextDepartures',html)

if __name__=='__main__':unittest.main()
