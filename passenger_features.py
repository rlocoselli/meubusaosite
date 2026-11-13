"""Derived passenger information from complete, dated transit schedules."""
from datetime import datetime, timedelta
from journey import active_services


def journey_metrics(journey):
    walking = sum(float(leg.get('distance') or 0) for leg in journey['legs'] if leg.get('mode') == 'walk')
    return {**journey, 'walking_meters': round(walking), 'walking_minutes': sum(max(0, round((_clock(leg['arrival'])-_clock(leg['departure']))/60)) for leg in journey['legs'] if leg.get('mode') == 'walk')}


def _clock(value):
    h,m,*s=map(int,value.split(':'))
    return h*3600+m*60+(s[0] if s else 0)


def compare_journeys(network, origin, destination, day, start, accessible=False):
    alternatives, reason = {}, None
    for preference in ('fastest','less_walking','fewest_transfers'):
        result = network.plan(origin,destination,day,start,accessible,preference=preference)
        reason = result.get('reason')
        for value in result['items']:
            item=journey_metrics(value)
            key=tuple((leg['mode'],leg.get('trip_id'),leg.get('from_id'),leg.get('to_id'),leg['departure'],leg['arrival']) for leg in item['legs'])
            alternatives.setdefault(key,item)
    items=sorted(alternatives.values(),key=lambda item:(item['duration'],item['transfers'],item['walking_meters']))
    if items:
        best={
            'fastest':min(items,key=lambda item:(item['duration'],item['transfers'],item['walking_meters'])),
            'less_walking':min(items,key=lambda item:(item['walking_meters'],item['duration'],item['transfers'])),
            'fewest_transfers':min(items,key=lambda item:(item['transfers'],item['duration'],item['walking_meters']))}
        selected=[]
        for item in best.values():
            if item not in selected:selected.append(item)
        for item in items:
            if item not in selected:selected.append(item)
        items=selected[:6]
        for item in items:item['highlights']=[name for name,value in best.items() if item is value]
    return dict(items=items,reason=None if items else reason)


def last_scheduled_services(network,stop_id,day,timezone,route_id=''):
    """Never infer an end of service from a truncated next-departure response."""
    services=active_services(network.calendar,network.exceptions,day)
    last,uncertain={},set()
    for tid,trip in network.trips.items():
        route=str(trip.get('route_id',''))
        if str(trip.get('service_id')) not in services or (route_id and route!=route_id):continue
        headsign=str(trip.get('trip_headsign',''))
        key=(route,headsign)
        at_stop=[row for row in trip['times'] if row['stop']==stop_id and row['pickup']=='0']
        if not at_stop:continue
        if tid in network.frequency_trips:
            uncertain.add(key);continue
        for row in at_stop:
            if key not in last or row['departure']>last[key]:last[key]=row['departure']
    midnight=datetime.combine(day,datetime.min.time(),tzinfo=timezone)
    result=[]
    for (route,headsign),departure in last.items():
        if (route,headsign) in uncertain:continue
        moment=midnight+timedelta(seconds=departure)
        route_data=network.routes.get(route,{})
        result.append(dict(route_id=route,route=route_data.get('route_short_name') or route,headsign=headsign,time=moment.strftime('%H:%M'),departure_at=int(moment.timestamp()*1000),day_offset=departure//86400,scheduled=True))
    return sorted(result,key=lambda item:item['departure_at'])
