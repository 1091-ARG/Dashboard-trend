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

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1E1E1E; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E0E0E0; }
    h1, h2, h3, h4 { color: #1E1E1E !important; font-weight: 600; }
    p, span, div, label { color: #333333 !important; }
    a { color: #2B547E !important; font-weight: 500; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .stButton > button { background-color: #2C3E50 !important; color: #FFFFFF !important; font-weight: bold !important; border-radius: 6px !important; border: none !important; }
    .stButton > button * { color: #FFFFFF !important; }
    .stButton > button:hover { background-color: #1A252F !important; }
    .stTextInput input, .stTextArea textarea, .stNumberInput input { background-color: #FFFFFF !important; color: #1E1E1E !important; }
    hr { border-color: #E0E0E0; }
    .sidebar-title { font-size: 20px; font-weight: bold; color: #2C3E50; padding-bottom: 16px; text-align: center; text-transform: uppercase; letter-spacing: 1px; }
    .news-card { background-color: #FFFFFF; padding: 14px 18px; border-radius: 10px; border-left: 4px solid #2C3E50; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 10px; }
    .news-nuevo { border-left-color: #c0392b !important; background-color: #fff8f7 !important; }
    .news-madrugada { border-left-color: #8e44ad !important; background-color: #faf7fc !important; }
    .tag-tiempo { font-size: 12px; font-weight: 700; padding: 2px 10px; border-radius: 12px; display: inline-block; }
    .tag-nuevo { background: #fdecea; color: #c0392b !important; }
    .tag-madrugada { background: #f3eafa; color: #8e44ad !important; }
    .tag-normal { background: #eef0f2; color: #555 !important; }
    .perfil-header { background: linear-gradient(135deg, #2C3E50, #3d5a73); color: white; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; }
    .perfil-nombre { font-size: 22px; font-weight: 700; color: white !important; margin: 0; }
    .perfil-meta { font-size: 13px; color: #b0c4d8 !important; margin-top: 4px; }
    .insight-box { background: #f0f7ff; border-left: 4px solid #2B547E; padding: 16px 20px; border-radius: 8px; margin-top: 16px; }
</style>
""", unsafe_allow_html=True)

# ── CREDENCIALES ──
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
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
except:
    GITHUB_TOKEN = GITHUB_REPO = ""

PALABRAS_CLAVE = ["jubilados", "femicidio", "tragedia", "muerte", "protesta",
                  "corrupción", "corrupcion", "paro", "represión", "represion",
                  "escándalo", "inundación", "adorni", "presupuesto"]

VENTANA_HORAS = 15
TOP_NOTICIAS = 15
PATH_INBOX = "noticias_inbox.csv"
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

# ══ FUNCIONES GITHUB (memoria permanente) ══
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

# ══ FUNCIONES BASE ══
def hash_noticia(titulo):
    return hashlib.md5(titulo.encode("utf-8")).hexdigest()[:12]

def leer_feed(url):
    """Lee un feed RSS. Si el acceso directo falla o viene vacío (bloqueo 403 a servidores),
    reintenta a través de un proxy que se hace pasar por navegador."""
    import urllib.parse
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
    # Intento 1: directo
    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code == 200:
            feed = feedparser.parse(r.content)
            if feed.entries:
                return feed
    except Exception:
        pass
    # Intento 2: vía proxy allorigins (destraba el 403 en la nube)
    try:
        proxy_url = "https://api.allorigins.win/raw?url=" + urllib.parse.quote(url, safe="")
        r = requests.get(proxy_url, headers=headers, timeout=20)
        if r.status_code == 200:
            feed = feedparser.parse(r.content)
            if feed.entries:
                return feed
    except Exception:
        pass
    # Intento 3: proxy corsproxy
    try:
        proxy_url = "https://corsproxy.io/?url=" + urllib.parse.quote(url, safe="")
        r = requests.get(proxy_url, headers=headers, timeout=20)
        if r.status_code == 200:
            feed = feedparser.parse(r.content)
            if feed.entries:
                return feed
    except Exception:
        pass
    # Si todo falla, devolver feed vacío
    return feedparser.parse("")

def parse_fecha(entry):
    for campo in ("published", "updated"):
        raw = entry.get(campo, "")
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None

def etiqueta_tiempo(dt_pub):
    if dt_pub is None:
        return "tag-normal", "Sin fecha", 999999
    ahora = datetime.now(timezone.utc)
    minutos = (ahora - dt_pub).total_seconds() / 60
    horas = minutos / 60
    hora_local = (dt_pub - timedelta(hours=3)).hour
    es_madrugada = 0 <= hora_local < 7
    if minutos < 60:
        return "tag-nuevo", f"Hace {int(minutos)} min · 🔥 NUEVO", minutos
    elif es_madrugada and dt_pub.date() == (ahora - timedelta(hours=3)).date():
        return "tag-madrugada", f"🌙 Madrugada · Hace {int(horas)}h", minutos
    else:
        return "tag-normal", f"Hace {int(horas)}h", minutos

def es_dentro_ventana(dt_pub):
    if dt_pub is None:
        return True
    return (datetime.now(timezone.utc) - dt_pub) <= timedelta(hours=VENTANA_HORAS)

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

# ══ INBOX (bandeja con descarte persistente) ══
def cargar_inbox():
    df, _ = cargar_csv_github(PATH_INBOX)
    if df.empty:
        return pd.DataFrame(columns=["id","titulo","link","region","fecha_pub","descartada"])
    return df

def escanear_y_actualizar_inbox(region):
    inbox = cargar_inbox()
    ids_existentes = set(inbox["id"].astype(str)) if not inbox.empty else set()
    nuevas = []
    for url in RSS_FEEDS[region]:
        try:
            feed = leer_feed(url)
            for entry in feed.entries[:12]:
                titulo = entry.get("title", "").strip()
                if not titulo:
                    continue
                dt_pub = parse_fecha(entry)
                if not es_dentro_ventana(dt_pub):
                    continue
                nid = hash_noticia(titulo)
                if nid in ids_existentes:
                    continue
                ids_existentes.add(nid)
                nuevas.append({
                    "id": nid, "titulo": titulo, "link": entry.get("link","#"),
                    "region": region, "fecha_pub": dt_pub.isoformat() if dt_pub else "",
                    "descartada": False,
                })
        except Exception:
            continue
    if nuevas:
        inbox = pd.concat([inbox, pd.DataFrame(nuevas)], ignore_index=True)
        guardar_csv_github(PATH_INBOX, inbox, f"Inbox {region} {datetime.now().strftime('%d/%m %H:%M')}")
    return inbox, len(nuevas)

def descartar_noticia(nid):
    inbox = cargar_inbox()
    if not inbox.empty:
        inbox.loc[inbox["id"].astype(str) == str(nid), "descartada"] = True
        guardar_csv_github(PATH_INBOX, inbox, f"Leída {nid}")

def limpiar_inbox_viejas():
    inbox = cargar_inbox()
    if inbox.empty:
        return
    ahora = datetime.now(timezone.utc)
    def vigente(row):
        try:
            dt = datetime.fromisoformat(row["fecha_pub"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (ahora - dt) <= timedelta(hours=VENTANA_HORAS)
        except Exception:
            return False
    filtrada = inbox[inbox.apply(vigente, axis=1)]
    if len(filtrada) != len(inbox):
        guardar_csv_github(PATH_INBOX, filtrada, "Limpieza fuera de ventana")

# ══ FUNCIONES IA ══
def ia_curar_inbox(noticias_activas, contexto_region, top=TOP_NOTICIAS):
    if not ANTHROPIC_API_KEY or not noticias_activas:
        return list(range(len(noticias_activas))), None
    titles = "\n".join([f"[{i}] {n['titulo']}" for i, n in enumerate(noticias_activas)])
    prompt = f"""Sos Jefe de Redacción cubriendo {contexto_region}.
Ordená las {top} noticias MÁS RELEVANTES políticamente (impacto, poder, conflicto, corrupción, tragedia, gestión). Descartá fútbol y farándula.
Devolvé SOLO JSON sin markdown: {{"orden": [índices de más a menos importante]}}

Noticias:
{titles}"""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=600,
                                     messages=[{"role": "user", "content": prompt}])
        data = extraer_json_seguro(msg.content[0].text)
        if data and "orden" in data:
            return data["orden"], None
        return list(range(len(noticias_activas))), None
    except Exception as e:
        return list(range(len(noticias_activas))), str(e)

def ia_analizar_perfil_cruzado(datos_twitter, datos_instagram, nombre_perfil):
    if not ANTHROPIC_API_KEY:
        return None, "Falta API key."
    prompt = f"""Sos analista de comunicación política. Perfil: {nombre_perfil}.
DATOS TWITTER/X:
{datos_twitter if datos_twitter else "Sin datos"}
DATOS INSTAGRAM:
{datos_instagram if datos_instagram else "Sin datos"}

Análisis comparativo cruzado. Devolvé SOLO JSON sin markdown:
{{"distribucion_temas": {{"Economía": %, "Derechos Sociales": %, "Seguridad": %, "Gestión/Obras": %, "Confrontación": %, "Otro": %}}, "distribucion_tono": {{"Agresivo": %, "Conciliador": %, "Constructivo": %, "Informativo": %}}, "insight_twitter": "2 oraciones", "insight_instagram": "qué formato funciona mejor, 2 oraciones", "recomendacion_general": "2-3 oraciones", "actitud_predominante": "Agresivo|Conciliador|Constructivo|Informativo"}}
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
    st.markdown("<p style='text-align:center; color:#555; font-size:13px;'>Panel de Control</p>", unsafe_allow_html=True)
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
        st.caption("⚠️ Configurá GITHUB_TOKEN")
    st.caption(f"Ventana: {VENTANA_HORAS}hs · Top {TOP_NOTICIAS}")

# ══════════════════════════════════════════════════════════════════════════════
#  BANDEJA DE NOTICIAS
# ══════════════════════════════════════════════════════════════════════════════
if menu == "📥 Bandeja de Noticias":
    st.header("📥 Bandeja de Entrada de Noticias")
    st.markdown(f"Las noticias frescas (últimas **{VENTANA_HORAS}hs**) entran a la lista. Las vas marcando como **leídas** y quedan archivadas para siempre. Lo de la madrugada queda destacado.")
    reg = st.selectbox("Región:", list(RSS_FEEDS.keys()))
    ca, cb = st.columns(2)
    with ca:
        escanear = st.button("🔄 Buscar noticias nuevas", use_container_width=True)
    with cb:
        limpiar = st.button("🧹 Limpiar viejas (+10hs)", use_container_width=True)
    if not GITHUB_TOKEN or not GITHUB_REPO:
        st.warning("⚠️ Sin GITHUB_TOKEN, el 'leído' no se guarda entre sesiones.")
    if limpiar:
        with st.spinner("Limpiando..."):
            limpiar_inbox_viejas()
        st.success("Inbox limpiado.")
    if escanear:
        with st.spinner(f"Buscando en {reg}..."):
            _, n_nuevas = escanear_y_actualizar_inbox(reg)
        st.success(f"✅ {n_nuevas} noticias nuevas en la bandeja.")
        st.rerun()

    inbox = cargar_inbox()
    if inbox.empty:
        st.info("Bandeja vacía. Hacé clic en 'Buscar noticias nuevas'.")
    else:
        df_reg = inbox[(inbox["region"] == reg) & (inbox["descartada"] != True) & (inbox["descartada"] != "True")]
        activas = []
        for _, row in df_reg.iterrows():
            fecha_raw = row["fecha_pub"]
            # Manejar NaN, vacío, o fecha válida
            if pd.isna(fecha_raw) or str(fecha_raw).strip() == "":
                dt = None  # sin fecha → se muestra igual
            else:
                try:
                    dt = datetime.fromisoformat(str(fecha_raw))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    # Si tiene fecha pero está fuera de ventana, la salteamos
                    if not es_dentro_ventana(dt):
                        continue
                except Exception:
                    dt = None  # fecha rota → se muestra igual
            activas.append({"id": row["id"], "titulo": row["titulo"], "link": row["link"], "dt": dt})
        if not activas:
            st.info(f"No hay noticias activas en {reg}. Buscá nuevas o probá otra región.")
        else:
            with st.spinner("Ordenando por relevancia..."):
                orden, _ = ia_curar_inbox(activas, REGION_CONTEXTO[reg])
            indices = [i for i in orden if i < len(activas)]
            for i in range(len(activas)):
                if i not in indices:
                    indices.append(i)
            st.caption(f"📬 {len(activas)} noticias en la bandeja de {reg}")
            st.divider()
            for idx in indices:
                n = activas[idx]
                clase_tag, texto_tag, _ = etiqueta_tiempo(n["dt"])
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
                        <span class="tag-tiempo {clase_tag}">{texto_tag}</span>{alerta}<br>
                        <a href="{n['link']}" target="_blank" style="font-size:16px; font-weight:600;">{n['titulo']}</a>
                    </div>""", unsafe_allow_html=True)
                with col_b:
                    if st.button("✓ Leída", key=f"d_{n['id']}", use_container_width=True):
                        descartar_noticia(n["id"])
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  TENDENCIAS
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🔥 Tendencias (Triple Respaldo)":
    st.header("🔥 Tendencias Virales de Argentina")
    st.markdown("**Triple respaldo**: Trends24 → GetDayTrends → Búsqueda web IA. Si las 3 fallan, avisa — nunca inventa ni tira datos viejos.")
    if st.button("Escanear Tendencias Ahora", use_container_width=True):
        if not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic.")
        else:
            with st.spinner("Probando fuentes: Trends24 → GetDayTrends → Web IA"):
                trends_raw, fuente = obtener_tendencias_con_respaldo()
            if not trends_raw:
                st.error("❌ Las 3 fuentes fallaron. No hay datos ahora. Probá en unos minutos.")
            else:
                st.success(f"✅ Datos desde: **{fuente}**")
                with st.spinner("Filtrando ruido y analizando ángulo político..."):
                    filtrados, err = ia_filtrar_tendencias(trends_raw, fuente)
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"### 🌐 Raw — {fuente}")
                    for t in trends_raw[:15]:
                        st.markdown(f"- {t}")
                with c2:
                    st.markdown("### 🤖 Curaduría Política IA")
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
            feed = leer_feed(url)
            items = []
            for entry in feed.entries[:15]:
                items.append({"titulo": entry.get("title","").strip(), "link": entry.get("link","#"), "dt": parse_fecha(entry)})
        if not items:
            st.warning(f"No se encontraron menciones de {rival}.")
        else:
            st.caption(f"{len(items)} menciones")
            for n in items:
                _, texto_tag, _ = etiqueta_tiempo(n["dt"])
                st.markdown(f"🔸 [{n['titulo']}]({n['link']}) · *{texto_tag}*")

# ══════════════════════════════════════════════════════════════════════════════
#  PREDICCIÓN Y AGENDA
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🔮 Predicción y Agenda":
    st.header("🔮 Calendario de Agenda y Predicción")
    if st.button("Generar Calendario", use_container_width=True):
        if not ANTHROPIC_API_KEY:
            st.error("Falta API key de Anthropic.")
        else:
            with st.spinner("Armando agenda..."):
                urls_ctx = RSS_FEEDS["POLÍTICA NACIONAL"] + RSS_FEEDS["CABA y Rosca"]
                noticias_ctx = []
                for url in urls_ctx:
                    try:
                        feed = leer_feed(url)
                        for e in feed.entries[:6]:
                            noticias_ctx.append(e.get("title","").strip())
                    except Exception:
                        continue
                contexto_texto = "\n".join([f"- {t}" for t in noticias_ctx if t])
            if not contexto_texto:
                st.warning("No hay noticias frescas para la agenda.")
            else:
                prompt = f"""Sos secretario de inteligencia política. Titulares de hoy:
{contexto_texto}
TAREA 1: Detectá eventos futuros (sesiones, paros, marchas, debates).
TAREA 2: Deducí 3 ejes de conflicto de la semana.
Devolvé SOLO JSON sin markdown: {{"agenda_concreta": [{{"tiempo": "cuándo", "evento": "qué", "explicacion": "por qué importa"}}], "ejes_estrategicos": [{{"titulo": "eje", "conflicto": "qué pasa", "tip": "qué hacer"}}]}}"""
                try:
                    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500,
                                                 messages=[{"role": "user", "content": prompt}])
                    data = extraer_json_seguro(msg.content[0].text)
                    if not data:
                        st.error("No se pudo interpretar la respuesta.")
                    else:
                        st.success("✅ Agenda generada.")
                        st.markdown("### 📅 Eventos Detectados")
                        for ev in data.get("agenda_concreta", []):
                            st.markdown(f"""<div class="news-card">
                                <span style='color:#e89a3c; font-weight:bold;'>🗓️ {ev.get('tiempo','').upper()}</span><br>
                                <span style='font-size:17px; font-weight:bold;'>{ev.get('evento','')}</span><br>
                                <span style='color:#555;'>📝 <i>{ev.get('explicacion','')}</i></span>
                            </div>""", unsafe_allow_html=True)
                        st.markdown("### 🎯 Ejes de Conflicto")
                        for eje in data.get("ejes_estrategicos", []):
                            st.markdown(f"#### {eje.get('titulo','')}")
                            st.markdown(f"**💥 Conflicto:** {eje.get('conflicto','')}")
                            st.markdown(f"**💡 Tip:** {eje.get('tip','')}")
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
Devolvé SOLO JSON sin markdown: {{"score": 0-100, "veredicto": "frase", "fortalezas": ["f1","f2"], "mejoras": ["m1","m2"], "plataforma_ideal": "X / Instagram"}}"""
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
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            st.markdown("👍 **Fuertes:**")
                            for f in data.get("fortalezas", []): st.markdown(f"- {f}")
                        with cc2:
                            st.markdown("🔧 **A mejorar:**")
                            for m in data.get("mejoras", []): st.markdown(f"- {m}")
                    else:
                        st.error("No se pudo procesar.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ══════════════════════════════════════════════════════════════════════════════
#  LABORATORIO DE AUDIENCIAS (Twitter + Instagram, foto, persistente)
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🧠 Laboratorio de Audiencias":
    st.header("🧠 Laboratorio de Perfiles y Audiencias")
    st.markdown("Memoria permanente: cargás un perfil y queda guardado. Actualizás mes a mes y ves la evolución.")
    COLS_AUD = ["Fecha","Perfil","Cargo","Organización","Alianzas","Plataforma",
                "Formato","Tema/Texto","Alcance","Interacciones","Engagement (%)"]
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
            with ca1:
                alc_tw = st.number_input("Impresiones", min_value=0, value=0, key="tw_alc")
            with ca2:
                int_tw = st.number_input("Interacciones", min_value=0, value=0, key="tw_int")
        if st.button("💾 Guardar registro Twitter", use_container_width=True):
            if perfil_tw.strip() and alc_tw > 0 and tema_tw.strip():
                eng = round((int_tw / alc_tw) * 100, 2)
                nuevo = {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Perfil": perfil_tw.strip(),
                         "Cargo": cargo_tw.strip(), "Organización": org_tw.strip(), "Alianzas": ali_tw.strip(),
                         "Plataforma": "Twitter", "Formato": "Tweet", "Tema/Texto": tema_tw.strip(),
                         "Alcance": alc_tw, "Interacciones": int_tw, "Engagement (%)": eng}
                df_aud = pd.concat([df_aud, pd.DataFrame([nuevo])], ignore_index=True)
                ok, msg = guardar_csv_github(PATH_AUDIENCIA, df_aud, f"Registro TW {perfil_tw}")
                if ok: st.success(f"✅ Guardado permanente. Engagement: {eng}%")
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
            with cb1:
                alc_ig = st.number_input("Alcance", min_value=0, value=0, key="ig_alc")
            with cb2:
                int_ig = st.number_input("Interacciones", min_value=0, value=0, key="ig_int")
        if st.button("💾 Guardar registro Instagram", use_container_width=True):
            if perfil_ig.strip() and alc_ig > 0 and tema_ig.strip():
                eng = round((int_ig / alc_ig) * 100, 2)
                nuevo = {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Perfil": perfil_ig.strip(),
                         "Cargo": cargo_ig.strip(), "Organización": org_ig.strip(), "Alianzas": ali_ig.strip(),
                         "Plataforma": "Instagram", "Formato": formato_ig, "Tema/Texto": tema_ig.strip(),
                         "Alcance": alc_ig, "Interacciones": int_ig, "Engagement (%)": eng}
                df_aud = pd.concat([df_aud, pd.DataFrame([nuevo])], ignore_index=True)
                ok, msg = guardar_csv_github(PATH_AUDIENCIA, df_aud, f"Registro IG {perfil_ig}")
                if ok: st.success(f"✅ Guardado permanente. Engagement: {eng}%")
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
                    st.error("Falta API key de Anthropic.")
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
                            st.warning("Agregá 'plotly' al requirements.txt para ver los gráficos.")
                        st.markdown(f"""<div class="insight-box">
                            <b>𝕏 Twitter:</b> {data.get('insight_twitter','')}<br><br>
                            <b>📸 Instagram:</b> {data.get('insight_instagram','')}<br><br>
                            <b>🎯 Recomendación cruzada:</b> {data.get('recomendacion_general','')}<br><br>
                            <b>Actitud predominante:</b> {data.get('actitud_predominante','')}
                        </div>""", unsafe_allow_html=True)
        with st.expander("🗑️ Borrar todo el historial"):
            if st.button("Confirmar borrado total"):
                guardar_csv_github(PATH_AUDIENCIA, pd.DataFrame(columns=COLS_AUD), "Borrado total")
                st.success("Historial borrado.")
                st.rerun()
    else:
        st.info("Todavía no hay registros guardados. Cargá el primero arriba.")

# ══════════════════════════════════════════════════════════════════════════════
#  ALERTAS Y REPORTES
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📧 Alertas y Reportes":
    st.header("📧 Centro de Envíos y Alertas")
    st.markdown("### Escáner de Palabras Clave + Mail")
    st.caption("Palabras gatillo: " + ", ".join(PALABRAS_CLAVE))
    if st.button("Escanear todas las regiones y enviar alertas", use_container_width=True):
        if not GMAIL_APP_PASSWORD:
            st.error("Falta la contraseña de Gmail en los Secrets.")
        else:
            with st.spinner("Rastreando palabras clave..."):
                alertas = []
                for region, urls in RSS_FEEDS.items():
                    for url in urls:
                        try:
                            feed = leer_feed(url)
                            for e in feed.entries[:5]:
                                titulo = e.get("title","").strip()
                                if not es_dentro_ventana(parse_fecha(e)):
                                    continue
                                claves = detectar_palabras_clave(titulo)
                                if claves:
                                    alertas.append((titulo, e.get("link","#"), claves))
                        except Exception:
                            continue
            seen, unicas = set(), []
            for a in alertas:
                if a[0] not in seen:
                    seen.add(a[0]); unicas.append(a)
            if not unicas:
                st.info("No se detectaron palabras clave en las últimas horas.")
            else:
                html = "<h2>🚨 Alertas Detectadas</h2>" + "".join(
                    [f"<p><b><a href='{l}'>{t}</a></b> <span style='color:#D32F2F'>[{', '.join(c).upper()}]</span></p>" for t,l,c in unicas])
                ok, msg = enviar_mail(f"🚨 {len(unicas)} Alertas de Monitoreo", html)
                if ok:
                    st.success(f"✅ {len(unicas)} alertas enviadas a {MAIL_DESTINO}")
                    for t,l,c in unicas:
                        st.markdown(f"🔸 [{t}]({l}) — **{', '.join(c).upper()}**")
                else:
                    st.error(f"❌ {msg}")
    st.divider()
    st.info("""**Próximo paso (otra sesión):** un bot que corra solo cada 15 min en un servidor externo y te avise por Telegram o Mail cuando salte una palabra clave, sin que nadie abra la app.""")
