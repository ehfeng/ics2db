# ics2db

Converts ics links to newline-delimited json for upload into an analytics database.

## Usage

### BigQuery

1. In Google Calendar, go to the "Calendar settings" and copy the "Secret address in iCal format"
2. `python main.py --calendar-url <GOOGLE CALENDAR SECRET ICAL URL> --json`
3. Upload `calendar_events.json` as a table in BigQuery

## Notes

Does not support endlessly recurring events. Recurring events are represented as separate events for simplicity when querying.

Outputs `calendar_events.csv` or `calendar_events.json`

```yaml
columns:
  id:
    type: string
    description: If event is a recurring event, this will be the same across all events.

  created:
    type: timestamp

  name:
    type: string

  description:
    type: string

  attendees:
    type: string
    mode: repeated

  all_day:
    type: bool

  start:
    type: timestamp

  end:
    type: timestamp

  timezone:
    type: string

  ics:
    type: string
    description: json representation of event in ics format
```
