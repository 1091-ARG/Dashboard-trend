import streamlit as st
import feedparser
import pandas as pd
import anthropic
import smtplib
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Centro de Monitoreo", layout="wide", initial_sidebar_state="expanded")

if "db_rendimiento" not in st.session_state:
    st.session_state["db_rendimiento"] = []

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1E1E1E; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E0E0E0; }
    h1, h2, h3, h4 { color: #1E1E1E !important; font-weight: 600; }
    p, span, div { color: #333333 !important; }
    a { color: #2B547E !important; font-weight: 500; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .stButton > button { background-color: #2C3E50 !important; color: #FFFFFF !important; font-weight: bold !important; border-radius: 6px !important; border: none !important; }
    .stButton > button * { color: #FFFFFF !important; }
    .stButton > button:hover { background-color: #1A252F !important; }
    .stTextInput input, .stTextArea textarea, .stNumberInput input { background-color: #FFFFFF !important; color: #1E1E1E !important; border: 1px solid #CCCCCC !important; }
    hr { border-color: #E0E0E0; }
    .sidebar-title { font-size: 20px; font-weight: bold; color: #2C3E50; padding-bottom: 16px; text-align: center; text-transform: uppercase; letter-spacing: 1px; }
    .evento-card { background-color: #FFFFFF; padding: 15px; border-radius: 8px; border-left: 5px solid #e89a3c; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 15px; }
    .perfil-header { background: linear-gradient(135deg, #2C3E50, #3d5a73); color: white; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; }
    .perfil-nombre { font-size: 22px; font-weight: 700; color: white !important; margin: 0; }
    .perfil-meta { font-size: 13px; color: #b0c4d8 !important; margin-top: 4px; }
    .insight-box { background: #f0f7ff; border-left: 4px solid #2B547E; padding: 16px 20px; border-radius: 8px; margin-top: 16px; }
    .fuente-tag { font-size: 11px; color: #888 !important; background: #f0f0f0; padding: 2px 8px; border-radius: 10px; display: inline-block; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  CREDENCIALES
# ══════════════════════════════════════════════════════════════════════════════

try:
    ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
except:
    ANTHROPIC_API_KEY = ""

try:
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]
    MAIL_DESTINO = st.secrets.get("MAIL_DESTINO", "correo@ejemplo.com")
except:
    GMAIL_USER = GMAIL_APP_PASSWORD = ""
    MAIL_DESTINO = "correo@ejemplo.com"

PALABRAS_CLAVE = ["jubilados", "femicidio", "terremoto", "tragedia", "muerte", "protesta",
                  "corrupción", "corrupcion", "paro", "represión", "represion", "escándalo", "inundación"]
CUTOFF_HORAS = 24
TOP_NOTICIAS = 8

# ══════════════════════════════════════════════════════════════════════════════
#  FEEDS RSS
# ══════════════════════════════════════════════════════════════════════════════

RSS_FEEDS = {
    "CENTRO Y ESPINAZO": [
        "https://news.google.com/rss/search?q=site:lavoz.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:lagaceta.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:rionegro.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:losandes.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:lacapital.com.ar&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "LITORAL": [
        "https://news.google.com/rss/search?q=site:rosario3.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:ellitoral.com&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "CUYO": [
        "https://news.google.com/rss/search?q=site:mdzol.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:diariodecuyo.com.ar&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "NOA": [
        "https://news.google.com/rss/search?q=site:eltribuno.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:elliberal.com.ar&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "NEA": [
        "https://news.google.com/rss/search?q=site:elterritorio.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:diarionorte.com&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "PATAGONIA": [
        "https://news.google.com/rss/search?q=site:lmneuquen.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:diariojornada.com.ar&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "INTERIOR BONAERENSE": [
        "https://news.google.com/rss/search?q=site:lanueva.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:eldia.com&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "CABA y Rosca": [
        "https://news.google.com/rss/search?q=Legislatura+Buenos+Aires+pol%C3%ADtica&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:lapoliticaonline.com+CABA&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "POLÍTICA NACIONAL": [
        "https://www.infobae.com/politica/feed/",
        "https://www.pagina12.com.ar/rss/secciones/el-pais/notas",
        "https://www.ambito.com/rss/politica.xml",
    ],
}

REGION_CONTEXTO = {
    "CENTRO Y ESPINAZO": "las provincias de Córdoba, Tucumán, Mendoza, Río Negro/Neuquén y Santa Fe (Rosario)",
    "LITORAL": "las provincias de Santa Fe y Entre Ríos",
    "CUYO": "las provincias de Mendoza, San Juan y San Luis",
    "NOA": "las provincias de Salta, Jujuy, Tucumán, Santiago del Estero y Catamarca",
    "NEA": "las provincias de Misiones, Chaco, Corrientes y Formosa",
    "PATAGONIA": "las provincias de Neuquén, Río Negro, Chubut, Santa Cruz y Tierra del Fuego",
    "INTERIOR BONAERENSE": "el interior de la provincia de Buenos Aires",
    "CABA y Rosca": "la Ciudad Autónoma de Buenos Aires: Legislatura, comunas, legisladores",
    "POLÍTICA NACIONAL": "la política nacional argentina",
}

# ══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES BASE
# ══════════════════════════════════════════════════════════════════════════════

def es_reciente(entry):
    for campo in ("published", "updated"):
        raw = entry.get(campo, "")
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt) <= timedelta(hours=CUTOFF_HORAS)
        except:
            continue
    return True

def obtener_noticias_crudas(urls, max_por_feed=8):
    noticias = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= max_por_feed:
                    break
                if not es_reciente(entry):
                    continue
                noticias.append({
                    "Título": entry.get("title", "Sin título").strip(),
                    "Link": entry.get("link", "#"),
                })
                count += 1
        except:
            continue
    seen, unicas = set(), []
    for n in noticias:
        if n["Título"] not in seen:
            seen.add(n["Título"])
            unicas.append(n)
    return unicas

def detectar_palabras_clave(titulo):
    t = titulo.lower()
    return [p for p in PALABRAS_CLAVE if p in t]

def extraer_json_seguro(texto):
    try:
        start = texto.find("{")
        end = texto.rfind("}")
        if start != -1 and end != -1:
            return json.loads(texto[start:end+1])
    except:
        pass
    return None

def enviar_mail(asunto, cuerpo_html):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return False, "Faltan credenciales de Gmail."
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"], msg["From"], msg["To"] = asunto, GMAIL_USER, MAIL_DESTINO
        msg.attach(MIMEText(cuerpo_html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True, "Mail enviado correctamente."
    except Exception as e:
        return False, str(e)

# ══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES IA
# ══════════════════════════════════════════════════════════════════════════════

def ia_curar_regional(noticias_lista, contexto_region, top=TOP_NOTICIAS):
    if not ANTHROPIC_API_KEY:
        return None, "Falta API key de Anthropic."
    if not noticias_lista:
        return [], None
    titles = "\n".join([f"[{i}] {n['Título']}" for i, n in enumerate(noticias_lista)])
    prompt = f"""Sos el Jefe de Redacción escaneando medios de {contexto_region}.
Elegí las {top} noticias de MAYOR IMPACTO. Buscás: tragedias, femicidios, desastres, protestas masivas, escándalos de corrupción, conflictos políticos locales reales.
DESCARTÁ: noticias locales blandas, fútbol, farándula, temas nacionales replicados genéricamente.
Devolvé SOLO JSON sin markdown: {{"top": [{{"idx": número, "porque": "impacto, max 12 palabras"}}]}}

Noticias:
{titles}"""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        data = extraer_json_seguro(msg.content[0].text)
        return (data["top"] if data else []), None
    except Exception as e:
        return None, str(e)

def generar_digest():
    todas = []
    for region, urls in RSS_FEEDS.items():
        for n in obtener_noticias_crudas(urls, max_por_feed=2):
            todas.append(n)
    if not todas:
        return None
    seen, unicas = set(), []
    for n in todas:
        if n["Título"] not in seen:
            seen.add(n["Título"])
            unicas.append(n)
    top, err = ia_curar_regional(unicas, "toda la Argentina, buscando impacto nacional fuerte", top=TOP_NOTICIAS)
    if err or not top:
        return None
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = f"<h2>📡 Digest — {hoy}</h2><p>Las {TOP_NOTICIAS} noticias de mayor impacto:</p>"
    for item in top:
        n = unicas[item["idx"]]
        html += f"<p><b><a href='{n['Link']}'>{n['Título']}</a></b><br><i style='color:#555'>{item['porque']}</i></p>"
    return html

# ══════════════════════════════════════════════════════════════════════════════
#  TENDENCIAS — SISTEMA TRIPLE RESPALDO
# ══════════════════════════════════════════════════════════════════════════════

def scrape_trends24():
    """Fuente 1: Trends24.in — trending topics de X Argentina."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get("https://trends24.in/argentina/", headers=headers, timeout=8)
        if r.status_code != 200:
            return []
        from html.parser import HTMLParser
        class TrendParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.trends = []
                self.in_trend = False
            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == "a" and "trend-link" in attrs_dict.get("class", ""):
                    self.in_trend = True
            def handle_data(self, data):
                if self.in_trend and data.strip():
                    self.trends.append(data.strip())
                    self.in_trend = False
        parser = TrendParser()
        parser.feed(r.text)
        return parser.trends[:20] if parser.trends else []
    except:
        return []

def scrape_getdaytrends():
    """Fuente 2: Getdaytrends.com — segunda fuente de X Argentina."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get("https://getdaytrends.com/es/argentina/", headers=headers, timeout=8)
        if r.status_code != 200:
            return []
        from html.parser import HTMLParser
        class TrendParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.trends = []
                self.capture = False
            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                cls = attrs_dict.get("class", "")
                if tag in ("td", "span") and ("trend" in cls.lower() or "main" in cls.lower()):
                    self.capture = True
            def handle_data(self, data):
                if self.capture and data.strip() and data.strip().startswith("#"):
                    self.trends.append(data.strip())
                    self.capture = False
            def handle_endtag(self, tag):
                self.capture = False
        parser = TrendParser()
        parser.feed(r.text)
        return list(dict.fromkeys(parser.trends))[:20]
    except:
        return []

def ia_web_search_tendencias():
    """Fuente 3: Búsqueda web IA — solo se activa si las dos anteriores fallan."""
    if not ANTHROPIC_API_KEY:
        return [], "Sin API key"
    hoy = datetime.now().strftime("%d/%m/%Y")
    prompt = f"""Hoy es {hoy}. Buscá AHORA MISMO qué hashtags y temas están siendo tendencia en X (Twitter) Argentina en este momento. Buscá en tiempo real, no uses datos de tu entrenamiento.

Devolvé SOLO JSON sin markdown:
{{"tendencias": ["#tema1", "#tema2", "tema3"]}}

Dame entre 8 y 15 temas/hashtags reales de hoy."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        texto = "".join([b.text for b in msg.content if hasattr(b, "text")])
        data = extraer_json_seguro(texto)
        if data and "tendencias" in data:
            return data["tendencias"], None
        return [], None
    except Exception as e:
        return [], str(e)

def ia_filtrar_tendencias(trends_raw, fuente):
    """La IA filtra el ruido (fútbol/farándula) y da el ángulo político de cada tema."""
    if not ANTHROPIC_API_KEY or not trends_raw:
        return None, "Sin datos o sin API key"
    lista = "\n".join([f"- {t}" for t in trends_raw])
    prompt = f"""Tenés esta lista de trending topics de X Argentina (fuente: {fuente}):
{lista}

Filtrá SOLO los que tengan impacto político, económico, social o de tragedia. IGNORÁ partidos de fútbol, deportes, cantantes, actores. Si no queda nada relevante, devolvé lista vacía.

Para cada uno, asigná un nivel real y un ángulo de contenido político.

Devolvé SOLO JSON sin markdown:
{{"filtrados": [{{"tema": "#hashtag o tema", "nivel": "explotando|subiendo|estable", "angulo": "por qué importa políticamente, 1 oración"}}]}}"""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        data = extraer_json_seguro(msg.content[0].text)
        return (data["filtrados"] if data else []), None
    except Exception as e:
        return None, str(e)

def obtener_tendencias_con_respaldo():
    """Sistema triple: prueba fuente 1, si falla fuente 2, si falla fuente 3. Si las 3 fallan, avisa."""
    # Fuente 1
    trends = scrape_trends24()
    if trends:
        return trends, "Trends24 (X Argentina)"
    # Fuente 2
    trends = scrape_getdaytrends()
    if trends:
        return trends, "GetDayTrends (X Argentina)"
    # Fuente 3
    trends, err = ia_web_search_tendencias()
    if trends:
        return trends, "Búsqueda web en tiempo real"
    # Todo falló
    return [], None

def emoji_nivel(nivel):
    n = str(nivel).lower()
    if "explot" in n: return "🔴 EXPLOTANDO"
    if "sub" in n: return "🟠 SUBIENDO"
    if "estable" in n: return "🟡 ESTABLE"
    return "⚪ SIN DATO"

# ══════════════════════════════════════════════════════════════════════════════
#  LABORATORIO DE AUDIENCIAS — ANÁLISIS CON GRÁFICOS
# ══════════════════════════════════════════════════════════════════════════════

def ia_analizar_perfil(datos_csv, nombre_perfil):
    """La IA analiza el historial de un perfil y devuelve categorías, tono y recomendaciones."""
    if not ANTHROPIC_API_KEY:
        return None, "Falta API key de Anthropic."
    prompt = f"""Sos un analista de comunicación política. Tenés el historial de posteos de {nombre_perfil}:

{datos_csv}

Analizá el patrón de engagement (Interacciones/Impresiones) y clasificá cada posteo.

Devolvé SOLO JSON sin markdown con esta estructura exacta:
{{
  "distribucion_temas": {{
    "Economía": número_porcentaje,
    "Derechos Sociales": número_porcentaje,
    "Seguridad": número_porcentaje,
    "Salud": número_porcentaje,
    "Gestión/Obras": número_porcentaje,
    "Confrontación": número_porcentaje,
    "Otro": número_porcentaje
  }},
  "distribucion_tono": {{
    "Agresivo/Confrontativo": número_porcentaje,
    "Conciliador": número_porcentaje,
    "Constructivo/Propositivo": número_porcentaje,
    "Informativo": número_porcentaje
  }},
  "distribucion_contenido": {{
    "Datos Duros": número_porcentaje,
    "Militancia": número_porcentaje,
    "Denuncia": número_porcentaje,
    "Gestión": número_porcentaje
  }},
  "insight_general": "Párrafo de 3-4 oraciones analizando qué le rinde más, cuál es su actitud predominante, su rol en la conversación pública y una recomendación táctica concreta.",
  "temas_exitosos": ["tema que más le rindió 1", "tema que más le rindió 2"],
  "actitud_predominante": "Agresivo|Conciliador|Constructivo|Informativo"
}}

Los porcentajes de cada distribución deben sumar 100."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        data = extraer_json_seguro(msg.content[0].text)
        return data, None
    except Exception as e:
        return None, str(e)

# ══════════════════════════════════════════════════════════════════════════════
#  MENÚ LATERAL
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<p class="sidebar-title">CENTRO DE MONITOREO</p>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555; font-size:13px;'>Panel de Control</p>", unsafe_allow_html=True)
    st.divider()
    menu = st.radio("", [
        "📰 Radar de Impacto Federal",
        "🔥 Tendencias (Triple Respaldo)",
        "🎯 Radar de Menciones",
        "🔮 Predicción y Agenda",
        "🤖 Evaluador de Contenido",
        "🧠 Laboratorio de Audiencias",
        "📧 Alertas y Reportes",
    ])
    st.divider()
    st.caption("Motor: IA Activa")
    st.caption("Tendencias: Triple Respaldo")

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINAS
# ══════════════════════════════════════════════════════════════════════════════

if menu == "📰 Radar de Impacto Federal":
    st.header("📰 Radar de Impacto Federal")
    st.markdown("La IA filtra los medios regionales buscando noticias de alto impacto.")
    reg = st.selectbox("Seleccionar Región:", list(RSS_FEEDS.keys()))
    if st.button("Escanear Región", use_container_width=True):
        if not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic.")
        else:
            with st.spinner(f"Escaneando medios en {reg}..."):
                crudas = obtener_noticias_crudas(RSS_FEEDS[reg], max_por_feed=10)
                top, err = ia_curar_regional(crudas, REGION_CONTEXTO[reg])
            if err:
                st.error(err)
            elif not top:
                st.info(f"No se detectaron noticias de impacto en {reg} en las últimas {CUTOFF_HORAS}hs.")
            else:
                st.caption(f"{len(top)} noticias seleccionadas de {len(crudas)} leídas")
                for item in top:
                    n = crudas[item["idx"]]
                    claves = detectar_palabras_clave(n["Título"])
                    marca = " 🚨 **" + ", ".join(claves).upper() + "**" if claves else ""
                    st.markdown(f"#### [{n['Título']}]({n['Link']}){marca}")
                    st.markdown(f"> *{item['porque']}*")
                    st.divider()

elif menu == "🔥 Tendencias (Triple Respaldo)":
    st.header("🔥 Tendencias Virales de Argentina")
    st.markdown("Sistema de **triple respaldo**: Trends24 → GetDayTrends → Búsqueda web IA. Si las 3 fuentes fallan, avisa claramente — nunca inventa ni tira datos viejos.")
    if st.button("Escanear Tendencias Ahora", use_container_width=True):
        if not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic.")
        else:
            with st.spinner("Probando fuentes en orden... Trends24 → GetDayTrends → Web Search IA"):
                trends_raw, fuente = obtener_tendencias_con_respaldo()
            if not trends_raw:
                st.error("❌ Las 3 fuentes fallaron. No hay datos de tendencias disponibles ahora. Intentá en unos minutos.")
            else:
                st.success(f"✅ Datos obtenidos desde: **{fuente}**")
                with st.spinner("Filtrando ruido y analizando ángulo político..."):
                    filtrados, err = ia_filtrar_tendencias(trends_raw, fuente)
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown(f"### 🌐 Raw desde {fuente}")
                    for t in trends_raw[:15]:
                        st.markdown(f"- {t}")
                with col2:
                    st.markdown("### 🤖 Curaduría Política IA")
                    if err or not filtrados:
                        st.info("Hoy la agenda viral es puro deporte/farándula. No hay tendencias con impacto político.")
                    else:
                        for u in filtrados:
                            nivel = emoji_nivel(u.get("nivel", ""))
                            st.success(f"**{u.get('tema', '')}**  ·  {nivel}")
                            st.markdown(f"💡 {u.get('angulo', '')}")
                            st.divider()

elif menu == "🎯 Radar de Menciones":
    st.header("🎯 Radar de Menciones")
    rival = st.text_input("Nombre o palabra clave a monitorear:", placeholder="Ej: Jorge Macri, jubilados...")
    if st.button("Rastrear Menciones", use_container_width=True) and rival.strip():
        url = f"https://news.google.com/rss/search?q=%22{rival.replace(' ', '+')}%22&hl=es-419&gl=AR&ceid=AR:es"
        with st.spinner(f"Buscando noticias sobre {rival}..."):
            crudas = obtener_noticias_crudas([url], max_por_feed=12)
        if not crudas:
            st.warning(f"No se encontraron noticias recientes sobre {rival}.")
        else:
            st.caption(f"{len(crudas)} noticias encontradas (últimas {CUTOFF_HORAS}hs)")
            for n in crudas:
                st.markdown(f"🔸 [{n['Título']}]({n['Link']})")

elif menu == "🔮 Predicción y Agenda":
    st.header("🔮 Calendario de Agenda y Predicción")
    st.markdown("El sistema lee los medios de hoy y arma el calendario táctico de la semana.")
    if st.button("Generar Calendario y Predicción", use_container_width=True):
        if not ANTHROPIC_API_KEY:
            st.error("Falta API key de Anthropic.")
        else:
            with st.spinner("Rastreando eventos y armando la agenda..."):
                urls_ctx = RSS_FEEDS["POLÍTICA NACIONAL"] + RSS_FEEDS["CABA y Rosca"]
                noticias_ctx = obtener_noticias_crudas(urls_ctx, max_por_feed=8)
                contexto_texto = "\n".join([f"- {n['Título']}" for n in noticias_ctx])
            if not contexto_texto:
                st.warning("No hay suficientes noticias frescas para armar la agenda.")
            else:
                prompt = f"""Sos un secretario de inteligencia política armando la agenda táctica.
Titulares de las últimas 24 horas:
{contexto_texto}

TAREA 1: Detectá eventos futuros (sesiones, paros, indagatorias, marchas, debates).
TAREA 2: Deducí 3 ejes de conflicto que dominarán la conversación esta semana.

Devolvé SOLO JSON sin markdown:
{{
  "agenda_concreta": [{{"tiempo": "cuándo", "evento": "qué es", "explicacion": "por qué importa"}}],
  "ejes_estrategicos": [{{"titulo": "nombre del eje", "conflicto": "qué va a pasar", "tip": "qué hacer"}}]
}}"""
                try:
                    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                    msg = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=1500,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    data = extraer_json_seguro(msg.content[0].text)
                    if not data:
                        st.error("No se pudo interpretar la respuesta. Intentá de nuevo.")
                    else:
                        st.success("✅ Agenda generada.")
                        st.markdown("### 📅 Eventos Detectados")
                        if not data.get("agenda_concreta"):
                            st.info("No se detectaron eventos con fecha concreta en los titulares de hoy.")
                        else:
                            for ev in data["agenda_concreta"]:
                                st.markdown(f"""<div class="evento-card">
                                    <span style='color:#e89a3c; font-weight:bold;'>🗓️ {ev.get('tiempo','').upper()}</span><br>
                                    <span style='font-size:17px; font-weight:bold; color:#2C3E50;'>{ev.get('evento','')}</span><br>
                                    <span style='color:#555;'>📝 <i>{ev.get('explicacion','')}</i></span>
                                </div>""", unsafe_allow_html=True)
                        st.markdown("### 🎯 Ejes de Conflicto")
                        for eje in data.get("ejes_estrategicos", []):
                            st.markdown(f"#### {eje.get('titulo','')}")
                            st.markdown(f"**💥 El conflicto:** {eje.get('conflicto','')}")
                            st.markdown(f"**💡 Tip:** {eje.get('tip','')}")
                            st.markdown("")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

elif menu == "🤖 Evaluador de Contenido":
    st.header("🤖 Evaluador Estratégico de Contenido")
    t = st.text_area("Pegá el borrador del texto:", height=150)
    if st.button("Evaluar Texto", use_container_width=True):
        if not t.strip():
            st.warning("Escribí algo primero.")
        elif not ANTHROPIC_API_KEY:
            st.error("Falta API key de Anthropic.")
        else:
            with st.spinner("Analizando..."):
                prompt = f"""Sos un editor de comunicación política. Evaluá este texto: "{t}".
Devolvé SOLO JSON sin markdown: {{"score": número 0-100, "veredicto": "frase corta", "fortalezas": ["f1", "f2"], "mejoras": ["m1", "m2"], "plataforma_ideal": "X / Instagram / LinkedIn"}}"""
                try:
                    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                    msg = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=600,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    data = extraer_json_seguro(msg.content[0].text)
                    if data:
                        score = data.get("score", 0)
                        if score >= 75: st.success(f"✅ Score: {score}/100 — {data.get('veredicto','')}")
                        elif score >= 50: st.warning(f"⚠️ Score: {score}/100 — {data.get('veredicto','')}")
                        else: st.error(f"❌ Score: {score}/100 — {data.get('veredicto','')}")
                        st.info(f"📱 **Plataforma ideal:** {data.get('plataforma_ideal','')}")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("👍 **Puntos Fuertes:**")
                            for f in data.get("fortalezas", []): st.markdown(f"- {f}")
                        with c2:
                            st.markdown("🔧 **A mejorar:**")
                            for m in data.get("mejoras", []): st.markdown(f"- {m}")
                    else:
                        st.error("No se pudo procesar la respuesta.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

elif menu == "🧠 Laboratorio de Audiencias":
    st.header("🧠 Laboratorio de Perfiles y Audiencias")
    st.markdown("Cargá posteos de cualquier figura pública y la IA analiza qué le rinde, su tono predominante y su rol político.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Cargar nuevo registro")
        perfil = st.text_input("👤 Nombre del perfil:", placeholder="Ej: @MairaMendoza")
        cargo = st.text_input("🏛️ Cargo:", placeholder="Ej: Diputada Nacional")
        organizacion = st.text_input("🏢 Organización/Partido:", placeholder="Ej: Unión por la Patria")
        alianzas = st.text_input("🤝 Aliado/a a:", placeholder="Ej: Kirchnerismo / Massa")
        imagen_subida = st.file_uploader("📸 Captura del posteo (Opcional)", type=["png", "jpg", "jpeg"])
        if imagen_subida:
            st.image(imagen_subida, caption="Captura cargada", use_container_width=True)
        tema_texto = st.text_area("✍️ Tema o texto del posteo:", placeholder="Ej: Recorrida por obras hidráulicas...")
        col_imp, col_int = st.columns(2)
        with col_imp:
            imp = st.number_input("Impresiones", min_value=0, value=0)
        with col_int:
            int_ = st.number_input("Interacciones", min_value=0, value=0)

        if st.button("Guardar en Historial", use_container_width=True):
            if not perfil.strip():
                st.error("Ponele nombre al perfil.")
            elif imp > 0 and tema_texto.strip():
                eng = round((int_ / imp) * 100, 2)
                st.session_state["db_rendimiento"].append({
                    "Perfil": perfil.strip(),
                    "Cargo": cargo.strip(),
                    "Organización": organizacion.strip(),
                    "Alianzas": alianzas.strip(),
                    "Tema/Texto": tema_texto.strip(),
                    "Impresiones": imp,
                    "Interacciones": int_,
                    "Engagement (%)": eng,
                })
                st.success(f"✅ Guardado. Engagement: {eng}%")
            else:
                st.error("Completá el texto y las impresiones.")

    with col2:
        st.markdown("### Base de datos histórica")
        df = pd.DataFrame(st.session_state["db_rendimiento"])
        if not df.empty:
            st.dataframe(df[["Perfil", "Cargo", "Organización", "Tema/Texto", "Engagement (%)"]], use_container_width=True)
        else:
            st.info("Todavía no hay registros. Cargá ejemplos a la izquierda.")

    st.divider()

    # ── ANÁLISIS COMPLETO POR PERFIL ──
    if not df.empty if "df" in dir() else not pd.DataFrame(st.session_state["db_rendimiento"]).empty:
        df = pd.DataFrame(st.session_state["db_rendimiento"])
        st.markdown("## 📊 Análisis por Perfil")
        perfiles_disponibles = df["Perfil"].unique().tolist()
        perfil_analizar = st.selectbox("Seleccioná el perfil a analizar:", perfiles_disponibles)

        if st.button("Generar Análisis Completo con IA", use_container_width=True):
            if not ANTHROPIC_API_KEY:
                st.error("Falta la API key de Anthropic.")
            else:
                datos_perfil = df[df["Perfil"] == perfil_analizar]
                datos_csv = datos_perfil[["Tema/Texto", "Impresiones", "Interacciones", "Engagement (%)"]].to_csv(index=False)

                # Datos del perfil
                meta = datos_perfil.iloc[0]
                cargo_p = meta.get("Cargo", "")
                org_p = meta.get("Organización", "")
                ali_p = meta.get("Alianzas", "")

                with st.spinner("La IA está analizando el patrón de audiencia..."):
                    data, err = ia_analizar_perfil(datos_csv, perfil_analizar)

                if err or not data:
                    st.error(f"No se pudo analizar: {err}")
                else:
                    # Header del perfil
                    st.markdown(f"""<div class="perfil-header">
                        <div class="perfil-nombre">{perfil_analizar}</div>
                        <div class="perfil-meta">{cargo_p} · {org_p} · Aliado/a: {ali_p}</div>
                        <div class="perfil-meta">{len(datos_perfil)} registros analizados · Engagement promedio: {datos_perfil['Engagement (%)'].mean():.2f}%</div>
                    </div>""", unsafe_allow_html=True)

                    # Tres gráficos de torta en paralelo
                    try:
                        import plotly.graph_objects as go

                        temas = data.get("distribucion_temas", {})
                        tono = data.get("distribucion_tono", {})
                        contenido = data.get("distribucion_contenido", {})

                        col_g1, col_g2, col_g3 = st.columns(3)

                        COLORS = ["#2C3E50", "#e89a3c", "#3d5a73", "#c0392b", "#27ae60", "#8e44ad", "#95a5a6"]

                        with col_g1:
                            st.markdown("#### Temas")
                            if temas:
                                fig1 = go.Figure(go.Pie(
                                    labels=list(temas.keys()),
                                    values=list(temas.values()),
                                    hole=0.3,
                                    marker_colors=COLORS,
                                    textfont_size=13,
                                ))
                                fig1.update_layout(
                                    height=380,
                                    margin=dict(t=20, b=20, l=10, r=10),
                                    showlegend=True,
                                    legend=dict(font=dict(size=11)),
                                )
                                st.plotly_chart(fig1, use_container_width=True)

                        with col_g2:
                            st.markdown("#### Tono")
                            if tono:
                                fig2 = go.Figure(go.Pie(
                                    labels=list(tono.keys()),
                                    values=list(tono.values()),
                                    hole=0.3,
                                    marker_colors=["#c0392b", "#27ae60", "#2980b9", "#e89a3c"],
                                    textfont_size=13,
                                ))
                                fig2.update_layout(
                                    height=380,
                                    margin=dict(t=20, b=20, l=10, r=10),
                                    showlegend=True,
                                    legend=dict(font=dict(size=11)),
                                )
                                st.plotly_chart(fig2, use_container_width=True)

                        with col_g3:
                            st.markdown("#### Tipo de contenido")
                            if contenido:
                                fig3 = go.Figure(go.Pie(
                                    labels=list(contenido.keys()),
                                    values=list(contenido.values()),
                                    hole=0.3,
                                    marker_colors=["#8e44ad", "#e89a3c", "#c0392b", "#27ae60"],
                                    textfont_size=13,
                                ))
                                fig3.update_layout(
                                    height=380,
                                    margin=dict(t=20, b=20, l=10, r=10),
                                    showlegend=True,
                                    legend=dict(font=dict(size=11)),
                                )
                                st.plotly_chart(fig3, use_container_width=True)

                    except ImportError:
                        st.warning("Instalá plotly para ver los gráficos: agregá 'plotly' al requirements.txt")

                    # Insight de la IA
                    st.markdown(f"""<div class="insight-box">
                        <b>🧠 Análisis IA — {perfil_analizar}</b><br><br>
                        {data.get('insight_general', '')}
                        <br><br>
                        <b>Temas que más le rinden:</b> {', '.join(data.get('temas_exitosos', []))} &nbsp;|&nbsp;
                        <b>Actitud predominante:</b> {data.get('actitud_predominante', '')}
                    </div>""", unsafe_allow_html=True)

elif menu == "📧 Alertas y Reportes":
    st.header("📧 Centro de Envíos y Alertas")
    st.markdown("### 1. Generar Digest")
    if st.button("Generar y Enviar Digest", use_container_width=True):
        if not ANTHROPIC_API_KEY or not GMAIL_APP_PASSWORD:
            st.error("Faltan claves de API o Mail en los Secrets.")
        else:
            with st.spinner("Compilando noticias..."):
                html = generar_digest()
            if html:
                ok, msg = enviar_mail(f"📡 Digest — Top {TOP_NOTICIAS} Impacto", html)
                if ok:
                    st.success(msg)
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.error(msg)
            else:
                st.error("No se pudo generar el digest.")

    st.divider()
    st.markdown("### 2. Escáner de Palabras Clave")
    st.caption("Palabras gatillo: " + ", ".join(PALABRAS_CLAVE))
    if st.button("Escanear Ahora", use_container_width=True):
        with st.spinner("Rastreando palabras clave..."):
            alertas = []
            for urls in RSS_FEEDS.values():
                for n in obtener_noticias_crudas(urls, 5):
                    claves = detectar_palabras_clave(n["Título"])
                    if claves:
                        alertas.append((n["Título"], n["Link"], claves))
        if alertas:
            html = "<h2>🚨 Alertas Detectadas</h2>" + "".join(
                [f"<p><b><a href='{l}'>{t}</a></b> <span style='color:#D32F2F'>[{', '.join(c).upper()}]</span></p>"
                 for t, l, c in alertas]
            )
            ok, msg = enviar_mail(f"🚨 {len(alertas)} Alertas", html)
            if ok:
                st.success(f"✅ {len(alertas)} alertas enviadas por mail.")
            else:
                st.error(f"❌ {msg}")
        else:
            st.info("No se detectaron palabras clave en este momento.")
