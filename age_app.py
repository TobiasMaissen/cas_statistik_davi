from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# import plotly.express as px
# import plotly.graph_objects as go
from owid.catalog import charts
from shiny.express import ui, input, render
from shiny import reactive
from shinyswatch import theme
# from shinywidgets import output_widget, render_widget

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

# Matplotlib dark style
plt.style.use('dark_background')

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
        value=1950
    )
    
    ui.hr()
    
    ui.h5("Medianes Alter")
    ui.input_slider(
        "median_year",
        "Jahr:",
        min=1950,
        max=2100,
        value=1950
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

# Hauptgrafiken
with ui.layout_columns(col_widths=[6, 6]):
    # Altersverteilung nach Geschlecht
    with ui.card(full_screen=True):
        with ui.card_header(class_="d-flex justify-content-between align-items-center"):
            "Altersverteilung nach Geschlecht"
            ui.input_action_button("play_age_distribution", "Play", class_="btn-sm btn-outline-success")
        
        @render.plot
        def age_distribution_plot():
            male_data, female_data = get_population_data()
            
            fig, ax = plt.subplots(figsize=(10, 8))

            if male_data.empty or female_data.empty:
                ax.text(0.5, 0.5, "Keine Daten verfügbar für die ausgewählte Kombination",
                        ha='center', va='center', transform=ax.transAxes, color="white")
                plt.close(fig) # Ensure figure is closed
                return fig
            
            # Daten vorbereiten
            age_labels_display = []
            male_populations = []
            female_populations = []

            # Sort age groups for correct order in the pyramid
            # Assuming male_age_groups and female_age_groups are the same and sorted if needed
            # For simplicity, using male_age_groups. If they can differ, this needs adjustment.
            sorted_age_groups = sorted(male_age_groups, key=lambda x: int(x.split('_')[0]) if x != '100plus' else 100)

            for age_group in sorted_age_groups:
                col_male = f'population__sex_male__age_{age_group}__variant_estimates'
                col_female = f'population__sex_female__age_{age_group}__variant_estimates'
                
                if age_group == '100plus':
                    age_label = '100+'
                else:
                    age_range = age_group.split('_')
                    age_label = f"{age_range[0]}-{age_range[1]}"
                age_labels_display.append(age_label)
                
                male_pop = male_data[col_male].iloc[0] / 1_000_000
                female_pop = female_data[col_female].iloc[0] / 1_000_000
                
                male_populations.append(-male_pop) # Negative for left side
                female_populations.append(female_pop)
            
            y_pos = np.arange(len(age_labels_display))
            
            ax.barh(y_pos, male_populations, color=colors['male'], label='Männer', height=0.8)
            ax.barh(y_pos, female_populations, color=colors['female'], label='Frauen', height=0.8)
            
            ax.set_yticks(y_pos)
            ax.set_yticklabels(age_labels_display)
            ax.set_xlabel('Bevölkerung (Millionen)')
            ax.set_ylabel('Altersgruppe')
            ax.set_title(f'Altersverteilung - {input.entity()} ({input.year()})')
            
            # Format x-axis to show positive numbers
            xticks = ax.get_xticks()
            ax.set_xticks(xticks)
            ax.set_xticklabels([str(abs(int(x))) for x in xticks])
            
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2)
            ax.grid(True, linestyle='--', alpha=0.7)
            fig.tight_layout(pad=1.5)
            
            plt.close(fig) # Important for Shiny to free memory
            return fig
    
    # Medianes Alter nach Region
    with ui.card(full_screen=True):
        with ui.card_header(class_="d-flex justify-content-between align-items-center"):
            "Medianes Alter nach Region"
            with ui.div(class_="d-flex align-items-center"):
                ui.input_action_button("play_median_age", "Play", class_="btn-sm btn-outline-success mr-2")
                @render.express
                def projection_info():
                    if input.median_year() > 2023:
                        ui.HTML("<span class='projection-note'>Projektion</span>")
                    else:
                        ui.HTML("<span>Historische Daten</span>")
        
        @render.plot
        def median_age_plot():
            year_data, is_projection = get_median_data()
            
            fig, ax = plt.subplots(figsize=(10, 6))

            if year_data.empty:
                ax.text(0.5, 0.5, "Keine Daten verfügbar für das ausgewählte Jahr",
                        ha='center', va='center', transform=ax.transAxes, color="white")
                plt.close(fig) # Ensure figure is closed
                return fig
            
            bar_colors = [colors["regions"].get(entity, "#cccccc") for entity in year_data["entities"]]
            
            bars = ax.bar(
                year_data["entities"],
                year_data["median_age_combined"],
                color=bar_colors,
                alpha=0.7 if is_projection else 1.0
            )
            
            ax.set_xlabel("Region")
            ax.set_ylabel("Medianes Alter (Jahre)")
            ax.set_title(f"Medianes Alter nach Region ({input.median_year()})")
            ax.set_ylim(0, year_data["median_age_combined"].max() * 1.2)
            ax.grid(True, linestyle='--', alpha=0.7, axis='y')

            # Text auf Balken
            for bar in bars:
                yval = bar.get_height()
                text_label = f"{yval:.1f}"
                if is_projection:
                    # For simplicity, adding (Proj.) to the label with Matplotlib
                    # More complex HTML-like styling as in Plotly is harder here directly.
                    # The projection_info render.express handles the general note.
                    text_label += "\n(Proj.)"
                
                ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, # Position slightly above bar
                        text_label,
                        ha='center', va='bottom',
                        fontsize=9,
                        color=colors["projection"] if is_projection else 'white')

            fig.tight_layout()
            plt.close(fig) # Important for Shiny to free memory
            return fig

# ============================================================================
# REAKTIVE BERECHNUNGEN
# ============================================================================

animating_age_distribution = reactive.Value(False)
animating_median_age = reactive.Value(False)

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
    ui.update_slider("year", value=1950)
    ui.update_slider("median_year", value=1950)
    ui.update_select("entity", selected="World")
    animating_age_distribution.set(False) # Stop animation on reset
    ui.update_action_button("play_age_distribution", label="Play") # Reset button label
    animating_median_age.set(False) # Stop median age animation on reset
    ui.update_action_button("play_median_age", label="Play") # Reset median age button label

@reactive.effect
@reactive.event(input.play_age_distribution)
def _():
    current_state = animating_age_distribution()
    animating_age_distribution.set(not current_state)
    if not current_state: # If it was False, it's now True (Playing)
        ui.update_action_button("play_age_distribution", label="Pause")
    else: # If it was True, it's now False (Paused)
        ui.update_action_button("play_age_distribution", label="Play")

@reactive.effect
def _animate_age_distribution():
    if animating_age_distribution():
        current_year = input.year()
        max_year = max(available_years)
        
        if current_year < max_year:
            next_year = current_year + 1
            ui.update_slider("year", value=next_year)
            reactive.invalidate_later(0.05) # Increased speed significantly (0.05 seconds per year)
        else:
            animating_age_distribution.set(False) # Stop at max year
            ui.update_action_button("play_age_distribution", label="Play")

@reactive.effect
@reactive.event(input.play_median_age)
def _():
    current_state = animating_median_age()
    animating_median_age.set(not current_state)
    if not current_state: # If it was False, it's now True (Playing)
        ui.update_action_button("play_median_age", label="Pause")
    else: # If it was True, it's now False (Paused)
        ui.update_action_button("play_median_age", label="Play")

@reactive.effect
def _animate_median_age():
    if animating_median_age():
        current_median_year = input.median_year()
        # Assuming slider max is 2100 as defined in ui.input_slider for median_year
        max_median_year = 2100 
        
        if current_median_year < max_median_year:
            next_median_year = current_median_year + 1
            ui.update_slider("median_year", value=next_median_year)
            reactive.invalidate_later(0.25) # Speed of animation (0.25 seconds per year)
        else:
            animating_median_age.set(False) # Stop at max year
            ui.update_action_button("play_median_age", label="Play")
