from copy import copy
import csv
from datetime import datetime
import json

import click
from dateutil.rrule import rrule, MONTHLY, WEEKLY, YEARLY, DAILY
from dateutil.parser import parse
import requests
from icalendar import Calendar, vDatetime
from icalendar.prop import vWeekday

rrule_freq = {
    'WEEKLY': WEEKLY,
    'MONTHLY': MONTHLY,
    'YEARLY': YEARLY,
    'DAILY': DAILY,
}

class BigQueryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(self, obj)


@click.command()
@click.option('--calendar-url', prompt='Calendar URL')
@click.option('--json', 'output_format', flag_value='json', default=True)
@click.option('--sql', 'output_format', flag_value='sql')
def convert(calendar_url, output_format):
    events = []

    calendar = Calendar.from_ical(requests.get(calendar_url).text)
    for component in calendar.subcomponents:
        if component.name == 'VEVENT':
            event = {
                    'id': component['uid'],
                    'name': component['summary'].to_ical().decode('utf-8'),
                    'created': parse(component['created'].to_ical().decode('utf-8')),
                    'description': component['description'].to_ical().decode('utf-8'),
                    'start': parse(component['dtstart'].to_ical().decode('utf-8')),
                    'end': parse(component['dtend'].to_ical().decode('utf-8')),
                    'attendees': [i.to_ical().decode('utf-8') for i in component.get('attendee', [])],
                }
            if 'organizer' in component:
                event['organizer'] = component.get('organizer').to_ical().decode('utf-8')

            if 'rrule' in component:
                assert len(component['rrule']['freq']) == 1, 'An rrule should only have 1 freq argument'
                assert len(component['rrule']['count']) == 1, 'An rrule must have a count argument'
                assert len(component['rrule'].get('interval', [])) <= 1, 'An rrule should only have 1 interval argument'

                rrule_inst = component['rrule']
                rrule_inst['freq'] = rrule_freq.get(rrule_inst['freq'][0])
                rrule_inst['dtstart'] = event['start']

                rrule_inst = {k.lower(): rrule_inst[k] for k in rrule_inst}
                for k in rrule_inst:
                    if k in ('count', 'interval'):
                        rrule_inst[k] = rrule_inst[k][0]
                    if k == 'byday':
                        rrule_inst['byweekday'] = [vWeekday.week_days[i] for i in rrule_inst.pop(k)]

                for rrule_event_start in rrule(**rrule_inst):
                    duration = event['end'] - event['start']
                    rrule_event = copy(event)
                    rrule_event['start'] = rrule_event_start
                    rrule_event['end'] = rrule_event_start + duration
                    events.append(rrule_event)
            else:
                events.append(event)

    if output_format == 'json':
        with open('calendar_events.json', 'w') as f:
            for event in events:
                f.write(json.dumps(event, cls=BigQueryEncoder))
                f.write('\n')


if __name__ == '__main__':
    convert()
