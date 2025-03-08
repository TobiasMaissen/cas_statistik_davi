"""
Dieses Skript demonstriert die Integration von Plotly-Grafiken in eine Shiny for Python Anwendung.
Hauptkomponenten für die Integration:
1. shinywidgets: Paket für die Integration interaktiver Widgets
2. plotly.express: Für die einfache Erstellung von Plotly-Grafiken
3. render_widget Decorator: Für das Rendern der Plotly-Figur
"""

from pathlib import Path
import pandas as pd
import numpy as np
# Plotly Bibliotheken für interaktive Visualisierungen
import plotly.express as px          # Hochlevel-API für schnelle Plotly-Grafiken
import plotly.graph_objects as go    # Lowlevel-API für detaillierte Kontrolle
from shiny.express import ui, input, render
from shiny import reactive
from shinyswatch import theme
# shinywidgets enthält die notwendigen Komponenten für Plotly-Integration
from shinywidgets import output_widget, render_widget

# Daten laden und vorbereiten
df = pd.read_csv('population.csv')
df_states = df[(df['SUMLEV'] == 40) & (df['STATE'] != '72') & (df['REGION'] != 'X')].copy()

# Prozentuale Veränderung berechnen
df_states['change_2010_2019'] = ((df_states['POPESTIMATE2019'] - df_states['POPESTIMATE2010']) / 
                                df_states['POPESTIMATE2010'] * 100)

# Region-Namen zuordnen
region_map = {
    '1': 'Northeast',
    '2': 'Midwest',
    '3': 'South',
    '4': 'West'
}
df_states['REGION_NAME'] = df_states['REGION'].map(region_map)

# Farbpalette
colors = {
    'Northeast': '#ffeb00',
    'Midwest': '#228B22',
    'South': '#4169E1',
    'West': '#FFA500'
}

# Dashboard Konfiguration
ui.page_opts(
    title="Bevölkerungswachstum Dashboard",
    fillable=True,
    theme=theme.cosmo
)

# Sidebar
with ui.sidebar(open="desktop"):
    ui.h4("Filteroptionen")
    
    ui.input_checkbox_group(
        "regions",
        "Regionen:",
        choices=list(colors.keys()),
        selected=list(colors.keys())
    )
    
    ui.input_slider(
        "top_n",
        "Anzahl Staaten:",
        min=5,
        max=51,
        value=51
    )

# Hauptbereich
ui.h1("Bevölkerungswachstum nach State", class_="mt-3")

# Hauptgrafik
# Die Plotly-Grafik wird in einer Card-Komponente platziert
with ui.card(full_screen=True):
    ui.card_header("Bevölkerungswachstum 2010-2019")
    
    # WICHTIG: Integration von Plotly in Shiny
    # Der @render_widget Decorator ist der Schlüssel zur Integration
    # - Er konvertiert die Plotly-Figur in ein interaktives Widget
    # - Die ID "population_widget" muss eindeutig sein
    # - Keine separate output_widget() Funktion nötig in Shiny.express
    @render_widget("population_widget")
    def _():
        # Daten für die Plotly-Figur vorbereiten
        # Die Daten werden reaktiv gefiltert basierend auf UI-Inputs
        filtered_df = df_states[df_states['REGION_NAME'].isin(input.regions())]
        plot_df = filtered_df.nlargest(input.top_n(), 'change_2010_2019')
        
        # PLOTLY-GRAFIK ERSTELLEN
        # px.bar() erstellt ein interaktives Balkendiagramm
        fig = px.bar(
            plot_df,
            x='change_2010_2019',       # x-Achsenwerte
            y='NAME',                   # y-Achsenwerte
            color='REGION_NAME',        # Farbkodierung nach Region
            orientation='h',            # Horizontale Balken
            color_discrete_map=colors,  # Eigene Farbpalette
            # labels: Dictionary zur Umbenennung der Spaltenbezeichnungen
            # - Schlüssel: Original-Spaltennamen aus dem DataFrame
            # - Werte: Neue, benutzerfreundliche Bezeichnungen
            # Diese Labels erscheinen:
            # - In der Hover-Information (beim Überfahren mit der Maus)
            # - Als Achsenbeschriftungen
            # - In der Legende
            labels={                    
                'change_2010_2019': 'Prozentuale Veränderung',  # Umbenennung für x-Achse und Hover
                'NAME': 'State',                                # Umbenennung für y-Achse und Hover
                'REGION_NAME': 'Region'                         # Umbenennung in der Legende
            }
        )
        
        # LAYOUT ANPASSEN
        # Plotly bietet umfangreiche Möglichkeiten zur Layoutanpassung
        # update_layout() konfiguriert das gesamte Erscheinungsbild
        fig.update_layout(
            height=800,              # Feste Höhe der Grafik
            showlegend=True,         # Legende anzeigen
            yaxis={
                'categoryorder': 'total ascending'  # Sortierung
            },
            xaxis_title='Prozentuale Veränderung',
            yaxis_title='States',
            plot_bgcolor='white',    # Weisser Hintergrund
            # Legende konfigurieren
            legend=dict(
                title='Region',
                yanchor='bottom',       # Ausrichtung oben
                y=0,
                xanchor='right',     # Ausrichtung rechts
                x=1
            ),
            # Abstände zum Rand definieren
            margin=dict(l=140, r=20, t=50, b=40)
        )
        
        # ACHSEN ANPASSEN
        # update_xaxes() konfiguriert speziell die x-Achse
        fig.update_xaxes(
            showgrid=True,           # Gitterlinien anzeigen
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=True,           # Nulllinie anzeigen
            zerolinewidth=1,
            zerolinecolor='black'
        )
        
        # WICHTIG: Rückgabe der Plotly-Figur
        # - Die Figur wird automatisch als interaktives Widget gerendert
        # - Alle Plotly-Interaktionen sind verfügbar:
        #   * Zoomen
        #   * Hovering für Details
        #   * Pan/Verschieben
        #   * Download als PNG
        #   * Auswahl und Filterung
        return fig

# Werte-Box für Durchschnittswachstum
# Eine Value-Box ist eine UI-Komponente, die einen wichtigen Kennwert hervorhebt
# Sie besteht aus einem Icon, einem Titel und einem Wert
with ui.layout_columns(fill=False):    # Layout-Container für die Value-Box
                                      # fill=False verhindert, dass die Box sich ausdehnt
    
    # Value-Box Definition
    # showcase: Bereich für das Icon (links in der Box)
    # ui.HTML(): Erlaubt die Verwendung von HTML/CSS-Icons (Font Awesome)
    # fa-solid fa-chart-line: Spezifisches Icon aus Font Awesome (Linien-Chart)
    with ui.value_box(showcase=ui.HTML('<i class="fa-solid fa-chart-line"></i>')):
        # Titel der Value-Box
        "Durchschnittliches Wachstum"
        
        # REAKTIVE BERECHNUNG DES DURCHSCHNITTSWACHSTUMS
        # @render.express: Decorator für automatisches Rendering
        # - Aktualisiert sich automatisch wenn sich input.regions() ändert
        # - Einfachere Syntax als @render.text (speziell für Shiny Express)
        @render.express
        def avg_growth():
            # 1. Datenfilterung
            # - Verwendet die gleichen Filter wie die Plotly-Grafik
            # - Stellt sicher, dass Value-Box und Grafik konsistent sind
            filtered_df = df_states[df_states['REGION_NAME'].isin(input.regions())]
            
            # 2. Berechnung des Durchschnitts
            # - mean(): Berechnet den Durchschnitt der prozentualen Veränderung
            # - Berücksichtigt nur die ausgewählten Regionen
            avg = filtered_df['change_2010_2019'].mean()
            
            # 3. Formatierung des Ergebnisses
            # f"": f-string für einfache String-Formatierung
            # .1f: Formatierung auf eine Dezimalstelle
            # %: Prozentzeichen anhängen
            f"{avg:.1f}%"
