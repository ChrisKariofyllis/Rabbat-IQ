# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

A household in Germany or Austria sharing one self-hosted install. They match nearby offers to one list.

## Product Purpose

Rabbat-IQ is a self-hosted beta for Germany and Austria. It finds nearby branches and the offers that match that list. Keyword matching is the default. A model and Telegram are optional. Success is a scan that keeps the matches and can send each new match once. Interests, flyer images, and API keys stay on that machine.

## Positioning

The scan is local and idempotent. Keyword matching works with no model key and in both languages. Semantic and vision modes are optional and use credentials the household provides, as does Telegram. The first source is Marktguru; OpenStreetMap fills in a branch a leaflet does not list. Direct chain scrapers can sit beside that source and are not wired in yet.

## Operating Context

The household sets a postal code, country, and radius, adds interests, and chooses Scan now. A scheduler repeats the scan (15–180 minutes, default 30). The web UI shows nearby stores, current flyers, offers, matches, interests, and settings. Telegram, when configured, accepts `/status`, `/interests`, `/add`, `/remove`, `/scan_now`, and `/stores`.

## Capabilities and Constraints

- Geocode the postal code, discover stores inside the radius, fetch flyers and offers, match interests, and notify once per offer, interest, price, and end date.
- Nearby branches include supermarket, discounter, drugstore, and hardware.
- Keyword matching is bilingual. Semantic and vision modes are separate opt-ins and spend the household's own API credit.
- Store discovery prefers the locality named for the postal area, then leaflet branch lists, then OpenStreetMap. The Stores page draws those coordinates on a street map (OpenStreetMap France tiles, no API key), with the search radius and a You marker at the postal code.
- Flyers are labeled local or broader. Offer links prefer a specific product URL and otherwise use the Marktguru offer page.
- Stores can be filtered by chain. Offers can be limited to current interests.
- Stack in this repository: Python 3.11+, FastAPI, Jinja, SQLite, httpx, APScheduler, python-telegram-bot. Optional Docker. Environment prefix `RABBAT_IQ_`.
- The household is responsible for each source’s terms. No remote font host at runtime.
- The interface stays usable with a keyboard and on a narrow phone.

## Brand Commitments

The product name is Rabbat-IQ. Voice is plain and specific. The confirmed visual constraints, recorded without expansion here, are the paper, gold, and green color variables and a top navigation bar over a centered column.

## Evidence on Hand

- Working app under `app/`, with the live SQLite database kept in `data/` and not committed.
- README describes scan behavior, store discovery, flyer scope, and offer links.
- No testimonials, press, pricing, or third-party case studies. Do not invent them.

## Product Principles

- Data and keys stay on the machine that runs the scan.
- The same deal is not announced twice.
- Keyword matching is enough, in either language. Semantic and vision modes are opt-ins.
- Nearby branches and matching offers are the point of the screen.
- Copy names the action and the source. Do not invent claims about retailers.
