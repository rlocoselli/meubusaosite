import unittest
from datetime import date
from journey import Network, active_services

DAY=date(2026,10,9)

def tables():
    stops=[dict(stop_id=id,stop_name=id,stop_lat=45+i*.02,stop_lon=5,wheelchair_boarding='1') for i,id in enumerate('ABCD')]
    trips=[dict(trip_id='t1',route_id='r1',service_id='daily',wheelchair_accessible='1'),dict(trip_id='t2',route_id='r2',service_id='daily',wheelchair_accessible='1')]
    times=[dict(trip_id=trip,stop_id=stop,stop_sequence=i,arrival_time=time,departure_time=time) for trip,rows in [('t1',[('A','10:00:00'),('B','10:10:00')]),('t2',[('B','10:13:00'),('D','10:30:00')])] for i,(stop,time) in enumerate(rows)]
    calendar=[dict(service_id='daily',start_date='20260101',end_date='20261231',**{day:'1' for day in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']})]
    return dict(stops=stops,trips=trips,routes=[dict(route_id='r1',route_short_name='1'),dict(route_id='r2',route_short_name='2')],stop_times=times,calendar=calendar,calendar_dates=[],transfers=[])

class JourneyTests(unittest.TestCase):
    def test_one_transfer_is_timed_and_accessible(self):
        result=Network(tables()).plan('A','D',DAY,9*3600+55*60,True)
        self.assertEqual(result['items'][0]['arrival'],'10:30:00')
        self.assertEqual(result['items'][0]['transfers'],1)
        self.assertEqual([leg['route'] for leg in result['items'][0]['legs']],['1','2'])

    def test_missed_connection_is_rejected(self):
        data=tables();data['stop_times'][2].update(arrival_time='10:11:00',departure_time='10:11:00')
        self.assertFalse(Network(data).plan('A','D',DAY,9*3600)['items'])

    def test_expired_calendar_and_removed_service(self):
        data=tables();data['calendar'][0]['end_date']='20230131'
        self.assertEqual(Network(data).plan('A','D',DAY,9*3600)['reason'],'no_service')
        data=tables();data['calendar_dates']=[dict(service_id='daily',date='20261009',exception_type='2')]
        self.assertFalse(Network(data).plan('A','D',DAY,9*3600)['items'])

    def test_calendar_exception_adds_service(self):
        self.assertEqual(active_services([], [dict(service_id='extra',date='20261009',exception_type='1')], DAY),{'extra'})

    def test_unknown_accessibility_is_not_confirmed(self):
        data=tables();data['trips'][0]['wheelchair_accessible']='0'
        self.assertFalse(Network(data).plan('A','D',DAY,9*3600,True)['items'])
        self.assertTrue(Network(data).plan('A','D',DAY,9*3600)['items'])

    def test_coordinate_approach_and_no_invented_accessibility(self):
        network=Network(tables())
        result=network.plan('45.0001,5','D',DAY,9*3600)
        self.assertEqual(result['items'][0]['legs'][0]['mode'],'walk')
        self.assertTrue(result['items'][0]['legs'][0]['approximate'])
        self.assertFalse(network.plan('45.0001,5','D',DAY,9*3600,True)['items'])

    def test_walking_transfer(self):
        data=tables();data['stops'][2]['stop_lat']=45.0201
        data['stop_times'][2]['stop_id']='C'
        result=Network(data).plan('A','D',DAY,9*3600)
        self.assertEqual([leg['mode'] for leg in result['items'][0]['legs']],['bus','walk','bus'])

    def test_forbidden_transfer(self):
        data=tables();data['transfers']=[dict(from_stop_id='B',to_stop_id='B',transfer_type='3')]
        self.assertFalse(Network(data).plan('A','D',DAY,9*3600)['items'])

    def test_no_pickup_or_dropoff(self):
        data=tables();data['stop_times'][0]['pickup_type']='1'
        self.assertFalse(Network(data).plan('A','D',DAY,9*3600)['items'])
        data=tables();data['stop_times'][-1]['drop_off_type']='1'
        self.assertFalse(Network(data).plan('A','D',DAY,9*3600)['items'])

    def test_previous_service_day_trip_after_midnight(self):
        data=tables();data['trips']=data['trips'][:1];data['stop_times']=data['stop_times'][:2]
        data['stop_times'][0].update(arrival_time='24:10:00',departure_time='24:10:00')
        data['stop_times'][1].update(arrival_time='24:20:00',departure_time='24:20:00')
        result=Network(data).plan('A','B',DAY,5*60)
        self.assertEqual(result['items'][0]['arrival'],'00:20:00')

if __name__=='__main__':unittest.main()
