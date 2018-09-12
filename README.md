# ics2db

Converts ics links to newline-delimited json for upload into an analytics database.

## Install

1. `git clone` and `cd` into this repo
2. `pip install -r requirements.txt`

## Usage

### BigQuery

1. Follow [Google's instructions](https://support.google.com/calendar/answer/37648?hl=en) for "See your calendar (view only)". If you're not able to do this and want this as a features, ping me [@ehfeng](https://twitter.com/ehfeng)
2. `python main.py --calendar-url <GOOGLE CALENDAR SECRET ICAL URL> --json`
3. Upload `calendar_events.json` as a table in BigQuery

## Notes

Only generates up to `now` for infintely recurring events. All recurring events are represented as separate events for simplicity when querying.

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
