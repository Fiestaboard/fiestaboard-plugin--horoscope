# Horoscope Setup

Show the daily horoscope for your zodiac sign on your board, using the free [Horoscope API](https://freehoroscopeapi.com/).

## Overview

**What it does:**
- Fetches the daily reading for one zodiac sign you pick
- Also gives you the sign's symbol, element, date range, and a lucky number (all computed locally — no extra API calls)
- No API key required

**Prerequisites:**
- Internet connection (to reach `freehoroscopeapi.com`)
- No API key needed — the service is free and open

## Quick Setup

### 1. Enable the Plugin

**Option A: Web UI**
1. Go to **Integrations** and find "Horoscope"
2. Toggle **Enable Horoscope** to on
3. Click **Save Changes**

**Option B: Environment Variable**

Add to your `.env` file:
```bash
HOROSCOPE_ENABLED=true
```

### 2. Configure

Click **Configure** and fill in:

- **Zodiac Sign** — Pick one of the 12 signs. This is the only sign the plugin fetches.
- **Day** — `TODAY` (default), `TOMORROW`, or `YESTERDAY`.
- **Refresh Interval** — How often to re-fetch, in seconds. Default `21600` (6 hours), minimum `3600` (1 hour). The text only changes once a day, so there is no reason to go lower.

### 3. Use in Templates

Available variables:

- `{{horoscope.horoscope}}` — The full daily reading (up to 264 chars — use with `|wrap`)
- `{{horoscope.short}}` — Just the first sentence (up to 66 chars)
- `{{horoscope.date}}` — The date the reading is for, e.g. `Sep 13`
- `{{horoscope.sign}}` — The sign name, e.g. `Aries`
- `{{horoscope.symbol}}` — The sign's symbol, e.g. `The Ram`
- `{{horoscope.element}}` — `Fire`, `Earth`, `Air`, or `Water`
- `{{horoscope.date_range}}` — e.g. `Mar 21 - Apr 19`
- `{{horoscope.lucky_number}}` — A number from 1 to 99, the same all day, different for each sign

### 4. Example Templates

**Full reading:**
```
{center}{{horoscope.sign}} {{horoscope.date}}
{{horoscope.horoscope|wrap}}
```

**Sign card:**
```
{center}{{horoscope.sign}} - {{horoscope.symbol}}
{center}{{horoscope.element}} {{horoscope.date_range}}
{center}LUCKY NUMBER {{horoscope.lucky_number}}
{{horoscope.short|wrap}}
```

**Note (3 x 15):**
```
{{horoscope.sign}}
{{horoscope.short|wrap}}
```

**Tip:** `|wrap` word-wraps the reading across the remaining lines of the page. Without it, long text is cut off at the end of the line.

### Colors

`{{horoscope.element}}` comes with default color rules, so the element shows up with a matching color tile:

| Element | Color |
|---------|-------|
| Fire | Red |
| Earth | Green |
| Air | Yellow |
| Water | Blue |

You can change these under the page's color rules.

## Configuration Reference

| Setting | Type | Required | Default | Description |
|---------|------|----------|---------|-------------|
| `enabled` | boolean | No | `false` | Enable or disable the plugin |
| `sign` | enum | Yes | `Aries` | One of the 12 zodiac signs |
| `day` | enum | No | `TODAY` | `TODAY`, `TOMORROW`, or `YESTERDAY` |
| `refresh_seconds` | integer | No | `21600` | Re-fetch interval (min `3600`, max `86400`) |

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HOROSCOPE_ENABLED` | No | `false` | Enable the horoscope feature |

## Display Example

With no template at all, the plugin shows this built-in page:

```
ARIES  SEP 13
Things are moving
quickly for Aries
right now, with new
opportunities coming
up fast. Stay...
```

The header is the sign and date; the reading is word-wrapped across the remaining lines and truncated with `...` if it does not fit.

## API Information

- **Endpoint:** `GET https://freehoroscopeapi.com/api/v1/get-horoscope/daily?sign=Aries&day=TODAY`
- **Authentication:** None required
- **Rate limits:** None published, but it is a free community service — please leave the refresh interval at 6 hours or higher
- **Format:** JSON

### Sample API Response

```json
{
  "data": {
    "date": "2026-09-13",
    "period": "daily",
    "sign": "Aries",
    "horoscope": "Things are moving quickly for Aries right now, with new opportunities and experiences coming up fast..."
  }
}
```

## Troubleshooting

### Nothing Shows on the Board

1. **Check if enabled:**
   ```bash
   grep HOROSCOPE_ENABLED .env
   # Should show: HOROSCOPE_ENABLED=true
   ```

2. **Check logs:**
   ```bash
   docker-compose logs | grep -i horoscope
   ```

3. **Check the API is reachable:**
   ```bash
   curl -L "https://freehoroscopeapi.com/api/v1/get-horoscope/daily?sign=Aries&day=TODAY"
   ```

### Plugin Shows "Not Available"

- The free service occasionally goes down or rate-limits. The plugin will pick the reading back up on the next refresh.
- Make sure your network/firewall allows outbound HTTPS.

### The Reading Looks Cut Off

The full reading can run well past 264 characters. The plugin trims it to 264 with a trailing `...` so it fits a 6 x 22 board. Use `{{horoscope.short}}` if you only want the first sentence.

## Restart After Changes

After changing Horoscope settings, restart the service:

```bash
docker-compose restart
docker-compose logs -f
```

## Summary

- **Enable:** `HOROSCOPE_ENABLED=true`
- **Pick your sign** in the plugin config
- **Use in pages:** `{{horoscope.horoscope|wrap}}`
- **No API key needed**
