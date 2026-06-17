# Mapah-Hechsher-Map
A community‑driven kosher‑restaurant map. Users can add places, upload kashrus certificates, and search places by hechsher on an interactive map. Includes AI certificate scanning and post screening. Supports English and Hebrew. 

מַפָּה — Hechsher Map Platform — Project Overview

A full‑stack, map‑based web application that crowdsources kosher restaurant and eatery information and validates it through certificate uploads, AI data extraction, and structured moderation. The platform overlays user‑verified kosher data on top of a general restaurant POI layer, enabling people to quickly find reliable, up‑to‑date kashrut information in both Hebrew and English.

1. Vision and Core Concept

The platform provides a Google‑Maps‑style interface where users can:

explore restaurants on an interactive map

view kosher certificates and hechshers

search nearby places by hechsher

submit new places or add kosher info to existing POIs

rely on AI‑assisted validation for accuracy

browse in Hebrew or English

The goal is to create a trustworthy, community‑driven source of kosher information with minimal friction for contributors and strong protections against vandalism.

2. Tech Stack

Frontend

React (SPA)

Mapbox GL JS for interactive maps

React Query for data fetching and caching

react‑i18next for bilingual UI (Hebrew/English)

Responsive drawer/sidebar UI (Google Maps–style)

Local Storage for device‑level preferences

Cloudflare Turnstile for spam prevention

Browser geolocation for submission location accuracy

Backend

FastAPI (Python)

PostgreSQL (primary database)

SQLAlchemy / Pydantic for models and validation

Render for deployment

Render Static Bucket for public certificate storage

AI / Automation

Vision model for:

extracting hechsher name

detecting expiration date

reading restaurant name from certificate

Text moderation model for:

spam detection

profanity / nonsense filtering

edit‑risk scoring

External Data

Mapbox Search API for preloading restaurant POIs

Mapbox Tiles for base map

Mapbox Geocoding for search/autocomplete

3. Data Model

Eatery

id

name_original

name_hebrew (optional)

name_english (optional)

aliases (list)

coordinates

address

source (“user” or “mapbox”)

status (“pending”, “approved”, “rejected”)

Kosher Info

eatery_id

hechsher_id

eatery_type (meat, dairy, parve)

certificate_url

certificate_expiration

certificate_detected_hechsher

certificate_confidence

validated (boolean)

Hechsher

id

display_name

logo_url

aliases (list)

is_verified

Submission / Edit

id

eatery_id

type (“submission” or “edit”)

diff (for edits)

certificate_url (if provided)

moderation_score

status (“pending”, “approved”, “rejected”)

4. Data Flow

A. Viewing the Map

User opens the app.

Mapbox loads the base map.

App preloads restaurant POIs from Mapbox Search API.

App overlays approved kosher listings from PostgreSQL.

User taps a POI → sidebar opens with details.

B. Submitting a New Listing

User taps a POI or adds a new marker.

User fills out the submission form.

User uploads a certificate (optional but encouraged).

Certificate is uploaded to public storage.

Backend runs vision extraction → autofills hechsher + expiration.

Submission enters moderation queue.

If approved → appears on map.

C. Editing an Existing Listing

User opens a listing and proposes an edit.

If the edit changes the hechsher, a certificate is required.

Backend compares the edit to existing data (diff analysis).

AI evaluates risk and certificate consistency.

Pending edits remain hidden until approved.

D. Bilingual UI + Search

UI language auto‑detected from browser settings.

Restaurant names stored in multiple fields + aliases.

Search matches Hebrew, English, and transliterations.

5. Phase 1 Features (Prototype by June)

Core Map + UI

Mapbox map with markers

Hechsher‑based filtering

Responsive sidebar (desktop → right panel, mobile → bottom drawer)

Add‑a‑place flow

Submissions

Submission form

Certificate upload

Vision‑based autofill (hechsher + expiration)

Basic moderation pipeline

Approved listings appear on map

Hechsher Selector

Database‑backed hechsher list

Searchable selector with logos

Aliases for variant spellings

Bilingual UI

Auto‑detect language

Hebrew/English UI text

RTL support

Storage + Backend

PostgreSQL schema

FastAPI endpoints

Public certificate storage

Basic admin approval interface

6. Phase 2 Features (Post‑June Enhancements)

Mapbox POI Integration

Preload restaurants from Mapbox Search API

Mark them as “No kosher data yet”

First kosher submission becomes a new listing

Advanced Moderation

Diff‑based edit scoring

Certificate‑required hechsher edits

EXIF metadata checks (optional, non‑invasive)

Trusted contributor system

User Accounts (Optional)

Optional login for power users

Synced preferences

Edit history tied to accounts

Search Improvements

Full bilingual search

Transliteration matching

Admin Tools

Hechsher management

Merge duplicates

Edit rollback

Certificate validation dashboard

UX Enhancements

Multiple certificate support

Photo galleries

Comments/reviews

Favorites
