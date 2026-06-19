import anthropic
import os

# Conexión segura a la API
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

def pedir_a_claude(prompt):
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
import streamlit as st
import feedparser
import pandas as pd
from pytrends.request import TrendReq

st.set_page_config(page_title="Centro de Monitoreo | 1091", layout="centered")

# Inyectamos CSS personalizado para lograr exactamente el diseño de la imagen
st.markdown("""
<style>
    /* Ocultar el header por defecto de Streamlit */
    header {visibility: hidden;}
    
    /* Estilos del Título y Subtítulo idénticos a la captura */
    .titulo-panel {
        font-size: 1.7rem;
        font-weight: 600;
        margin-bottom: 0px;
        padding-bottom: 0px;
        color: #ffffff;
    }
    .icono-naranja {
        color: #ff7f50; /* Naranja coral */
    }
    .subtitulo-panel {
        color: #8c92a5;
        font-size: 0.9rem;
        margin-top: 5px;
        margin-bottom: 15px;
    }
    .fecha-naranja {
        color: #ff7f50;
        font-weight: 600;
    }
    .linea-divisoria {
        border-bottom: 1px solid #333333;
        margin-bottom: 25px;
    }
    
    /* Estilos de la lista de noticias */
    .noticia-item {
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid #2b2b2b;
    }
    .noticia-titulo {
        color: #3b9cff !important; /* Celeste enlaces */
        text-decoration: none;
        font-size: 0.95rem;
        font-weight: 500;
        line-height: 1.4;
    }
    .noticia-titulo:hover {
        text-decoration: underline;
    }
    .bullet-naranja {
        color: #ff7f50;
        font-size: 1.2rem;
        margin-right: 6px;
        line-height: 0;
        position: relative;
        top: 2px;
    }
    .noticia-fuente {
        color: #6c757d;
        font-size: 0.75rem;
        margin-top: 4px;
        margin-left: 18px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="titulo-panel"><span class="icono-naranja">📡</span> Centro de Monitoreo</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo-panel">Coyuntura, Tendencias y Autoridad Digital — <span class="fecha-naranja">18 de Junio de 2026</span></div>', unsafe_allow_html=True)
st.markdown('<div class="linea-divisoria"></div>', unsafe_allow_html=True)

rss_feeds = {
    "CABA y Rosca Porteña": [
        "https://news.google.com/rss/search?q=Legislatura+Buenos+Aires+política&hl=es-419-AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:lapoliticaonline.com+CABA&hl=es-419-AR&ceid=AR:es"
    ],
    "Transporte CABA (Subte/Colectivos)": [
        "https://news.google.com/rss/search?q=Subte+aumento+OR+paro+OR+gratis+CABA&hl=es-419-AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=transporte+colectivos+CABA&hl=es-419-AR&ceid=AR:es"
    ],
    "Jubilados / PAMI / Salud": [
        "https://news.google.com/rss/search?q=PAMI+OR+Jubilados+Argentina&hl=es-419-AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=IOMA+OR+prepagas+salud&hl=es-419-AR&ceid=AR:es"
    ],
    "Educación CABA": [
        "https://news.google.com/rss/search?q=docentes+CABA+escuelas+paro&hl=es-419-AR&ceid=AR:es"
    ],
    "Interna PJ (Nacional y CABA)": [
        "https://news.google.com/rss/search?q=interna+PJ+peronismo+elecciones&hl=es-419-AR&ceid=AR:es"
    ],
    "Nacional (Pesos Pesados)": [
        "https://www.infobae.com/politica/feed/",
        "https://www.clarin.com/rss/politica/",
        "https://www.pagina12.com.ar/rss/secciones/el-pais/notas"
    ]
}

@st.cache_data(ttl=600) # Cache para no recargar en cada clic
def obtener_noticias(url_list):
    noticias = []
    for url in url_list:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]: # Tomar hasta 4 de cada feed
                # Intentar limpiar el título de Google News (sacar la fuente del final)
                titulo = entry.title
                if " - " in titulo:
                    titulo = titulo.rsplit(" - ", 1)[0]
                
                # Intentar extraer el nombre del medio
                fuente = "Portal de Noticias"
                if hasattr(entry, 'source') and hasattr(entry.source, 'title'):
                    fuente = entry.source.title
                elif "infobae" in url: fuente = "Infobae"
                elif "clarin" in url: fuente = "Clarín"
                elif "pagina12" in url: fuente = "Página/12"
                elif "lapoliticaonline" in url: fuente = "La Política Online"
                
                noticias.append({"Título": titulo, "Link": entry.link, "Fuente": fuente})
        except Exception:
            continue
    
    # Devolver las 5 primeras
    return pd.DataFrame(noticias).head(5)

tab1, tab2, tab3 = st.tabs(["Radar de Noticias", "Google Trends", "Predictor de Posteos"])

# --- SOLAPA 1: NOTICIAS ---
with tab1:
    st.markdown("#### Filtro Geográfico y Temático")
    region = st.selectbox("Seleccioná la región o tema a monitorear:", list(rss_feeds.keys()))
    
    st.markdown(f"<p style='color: #8c92a5; font-size: 0.9rem;'>Top 5 Noticias Frescas de: {region}</p>", unsafe_allow_html=True)
    
    df_noticias = obtener_noticias(rss_feeds[region])
    
    # Renderizado idéntico a la imagen usando HTML
    for index, row in df_noticias.iterrows():
        html_noticia = f"""
        <div class="noticia-item">
            <span class="bullet-naranja">•</span>
            <a href="{row['Link']}" target="_blank" class="noticia-titulo">{row['Título']}</a>
            <div class="noticia-fuente">{row['Fuente']}</div>
        </div>
        """
        st.markdown(html_noticia, unsafe_allow_html=True)

# --- SOLAPA 2: GOOGLE TRENDS ---
with tab2:
    st.markdown("#### Termómetro de Búsquedas (Argentina)")
    st.caption("Buscando picos de interés actuales en Google...")
    
    try:
        pytrends = TrendReq(hl='es-AR', tz=180)
        kw_list = ["Jubilados", "Subte", "Paro"]
        pytrends.build_payload(kw_list, cat=0, timeframe='now 7-d', geo='AR')
        tendencias = pytrends.interest_over_time()
        
        if not tendencias.empty:
            st.line_chart(tendencias[kw_list])
        else:
            st.warning("Recolectando datos. Intente nuevamente en unos minutos.")
    except Exception as e:
        st.info("Conectando con la API de Google Trends... (Si el error persiste, intente más tarde).")

# --- SOLAPA 3: PREDICTOR ---
with tab3:
    st.markdown("#### Simulador de Rendimiento (Algoritmo 1091)")
    texto_tuit = st.text_area("Borrador del posteo:")
    
    col1, col2 = st.columns(2)
    with col1:
        porcentaje_datos = st.slider("Proporción Datos Duros (%)", 0, 100, 30)
    with col2:
        confronta = st.checkbox("¿Confronta con oficialismo (LLA/PRO)?")

    if st.button("Calcular Score Estratégico"):
        if 20 <= porcentaje_datos <= 40 and not confronta:
            st.success("✅ Score: 85/100. Balance militante/técnico óptimo.")
        elif confronta:
            st.warning("⚠️ Score: 70/100. Alto alcance esperado, pero riesgo de polarización. Reforzar con datos.")
        else:
            st.error("❌ Score: 40/100. Fuera del parámetro estratégico 70/30.")
