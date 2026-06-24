import streamlit as st
import feedparser
import pandas as pd
import anthropic
import smtplib
import json
import requests
import base64
import io
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

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
    .sidebar-title { font-size: 22px; font-weight: bold; color: #2C3E50; padding-bottom: 20px; text-align: center; text-transform: uppercase; letter-spacing: 1px; }
    .news-card { background-color: #FFFFFF; padding: 14px 18px; border-radius: 10px; border-left: 4px solid #2C3E50; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 10px; }
    .news-nuevo { border-left-color: #c0392b !important; background-color: #fff8f7 !important; }
    .news-madrugada { border-left-color: #8e44ad !important; background-color: #faf7fc !important; }
    .tag { font-size: 12px; font-weight: 700; padding: 2px 10px; border-radius: 12px; display: inline-block; margin-bottom: 4px; }
    .tag-nuevo { background: #fdecea; color: #c0392b !important; }
    .tag-madrugada { background: #f3eafa; color: #8e44ad !important; }
    .tag-normal { background: #eef0f2; color: #555 !important; }
    .perfil-header { background: linear-gradient(135deg, #2C3E50, #3d5a73); color: white; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; }
    .perfil-nombre { font-size: 22px; font-weight: 700; color: white !important; }
    .perfil-meta { font-size: 13px; color: #b0c4d8 !important; margin-top: 4px; }
    .insight-box { background: #f0f7ff; border-left: 4px solid #2B547E; padding: 16px 20px; border-radius: 8px; margin-top: 16px; }
    .evento-card { background-color: #FFFFFF; padding: 15px; border-radius: 8px; border-left: 5px solid #e89a3c; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# ── CREDENCIALES ──
try: ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
except: ANTHROPIC_API_KEY = ""
try:
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]
    MAIL_DESTINO = st.secrets.get("MAIL_DESTINO", "correo@ejemplo.com")
except: GMAIL_USER = GMAIL_APP_PASSWORD = ""; MAIL_DESTINO = "correo@ejemplo.com"
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
except: GITHUB_TOKEN = GITHUB_REPO = ""

PALABRAS_CLAVE = ["jubilados", "femicidio", "terremoto", "tragedia", "muerte", "protesta",
                  "corrupción", "corrupcion", "paro", "represión", "represion", "escándalo",
                  "inundación", "adorni", "presupuesto", "cristina", "milei"]

CUTOFF_HORAS = 15
TOP_NOTICIAS = 15
PATH_INBOX   = "noticias_inbox.csv"
PATH_AUDIENCIA = "datos_audiencia.csv"

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
        "https://news.google.com/rss/search?q=site:letrap.com.ar&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "POLÍTICA NACIONAL": [
        "https://www.infobae.com/politica/feed/",
        "https://www.pagina12.com.ar/rss/secciones/el-pais/notas",
        "https://www.ambito.com/rss/politica.xml",
        "https://news.google.com/rss/search?q=site:clarin.com+pol%C3%ADtica&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:lanacion.com.ar+pol%C3%ADtica&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:eldestapeweb.com&hl=es-419&gl=AR&ceid=AR:es",
    ],
}
REGION_CONTEXTO = {
    "CENTRO Y ESPINAZO": "las provincias de Córdoba, Tucumán, Mendoza, Río Negro/Neuquén y Santa Fe",
    "LITORAL": "las provincias de Santa Fe y Entre Ríos",
    "CUYO": "las provincias de Mendoza, San Juan y San Luis",
    "NOA": "las provincias de Salta, Jujuy, Tucumán, Santiago del Estero y Catamarca",
    "NEA": "las provincias de Misiones, Chaco, Corrientes y Formosa",
    "PATAGONIA": "las provincias de Neuquén, Río Negro, Chubut, Santa Cruz y Tierra del Fuego",
    "INTERIOR BONAERENSE": "el interior de la provincia de Buenos Aires",
    "CABA y Rosca": "la Ciudad Autónoma de Buenos Aires: Legislatura, comunas, legisladores",
    "POLÍTICA NACIONAL": "la política nacional argentina",
}

# ══ FUNCIONES GITHUB ══
def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def cargar_csv_github(path):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return pd.DataFrame(), None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    try:
        r = requests.get(url, headers=github_headers(), timeout=10)
        if r.status_code == 200:
            info = r.json()
            contenido = base64.b64decode(info["content"]).decode("utf-8")
            if not contenido.strip():
                return pd.DataFrame(), info["sha"]
            return pd.read_csv(io.StringIO(contenido)), info["sha"]
        return pd.DataFrame(), None
    except Exception:
        return pd.DataFrame(), None

def guardar_csv_github(path, df, mensaje):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "Faltan GITHUB_TOKEN o GITHUB_REPO."
    try:
        csv_texto = df.to_csv(index=False)
        contenido_b64 = base64.b64encode(csv_texto.encode("utf-8")).decode("utf-8")
        _, sha = cargar_csv_github(path)
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
        payload = {"message": mensaje, "content": contenido_b64}
        if sha:
            payload["sha"] = sha
        r = requests.put(url, headers=github_headers(), json=payload, timeout=10)
        if r.status_code in (200, 201):
            return True, "Guardado."
        return False, f"Error GitHub {r.status_code}: {r.json().get('message','')}"
    except Exception as e:
        return False, str(e)

# ══ FUNCIONES DE NOTICIAS — igual que el original que funcionaba ══
def es_reciente(entry):
    """Igual al original: devuelve True si no hay fecha (nunca descarta por falta de fecha)."""
    for campo in ("published", "updated"):
        raw = entry.get(campo, "")
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt) <= timedelta(hours=CUTOFF_HORAS)
        except Exception:
            continue
    return True  # sin fecha → se muestra siempre

def obtener_noticias_crudas(urls, max_por_feed=8):
    """Exactamente igual al original que funcionaba: feedparser.parse(url) directo."""
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
                    "titulo": entry.get("title", "Sin título").strip(),
                    "link": entry.get("link", "#"),
                    "fecha_pub": entry.get("published", "") or entry.get("updated", ""),
                })
                count += 1
        except Exception:
            continue
    seen, unicas = set(), []
    for n in noticias:
        if n["titulo"] not in seen:
            seen.add(n["titulo"])
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
    except Exception:
        pass
    return None

def hash_noticia(titulo):
    return hashlib.md5(titulo.encode("utf-8")).hexdigest()[:12]

def get_dt_pub(fecha_raw):
    """Parsea fecha de publicación de un string. Devuelve datetime o None."""
    if not fecha_raw or pd.isna(fecha_raw) if hasattr(pd, 'isna') else not fecha_raw:
        return None
    try:
        dt = parsedate_to_datetime(str(fecha_raw))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def etiqueta_tiempo(fecha_raw):
    """Genera tag visual según antigüedad y franja horaria."""
    dt = get_dt_pub(fecha_raw)
    if dt is None:
        return "tag-normal", "Sin fecha"
    ahora = datetime.now(timezone.utc)
    minutos = (ahora - dt).total_seconds() / 60
    horas = minutos / 60
    hora_local = (dt - timedelta(hours=3)).hour
    if minutos < 60:
        return "tag-nuevo", f"🔥 Hace {int(minutos)} min · NUEVO"
    elif 0 <= hora_local < 7:
        return "tag-madrugada", f"🌙 Madrugada · Hace {int(horas)}h"
    else:
        return "tag-normal", f"Hace {int(horas)}h"

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
        return True, "Mail enviado."
    except Exception as e:
        return False, str(e)

# ══ INBOX CON DESCARTE PERSISTENTE ══
def cargar_inbox():
    df, _ = cargar_csv_github(PATH_INBOX)
    if df.empty:
        return pd.DataFrame(columns=["id","titulo","link","region","fecha_pub","descartada"])
    return df

def guardar_en_inbox(region, noticias_nuevas):
    """Agrega noticias nuevas al inbox guardado en GitHub, sin duplicar."""
    inbox = cargar_inbox()
    ids_existentes = set(inbox["id"].astype(str)) if not inbox.empty else set()
    agregar = []
    for n in noticias_nuevas:
        nid = hash_noticia(n["titulo"])
        if nid not in ids_existentes:
            ids_existentes.add(nid)
            agregar.append({
                "id": nid, "titulo": n["titulo"], "link": n["link"],
                "region": region, "fecha_pub": n.get("fecha_pub",""),
                "descartada": False,
            })
    if agregar:
        inbox = pd.concat([inbox, pd.DataFrame(agregar)], ignore_index=True)
        guardar_csv_github(PATH_INBOX, inbox, f"Inbox {region} {datetime.now().strftime('%d/%m %H:%M')}")
    return inbox, len(agregar)

def descartar_noticia(nid):
    inbox = cargar_inbox()
    if not inbox.empty:
        inbox.loc[inbox["id"].astype(str) == str(nid), "descartada"] = True
        guardar_csv_github(PATH_INBOX, inbox, f"Leída {nid}")

# ══ FUNCIONES IA ══
def ia_curar_regional(noticias_lista, contexto_region, top=TOP_NOTICIAS):
    if not ANTHROPIC_API_KEY or not noticias_lista:
        return list(range(len(noticias_lista))), None
    titles = "\n".join([f"[{i}] {n['titulo']}" for i, n in enumerate(noticias_lista)])
    prompt = f"""Sos Jefe de Redacción de un medio federal cubriendo {contexto_region}.
Elegí las {top} noticias MÁS RELEVANTES políticamente. Priorizá poder provincial, corrupción, conflictos, gestión. Descartá fútbol y farándula.
Devolvé SOLO JSON: {{"orden": [índices de más a menos importante]}}

Noticias:
{titles}"""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=600,
                                     messages=[{"role": "user", "content": prompt}])
        data = extraer_json_seguro(msg.content[0].text)
        if data and "orden" in data:
            return data["orden"], None
        return list(range(len(noticias_lista))), None
    except Exception as e:
        return list(range(len(noticias_lista))), str(e)

def ia_analizar_perfil_cruzado(datos_twitter, datos_instagram, nombre_perfil):
    if not ANTHROPIC_API_KEY:
        return None, "Falta API key."
    prompt = f"""Sos analista de comunicación política. Perfil: {nombre_perfil}.
TWITTER/X: {datos_twitter if datos_twitter else "Sin datos"}
INSTAGRAM: {datos_instagram if datos_instagram else "Sin datos"}
Análisis comparativo. SOLO JSON:
{{"distribucion_temas":{{"Economía":0,"Derechos Sociales":0,"Seguridad":0,"Gestión/Obras":0,"Confrontación":0,"Otro":0}},"distribucion_tono":{{"Agresivo":0,"Conciliador":0,"Constructivo":0,"Informativo":0}},"insight_twitter":"2 oraciones","insight_instagram":"qué formato funciona mejor, 2 oraciones","recomendacion_general":"2-3 oraciones","actitud_predominante":"texto"}}
Cada distribución suma 100."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500,
                                     messages=[{"role": "user", "content": prompt}])
        return extraer_json_seguro(msg.content[0].text), None
    except Exception as e:
        return None, str(e)

# ══ TENDENCIAS — TRIPLE RESPALDO ══
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
#  MENÚ LATERAL
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<p class="sidebar-title">CENTRO DE MONITOREO</p>', unsafe_allow_html=True)
    st.divider()
    menu = st.radio("", [
        "📥 Bandeja de Noticias",
        "🔥 Tendencias (Triple Respaldo)",
        "🎯 Radar de Menciones",
        "🔮 Predicción y Agenda",
        "🤖 Evaluador de Contenido",
        "🧠 Laboratorio de Audiencias",
        "📧 Alertas y Reportes",
    ])
    st.divider()
    if GITHUB_TOKEN and GITHUB_REPO:
        st.caption("💾 Memoria permanente: ACTIVA")
    else:
        st.caption("⚠️ Sin GITHUB_TOKEN: descarte temporal")
    st.caption(f"Ventana: {CUTOFF_HORAS}hs · Top {TOP_NOTICIAS}")

# ══════════════════════════════════════════════════════════════════════════════
#  BANDEJA DE NOTICIAS
# ══════════════════════════════════════════════════════════════════════════════
if menu == "📥 Bandeja de Noticias":
    st.header("📥 Bandeja de Entrada de Noticias")
    st.markdown(f"Noticias frescas (últimas **{CUTOFF_HORAS}hs**). Marcalas como leídas y desaparecen para siempre. 🌙 Madrugada queda destacado.")
    reg = st.selectbox("Región:", list(RSS_FEEDS.keys()))
    ca, cb = st.columns(2)
    with ca:
        escanear = st.button("🔄 Buscar noticias nuevas", use_container_width=True)
    with cb:
        ver_todo = st.button("👁️ Ver todo el inbox", use_container_width=True)

    if escanear:
        with st.spinner(f"Buscando en {reg}..."):
            # Usar feedparser.parse directo — igual que el original que funcionaba
            crudas = obtener_noticias_crudas(RSS_FEEDS[reg], max_por_feed=10)
            n_guardadas = 0
            if GITHUB_TOKEN and GITHUB_REPO:
                _, n_guardadas = guardar_en_inbox(reg, crudas)
        if crudas:
            # Guardar también en session_state para mostrar sin depender del GitHub
            st.session_state[f"noticias_{reg}"] = crudas
            st.session_state[f"noticias_{reg}_ts"] = datetime.now()
            st.success(f"✅ {len(crudas)} noticias encontradas.")
        else:
            st.warning("No se encontraron noticias. Probá otra región.")

    # Cargar noticias descartadas para ocultarlas
    descartadas = set()
    if GITHUB_TOKEN and GITHUB_REPO:
        inbox_gh = cargar_inbox()
        if not inbox_gh.empty:
            mask = (inbox_gh["descartada"] == True) | (inbox_gh["descartada"] == "True")
            descartadas = set(inbox_gh[mask]["id"].astype(str).tolist())

    # Mostrar noticias del session_state (lo que trajo el último escaneo)
    noticias_mostrar = st.session_state.get(f"noticias_{reg}", [])

    if ver_todo and GITHUB_TOKEN and GITHUB_REPO:
        # Cargar todo el inbox de GitHub para esta región
        inbox_gh = cargar_inbox()
        if not inbox_gh.empty:
            df_reg = inbox_gh[
                (inbox_gh["region"] == reg) &
                (inbox_gh["descartada"] != True) &
                (inbox_gh["descartada"] != "True")
            ]
            noticias_mostrar = df_reg.rename(columns={"titulo": "titulo", "link": "link", "fecha_pub": "fecha_pub"})[["titulo","link","fecha_pub"]].to_dict("records")

    if noticias_mostrar:
        # Ordenar por IA si hay API key
        if ANTHROPIC_API_KEY and len(noticias_mostrar) > 1:
            with st.spinner("Ordenando por relevancia política..."):
                orden, _ = ia_curar_regional(noticias_mostrar, REGION_CONTEXTO[reg])
        else:
            orden = list(range(len(noticias_mostrar)))

        indices = [i for i in orden if i < len(noticias_mostrar)]
        for i in range(len(noticias_mostrar)):
            if i not in indices:
                indices.append(i)

        st.caption(f"📬 {len(noticias_mostrar)} noticias en {reg}")
        st.divider()

        for idx in indices:
            n = noticias_mostrar[idx]
            nid = hash_noticia(n["titulo"])

            # Saltar descartadas
            if nid in descartadas:
                continue

            clase_tag, texto_tag = etiqueta_tiempo(n.get("fecha_pub",""))
            clase_card = "news-card"
            if clase_tag == "tag-nuevo":
                clase_card += " news-nuevo"
            elif clase_tag == "tag-madrugada":
                clase_card += " news-madrugada"

            claves = detectar_palabras_clave(n["titulo"])
            alerta = " 🚨 " + ", ".join(claves).upper() if claves else ""

            col_n, col_b = st.columns([5, 1])
            with col_n:
                st.markdown(f"""<div class="{clase_card}">
                    <span class="tag {clase_tag}">{texto_tag}</span>{alerta}<br>
                    <a href="{n['link']}" target="_blank" style="font-size:15px; font-weight:600;">{n['titulo']}</a>
                </div>""", unsafe_allow_html=True)
            with col_b:
                if st.button("✓ Leída", key=f"leer_{nid}_{idx}", use_container_width=True):
                    if GITHUB_TOKEN and GITHUB_REPO:
                        descartar_noticia(nid)
                    # Remover del session_state también
                    noticias_act = st.session_state.get(f"noticias_{reg}", [])
                    st.session_state[f"noticias_{reg}"] = [x for x in noticias_act if hash_noticia(x["titulo"]) != nid]
                    st.rerun()
    elif not escanear:
        st.info("Seleccioná una región y hacé clic en 'Buscar noticias nuevas'.")

# ══════════════════════════════════════════════════════════════════════════════
#  TENDENCIAS
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🔥 Tendencias (Triple Respaldo)":
    st.header("🔥 Tendencias Virales de Argentina")
    st.markdown("**Triple respaldo:** Trends24 → GetDayTrends → Búsqueda web IA. Nunca inventa.")
    if st.button("Escanear Tendencias Ahora", use_container_width=True):
        if not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic.")
        else:
            with st.spinner("Probando fuentes..."):
                trends_raw, fuente = obtener_tendencias_con_respaldo()
            if not trends_raw:
                st.error("❌ Las 3 fuentes fallaron. Probá en unos minutos.")
            else:
                st.success(f"✅ Datos desde: **{fuente}**")
                with st.spinner("Filtrando ruido político..."):
                    filtrados, err = ia_filtrar_tendencias(trends_raw, fuente)
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"### 🌐 Raw — {fuente}")
                    for t in trends_raw[:15]:
                        st.markdown(f"- {t}")
                with c2:
                    st.markdown("### 🤖 Curaduría Política")
                    if err or not filtrados:
                        st.info("Hoy la agenda viral es puro deporte/farándula.")
                    else:
                        for u in filtrados:
                            st.success(f"**{u.get('tema','')}** · {emoji_nivel(u.get('nivel',''))}")
                            st.markdown(f"💡 {u.get('angulo','')}")
                            st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  RADAR DE MENCIONES
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🎯 Radar de Menciones":
    st.header("🎯 Radar de Menciones")
    rival = st.text_input("Nombre o palabra clave:", placeholder="Ej: Jorge Macri, jubilados...")
    if st.button("Rastrear", use_container_width=True) and rival.strip():
        url = f"https://news.google.com/rss/search?q=%22{rival.replace(' ', '+')}%22&hl=es-419&gl=AR&ceid=AR:es"
        with st.spinner(f"Buscando sobre {rival}..."):
            feed = feedparser.parse(url)
            items = []
            for entry in feed.entries[:15]:
                items.append({"titulo": entry.get("title","").strip(), "link": entry.get("link","#"), "fecha_pub": entry.get("published","")})
        if not items:
            st.warning(f"No se encontraron menciones de {rival}.")
        else:
            st.caption(f"{len(items)} menciones")
            for n in items:
                _, texto_tag = etiqueta_tiempo(n["fecha_pub"])
                st.markdown(f"🔸 [{n['titulo']}]({n['link']}) · *{texto_tag}*")

# ══════════════════════════════════════════════════════════════════════════════
#  PREDICCIÓN Y AGENDA
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🔮 Predicción y Agenda":
    st.header("🔮 Calendario de Agenda y Predicción")
    if st.button("Generar Calendario", use_container_width=True):
        if not ANTHROPIC_API_KEY:
            st.error("Falta API key.")
        else:
            with st.spinner("Armando agenda..."):
                noticias_ctx = obtener_noticias_crudas(
                    RSS_FEEDS["POLÍTICA NACIONAL"] + RSS_FEEDS["CABA y Rosca"], max_por_feed=6)
            contexto = "\n".join([f"- {n['titulo']}" for n in noticias_ctx])
            if not contexto:
                st.warning("No hay noticias frescas para la agenda.")
            else:
                prompt = f"""Sos secretario de inteligencia política. Titulares de hoy:
{contexto}
TAREA 1: Detectá eventos futuros (sesiones, paros, marchas, debates).
TAREA 2: Deducí 3 ejes de conflicto de la semana.
Devolvé SOLO JSON: {{"agenda_concreta": [{{"tiempo":"cuándo","evento":"qué","explicacion":"por qué"}}], "ejes_estrategicos": [{{"titulo":"eje","conflicto":"qué pasa","tip":"qué hacer"}}]}}"""
                try:
                    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500,
                                                 messages=[{"role": "user", "content": prompt}])
                    data = extraer_json_seguro(msg.content[0].text)
                    if data:
                        st.success("✅ Agenda generada.")
                        st.markdown("### 📅 Eventos Detectados")
                        for ev in data.get("agenda_concreta", []):
                            st.markdown(f"""<div class="evento-card">
                                <span style='color:#e89a3c; font-weight:bold;'>🗓️ {ev.get('tiempo','').upper()}</span><br>
                                <span style='font-size:17px; font-weight:bold;'>{ev.get('evento','')}</span><br>
                                <i style='color:#555;'>{ev.get('explicacion','')}</i>
                            </div>""", unsafe_allow_html=True)
                        st.markdown("### 🎯 Ejes de Conflicto")
                        for eje in data.get("ejes_estrategicos", []):
                            st.markdown(f"#### {eje.get('titulo','')}")
                            st.markdown(f"**💥 Conflicto:** {eje.get('conflicto','')}")
                            st.markdown(f"**💡 Tip:** {eje.get('tip','')}")
                    else:
                        st.error("No se pudo interpretar la respuesta.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ══════════════════════════════════════════════════════════════════════════════
#  EVALUADOR DE CONTENIDO
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🤖 Evaluador de Contenido":
    st.header("🤖 Evaluador Estratégico de Contenido")
    t = st.text_area("Pegá el borrador:", height=150)
    if st.button("Evaluar", use_container_width=True):
        if not t.strip():
            st.warning("Escribí algo primero.")
        elif not ANTHROPIC_API_KEY:
            st.error("Falta API key.")
        else:
            with st.spinner("Analizando..."):
                prompt = f"""Evaluá este texto político: "{t}".
SOLO JSON: {{"score":0-100,"veredicto":"frase","fortalezas":["f1","f2"],"mejoras":["m1","m2"],"plataforma_ideal":"X / Instagram"}}"""
                try:
                    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=600,
                                                 messages=[{"role": "user", "content": prompt}])
                    data = extraer_json_seguro(msg.content[0].text)
                    if data:
                        score = data.get("score", 0)
                        if score >= 75: st.success(f"✅ Score: {score}/100 — {data.get('veredicto','')}")
                        elif score >= 50: st.warning(f"⚠️ Score: {score}/100 — {data.get('veredicto','')}")
                        else: st.error(f"❌ Score: {score}/100 — {data.get('veredicto','')}")
                        st.info(f"📱 Plataforma ideal: {data.get('plataforma_ideal','')}")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("👍 **Fuertes:**")
                            for f in data.get("fortalezas", []): st.markdown(f"- {f}")
                        with c2:
                            st.markdown("🔧 **A mejorar:**")
                            for m in data.get("mejoras", []): st.markdown(f"- {m}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ══════════════════════════════════════════════════════════════════════════════
#  LABORATORIO DE AUDIENCIAS (Twitter + Instagram, foto, persistente)
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🧠 Laboratorio de Audiencias":
    st.header("🧠 Laboratorio de Perfiles y Audiencias")
    st.markdown("Memoria permanente: cargás una vez y queda. Vas actualizando mes a mes y ves la evolución.")
    COLS_AUD = ["Fecha","Perfil","Cargo","Organización","Alianzas","Plataforma","Formato","Tema/Texto","Alcance","Interacciones","Engagement (%)"]
    df_aud, _ = cargar_csv_github(PATH_AUDIENCIA)
    if df_aud.empty:
        df_aud = pd.DataFrame(columns=COLS_AUD)
    if GITHUB_TOKEN and GITHUB_REPO:
        st.caption("💾 Memoria permanente activa")
    else:
        st.caption("⚠️ Configurá GITHUB_TOKEN para guardar permanente")

    tab_tw, tab_ig = st.tabs(["𝕏  Twitter (X)", "📸  Instagram"])

    with tab_tw:
        st.markdown("### Cargar registro de Twitter/X")
        c1, c2 = st.columns(2)
        with c1:
            perfil_tw = st.text_input("👤 Perfil:", key="tw_perfil", placeholder="@MayraMendoza")
            cargo_tw = st.text_input("🏛️ Cargo:", key="tw_cargo", placeholder="Diputada Nacional")
            org_tw = st.text_input("🏢 Organización:", key="tw_org", placeholder="Unión por la Patria")
            ali_tw = st.text_input("🤝 Aliado/a a:", key="tw_ali", placeholder="Kirchnerismo")
        with c2:
            img_tw = st.file_uploader("📸 Captura del tweet (opcional)", type=["png","jpg","jpeg"], key="tw_img")
            if img_tw:
                st.image(img_tw, caption="Captura cargada", use_container_width=True)
            tema_tw = st.text_area("✍️ Tema/Texto del tweet:", key="tw_tema", height=100)
            ca1, ca2 = st.columns(2)
            with ca1: alc_tw = st.number_input("Impresiones", min_value=0, value=0, key="tw_alc")
            with ca2: int_tw = st.number_input("Interacciones", min_value=0, value=0, key="tw_int")
        if st.button("💾 Guardar registro Twitter", use_container_width=True):
            if perfil_tw.strip() and alc_tw > 0 and tema_tw.strip():
                eng = round((int_tw / alc_tw) * 100, 2)
                nuevo = {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Perfil": perfil_tw.strip(),
                         "Cargo": cargo_tw.strip(), "Organización": org_tw.strip(), "Alianzas": ali_tw.strip(),
                         "Plataforma": "Twitter", "Formato": "Tweet", "Tema/Texto": tema_tw.strip(),
                         "Alcance": alc_tw, "Interacciones": int_tw, "Engagement (%)": eng}
                df_aud = pd.concat([df_aud, pd.DataFrame([nuevo])], ignore_index=True)
                ok, msg = guardar_csv_github(PATH_AUDIENCIA, df_aud, f"Registro TW {perfil_tw}")
                if ok: st.success(f"✅ Guardado. Engagement: {eng}%")
                else: st.warning(f"Falló: {msg}")
            else:
                st.error("Completá perfil, texto y alcance.")

    with tab_ig:
        st.markdown("### Cargar registro de Instagram")
        c1, c2 = st.columns(2)
        with c1:
            perfil_ig = st.text_input("👤 Perfil:", key="ig_perfil", placeholder="@mayra.mendoza")
            cargo_ig = st.text_input("🏛️ Cargo:", key="ig_cargo", placeholder="Diputada Nacional")
            org_ig = st.text_input("🏢 Organización:", key="ig_org", placeholder="Unión por la Patria")
            ali_ig = st.text_input("🤝 Aliado/a a:", key="ig_ali", placeholder="Kirchnerismo")
        with c2:
            img_ig = st.file_uploader("📸 Captura del posteo (opcional)", type=["png","jpg","jpeg"], key="ig_img")
            if img_ig:
                st.image(img_ig, caption="Captura cargada", use_container_width=True)
            formato_ig = st.selectbox("📐 Formato:", ["Reel","Carrusel de fotos","Imagen fija","Historia"], key="ig_fmt")
            tema_ig = st.text_area("✍️ Tema/Descripción:", key="ig_tema", height=80)
            cb1, cb2 = st.columns(2)
            with cb1: alc_ig = st.number_input("Alcance", min_value=0, value=0, key="ig_alc")
            with cb2: int_ig = st.number_input("Interacciones", min_value=0, value=0, key="ig_int")
        if st.button("💾 Guardar registro Instagram", use_container_width=True):
            if perfil_ig.strip() and alc_ig > 0 and tema_ig.strip():
                eng = round((int_ig / alc_ig) * 100, 2)
                nuevo = {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Perfil": perfil_ig.strip(),
                         "Cargo": cargo_ig.strip(), "Organización": org_ig.strip(), "Alianzas": ali_ig.strip(),
                         "Plataforma": "Instagram", "Formato": formato_ig, "Tema/Texto": tema_ig.strip(),
                         "Alcance": alc_ig, "Interacciones": int_ig, "Engagement (%)": eng}
                df_aud = pd.concat([df_aud, pd.DataFrame([nuevo])], ignore_index=True)
                ok, msg = guardar_csv_github(PATH_AUDIENCIA, df_aud, f"Registro IG {perfil_ig}")
                if ok: st.success(f"✅ Guardado. Engagement: {eng}%")
                else: st.warning(f"Falló: {msg}")
            else:
                st.error("Completá perfil, descripción y alcance.")

    st.divider()
    if not df_aud.empty:
        st.markdown("### 📚 Historial guardado")
        st.dataframe(df_aud[["Fecha","Perfil","Plataforma","Formato","Engagement (%)"]], use_container_width=True)
        st.markdown("### 📊 Análisis Cruzado por Perfil")
        perfiles = sorted(set(df_aud["Perfil"].dropna().tolist()))
        if perfiles:
            perfil_sel = st.selectbox("Perfil a analizar:", perfiles)
            if st.button("Generar Patrón de Rendimiento con IA", use_container_width=True):
                if not ANTHROPIC_API_KEY:
                    st.error("Falta API key.")
                else:
                    datos_p = df_aud[df_aud["Perfil"] == perfil_sel]
                    tw = datos_p[datos_p["Plataforma"] == "Twitter"]
                    ig = datos_p[datos_p["Plataforma"] == "Instagram"]
                    csv_tw = tw[["Tema/Texto","Alcance","Interacciones","Engagement (%)"]].to_csv(index=False) if not tw.empty else ""
                    csv_ig = ig[["Formato","Tema/Texto","Alcance","Interacciones","Engagement (%)"]].to_csv(index=False) if not ig.empty else ""
                    meta = datos_p.iloc[0]
                    with st.spinner("Analizando patrón cruzado..."):
                        data, err = ia_analizar_perfil_cruzado(csv_tw, csv_ig, perfil_sel)
                    if err or not data:
                        st.error(f"No se pudo analizar: {err}")
                    else:
                        st.markdown(f"""<div class="perfil-header">
                            <div class="perfil-nombre">{perfil_sel}</div>
                            <div class="perfil-meta">{meta.get('Cargo','')} · {meta.get('Organización','')} · Aliado/a: {meta.get('Alianzas','')}</div>
                            <div class="perfil-meta">{len(datos_p)} registros · Eng. promedio: {datos_p['Engagement (%)'].mean():.2f}% · TW: {len(tw)} · IG: {len(ig)}</div>
                        </div>""", unsafe_allow_html=True)
                        try:
                            import plotly.graph_objects as go
                            COLORS = ["#2C3E50","#e89a3c","#3d5a73","#c0392b","#27ae60","#8e44ad","#95a5a6"]
                            cg1, cg2 = st.columns(2)
                            with cg1:
                                temas = data.get("distribucion_temas", {})
                                if temas:
                                    st.markdown("#### Temas")
                                    fig = go.Figure(go.Pie(labels=list(temas.keys()), values=list(temas.values()), hole=0.3, marker_colors=COLORS))
                                    fig.update_layout(height=360, margin=dict(t=20,b=20,l=10,r=10))
                                    st.plotly_chart(fig, use_container_width=True)
                            with cg2:
                                tono = data.get("distribucion_tono", {})
                                if tono:
                                    st.markdown("#### Tono")
                                    fig = go.Figure(go.Pie(labels=list(tono.keys()), values=list(tono.values()), hole=0.3, marker_colors=["#c0392b","#27ae60","#2980b9","#e89a3c"]))
                                    fig.update_layout(height=360, margin=dict(t=20,b=20,l=10,r=10))
                                    st.plotly_chart(fig, use_container_width=True)
                        except ImportError:
                            st.warning("Agregá 'plotly' al requirements.txt.")
                        st.markdown(f"""<div class="insight-box">
                            <b>𝕏 Twitter:</b> {data.get('insight_twitter','')}<br><br>
                            <b>📸 Instagram:</b> {data.get('insight_instagram','')}<br><br>
                            <b>🎯 Recomendación:</b> {data.get('recomendacion_general','')}<br><br>
                            <b>Actitud predominante:</b> {data.get('actitud_predominante','')}
                        </div>""", unsafe_allow_html=True)
        with st.expander("🗑️ Borrar todo el historial"):
            if st.button("Confirmar borrado total"):
                guardar_csv_github(PATH_AUDIENCIA, pd.DataFrame(columns=COLS_AUD), "Borrado total")
                st.success("Historial borrado.")
                st.rerun()
    else:
        st.info("Todavía no hay registros. Cargá el primero arriba.")

# ══════════════════════════════════════════════════════════════════════════════
#  ALERTAS Y REPORTES
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📧 Alertas y Reportes":
    st.header("📧 Centro de Envíos y Alertas")
    st.markdown("### Escáner de Palabras Clave + Mail")
    st.caption("Palabras gatillo: " + ", ".join(PALABRAS_CLAVE))
    if st.button("Escanear y enviar alertas por mail", use_container_width=True):
        if not GMAIL_APP_PASSWORD:
            st.error("Falta contraseña de Gmail en los Secrets.")
        else:
            with st.spinner("Rastreando palabras clave..."):
                alertas = []
                for region, urls in RSS_FEEDS.items():
                    noticias = obtener_noticias_crudas(urls, max_por_feed=5)
                    for n in noticias:
                        claves = detectar_palabras_clave(n["titulo"])
                        if claves:
                            alertas.append((n["titulo"], n["link"], claves))
            seen, unicas = set(), []
            for a in alertas:
                if a[0] not in seen:
                    seen.add(a[0]); unicas.append(a)
            if not unicas:
                st.info("No se detectaron palabras clave.")
            else:
                html = "<h2>🚨 Alertas</h2>" + "".join(
                    [f"<p><b><a href='{l}'>{t}</a></b> [{', '.join(c).upper()}]</p>" for t,l,c in unicas])
                ok, msg = enviar_mail(f"🚨 {len(unicas)} Alertas", html)
                if ok:
                    st.success(f"✅ {len(unicas)} alertas enviadas a {MAIL_DESTINO}")
                    for t,l,c in unicas:
                        st.markdown(f"🔸 [{t}]({l}) — **{', '.join(c).upper()}**")
                else:
                    st.error(f"❌ {msg}")
    st.divider()
    st.info("**Próxima sesión:** bot automático con Telegram que manda alertas aunque nadie esté mirando la app.")
