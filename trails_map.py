import folium
import gpxpy
import pandas as pd
import json
import os

# 1. Carica la configurazione JSON
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

CARTELLA = config.get('cartella_gpx', '')
COLORI = config.get('colori_percorsi', {})

# 2. Carica il database Excel
df = pd.read_excel('percorsi.xlsx')

# Inizializza la mappa
mymap = folium.Map(location=[45.5, 10.5], zoom_start=7, tiles='OpenStreetMap')
layers = {}

print(f"Monitoraggio cartella: {CARTELLA}")

for index, row in df.iterrows():
    # Costruisci il percorso completo del file
    gpx_path = os.path.join(CARTELLA, row['File_GPX'])
    tipo = str(row['Tipo']).strip()
    location = str(row['Location']).strip()
    
    # Recupera il colore dal JSON (usa 'default' se il tipo non esiste)
    colore = COLORI.get(tipo, COLORI.get('default', 'gray'))

    if not os.path.exists(gpx_path):
        print(f"⚠️ Salto {row['File_GPX']}: file non trovato in {CARTELLA}")
        continue

    # Crea il gruppo per il filtro se non esiste
    if tipo not in layers:
        layers[tipo] = folium.FeatureGroup(name=f"📂 {tipo}")
        layers[tipo].add_to(mymap)

    # Elaborazione GPX
    with open(gpx_path, 'r', encoding='utf-8') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude))
    
    if points:
        distanza = gpx.length_3d() / 1000
        dislivello = gpx.get_uphill_downhill().uphill or 0
        
        html_popup = f"""
        <div style="font-family: Arial; width: 200px;">
            <<h4 style="margin:0; color: {colore}; border-bottom: 1px solid #ccc; padding-bottom: 5px;">{row['Titolo']}</h4>
            <div style="padding: 8px 0; font-size: 13px;">
                <b>📅 Data:</b> {row['Data']}<br>
                <b>📍 Località:</b> {location}<br>
                <b>🏃 Tipo:</b> {tipo}<br>
                <hr style="margin: 5px 0; border: 0; border-top: 1px solid #eee;">
                <b>📏 Distanza:</b> {distanza:.2f} km<br>
                <b>⛰️ Dislivello:</b> +{dislivello:.0f} m<br>
            </div>
            <a href="{row['Link']}" target="_blank" 
               style="display: block; text-align: center; background: {colore}; color: white; 
                      text-decoration: none; padding: 5px; border-radius: 4px; font-size: 12px; font-weight: bold;">
               Vedi Dettagli Online
            </a>
        </div>
        """

        # Aggiungi traccia e marker al relativo gruppo
        folium.Marker(
            location=points[0],
            popup=folium.Popup(html_popup, max_width=300),
            icon=folium.Icon(color=colore, icon='info-sign')
        ).add_to(layers[tipo])

        folium.PolyLine(
            points, color=colore, weight=4, opacity=0.7, tooltip=row['Titolo']
        ).add_to(layers[tipo])

# 3. Aggiungi controlli e salvataggio
folium.LayerControl(collapsed=False).add_to(mymap)

# Generazione legenda dinamica basata sul JSON
legend_items = "".join([f'<div><i style="background:{c}; width:10px; height:10px; display:inline-block;"></i> {t}</div>' 
                       for t, c in COLORI.items() if t != "default"])

legend_html = f'''
     <div style="position: fixed; bottom: 30px; left: 30px; width: 120px; z-index:9999; 
     background:white; padding: 10px; border:2px solid gray; border-radius:5px; font-size:12px;">
     <b>LEGENDA</b><br>{legend_items}
     </div>
'''
mymap.get_root().html.add_child(folium.Element(legend_html))
# Raccogli tutti i punti di tutti i percorsi in una lista chiamata 'all_points' durante il loop
# Poi usa questa riga alla fine:
mymap.fit_bounds(mymap.get_bounds())

mymap.save('trails_map.html')
print("Mappa generata con successo!")
