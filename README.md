# Horoscope Plugin

Display the daily horoscope for your zodiac sign from the free [Horoscope App API](https://horoscope-app-api.vercel.app/).

**→ [Setup Guide](./docs/SETUP.md)** - Configuration instructions

## Overview

The Horoscope plugin fetches the daily reading for one zodiac sign and displays it on your board. It also computes a few sign facts locally (no API call): the sign's symbol name, element, calendar date range, and a lucky number that stays the same all day and differs per sign.

Default display (no template needed):

```
ARIES  SEP 13
Things are moving
quickly for Aries
right now, with new
opportunities coming
up fast. Stay...
```

## Template Variables

```
{{horoscope.horoscope}}     # Full daily reading (up to 264 chars, use with |wrap)
{{horoscope.short}}         # First sentence of the reading (up to 66 chars)
{{horoscope.date}}          # Date the reading is for, e.g. "Sep 13"
{{horoscope.sign}}          # Sign name, e.g. "Aries"
{{horoscope.symbol}}        # Sign symbol, e.g. "The Ram"
{{horoscope.element}}       # Fire / Earth / Air / Water
{{horoscope.date_range}}    # e.g. "Mar 21 - Apr 19"
{{horoscope.lucky_number}}  # 1-99, stable for the day
```

`element` has default color rules: Fire is red, Earth green, Air yellow, Water blue. The color tile is added automatically when you use `{{horoscope.element}}` in a template.

## Example Templates

### Full Reading (Recommended)

```
{center}{{horoscope.sign}} {{horoscope.date}}
{{horoscope.horoscope|wrap}}
```

### Sign Card

```
{center}{{horoscope.sign}} - {{horoscope.symbol}}
{center}{{horoscope.element}} {{horoscope.date_range}}
{center}LUCKY NUMBER {{horoscope.lucky_number}}
{{horoscope.short|wrap}}
```

### Note (3 x 15)

```
{{horoscope.sign}}
{{horoscope.short|wrap}}
```

## Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| enabled | boolean | false | Enable/disable the plugin |
| sign | enum | Aries | One of the 12 zodiac signs |
| day | enum | TODAY | TODAY, TOMORROW or YESTERDAY |
| refresh_seconds | integer | 21600 | Re-fetch interval (min 3600, max 86400) |

The reading only changes once a day, so the default refresh is 6 hours. The minimum is 1 hour to avoid hammering a free service.

## API

This plugin uses the free [Horoscope App API](https://horoscope-app-api.vercel.app/). No API key is required.

```
GET https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily?sign=Aries&day=TODAY
```

The service currently redirects to `freehoroscopeapi.com` and responds with:

```json
{"data": {"date": "2026-09-13", "period": "daily", "sign": "Aries", "horoscope": "..."}}
```

Older deployments returned the text under `data.horoscope_data` with `status`/`success` fields; the plugin reads either key and treats `"success": false` as unavailable.

## Development

```bash
pip install -r requirements-dev.txt
pytest tests/ --cov=. --cov-report=term-missing
```

Tests mock all network calls. See `.github/workflows/ci.yml` for the full CI setup (it checks out FiestaBoard core alongside the plugin).

## Author

FiestaBoard Team
