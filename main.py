from copy import copy
import csv
from datetime import datetime
import json

import click
from dateutil.rrule import (
    rrule,
    MONTHLY, WEEKLY, YEARLY, DAILY,
    MO, TU, WE, TH, FR, SA, SU,
)
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

rrule_weekdays = {
    'MO': MO,
    'TU': TU,
    'WE': WE,
    'TH': TH,
    'FR': FR,
    'SA': SA,
    'SU': SU,
}

class BigQueryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(self, obj)


@click.command()
@click.option('--calendar-url', prompt='Calendar URL')
@click.option('--calendar-name', prompt='Calendar Name')
@click.option('--json', 'output_format', flag_value='json', default=True)
@click.option('--sql', 'output_format', flag_value='sql')
def convert(calendar_url, calendar_name, output_format):
    events = []

    calendar = Calendar.from_ical(requests.get(calendar_url).text)
    for component in calendar.subcomponents:
        attendees = []
        if component.get('attendee'):
            if isinstance(component['attendee'], str):
                attendees = [component['attendee']]
            else:
                for a in component['attendee']:
                    if isinstance(a, str):
                        attendees.append(a)
                    else:
                        attendees.append(i.to_ical().decode('utf-8'))

        if component.name == 'VEVENT':
            event = {
                'id': component['uid'],
                'calendar': calendar_name,
                'name': component['summary'].to_ical().decode('utf-8'),
                'created': parse((component['created'] or component['dtstart']).to_ical().decode('utf-8')),
                'description': component['description'].to_ical().decode('utf-8') if 'description' in component else '',
                'start': parse(component['dtstart'].to_ical().decode('utf-8')),
                'end': parse(component['dtend'].to_ical().decode('utf-8')) if 'dtend' in component else parse(component['dtstart'].to_ical().decode('utf-8')),
                'attendees': attendees,
                }
            # if 'organizer' in component:
            #     event['organizer'] = component.get('organizer').to_ical().decode('utf-8')

            if 'rrule' in component:
                if not isinstance(component['rrule']['freq'], str) and len(component['rrule']['freq']) != 1:
                    print('An rrule should only have 1 freq argument', component.to_ical())
                    break

                rrule_inst = component['rrule']
                rrule_inst['freq'] = rrule_freq.get(rrule_inst['freq'][0])
                rrule_inst['dtstart'] = event['start']

                rrule_inst = {k.lower(): rrule_inst[k] for k in rrule_inst}
                for k in rrule_inst:
                    if k in ('count', 'interval', 'until', 'wkst'):
                        rrule_inst[k] = rrule_inst[k][0]

                        if isinstance(rrule_inst[k], datetime):
                            rrule_inst[k] = rrule_inst[k].replace(tzinfo=None)
                        if k == 'wkst':
                            rrule_inst[k] = rrule_weekdays[rrule_inst[k]]

                    if k == 'byday':
                        rrule_inst['byweekday'] = rrule_inst.pop(k)
                        new_byweeday = []
                        for i in rrule_inst['byweekday']:
                            if len(i) > 2:
                                try:
                                    i_int = int(i[:-2])
                                except:
                                    print('Not a valid rrule', rrule_inst)
                                    break
                                new_byweeday.append(rrule_weekdays[i[-2:]](i_int))
                            else:
                                new_byweeday.append(vWeekday.week_days[i])

                        rrule_inst['byweekday'] = new_byweeday

                rrule_inst['until'] = min(rrule_inst.get('until', datetime.now()), datetime.now())
                for rrule_event_start in rrule(**rrule_inst):
                    if rrule_event_start < datetime.now():
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
    elif output_format == 'sql':
        with open('calendar_events.sql', 'w') as f:
            column_names = events[0].keys()
            column_names_str = ','.join(['"' + k + '"' for k in column_names])
            values_list = []
            for event in events:
                values = []
                for column_name in column_names:
                    value = event.get(column_name)

                    if not value:
                        values.append('null')
                    elif isinstance(value, str):
                        value = value.replace("'", '"')
                        value = value.replace("\\", '\\\\')
                        value = value.encode('ascii','replace').decode('utf-8')
                        values.append('E\'{}\''.format(value))
                    elif isinstance(value, datetime):
                        values.append('\'{}\'::timestamp'.format(value))
                    elif isinstance(value, list):
                        values.append('\'{{\"{}\"}}\''.format('\", \"'.join(value)))
                    else:
                        values.append(str(value))

                values_list.append("(" + ','.join(values) + ")")

            # f.write('create schema if not exists google_calendar;\n')
            # f.write('drop table google_calendar.events;\n')
            # f.write('create table if not exists google_calendar.events ( id text, calendar text, created timestamp, name text, description text, attendees text[], all_day bool, start timestamp, "end" timestamp, timezone text);\n')
            f.write('insert into google_calendar.events ({}) values \n{};'.format(column_names_str, ',\n'.join(values_list)))


if __name__ == '__main__':
    convert()
