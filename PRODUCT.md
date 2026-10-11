# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Someone in Germany or Austria who wants supermarket offers near a postal code matched to a personal shopping list. They run Rabbat-IQ on their own machine. (Inferred: the usual moment is checking what is on offer before a shop, on a phone or a laptop at home.)

## Product Purpose

Rabbat-IQ watches leaflets and offers near a postal code and reports the ones that match interests the person actually buys. Success is a scan that finds the nearby branches, keeps the matching offers, and can send each new match once. Interests, flyer images, and API keys stay on that machine.

## Positioning

The scan is local and idempotent. Keyword matching works with no model key. A model and a Telegram bot are optional and use credentials the person provides. The first source is Marktguru; OpenStreetMap fills in a branch a leaflet does not list. Direct chain scrapers can sit beside that source and are not wired in yet.

## Operating Context

The person sets a postal code, country, and radius, adds interests, and chooses Scan now. A scheduler repeats the scan (15–180 minutes, default 30). The web UI shows nearby stores, current flyers, offers, matches, interests, and settings. Telegram, when configured, accepts `/status`, `/interests`, `/add`, `/remove`, `/scan_now`, and `/stores`.

## Capabilities and Constraints

- Geocode the postal code, discover stores inside the radius, fetch flyers and offers, match interests, and notify once per offer, interest, price, and end date.
- Store discovery prefers the locality named for the postal area, then leaflet branch lists, then OpenStreetMap. The map is a relative plot, not a street map.
- Flyers are labeled local or broader. Offer links prefer a specific product URL and otherwise use the Marktguru offer page.
- Stores can be filtered by chain. Offers can be limited to current interests.
- Stack in this repository: Python 3.11+, FastAPI, Jinja, SQLite, httpx, APScheduler, python-telegram-bot. Optional Docker. Environment prefix `RABBAT_IQ_`.
- The person is responsible for each source’s terms. No remote font host at runtime.
- The interface stays usable with a keyboard and on a narrow phone. (Confirmed by the request to keep the app functional and mobile-friendly.)

## Brand Commitments

The product name is Rabbat-IQ. Voice is plain and specific. The confirmed visual constraints, recorded without expansion here, are the paper, gold, and green color variables and a top navigation bar over a centered column.

## Evidence on Hand

- Working app under `app/`, with the live SQLite database kept in `data/` and not committed.
- README describes scan behavior, store discovery, flyer scope, and offer links.
- No testimonials, press, pricing, or third-party case studies. Do not invent them.

## Product Principles

- Data and keys stay on the machine that runs the scan.
- The same deal is not announced twice.
- Keyword matching is enough; a model is an opt-in.
- Nearby branches and matching offers are the point of the screen.
- Copy names the action and the source. Do not invent claims about retailers.
