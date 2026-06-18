import streamlit as st
import feedparser
import pandas as pd
from pytrends.request import TrendReq

# Configuración inicial del Dashboard
st.set_page_config(page_title="GTrends | Magui Dashboard", layout="wide")
st.title("📡 Centro de Operaciones Magui Tiesso")
st.markdown("Monitor de Coyuntura, Tendencias y Autoridad Digital - **Actualizado al 18 de Junio de 2026**")

# Diccionario de Feeds RSS Estratégicos (Basado en el archivo "La Aurora" y Medios Nacionales)
rss_feeds = {
    "CABA y Rosca Porteña": [
        "https://news.google.com/rss/search?q=Legislatura+Buenos+Aires+política&hl=es-419-AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:lapoliticaonline.com+CABA&hl=es-419-AR&ceid=AR:es"
    ],
    "Nacional Pesos Pesados": [
        "https://www.infobae.com/politica/feed/",
        "https://www.pagina12.com.ar/rss/secciones/el-pais/notas"
    ],
    "Jubilados / PAMI / Transporte": [
        "https://news.google.com/rss/search?q=PAMI+OR+Jubilados+Argentina&hl=es-419-AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=Subte+CABA+aumento+OR+gratis&hl=es-419-AR&ceid=AR:es"
    ]
}

# Función para extraer las Top 5 Noticias
def obtener_noticias(url_list):
    noticias = []
    for url in url_list:
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]: # Saca las primeras de cada link para armar el Top 5 general
            noticias.append({"Título": entry.title, "Link": entry.link})
    return pd.DataFrame(noticias).head(5)

# --- CREACIÓN DE SOLAPAS (TABS) EN LA WEB ---
tab1, tab2, tab3 = st.tabs(["📰 Radar de Noticias (RSS)", "📈 Google Trends en Vivo", "🤖 Predictor de Posteos"])

# --- SOLAPA 1: NOTICIAS ---
with tab1:
    st.subheader("Filtro Geográfico y Temático")
    region = st.selectbox("Seleccioná la región o tema a monitorear:", list(rss_feeds.keys()))
    
    st.markdown(f"**Top 5 Noticias Frescas de: {region}**")
    df_noticias = obtener_noticias(rss_feeds[region])
    for index, row in df_noticias.iterrows():
        st.write(f"- [{row['Título']}]({row['Link']})")

# --- SOLAPA 2: GOOGLE TRENDS ---
with tab2:
    st.subheader("Termómetro de la Calle Digital (Argentina)")
    st.info("Buscando picos de interés actuales para la estrategia de Magui...")
    
    try:
        pytrends = TrendReq(hl='es-AR', tz=180)
        # Palabras clave estratégicas para la coyuntura actual
        kw_list = ["Jubilados", "Subte", "PAMI", "Desregulación"]
        pytrends.build_payload(kw_list, cat=0, timeframe='now 7-d', geo='AR')
        tendencias = pytrends.interest_over_time()
        
        if not tendencias.empty:
            st.line_chart(tendencias[kw_list])
            st.success("Gráfico generado con éxito. Si la línea de 'Subte' o 'Jubilados' sube, es momento de publicar contenido de servicio (Ej: Ley 6.817).")
        else:
            st.warning("No hay suficientes datos de búsqueda en las últimas horas para estas palabras.")
    except Exception as e:
        st.error("Error al conectar con Google Trends. Reintentando...")

# --- SOLAPA 3: PREDICTOR (Simulador visual) ---
with tab3:
    st.subheader("El Filtro Magui: Evaluación de Borradores")
    texto_tuit = st.text_area("Pegá acá el borrador del tuit o texto:")
    
    col1, col2 = st.columns(2)
    with col1:
        porcentaje_datos = st.slider("Proporción de Datos Duros vs Militancia (%)", 0, 100, 30)
    with col2:
        confronta = st.checkbox("¿Menciona o responde a adversarios de CABA (Ej: Pilar Ramírez, Lospennato)?")

    if st.button("Analizar Tono y Viralidad"):
        # Lógica simulada basada en la regla 70/30
        if 20 <= porcentaje_datos <= 40 and not confronta:
            st.success("✅ Score: 85/100. ¡Excelente! Perfil militante con el respaldo técnico justo. Ideal para Instagram o TikTok.")
        elif confronta:
            st.warning("⚠️ Score: 70/100. Alto potencial de viralidad en X (Twitter), pero preparate para contener el hate libertario con datos institucionales.")
        else:
            st.error("❌ Score: 40/100. Suena a candidata en campaña tradicional o le faltan datos duros. Revisá el texto.")
