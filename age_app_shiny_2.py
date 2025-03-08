from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from owid.catalog import charts
from shiny.express import ui, input, render
from shiny import reactive
from shinyswatch import theme
from shinywidgets import output_widget, render_widget

# ============================================================================
# DATEN LADEN UND VORBEREITEN
# ============================================================================

# Pfad zum aktuellen Verzeichnis
app_dir = Path(__file__).parent

# Daten aus der OWID (Our World in Data) Katalog laden
male_popl_by_age_df = charts.get_data("male-population-by-age-group")
female_popl_by_age_df = charts.get_data("female-population-by-age-group")
median_df = charts.get_data("median-age")

# Hilfsfunktion zum Extrahieren der Altersgruppen
def extract_age_groups(df, sex):
    age_columns = [col for col in df.columns if f'__sex_{sex}__age_' in col]
    age_groups = [col.split('__age_')[1].split('__variant')[0] for col in age_columns]
    return age_groups

# Altersgruppen extrahieren
male_age_groups = extract_age_groups(male_popl_by_age_df, 'male')
female_age_groups = extract_age_groups(female_popl_by_age_df, 'female')

# Verfügbare Jahre und Entitäten
available_years = sorted(male_popl_by_age_df['years'].unique())
available_entities = sorted(male_popl_by_age_df['entities'].unique())

# Regionen für die Median-Alters-Grafik
median_regions = ["Asia (UN)", "Europe (UN)", "United States", "Africa (UN)"]

# Farbpalette für konsistentes Design
colors = {
    "male": "#2ecc71",
    "female": "#e74c3c",
    "regions": {
        "Africa (UN)": "#1f77b4",
        "Asia (UN)": "#ff7f0e",
        "Europe (UN)": "#2ca02c",
        "United States": "#d62728"
    },
    "projection": "#ffd700"
}

# ============================================================================
# DASHBOARD KONFIGURATION
# ============================================================================

# Seitenkonfiguration
ui.page_opts(
    title="Bevölkerungsanalyse Dashboard",
    fillable=True,
    theme=theme.darkly
)

# CSS einbinden
ui.include_css(app_dir / "styles.css")

# ============================================================================
# SIDEBAR
# ============================================================================

with ui.sidebar(open="desktop"):
    ui.h4("Filteroptionen")
    
    ui.hr()
    
    ui.h5("Altersverteilung")
    ui.input_select(
        "entity",
        "Region/Land:",
        {entity: entity for entity in available_entities},
        selected="World"
    )
    
    ui.input_slider(
        "year",
        "Jahr:",
        min=min(available_years),
        max=max(available_years),
        value=2023
    )
    
    ui.hr()
    
    ui.h5("Medianes Alter")
    ui.input_slider(
        "median_year",
        "Jahr:",
        min=1950,
        max=2100,
        value=2023
    )
    
    ui.hr()
    
    ui.input_action_button(
        "reset", 
        "Filter zurücksetzen", 
        class_="btn-primary w-100"
    )

# ============================================================================
# HAUPTBEREICH
# ============================================================================

# Überschrift
ui.h1("Bevölkerungsanalyse", class_="mt-3")

# Hauptgrafiken - Direkt ohne Value-Boxen
with ui.layout_columns(col_widths=[6, 6]):
    # Altersverteilung nach Geschlecht
    with ui.card(full_screen=True):
        ui.card_header("Altersverteilung nach Geschlecht")
        
        @render_widget("age_distribution_widget")
        def age_distribution_render():
            male_data, female_data = get_population_data()
            
            if male_data.empty or female_data.empty:
                return go.Figure().add_annotation(
                    text="Keine Daten verfügbar für die ausgewählte Kombination",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            
            # Daten vorbereiten
            age_data = []
            for age_group in male_age_groups:
                col_male = f'population__sex_male__age_{age_group}__variant_estimates'
                col_female = f'population__sex_female__age_{age_group}__variant_estimates'
                
                if age_group == '100plus':
                    age_label = '100+'
                else:
                    age_range = age_group.split('_')
                    age_label = f"{age_range[0]}-{age_range[1]}"
                
                male_pop = -male_data[col_male].iloc[0] / 1_000_000
                female_pop = female_data[col_female].iloc[0] / 1_000_000
                
                age_data.append({
                    'Age': age_label,
                    'Male': male_pop,
                    'Female': female_pop
                })
            
            df_plot = pd.DataFrame(age_data)
            
            # Erstelle zwei separate Balken für Männer und Frauen
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                y=df_plot['Age'],
                x=df_plot['Male'],
                name='Männer',
                orientation='h',
                marker_color=colors['male']
            ))
            
            fig.add_trace(go.Bar(
                y=df_plot['Age'],
                x=df_plot['Female'],
                name='Frauen',
                orientation='h',
                marker_color=colors['female']
            ))
            
            # Layout anpassen
            fig.update_layout(
                title=f'Altersverteilung - {input.entity()} ({input.year()})',
                xaxis_title='Bevölkerung (Millionen)',
                yaxis_title='Altersgruppe',
                barmode='relative',
                bargap=0.1,
                autosize=True,
                # height=600,
                template='plotly_dark',
                margin=dict(l=80, r=30, t=80, b=80),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                ),
                xaxis=dict(
                    gridcolor='lightgray',
                    zeroline=True,
                    zerolinecolor='black',
                    zerolinewidth=1
                ),
                yaxis=dict(
                    autorange=True,
                    gridcolor='lightgray',
                    dtick=1  # Zeigt jeden Tick an
                )
            )
            
            # Achsenbeschriftungen anpassen
            fig.update_xaxes(ticktext=[str(abs(int(x))) for x in fig.data[0].x])
            
            return fig
    
    # Medianes Alter nach Region
    with ui.card(full_screen=True):
        with ui.card_header(class_="d-flex justify-content-between align-items-center"):
            "Medianes Alter nach Region"
            
            @render.express
            def projection_info():
                if input.median_year() > 2023:
                    ui.HTML("<span class='projection-note'>Projektion</span>")
                else:
                    ui.HTML("<span>Historische Daten</span>")
        
        @render_widget("median_age_widget")
        def median_age_render():
            year_data, is_projection = get_median_data()
            
            if year_data.empty:
                return go.Figure().add_annotation(
                    text="Keine Daten verfügbar für das ausgewählte Jahr",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            
            # Erstelle eine benutzerdefinierte Textspalte
            year_data['custom_text'] = year_data.apply(
                lambda row: f"{row['median_age_combined']:.1f}<br><span style='color:#edeaa8;font-size:12px'>Projected</span>" 
                if is_projection 
                else f"{row['median_age_combined']:.1f}",
                axis=1
            )
            
            # Erstelle das Balkendiagramm
            fig = px.bar(
                year_data,
                x="entities",
                y="median_age_combined",
                color="entities",
                color_discrete_map=colors["regions"],
                text="custom_text",
                title=f"Medianes Alter nach Region ({input.median_year()})",
                labels={
                    "entities": "Region",
                    "median_age_combined": "Medianes Alter (Jahre)"
                }
            )
            
            # Layout anpassen für das Medianes Alter Diagramm
            fig.update_layout(
                template="plotly_dark",
                showlegend=False,
                autosize=True,
                # height=600,
                margin=dict(l=80, r=30, t=80, b=80),
                yaxis=dict(
                    range=[0, year_data["median_age_combined"].max() * 1.2],
                    gridcolor='lightgray'
                )
            )
            
            # Textposition anpassen
            fig.update_traces(
                textposition="outside",
                opacity=0.7 if is_projection else 1.0
            )
            
            return fig

# ============================================================================
# REAKTIVE BERECHNUNGEN
# ============================================================================

@reactive.calc
def get_population_data():
    male_data = male_popl_by_age_df[
        (male_popl_by_age_df['entities'] == input.entity()) & 
        (male_popl_by_age_df['years'] == input.year())
    ]
    female_data = female_popl_by_age_df[
        (female_popl_by_age_df['entities'] == input.entity()) & 
        (female_popl_by_age_df['years'] == input.year())
    ]
    
    return male_data, female_data

@reactive.calc
def get_median_data():
    filtered_df = median_df[median_df["entities"].isin(median_regions)].copy()
    
    estimates_column = "median_age__sex_all__age_all__variant_estimates"
    medium_column = "median_age__sex_all__age_all__variant_medium"
    
    filtered_df["median_age_combined"] = np.where(
        filtered_df[estimates_column].notna(),
        filtered_df[estimates_column],
        filtered_df[medium_column]
    )
    
    year_data = filtered_df[filtered_df["years"] == input.median_year()]
    
    return year_data, input.median_year() > 2023

@reactive.effect
@reactive.event(input.reset)
def _():
    ui.update_slider("year", value=2023)
    ui.update_slider("median_year", value=2023)
    ui.update_select("entity", selected="World")
