import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import math
import io

st.set_page_config(
    page_title="SIG Pastoral Mauritanie",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 24px;
        font-weight: bold;
        color: #1b4332;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 14px;
        color: #52796f;
        margin-bottom: 15px;
    }
    .metric-card {
        background: #f8f9fa;
        border-left: 5px solid #2d6a4f;
        padding: 10px 14px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def charger_donnees():
    try:
        return pd.read_excel('infrastructures_unifiees.xlsx')
    except Exception as e:
        return None

df = charger_donnees()

if df is None:
    st.error("Le fichier 'infrastructures_unifiees.xlsx' n'a pas été trouvé dans le répertoire de travail.")
    st.info("Assurez-vous que 'infrastructures_unifiees.xlsx' se trouve dans le même dossier que 'app.py'.")
    st.stop()

# Barre latérale : Filtres
st.sidebar.image("https://img.icons8.com/color/96/oasis.png", width=60)
st.sidebar.title("SIG Pastoral")
st.sidebar.caption("Plateforme d'aide à la décision et de zonage")

st.sidebar.subheader("Filtrage Géographique")
wilayas_dispos = sorted(df['wilaya'].dropna().unique())
sel_wilayas = st.sidebar.multiselect("Wilaya", options=wilayas_dispos, default=[])

df_zone = df[df['wilaya'].isin(sel_wilayas)] if sel_wilayas else df

moughataas_dispos = sorted(df_zone['moughataa'].dropna().unique())
sel_moughataas = st.sidebar.multiselect("Moughataa", options=moughataas_dispos, default=[])
if sel_moughataas:
    df_zone = df_zone[df_zone['moughataa'].isin(sel_moughataas)]

st.sidebar.subheader("Filtrage Thématique")
categories_dispos = sorted(df['categorie'].dropna().unique())
sel_cats = st.sidebar.multiselect("Catégorie d'infrastructure", options=categories_dispos, default=[])
if sel_cats:
    df_zone = df_zone[df_zone['categorie'].isin(sel_cats)]

etats_dispos = sorted(df['etat'].dropna().unique())
sel_etats = st.sidebar.multiselect("État physique", options=etats_dispos, default=[])
if sel_etats:
    df_zone = df_zone[df_zone['etat'].isin(sel_etats)]

st.sidebar.markdown("---")
st.sidebar.subheader("Paramètres de l'Analyse Pastorale")
rayon_buffer = st.sidebar.slider("Rayon d'action pastorale (km)", min_value=3, max_value=25, value=15, step=1,
                                 help="Norme sahélienne standard : 5 km (petits ruminants), 15 km (bovins en saison sèche).")
montrer_degrades = st.sidebar.checkbox("Afficher le potentiel des puits à réhabiliter", value=True)

# En-tête principal
st.markdown('<div class="main-header">Système d\'Information Géographique Pastoral — Mauritanie</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Identification, analyse spatiale et planification des interventions d\'urgence pastorale</div>', unsafe_allow_html=True)

# Indicateurs de bord
col1, col2, col3, col4, col5 = st.columns(5)

total_pts = len(df_zone)
df_puits = df_zone[df_zone['categorie'] == 'Hydraulique pastorale']
puits_actifs = df_puits[~df_puits['etat'].str.contains('hors|réhab', case=False, na=False)]
puits_degrades = df_puits[df_puits['etat'].str.contains('hors|réhab', case=False, na=False)]

surface_unitaire = math.pi * (rayon_buffer ** 2)
surface_active_km2 = len(puits_actifs) * surface_unitaire
potentiel_rehab_km2 = len(puits_degrades) * surface_unitaire

col1.metric("Ouvrages sélectionnés", f"{total_pts:,}")
col2.metric("Puits fonctionnels", f"{len(puits_actifs):,}")
col3.metric("Puits à réhabiliter", f"{len(puits_degrades):,}")
col4.metric(f"Desserte active (R={rayon_buffer}km)", f"{surface_active_km2:,.0f} km²")
col5.metric(f"Potentiel déblocable", f"{potentiel_rehab_km2:,.0f} km²")

# Onglets
tab_carte, tab_zonage, tab_donnees = st.tabs([
    "🗺️ Carte Globale & Répartition",
    "🛰️ Analyse de Couverture & Pâturages (Buffers)",
    "📋 Données & Exports"
])

def get_color(etat):
    e = str(etat).lower()
    if 'bon' in e: return '#2d6a4f'
    if 'lég' in e or 'leger' in e: return '#f39c12'
    return '#d62828'

with tab_carte:
    if total_pts > 0:
        moy_lat = df_zone['latitude'].mean()
        moy_lon = df_zone['longitude'].mean()
        carte_inv = folium.Map(location=[moy_lat, moy_lon], zoom_start=8, tiles='OpenStreetMap')
        cluster = MarkerCluster(name="Regroupements d'ouvrages").add_to(carte_inv)

        for _, r in df_zone.head(1500).iterrows():
            txt_pop = f"""
            <b>{r['nom']}</b><br>
            <b>Type :</b> {r['type_ouvrage']}<br>
            <b>Localité :</b> {r['localite']} ({r['moughataa']}, {r['wilaya']})<br>
            <b>État :</b> {r['etat']}<br>
            <b>Gestion :</b> {r['responsable'] or r['gestion']}
            """
            folium.CircleMarker(
                location=[r['latitude'], r['longitude']],
                radius=5,
                color=get_color(r['etat']),
                fill=True,
                fill_opacity=0.85,
                popup=folium.Popup(txt_pop, max_width=280)
            ).add_to(cluster)

        folium.LayerControl().add_to(carte_inv)
        st_folium(carte_inv, width="100%", height=550)
        if total_pts > 1500:
            st.caption(f"ℹ️ Affichage optimisé à 1 500 points sur {total_pts} pour garantir une réactivité maximale.")
    else:
        st.warning("Aucune infrastructure ne correspond aux critères de filtre.")

with tab_zonage:
    st.subheader(f"Modélisation de l'empreinte pastorale ({rayon_buffer} km autour des points d'eau)")
    st.caption("Cercles verts : zones pâturables sécurisées par un point d'eau opérationnel. Cercles rouges en pointillés : pâturages enclavés ou sous-exploités dont l'accès dépend de la réhabilitation du point d'eau.")
    
    if len(df_puits) > 0:
        moy_lat = df_puits['latitude'].mean()
        moy_lon = df_puits['longitude'].mean()
        carte_zone = folium.Map(location=[moy_lat, moy_lon], zoom_start=9, tiles='OpenStreetMap')

        fg_verts = folium.FeatureGroup(name="Zones couvertes (Puits fonctionnels)")
        fg_rouges = folium.FeatureGroup(name="Zones à débloquer (À réhabiliter)")

        for _, p in puits_actifs.head(500).iterrows():
            folium.Circle(
                location=[p['latitude'], p['longitude']],
                radius=rayon_buffer * 1000,
                color='#2d6a4f',
                weight=1,
                fill=True,
                fill_color='#52b788',
                fill_opacity=0.15
            ).add_to(fg_verts)
            folium.CircleMarker(
                location=[p['latitude'], p['longitude']],
                radius=4,
                color='#1b4332',
                fill=True,
                fill_opacity=1,
                popup=f"<b>{p['nom']}</b> ({p['localite']})<br>État: {p['etat']}"
            ).add_to(fg_verts)

        if montrer_degrades:
            for _, p in puits_degrades.head(500).iterrows():
                folium.Circle(
                    location=[p['latitude'], p['longitude']],
                    radius=rayon_buffer * 1000,
                    color='#d62828',
                    weight=1.5,
                    dash_array='4, 6',
                    fill=True,
                    fill_color='#e63946',
                    fill_opacity=0.10
                ).add_to(fg_rouges)
                folium.CircleMarker(
                    location=[p['latitude'], p['longitude']],
                    radius=4,
                    color='#a4161a',
                    fill=True,
                    fill_opacity=1,
                    popup=f"<b>{p['nom']} (À RÉHABILITER)</b> ({p['localite']})<br>État: {p['etat']}"
                ).add_to(fg_rouges)

        fg_verts.add_to(carte_zone)
        if montrer_degrades:
            fg_rouges.add_to(carte_zone)

        folium.LayerControl().add_to(carte_zone)
        st_folium(carte_zone, width="100%", height=550)
    else:
        st.warning("Aucun point d'eau présent dans la sélection actuelle.")

with tab_donnees:
    st.subheader("Base d'inventaire tabulaire")
    st.dataframe(
        df_zone[['id', 'categorie', 'type_ouvrage', 'nom', 'localite', 'wilaya', 'moughataa', 'commune', 'etat', 'profondeur_m', 'latitude', 'longitude']],
        use_container_width=True,
        hide_index=True
    )

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        csv_bytes = df_zone.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger la sélection en CSV",
            data=csv_bytes,
            file_name="selection_pastorale.csv",
            mime="text/csv"
        )
    with col_dl2:
        # Export Excel direct
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_zone.to_excel(writer, index=False, sheet_name='Ouvrages')
        excel_data = output.getvalue()
        st.download_button(
            label="📊 Télécharger la sélection en Excel (.xlsx)",
            data=excel_data,
            file_name="selection_pastorale.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
