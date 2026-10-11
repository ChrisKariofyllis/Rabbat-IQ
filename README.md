# Rabbat-IQ

Rabbat-IQ is a self-hosted tool that watches supermarket offers near a postal code and tells you when something matches what you actually buy. Interests, flyer images, and API keys stay on your machine. The model and the Telegram bot are optional, and both use credentials you provide.

It is aimed at Germany and Austria. The first data source is [Marktguru](https://www.marktguru.de/). Direct chain scrapers can be added beside it.

## What a scan does

1. Turns your postal code into a place (Marktguru’s location search, then OpenStreetMap Nominatim if that fails).
2. Loads current leaflets for that postal code and keeps supermarket, discounter, drugstore, and hardware branches inside your radius.
3. Searches offers for each interest.
4. Matches them locally by keyword, or with your own vision/chat model if you turn that on.
5. Saves new matches and, when Telegram is configured, sends each one once.

The same offer, interest, price, and end date are not sent again.

## How nearby stores are found

Marktguru’s location search returns every locality that shares a postal code, and the first hit is often a hamlet on the edge. Rabbat-IQ averages those points into one postal-code center (for 93161 that is the Sinzing area, not the first village alone). Nominatim is used only when Marktguru returns no coordinates.

Leaflets are loaded for that postal code. Branches come from Marktguru’s store list on each leaflet, up to four leaflets per chain and not only the booklet with the most offers. A national or regional booklet can list a branch in the next town, while a smaller booklet for the same chain lists the local one. Each branch is measured from the postal-code center. It is kept when that distance is inside the radius you set, then duplicates are dropped in favor of the nearest.

A chain can still be absent. If its closest branch in Marktguru’s lists is farther than the radius, it is left off the Stores page. Raising the radius in Settings is the way to include it. The map is a relative plot of those saved branches, not a street map.

## Flyer scope

Flyers are the leaflets Marktguru returns for your postal code. They are not a dump of every German leaflet. Each one is labeled:

- **Local** — one booklet (`spreadLeaflet` is false and `leafletCount` is 1). This is the tighter match for your area.
- **Broader** — a spread campaign, or a flight that stacks more than one leaflet. The offers still reach your postal code, and the same booklet is shared across many stores.

Local booklets are listed first. Broader ones stay on the page because weekly chain offers often live in those shared campaigns.

## Run with Docker

```bash
docker compose up --build
```

Open http://127.0.0.1:8787. The compose file binds that port to localhost. The SQLite database lives in the `rabbat-iq-data` volume.

Then:

1. Set a postal code, country, and radius under Settings.
2. Add interests such as `Greek yogurt`, `beer`, or `Werkzeugkasten`.
3. Choose Scan now.

The scheduler repeats the scan on the interval you set (15–180 minutes, default 30). The first automatic run happens within about a minute after a postal code and at least one interest are saved.

## Run without Docker

Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --host 127.0.0.1 --port 8642
```

Open http://127.0.0.1:8642.

Copy `.env.example` to `.env` if you want a different database path, HTTP basic auth, or your own Marktguru keys. Shopping settings are edited in the web UI and stored in SQLite, not in the env file.

## Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather) and paste the token into Settings.
2. Open the bot and send `/start`. It replies with your chat id.
3. Save that chat id. From then on, only that chat can use the bot.

Commands: `/status`, `/interests`, `/add beer`, `/remove beer`, `/scan_now`, `/stores`.

Alerts include the product, price, store, validity, why it matched, and a picture when the source has one. Unsent matches are retried on a later scan, up to three attempts.

## AI providers

Keyword matching works with no key. It understands a short bilingual grocery list (`beer` / `Bier`, `yogurt` / `Joghurt`, `tools` / `Werkzeug`) and otherwise looks for your words. The same list is used to build the Marktguru query, so an English interest still searches the German index. “beer” is searched as Bier or Pils, because that index stems the English word into Beeren (berries).

| Provider | Default model | Key |
| --- | --- | --- |
| OpenAI | `gpt-4o-mini` | Your OpenAI API key |
| Gemini | `gemini-2.5-flash` | Your Gemini API key |
| Anthropic | `claude-haiku-4-5` | Your Anthropic API key |
| Ollama | `llava` | None. Set the base URL, usually `http://127.0.0.1:11434` |

Semantic mode asks the model which offers fit, including the same product in another language. Vision mode sends flyer covers (not every page) up to the page budget in Settings. Both are off until you opt in, because they spend your API credit. Results are cached locally so the same page is not billed twice.

The model is asked to return:

```json
{
  "matches": [
    {
      "interest": "Greek yogurt",
      "offer_id": "25289747",
      "product": "Joghurt",
      "price": "0.59",
      "original_price": "0.89",
      "discount": "−34%",
      "store": "Kaufland",
      "valid_from": "12 Oct",
      "valid_to": "18 Oct",
      "confidence": 0.86,
      "reason": "Griechischer Joghurt matches Greek yogurt"
    }
  ]
}
```

## Configuration

Environment variables use the `RABBAT_IQ_` prefix. See `.env.example`.

| Variable | Purpose |
| --- | --- |
| `RABBAT_IQ_DATABASE_URL` | SQLite URL. Default `sqlite:///./data/rabbat-iq.db` |
| `RABBAT_IQ_DATA_DIR` | Key cache and other local files |
| `RABBAT_IQ_BASIC_AUTH_USER` / `PASSWORD` | Optional password for the web UI |
| `RABBAT_IQ_MARKTGURU_API_KEY` / `CLIENT_KEY` | Optional. Otherwise keys are read from the public homepage and cached for 12 hours |
| `RABBAT_IQ_POSTAL_CODE` / `COUNTRY` | Used only when the database is first created |

If you publish the port beyond localhost, set the basic-auth variables.

## Adding a source

`app/adapters/base.py` describes the interface: geocode, leaflets, nearby stores, and offer search. `app/adapters/chain_template.py` is a copy-ready skeleton. Register the class from `app/adapters/registry.py` and include it in `build` / the scan’s source list.

A new adapter should identify itself with a clear User-Agent, wait between requests, and cache work it has already done. Read the site’s robots.txt and terms first. Do not bypass logins or other access controls.

## Privacy

- Interests, matches, and keys are in the local SQLite file.
- Marktguru is contacted only to load public offer data for the postal code you set.
- Nominatim is contacted only when Marktguru cannot locate that postal code.
- Your AI key is sent only to the provider you select.
- Telegram receives a match only when a token and chat id are saved.
- The UI sends `noindex` and `robots.txt` disallows crawlers. It is a personal tool, not a public site.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Legal

Rabbat-IQ is an unofficial, personal, self-hosted client. You are responsible for complying with the terms of Marktguru and of any site you add a scraper for. Prefer the public aggregator API. This project does not ship scrapers for Lidl, Aldi, Rewe, or other chains.

Offer text, prices, and images remain the property of their sources. The relative store map is computed locally and does not load map tiles.

## Layout

```
app/
  main.py                 web process, auth, security headers
  scheduler.py            interval taken from settings
  adapters/               Marktguru, plus a scraper template
  ai/                     keyword matcher and model clients
  notifications/          Telegram alerts
  bot/                    /status, /add, /scan_now, and the rest
  services/               database and the scan pipeline
  web/                    pages, CSS, and the scan poller
```
