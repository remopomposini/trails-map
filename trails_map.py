import folium
import gpxpy
import pandas as pd
import json
import os
from datetime import datetime

# 1. Carica la configurazione JSON
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

CARTELLA = config.get('cartella_gpx', '')
COLORI = config.get('colori_percorsi', {})

# Colori hex per uso nel layout HTML
COLORI_HEX = {
    'Biking': '#e05c2a',
    'Hiking': '#2a7ae0',
    'default': '#888888'
}

# 2. Carica il database Excel
df = pd.read_excel('percorsi.xlsx')

# 3. Raccolta dati percorsi con statistiche GPX
percorsi_data = []

print(f"Monitoraggio cartella: {CARTELLA}")

for index, row in df.iterrows():
    gpx_path = os.path.join(CARTELLA, row['File_GPX'])
    tipo = str(row['Tipo']).strip()
    location = str(row['Location']).strip()
    colore_map = COLORI.get(tipo, COLORI.get('default', 'gray'))
    colore_hex = COLORI_HEX.get(tipo, COLORI_HEX['default'])

    # Formatta la data
    try:
        if hasattr(row['Data'], 'strftime'):
            data_fmt = row['Data'].strftime('%d/%m/%Y')
        else:
            data_fmt = str(row['Data'])
    except:
        data_fmt = str(row['Data'])

    if not os.path.exists(gpx_path):
        print(f"⚠️ Salto {row['File_GPX']}: file non trovato")
        continue

    with open(gpx_path, 'r', encoding='utf-8') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude))

    if not points:
        continue

    distanza = gpx.length_3d() / 1000
    dislivello = gpx.get_uphill_downhill().uphill or 0
    centro = points[len(points) // 2]

    percorsi_data.append({
        'id': index,
        'titolo': str(row['Titolo']),
        'data': data_fmt,
        'location': location,
        'tipo': tipo,
        'file_gpx': str(row['File_GPX']),
        'link': str(row['Link']),
        'colore_map': colore_map,
        'colore_hex': colore_hex,
        'distanza': round(distanza, 1),
        'dislivello': round(dislivello),
        'points': points,
        'centro': centro,
    })

print(f"Percorsi caricati: {len(percorsi_data)}")

# 4. Costruisci la mappa Folium
all_points = []
for p in percorsi_data:
    all_points.extend(p['points'])

if all_points:
    lats = [pt[0] for pt in all_points]
    lons = [pt[1] for pt in all_points]
    center = [(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2]
else:
    center = [45.5, 10.5]

mymap = folium.Map(location=center, zoom_start=7, tiles='OpenStreetMap',
                   zoom_control=False, scrollWheelZoom=True)

for p in percorsi_data:
    layer = folium.FeatureGroup(name=p['tipo'], show=True)

    folium.PolyLine(
        p['points'],
        color=p['colore_hex'],
        weight=3,
        opacity=0.85,
        tooltip=p['titolo'],
    ).add_to(layer)

    # Marker di partenza
    folium.CircleMarker(
        location=p['points'][0],
        radius=5,
        color=p['colore_hex'],
        fill=True,
        fill_color=p['colore_hex'],
        fill_opacity=1,
        tooltip=p['titolo'],
    ).add_to(layer)

    layer.add_to(mymap)

if all_points:
    lats = [pt[0] for pt in all_points]
    lons = [pt[1] for pt in all_points]
    mymap.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

# Estrai solo l'HTML interno della mappa
map_html = mymap.get_root().render()

# Estrai il div della mappa e gli script necessari
import re

# Prendiamo l'id della mappa
map_id = mymap.get_name()

# 5. Costruisci i dati JS per le tracce
js_percorsi = json.dumps([{
    'id': p['id'],
    'titolo': p['titolo'],
    'data': p['data'],
    'location': p['location'],
    'tipo': p['tipo'],
    'link': p['link'],
    'colore': p['colore_hex'],
    'distanza': p['distanza'],
    'dislivello': p['dislivello'],
    'centro': p['centro'],
    'points': p['points'],
} for p in percorsi_data], ensure_ascii=False)

# 6. Genera HTML finale
tipos = sorted(set(p['tipo'] for p in percorsi_data))
filter_buttons = ''
for t in tipos:
    col = COLORI_HEX.get(t, '#888')
    filter_buttons += f'<button class="filter-btn active" data-tipo="{t}" style="--tipo-color:{col}" onclick="toggleFilter(this)">{t}</button>\n'

cards_html = ''
for p in percorsi_data:
    icon = '🚵' if p['tipo'] == 'Biking' else '🥾'
    cards_html += f'''
    <div class="trail-card" data-tipo="{p['tipo']}" data-id="{p['id']}" onclick="selectTrail({p['id']})">
        <div class="card-accent" style="background:{p['colore_hex']}"></div>
        <div class="card-body">
            <div class="card-header">
                <span class="card-icon">{icon}</span>
                <div class="card-title-group">
                    <h3 class="card-title">{p['titolo']}</h3>
                    <span class="card-location">📍 {p['location']}</span>
                </div>
            </div>
            <div class="card-stats">
                <div class="stat">
                    <span class="stat-val">{p['distanza']} km</span>
                    <span class="stat-label">distanza</span>
                </div>
                <div class="stat-divider"></div>
                <div class="stat">
                    <span class="stat-val">+{p['dislivello']} m</span>
                    <span class="stat-label">dislivello</span>
                </div>
                <div class="stat-divider"></div>
                <div class="stat">
                    <span class="stat-val">{p['data']}</span>
                    <span class="stat-label">data</span>
                </div>
            </div>
        </div>
        <a href="{p['link']}" target="_blank" class="card-link" onclick="event.stopPropagation()">↗</a>
    </div>
    '''

html_output = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Le mie uscite</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        :root {{
            --bg: #ffffff;
            --surface: #f7f6f4;
            --surface2: #ffffff;
            --border: #e8e5e0;
            --text: #1a1714;
            --text-muted: #9a9590;
            --accent: #e05c2a;
            --font-display: 'Syne', sans-serif;
            --font-body: 'DM Sans', sans-serif;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: var(--font-body);
            background: var(--bg);
            color: var(--text);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        /* ── HEADER ── */
        header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 28px;
            height: 56px;
            border-bottom: 1px solid var(--border);
            background: var(--bg);
            flex-shrink: 0;
            z-index: 100;
        }}

        .header-title {{
            font-family: var(--font-display);
            font-weight: 800;
            font-size: 1.15rem;
            letter-spacing: -0.01em;
        }}

        .header-title span {{
            color: var(--accent);
        }}

        .header-count {{
            font-size: 0.78rem;
            color: var(--text-muted);
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}

        /* ── LAYOUT ── */
        .main {{
            display: flex;
            flex: 1;
            overflow: hidden;
        }}

        /* ── SIDEBAR ── */
        .sidebar {{
            width: 380px;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            border-right: 1px solid var(--border);
            background: var(--surface);
            overflow: hidden;
        }}

        .sidebar-top {{
            padding: 16px 20px 12px;
            border-bottom: 1px solid var(--border);
            flex-shrink: 0;
        }}

        .filter-row {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            font-family: var(--font-display);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 5px 12px;
            border-radius: 20px;
            border: 1.5px solid var(--tipo-color);
            color: var(--tipo-color);
            background: transparent;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .filter-btn.active {{
            background: var(--tipo-color);
            color: #0f0f0f;
        }}

        .trails-list {{
            overflow-y: auto;
            flex: 1;
            padding: 12px 12px;
            scrollbar-width: thin;
            scrollbar-color: var(--border) transparent;
        }}

        /* ── CARD ── */
        .trail-card {{
            display: flex;
            align-items: stretch;
            background: var(--surface2);
            border-radius: 10px;
            margin-bottom: 8px;
            cursor: pointer;
            border: 1px solid var(--border);
            transition: border-color 0.2s, transform 0.15s;
            position: relative;
            overflow: hidden;
        }}

        .trail-card:hover {{
            border-color: #bbb;
            transform: translateX(2px);
        }}

        .trail-card.selected {{
            border-color: var(--accent);
            background: #fff5f1;
        }}

        .trail-card.hidden {{
            display: none;
        }}

        .card-accent {{
            width: 4px;
            flex-shrink: 0;
            border-radius: 10px 0 0 10px;
        }}

        .card-body {{
            flex: 1;
            padding: 10px 12px;
            min-width: 0;
        }}

        .card-header {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            margin-bottom: 8px;
        }}

        .card-icon {{
            font-size: 1.2rem;
            flex-shrink: 0;
            line-height: 1;
            margin-top: 1px;
        }}

        .card-title-group {{
            min-width: 0;
        }}

        .card-title {{
            font-family: var(--font-display);
            font-size: 0.88rem;
            font-weight: 700;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.2;
        }}

        .card-location {{
            font-size: 0.72rem;
            color: var(--text-muted);
            margin-top: 2px;
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .card-stats {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .stat {{
            display: flex;
            flex-direction: column;
        }}

        .stat-val {{
            font-family: var(--font-display);
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text);
            line-height: 1;
        }}

        .stat-label {{
            font-size: 0.62rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-top: 2px;
        }}

        .stat-divider {{
            width: 1px;
            height: 24px;
            background: var(--border);
            flex-shrink: 0;
        }}

        .card-link {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            flex-shrink: 0;
            color: var(--text-muted);
            font-size: 1rem;
            text-decoration: none;
            transition: color 0.2s, background 0.2s;
        }}

        .card-link:hover {{
            color: var(--text);
            background: #f0ede8;
        }}

        /* ── MAP ── */
        .map-container {{
            flex: 1;
            position: relative;
        }}

        #map {{
            width: 100%;
            height: 100%;
        }}

        /* ── MAP BADGE ── */
        .map-badge {{
            position: absolute;
            top: 14px;
            right: 14px;
            z-index: 500;
            background: rgba(255,255,255,0.92);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px 12px;
            font-size: 0.65rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            min-width: 140px;
            max-width: 190px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }}
        .badge-title {{
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 0.78rem;
            color: var(--text);
            letter-spacing: -0.01em;
            line-height: 1.2;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: none;
        }}
        .badge-stats {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .badge-count {{
            font-family: var(--font-display);
            font-weight: 800;
            font-size: 1.1rem;
            color: var(--text);
            letter-spacing: -0.03em;
            line-height: 1;
        }}
        .badge-label {{ line-height: 1.5; }}
        .badge-actions {{
            display: none;
            margin-top: 8px;
            gap: 5px;
            flex-direction: column;
        }}
        .badge-link, .badge-deselect {{
            display: block;
            padding: 4px 8px;
            border-radius: 5px;
            font-family: var(--font-display);
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-align: center;
            pointer-events: all;
            cursor: pointer;
            transition: opacity 0.2s;
            text-decoration: none;
        }}
        .badge-link {{
            background: var(--accent);
            color: white;
            border: none;
        }}
        .badge-deselect {{
            background: transparent;
            color: var(--text-muted);
            border: 1px solid var(--border);
        }}
        .badge-link:hover, .badge-deselect:hover {{ opacity: 0.75; }}

        /* ── SCROLLBAR ── */
        .trails-list::-webkit-scrollbar {{ width: 4px; }}
        .trails-list::-webkit-scrollbar-track {{ background: transparent; }}
        .trails-list::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

        /* ── RESET BTN ── */
        .reset-btn {{
            display: none;
            margin-top: 10px;
            width: 100%;
            padding: 6px;
            background: transparent;
            border: 1px dashed var(--border);
            color: var(--text-muted);
            font-family: var(--font-body);
            font-size: 0.75rem;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .reset-btn:hover {{ border-color: #aaa; color: var(--text); }}
        .reset-btn.visible {{ display: block; }}

        /* ── TAB BAR (mobile only) ── */
        .tab-bar {{
            display: none;
            height: 48px;
            flex-shrink: 0;
            border-bottom: 1px solid var(--border);
            background: var(--bg);
        }}
        .tab-bar button {{
            flex: 1;
            height: 100%;
            border: none;
            background: transparent;
            font-family: var(--font-display);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--text-muted);
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}
        .tab-bar button.active {{
            color: var(--accent);
            border-bottom-color: var(--accent);
        }}

        /* ── MOBILE LAYOUT ── */
        @media (max-width: 700px) {{
            header {{ padding: 0 16px; height: 50px; }}
            .tab-bar {{ display: flex; }}
            .main {{ flex-direction: column; }}
            .sidebar {{
                width: 100%;
                border-right: none;
                border-top: 1px solid var(--border);
                flex: 1;
                display: none;
            }}
            .map-container {{ width: 100%; height: 100%; display: none; }}
            .main.show-map .map-container {{ display: block; flex: 1; }}
            .main.show-list .sidebar {{ display: flex; flex: 1; }}
            .map-badge {{ top: 8px; right: 8px; padding: 8px 10px; font-size: 0.6rem; min-width: 130px; max-width: 170px; }}
            .badge-count {{ font-size: 0.95rem; }}
            .badge-title {{ font-size: 0.72rem; }}
            .trail-card:hover {{ transform: none; }}
        }}

    </style>
</head>
<body>

<header>
    <div class="header-title">Le mie <span>uscite</span></div>
    <div class="header-count" id="count-label">{len(percorsi_data)} percorsi</div>
</header>
<div class="tab-bar" id="tab-bar">
    <button id="tab-map" class="active" onclick="switchTab('map')">🗺 Mappa</button>
    <button id="tab-list" onclick="switchTab('list')">📋 Lista</button>
</div>
<div class="main show-map" id="main">
    <!-- SIDEBAR -->
    <div class="sidebar" id="sidebar">
        <div class="sidebar-top">
            <div class="filter-row">
                {filter_buttons}
            </div>
            <button class="reset-btn" id="reset-btn" onclick="resetSelection()">✕ Deseleziona percorso</button>
        </div>
        <div class="trails-list" id="trails-list">
            {cards_html}
        </div>
    </div>

    <!-- MAPPA -->
    <div class="map-container" id="map-container">
        <div id="map"></div>
        <div class="map-badge" id="map-badge">
            <div class="badge-title" id="badge-title"></div>
            <div class="badge-stats">
                <div class="badge-count" id="badge-num">{len(percorsi_data)}</div>
                <div class="badge-label" id="badge-label">percorsi totali</div>
            </div>
            <div class="badge-actions" id="badge-actions">
                <a class="badge-link" id="badge-link" href="#" target="_blank">↗ Vedi percorso</a>
                <button class="badge-deselect" onclick="resetSelection()">✕ Tutti i percorsi</button>
            </div>
        </div>
    </div>
</div>

<script>
const PERCORSI = {js_percorsi};

// Init mappa
const map = L.map('map', {{
    zoomControl: true,
    scrollWheelZoom: true
}});

L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
}}).addTo(map);

// Disegna tutte le tracce
const polylines = {{}};
const allLatLngs = [];

PERCORSI.forEach(p => {{
    const latlngs = p.points.map(pt => [pt[0], pt[1]]);
    allLatLngs.push(...latlngs);

    const poly = L.polyline(latlngs, {{
        color: p.colore,
        weight: 3,
        opacity: 0.8
    }}).addTo(map);

    poly.bindTooltip(p.titolo, {{sticky: true}});

    poly.on('click', () => selectTrail(p.id));

    // Marker di partenza
    const marker = L.circleMarker(latlngs[0], {{
        radius: 5,
        color: p.colore,
        fillColor: p.colore,
        fillOpacity: 1,
        weight: 2
    }}).addTo(map);

    marker.on('click', () => selectTrail(p.id));

    polylines[p.id] = {{ poly, marker }};
}});

// Fit bounds
if (allLatLngs.length > 0) {{
    map.fitBounds(L.latLngBounds(allLatLngs), {{ padding: [30, 30] }});
}}

let selectedId = null;
let activeFilters = new Set(PERCORSI.map(p => p.tipo));

// Controlla se almeno un punto del percorso interseca il bounds
function trailInView(p, bounds) {{
    bounds = bounds || map.getBounds();
    return p.points.some(pt => bounds.contains([pt[0], pt[1]]));
}}

function updateListByView(boundsOverride) {{
    if (selectedId !== null) return 0;
    const bounds = boundsOverride || map.getBounds();
    let visCount = 0;
    document.querySelectorAll('.trail-card').forEach(card => {{
        const id = parseInt(card.dataset.id);
        const p = PERCORSI.find(x => x.id === id);
        const show = activeFilters.has(p.tipo) && trailInView(p, bounds);
        card.classList.toggle('hidden', !show);
        if (show) visCount++;
    }});
    document.getElementById('count-label').textContent = visCount + ' percorsi';
    return visCount;
}}

let moveTimer = null;
map.on('moveend zoomend', () => {{
    clearTimeout(moveTimer);
    moveTimer = setTimeout(updateListByView, 150);
}});

function selectTrail(id) {{
    const p = PERCORSI.find(x => x.id === id);
    if (!p) return;
    if (selectedId === id) {{ resetSelection(); return; }}
    selectedId = id;

    // Nascondi tutti gli altri, mostra solo il selezionato
    PERCORSI.forEach(other => {{
        if (other.id === id) {{
            polylines[other.id].poly.addTo(map);
            polylines[other.id].marker.addTo(map);
            polylines[other.id].poly.setStyle({{ weight: 6, opacity: 1 }});
            polylines[other.id].poly.bringToFront();
        }} else {{
            map.removeLayer(polylines[other.id].poly);
            map.removeLayer(polylines[other.id].marker);
        }}
    }});

    map.fitBounds(polylines[id].poly.getBounds(), {{ padding: [60, 60], maxZoom: 14 }});

    document.querySelectorAll('.trail-card').forEach(c => {{
        c.classList.remove('selected');
        c.classList.toggle('hidden', parseInt(c.dataset.id) !== id);
        if (parseInt(c.dataset.id) === id) {{
            c.classList.add('selected');
            c.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
        }}
    }});
    document.getElementById('count-label').textContent = '1 percorso';
    document.getElementById('badge-title').textContent = p.titolo;
    document.getElementById('badge-title').style.display = 'block';
    document.getElementById('badge-num').textContent = p.distanza + ' km';
    document.getElementById('badge-label').textContent = '↑ +' + p.dislivello + ' m';
    document.getElementById('badge-link').href = p.link;
    document.getElementById('badge-actions').style.display = 'flex';
    document.getElementById('reset-btn').classList.add('visible');

    // Su mobile passa automaticamente alla vista mappa
    if (window.innerWidth <= 700) switchTab('map');
}}

function resetSelection() {{
    selectedId = null;

    PERCORSI.forEach(p => {{
        if (activeFilters.has(p.tipo)) {{
            polylines[p.id].poly.addTo(map);
            polylines[p.id].marker.addTo(map);
        }}
        polylines[p.id].poly.setStyle({{ weight: 3, opacity: 0.85 }});
    }});

    document.querySelectorAll('.trail-card').forEach(c => c.classList.remove('selected'));
    if (allLatLngs.length > 0) {{
        map.fitBounds(L.latLngBounds(allLatLngs), {{ padding: [30, 30] }});
    }}
    // Aggiorna lista usando i bounds completi (fitBounds non ha ancora finito l'animazione)
    const allBounds = L.latLngBounds(allLatLngs);
    const visCount = updateListByView(allBounds);
    document.getElementById('badge-title').style.display = 'none';
    document.getElementById('badge-title').textContent = '';
    document.getElementById('badge-num').textContent = visCount;
    document.getElementById('badge-label').textContent = 'percorsi totali';
    document.getElementById('badge-actions').style.display = 'none';
    document.getElementById('reset-btn').classList.remove('visible');
}}

function toggleFilter(btn) {{
    const tipo = btn.dataset.tipo;
    if (activeFilters.has(tipo)) {{
        if (activeFilters.size === 1) return;
        activeFilters.delete(tipo);
        btn.classList.remove('active');
    }} else {{
        activeFilters.add(tipo);
        btn.classList.add('active');
    }}
    PERCORSI.forEach(p => {{
        const show = activeFilters.has(p.tipo);
        if (show) {{ polylines[p.id].poly.addTo(map); polylines[p.id].marker.addTo(map); }}
        else {{ map.removeLayer(polylines[p.id].poly); map.removeLayer(polylines[p.id].marker); }}
    }});
    if (selectedId !== null) resetSelection();
    else updateListByView();
}}

// ── MOBILE TAB SWITCHING ──
function switchTab(tab) {{
    const main = document.getElementById('main');
    const tabMap = document.getElementById('tab-map');
    const tabList = document.getElementById('tab-list');
    if (tab === 'map') {{
        main.className = 'main show-map';
        tabMap.classList.add('active');
        tabList.classList.remove('active');
        setTimeout(() => map.invalidateSize(), 50);
    }} else {{
        main.className = 'main show-list';
        tabList.classList.add('active');
        tabMap.classList.remove('active');
    }}
}}
</script>
</body>
</html>'''

output_file = 'trails_map.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_output)

print(f"✅ Mappa generata: {output_file}")
print(f"   {len(percorsi_data)} percorsi inclusi")
