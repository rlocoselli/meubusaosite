"""Schedule-based journey planning; no inferred live service or accessibility."""
from collections import defaultdict
from datetime import timedelta
import csv
import io
import math
import zipfile


def seconds(value):
    try:
        parts = str(value).split(':')
        hour, minute = int(parts[0]), int(parts[1])
        second = int(parts[2]) if len(parts) > 2 else 0
        return hour * 3600 + minute * 60 + second if hour >= 0 and 0 <= minute < 60 and 0 <= second < 60 else None
    except (ValueError, IndexError, TypeError):
        return None


def clock(value):
    value = int(value)
    return f'{value // 3600:02d}:{value % 3600 // 60:02d}:{value % 60:02d}'


def distance(a, b):
    try:
        lat1, lon1, lat2, lon2 = map(float, (a['lat'], a['lon'], b['lat'], b['lon']))
        if not all(math.isfinite(x) for x in (lat1, lon1, lat2, lon2)): return None
        dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        h = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
        return 6371000 * 2 * math.asin(math.sqrt(min(1, h)))
    except (KeyError, ValueError, TypeError):
        return None


def active_services(calendar, exceptions, day):
    stamp = day.strftime('%Y%m%d')
    weekday = ('monday','tuesday','wednesday','thursday','friday','saturday','sunday')[day.weekday()]
    services = {str(row['service_id']) for row in calendar if str(row.get('start_date','')).replace('-','') <= stamp <= str(row.get('end_date','')).replace('-','') and str(row.get(weekday,'0')) == '1'}
    for row in exceptions:
        if str(row.get('date','')).replace('-','') != stamp: continue
        sid = str(row.get('service_id',''))
        if str(row.get('exception_type')) == '1': services.add(sid)
        elif str(row.get('exception_type')) == '2': services.discard(sid)
    return services


def load_zip(path):
    with zipfile.ZipFile(path) as archive:
        def table(name):
            filename = next((entry for entry in archive.namelist() if entry.split('/')[-1] == name), None)
            if not filename: return []
            with archive.open(filename) as stream:
                return list(csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig', newline='')))
        return {key:table(key+'.txt') for key in ('stops','routes','trips','stop_times','calendar','calendar_dates','transfers','frequencies')}


class Network:
    def __init__(self, tables):
        self.stops = {}
        for raw in tables['stops']:
            try: lat, lon = float(raw.get('stop_lat')), float(raw.get('stop_lon'))
            except (TypeError, ValueError): lat, lon = None, None
            self.stops[str(raw['stop_id'])] = dict(id=str(raw['stop_id']), name=raw.get('stop_name') or str(raw['stop_id']), lat=lat, lon=lon, wheelchair=str(raw.get('wheelchair_boarding','0')))
        # GTFS stop accessibility can be inherited from a parent station.
        for raw in tables['stops']:
            stop = self.stops[str(raw['stop_id'])]
            parent = self.stops.get(str(raw.get('parent_station','')))
            if stop['wheelchair'] in ('','0') and parent: stop['wheelchair'] = parent['wheelchair']
        self.routes = {str(row['route_id']):row for row in tables['routes']}
        self.calendar, self.exceptions = tables['calendar'], tables['calendar_dates']
        self.trips = {str(row['trip_id']):dict(row, times=[]) for row in tables['trips']}
        self.frequency_trips = {str(row['trip_id']) for row in tables.get('frequencies',[])}
        for raw in tables['stop_times']:
            trip = self.trips.get(str(raw.get('trip_id','')))
            arrival, departure = seconds(raw.get('arrival_time')), seconds(raw.get('departure_time'))
            if trip is None or arrival is None or departure is None or arrival>departure or str(raw.get('stop_id')) not in self.stops: continue
            try: sequence = int(raw.get('stop_sequence',0))
            except (ValueError, TypeError): continue
            trip['times'].append(dict(stop=str(raw['stop_id']), arrival=arrival, departure=departure, sequence=sequence, pickup=str(raw.get('pickup_type','0') or '0'), dropoff=str(raw.get('drop_off_type','0') or '0')))
        for trip in self.trips.values(): trip['times'].sort(key=lambda row:row['sequence'])
        self.transfers = {(str(row.get('from_stop_id')),str(row.get('to_stop_id'))):row for row in tables.get('transfers',[]) if not any(row.get(key) for key in ('from_trip_id','to_trip_id','from_route_id','to_route_id'))}
        self.complex_transfers = any(any(row.get(key) for key in ('from_trip_id','to_trip_id','from_route_id','to_route_id')) for row in tables.get('transfers',[]))
        self.buckets = defaultdict(list)
        for sid, stop in self.stops.items():
            if stop['lat'] is not None and stop['lon'] is not None and math.isfinite(stop['lat']) and math.isfinite(stop['lon']):
                self.buckets[(int(stop['lat']*200), int(stop['lon']*200))].append(sid)

    def neighbors(self, sid):
        stop = self.stops[sid]
        if stop['lat'] is None or stop['lon'] is None: return []
        cell = (int(stop['lat']*200), int(stop['lon']*200))
        # Longitude grid width varies with latitude.
        width = min(100, math.ceil(1/max(.01, math.cos(math.radians(stop['lat'])))))
        result = []
        for x in range(cell[0]-1,cell[0]+2):
            for y in range(cell[1]-width,cell[1]+width+1):
                for other in self.buckets.get((x,y),[]):
                    if other == sid: continue
                    meters = distance(stop,self.stops[other])
                    transfer = self.transfers.get((sid,other),{})
                    if str(transfer.get('transfer_type')) == '3': continue
                    if meters is not None and meters <= 250:
                        try: minimum = int(transfer.get('min_transfer_time',0) or 0)
                        except ValueError: minimum = 0
                        result.append((other,max(60,math.ceil(meters/1.2),minimum),round(meters)))
        return result

    def endpoints(self, value, accessible=False):
        if value in self.stops:
            stop=self.stops[value]
            return [(value,0,0)] if not accessible or stop['wheelchair']=='1' else []
        try:
            lat,lon = map(float,value.split(','))
            if not math.isfinite(lat) or not math.isfinite(lon) or abs(lat)>90 or abs(lon)>180: raise ValueError()
        except (ValueError, AttributeError): raise ValueError('invalid_endpoint')
        # Accessibility of arbitrary pedestrian approaches cannot be confirmed.
        if accessible: return []
        candidates=[]
        for sid,stop in self.stops.items():
            meters=distance(dict(lat=lat,lon=lon),stop)
            if meters is not None and meters <= 800: candidates.append((sid,max(0,math.ceil(meters/1.2)),round(meters)))
        return sorted(candidates,key=lambda row:row[1])[:8]

    def plan(self, origin, destination, day, start, accessible=False):
        services=active_services(self.calendar,self.exceptions,day)
        yesterday=active_services(self.calendar,self.exceptions,day-timedelta(days=1))
        if not services and not yesterday: return dict(items=[], reason='no_service')
        if self.complex_transfers: return dict(items=[],reason='unsupported_transfers')
        origins,targets=self.endpoints(origin,accessible),self.endpoints(destination,accessible)
        if not origins or not targets: return dict(items=[],reason='no_stops')
        horizon=start+12*3600
        eligible=[(tid,trip) for tid,trip in self.trips.items() if str(trip.get('service_id')) in services and tid not in self.frequency_trips and (not accessible or str(trip.get('wheelchair_accessible'))=='1')]
        for tid,trip in self.trips.items():
            if str(trip.get('service_id')) in yesterday and tid not in self.frequency_trips and (not accessible or str(trip.get('wheelchair_accessible'))=='1'):
                shifted=[dict(row,arrival=row['arrival']-86400,departure=row['departure']-86400) for row in trip['times']]
                if shifted and shifted[-1]['arrival']>=start:eligible.append((tid+'@previous-day',dict(trip,times=shifted)))
        labels={}
        for sid,duration,meters in origins:
            legs=[] if not duration else [dict(mode='walk',from_id=None,to_id=sid,from_name=origin,to_name=self.stops[sid]['name'],departure=clock(start),arrival=clock(start+duration),distance=meters,approximate=True)]
            labels[sid]=(start+duration,legs)
        journeys=[]
        target_map={sid:(duration,meters) for sid,duration,meters in targets}
        def collect(current):
            best=None
            for sid,(duration,meters) in target_map.items():
                if sid not in current: continue
                arrival,legs=current[sid]
                if duration: legs=legs+[dict(mode='walk',from_id=sid,to_id=None,from_name=self.stops[sid]['name'],to_name=destination,departure=clock(arrival),arrival=clock(arrival+duration),distance=meters,approximate=True)]
                if best is None or arrival+duration<best[0]:best=(arrival+duration,legs)
            if best and best[0]<=horizon:
                buses=sum(leg['mode']=='bus' for leg in best[1])
                result=dict(departure=clock(start),arrival=clock(best[0]),duration=math.ceil((best[0]-start)/60),transfers=max(0,buses-1),legs=best[1])
                if not any(result['legs']==item['legs'] for item in journeys): journeys.append(result)
        collect(labels)
        for round_index in range(3):
            updated=dict(labels)
            for tid,trip in eligible:
                board=None
                for index,row in enumerate(trip['times']):
                    sid=row['stop']
                    if accessible and self.stops[sid]['wheelchair']!='1': continue
                    if board is not None and row['dropoff']=='0':
                        board_index,previous_legs=board
                        first=trip['times'][board_index]
                        if first['departure'] <= row['arrival'] <= horizon and (sid not in updated or row['arrival']<updated[sid][0]):
                            route=self.routes.get(str(trip.get('route_id')), {})
                            leg=dict(mode='bus',trip_id=tid,route_id=str(trip.get('route_id','')),route=route.get('route_short_name') or str(trip.get('route_id','')),headsign=trip.get('trip_headsign',''),from_id=first['stop'],to_id=sid,from_name=self.stops[first['stop']]['name'],to_name=self.stops[sid]['name'],departure=clock(first['departure']),arrival=clock(row['arrival']),wheelchair=str(trip.get('wheelchair_accessible','0')))
                            updated[sid]=(row['arrival'],previous_legs+[leg])
                    if board is None and sid in labels and row['pickup']=='0' and row['departure']>=labels[sid][0] and row['departure']<=horizon:
                        previous_legs=labels[sid][1]
                        last_bus=next((leg for leg in reversed(previous_legs) if leg['mode']=='bus'),None)
                        if last_bus and last_bus['trip_id']!=tid:
                            transfer=self.transfers.get((last_bus['to_id'],sid),{})
                            if str(transfer.get('transfer_type'))=='3':continue
                            try: buffer=max(120,int(transfer.get('min_transfer_time',0) or 0))
                            except ValueError: buffer=120
                            if row['departure']<labels[sid][0]+buffer:continue
                        board=(index,previous_legs)
            # One nearby-stop walking connection between boardings; no invented street path.
            if not accessible:
                walked=dict(updated)
                for sid,(arrival,legs) in updated.items():
                    if not legs or legs[-1]['mode']!='bus':continue
                    for other,duration,meters in self.neighbors(sid):
                        if other not in walked or arrival+duration<walked[other][0]:
                            leg=dict(mode='walk',from_id=sid,to_id=other,from_name=self.stops[sid]['name'],to_name=self.stops[other]['name'],departure=clock(arrival),arrival=clock(arrival+duration),distance=meters,approximate=True)
                            walked[other]=(arrival+duration,legs+[leg])
                updated=walked
            collect(updated)
            labels=updated
        return dict(items=sorted(journeys,key=lambda item:(item['duration'],item['transfers']))[:3],reason=None if journeys else 'no_journey',frequency_trips_skipped=bool(self.frequency_trips))
