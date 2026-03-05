# 🚵 Trails Map

Interactive map of my bike rides and hiking trails, generated from GPX tracks and an Excel database.

![Python](https://img.shields.io/badge/Python-3.x-blue) ![Leaflet](https://img.shields.io/badge/Leaflet-1.9-green) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

## Overview

A Python script that reads route data from an Excel file and a folder of GPX tracks, then generates a self-contained HTML page with an interactive split-view map. The left panel shows a filterable list of routes; the right panel shows all tracks on an OpenStreetMap base layer.

**Live demo:** [flautube.com/map/ride_map.html](https://www.flautube.com/map/ride_map.html)

## Features

- **Split layout** — route list on the left, interactive map on the right
- **Click to isolate** — selecting a route hides all others on the map and zooms in on the track; deselecting restores the full view
- **Dynamic list filtering** — as you pan or zoom the map, the list automatically updates to show only the routes visible in the current viewport
- **Type filters** — toggle Biking and Hiking routes independently
- **Stats per route** — distance (km) and elevation gain (m) calculated directly from the GPX data
- **Direct links** — each card links to the full route on Komoot or other external platforms
- **Single file output** — the script produces one self-contained `trails_map.html` with no external dependencies beyond a CDN

## Project Structure

```
trails-map/
├── trails_map.py       # Main script — reads data and generates HTML
├── config.json         # Folder path and color settings per activity type
├── percorsi.xlsx       # Route database (title, date, location, type, GPX filename, link)
├── percorsi_gpx/       # Folder containing all .gpx files
└── trails_map.html     # Generated output (not committed)
```

## Requirements

```
python >= 3.8
gpxpy
pandas
openpyxl
```

Install dependencies:

```bash
pip install gpxpy pandas openpyxl
```

## Usage

1. Add your routes to `percorsi.xlsx` with these columns:

   | Column | Description |
   |--------|-------------|
   | `Titolo` | Route name |
   | `Data` | Date |
   | `Location` | Starting location |
   | `Tipo` | Activity type (e.g. `Biking`, `Hiking`) |
   | `File_GPX` | GPX filename (must be in the folder set in `config.json`) |
   | `Link` | URL to the route on an external platform |

2. Place your `.gpx` files in the folder defined in `config.json` (default: `percorsi_gpx/`).

3. Adjust `config.json` to set the GPX folder path and a color per activity type:

   ```json
   {
     "cartella_gpx": "percorsi_gpx/",
     "colori_percorsi": {
       "Biking": "red",
       "Hiking": "blue",
       "default": "gray"
     }
   }
   ```

4. Run the script:

   ```bash
   python trails_map.py
   ```

5. Open the generated `trails_map.html` in any browser.

## How It Works

The script parses each GPX file with `gpxpy` to extract the track coordinates and compute distance and elevation gain. All route data is serialised as JSON and embedded directly into the HTML output alongside Leaflet.js (loaded from CDN), so the final file works offline and requires no server.
