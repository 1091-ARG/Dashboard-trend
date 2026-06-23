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

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

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
    .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox div { background-color: #FFFFFF !important; color: #1E1E1E !important; }
    hr { border-color: #E0E0E0; }
    .sidebar-title { font-size: 20px; font-weight: bold; color: #2C3E50; padding-bottom: 16px; text-align: center; text-transform: uppercase; letter-spacing: 1px; }
    .news-card { background-color: #FFFFFF; padding: 16px 20px; border-radius: 10px; border-left: 4px solid #2C3E50; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 12px; }
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

try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
except:
    GITHUB_TOKEN = GITHUB_REPO = ""

PALABRAS_CLAVE = ["jubilados", "femicidio", "tragedia", "muerte", "protesta",
                  "corrupción", "corrupcion", "paro", "represión", "represion",
                  "escándalo", "inundación", "adorni", "presupuesto"]

VENTANA_HORAS = 10       # Ventana de frescura de noticias
TOP_NOTICIAS = 15        # Cantidad de noticias en la bandeja

# Rutas de los archivos de datos en GitHub
PATH_INBOX = "noticias_inbox.csv"
PATH_AUDIENCIA = "datos_audiencia.csv"

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
#  FUNCIONES DE GITHUB (memoria permanente)
# ══════════════════════════════════════════════════════════════════════════════

def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def cargar_csv_github(path):
    """Lee un CSV de GitHub. Devuelve (DataFrame, sha) o (DataFrame vacío, None)."""
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
            df = pd.read_csv(io.StringIO(contenido))
            return df, info["sha"]
        return pd.DataFrame(), None
    except Exception:
        return pd.DataFrame(), None

def guardar_csv_github(path, df, mensaje):
    """Sobrescribe un CSV en GitHub con el DataFrame dado."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "Faltan GITHUB_TOKEN o GITHUB_REPO en los Secrets."
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
            return True, "Guardado correctamente."
        return False, f"Error GitHub {r.status_code}: {r.json().get('message','')}"
    except Exception as e:
        return False, str(e)

# ══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES BASE DE NOTICIAS
# ══════════════════════════════════════════════════════════════════════════════

def hash_noticia(titulo):
    """ID único y estable de una noticia, basado en su título."""
    return hashlib.md5(titulo.encode("utf-8")).hexdigest()[:12]

def parse_fecha(entry):
    """Devuelve datetime con tz de la noticia, o None."""
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
    """Genera la etiqueta visual según antigüedad y franja horaria."""
    if dt_pub is None:
        return "tag-normal", "Sin fecha", 999999
    ahora = datetime.now(timezone.utc)
    delta = ahora - dt_pub
    minutos = delta.total_seconds() / 60
    horas = minutos / 60
    # Hora local Argentina (UTC-3) para detectar madrugada
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
        return True, "Mail enviado correctamente."
    except Exception as e:
        return False, str(e)

# ══════════════════════════════════════════════════════════════════════════════
#  BANDEJA DE ENTRADA — escaneo + descarte persistente
# ══════════════════════════════════════════════════════════════════════════════

def cargar_inbox():
    """Carga el inbox de GitHub. Columnas: id, titulo, link, region, fecha_pub, descartada."""
    df, _ = cargar_csv_github(PATH_INBOX)
    if df.empty:
        return pd.DataFrame(columns=["id", "titulo", "link", "region", "fecha_pub", "descartada"])
    return df

def escanear_y_actualizar_inbox(region):
    """Lee los feeds de la región, agrega noticias nuevas al inbox (sin duplicar ni resucitar descartadas)."""
    inbox = cargar_inbox()
    ids_existentes = set(inbox["id"].astype(str)) if not inbox.empty else set()
    nuevas = []
    for url in RSS_FEEDS[region]:
        try:
            feed = feedparser.parse(url)
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
                    "id": nid,
                    "titulo": titulo,
                    "link": entry.get("link", "#"),
                    "region": region,
                    "fecha_pub": dt_pub.isoformat() if dt_pub else "",
                    "descartada": False,
                })
        except Exception:
            continue
    if nuevas:
        inbox = pd.concat([inbox, pd.DataFrame(nuevas)], ignore_index=True)
        guardar_csv_github(PATH_INBOX, inbox, f"Inbox actualizado {region} {datetime.now().strftime('%d/%m %H:%M')}")
    return inbox, len(nuevas)

def descartar_noticia(nid):
    """Marca una noticia como descartada y guarda en GitHub."""
    inbox = cargar_inbox()
    if not inbox.empty:
        inbox.loc[inbox["id"].astype(str) == str(nid), "descartada"] = True
        guardar_csv_github(PATH_INBOX, inbox, f"Descartada noticia {nid}")

def limpiar_inbox_viejas():
    """Borra del inbox las noticias que ya salieron de la ventana de 10hs (descartadas o no)."""
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
    inbox_filtrada = inbox[inbox.apply(vigente, axis=1)]
    if len(inbox_filtrada) != len(inbox):
        guardar_csv_github(PATH_INBOX, inbox_filtrada, "Limpieza de noticias fuera de ventana")

# ══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES IA
# ══════════════════════════════════════════════════════════════════════════════

def ia_curar_inbox(noticias_activas, contexto_region, top=TOP_NOTICIAS):
    """La IA ordena y prioriza las noticias activas del inbox por relevancia política."""
    if not ANTHROPIC_API_KEY or not noticias_activas:
        return list(range(len(noticias_activas))), None
    titles = "\n".join([f"[{i}] {n['titulo']}" for i, n in enumerate(noticias_activas)])
    prompt = f"""Sos el Jefe de Redacción de un medio federal cubriendo {contexto_region}.
De estas noticias frescas, ordená las {top} MÁS RELEVANTES políticamente (impacto, poder, conflicto, corrupción, tragedia, gestión). Descartá fútbol y farándula.
Devolvé SOLO JSON sin markdown: {{"orden": [lista de índices ordenados de más a menos importante]}}

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
    """Análisis comparativo Twitter vs Instagram de un perfil."""
    if not ANTHROPIC_API_KEY:
        return None, "Falta API key de Anthropic."
    prompt = f"""Sos analista de comunicación política. Perfil: {nombre_perfil}.

DATOS DE TWITTER/X:
{datos_twitter if datos_twitter else "Sin datos"}

DATOS DE INSTAGRAM:
{datos_instagram if datos_instagram else "Sin datos"}

Hacé un análisis comparativo cruzado. Devolvé SOLO JSON sin markdown:
{{
  "distribucion_temas": {{"Economía": %, "Derechos Sociales": %, "Seguridad": %, "Gestión/Obras": %, "Confrontación": %, "Otro": %}},
  "distribucion_tono": {{"Agresivo": %, "Conciliador": %, "Constructivo": %, "Informativo": %}},
  "insight_twitter": "qué le rinde en Twitter, 2 oraciones",
  "insight_instagram": "qué le rinde en Instagram y qué formato funciona mejor, 2 oraciones",
  "recomendacion_general": "recomendación táctica cruzada, 2-3 oraciones",
  "actitud_predominante": "Agresivo|Conciliador|Constructivo|Informativo"
}}
Los porcentajes de cada distribución suman 100."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500,
                                     messages=[{"role": "user", "content": prompt}])
        data = extraer_json_seguro(msg.content[0].text)
        return data, None
    except Exception as e:
        return None, str(e)

# ══════════════════════════════════════════════════════════════════════════════
#  MENÚ LATERAL
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<p class="sidebar-title">CENTRO DE MONITOREO</p>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#555; font-size:13px;'>Panel de Control</p>", unsafe_allow_html=True)
    st.divider()
    menu = st.radio("", [
        "📥 Bandeja de Noticias",
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
        st.caption("⚠️ Memoria: configurá GITHUB_TOKEN")
    st.caption(f"Ventana: {VENTANA_HORAS}hs · Top {TOP_NOTICIAS}")

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: BANDEJA DE NOTICIAS
# ══════════════════════════════════════════════════════════════════════════════

if menu == "📥 Bandeja de Noticias":
    st.header("📥 Bandeja de Entrada de Noticias")
    st.markdown(f"Estilo mail: las noticias frescas (últimas **{VENTANA_HORAS}hs**) entran acá. Las vas **descartando** a medida que las leés y quedan archivadas para siempre. Lo de la madrugada queda destacado.")

    reg = st.selectbox("Región:", list(RSS_FEEDS.keys()))

    col_a, col_b = st.columns([1, 1])
    with col_a:
        escanear = st.button("🔄 Buscar noticias nuevas", use_container_width=True)
    with col_b:
        limpiar = st.button("🧹 Limpiar viejas (fuera de 10hs)", use_container_width=True)

    if not GITHUB_TOKEN or not GITHUB_REPO:
        st.warning("⚠️ Sin GITHUB_TOKEN configurado, el descarte no se guarda entre sesiones.")

    if limpiar:
        with st.spinner("Limpiando..."):
            limpiar_inbox_viejas()
        st.success("Inbox limpiado.")

    if escanear:
        with st.spinner(f"Buscando en {reg}..."):
            _, n_nuevas = escanear_y_actualizar_inbox(reg)
        st.success(f"✅ {n_nuevas} noticias nuevas agregadas a la bandeja.")

    # Mostrar la bandeja: noticias de la región, no descartadas, dentro de ventana
    inbox = cargar_inbox()
    if inbox.empty:
        st.info("Bandeja vacía. Hacé clic en 'Buscar noticias nuevas' para empezar.")
    else:
        # Filtrar por región y no descartadas
        df_reg = inbox[(inbox["region"] == reg) & (inbox["descartada"] != True) & (inbox["descartada"] != "True")]
        activas = []
        for _, row in df_reg.iterrows():
            try:
                dt = datetime.fromisoformat(row["fecha_pub"]) if row["fecha_pub"] else None
                if dt and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = None
            if es_dentro_ventana(dt):
                activas.append({"id": row["id"], "titulo": row["titulo"], "link": row["link"], "dt": dt})

        if not activas:
            st.info(f"No hay noticias activas en {reg}. Buscá nuevas o probá otra región.")
        else:
            # Ordenar por IA (relevancia) y luego mostrar
            with st.spinner("Ordenando por relevancia..."):
                orden, _ = ia_curar_inbox(activas, REGION_CONTEXTO[reg])
            # Aplicar orden de IA, los que no estén van al final
            indices_ordenados = [i for i in orden if i < len(activas)]
            for i in range(len(activas)):
                if i not in indices_ordenados:
                    indices_ordenados.append(i)

            st.caption(f"📬 {len(activas)} noticias en la bandeja de {reg}")
            st.divider()

            for idx in indices_ordenados:
                n = activas[idx]
                clase_tag, texto_tag, _ = etiqueta_tiempo(n["dt"])
                clase_card = "news-card"
                if clase_tag == "tag-nuevo":
                    clase_card += " news-nuevo"
                elif clase_tag == "tag-madrugada":
                    clase_card += " news-madrugada"
                claves = detectar_palabras_clave(n["titulo"])
                alerta = " 🚨 " + ", ".join(claves).upper() if claves else ""

                col_news, col_btn = st.columns([5, 1])
                with col_news:
                    st.markdown(f"""<div class="{clase_card}">
                        <span class="tag-tiempo {clase_tag}">{texto_tag}</span>{alerta}<br>
                        <a href="{n['link']}" target="_blank" style="font-size:16px; font-weight:600;">{n['titulo']}</a>
                    </div>""", unsafe_allow_html=True)
                with col_btn:
                    if st.button("✓ Leída", key=f"desc_{n['id']}", use_container_width=True):
                        descartar_noticia(n["id"])
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: RADAR DE MENCIONES
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
                dt = parse_fecha(entry)
                if es_dentro_ventana(dt) or True:  # menciones: mostramos aunque sean de +10hs
                    items.append({"titulo": entry.get("title","").strip(), "link": entry.get("link","#"), "dt": dt})
        if not items:
            st.warning(f"No se encontraron menciones de {rival}.")
        else:
            st.caption(f"{len(items)} menciones")
            for n in items:
                _, texto_tag, _ = etiqueta_tiempo(n["dt"])
                st.markdown(f"🔸 [{n['titulo']}]({n['link']}) · *{texto_tag}*")

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: PREDICCIÓN Y AGENDA
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
                        feed = feedparser.parse(url)
                        for e in feed.entries[:6]:
                            noticias_ctx.append(e.get("title","").strip())
                    except Exception:
                        continue
                contexto_texto = "\n".join([f"- {t}" for t in noticias_ctx if t])
            if not contexto_texto:
                st.warning("No hay noticias frescas para armar la agenda.")
            else:
                prompt = f"""Sos secretario de inteligencia política. Titulares de hoy:
{contexto_texto}

TAREA 1: Detectá eventos futuros (sesiones, paros, marchas, debates).
TAREA 2: Deducí 3 ejes de conflicto de la semana.
Devolvé SOLO JSON sin markdown:
{{"agenda_concreta": [{{"tiempo": "cuándo", "evento": "qué", "explicacion": "por qué importa"}}], "ejes_estrategicos": [{{"titulo": "eje", "conflicto": "qué pasa", "tip": "qué hacer"}}]}}"""
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
#  PÁGINA: EVALUADOR DE CONTENIDO
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
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("👍 **Fuertes:**")
                            for f in data.get("fortalezas", []): st.markdown(f"- {f}")
                        with c2:
                            st.markdown("🔧 **A mejorar:**")
                            for m in data.get("mejoras", []): st.markdown(f"- {m}")
                    else:
                        st.error("No se pudo procesar.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: LABORATORIO DE AUDIENCIAS (Twitter + Instagram, persistente)
# ══════════════════════════════════════════════════════════════════════════════

elif menu == "🧠 Laboratorio de Audiencias":
    st.header("🧠 Laboratorio de Perfiles y Audiencias")
    st.markdown("Memoria permanente: cargás un perfil una vez y queda guardado. Vas actualizando mes a mes y viendo la evolución.")

    COLS_AUD = ["Fecha", "Perfil", "Cargo", "Organización", "Alianzas", "Plataforma",
                "Formato", "Tema/Texto", "Alcance", "Interacciones", "Engagement (%)"]

    # Cargar datos guardados
    df_aud, _ = cargar_csv_github(PATH_AUDIENCIA)
    if df_aud.empty:
        df_aud = pd.DataFrame(columns=COLS_AUD)

    if GITHUB_TOKEN and GITHUB_REPO:
        st.caption("💾 Memoria permanente activa")
    else:
        st.caption("⚠️ Configurá GITHUB_TOKEN para guardar permanente")

    tab_tw, tab_ig = st.tabs(["𝕏  Twitter (X)", "📸  Instagram"])

    # ── TWITTER ──
    with tab_tw:
        st.markdown("### Cargar registro de Twitter/X")
        c1, c2 = st.columns(2)
        with c1:
            perfil_tw = st.text_input("👤 Perfil:", key="tw_perfil", placeholder="@MayraMendoza")
            cargo_tw = st.text_input("🏛️ Cargo:", key="tw_cargo", placeholder="Diputada Nacional")
            org_tw = st.text_input("🏢 Organización:", key="tw_org", placeholder="Unión por la Patria")
            ali_tw = st.text_input("🤝 Aliado/a a:", key="tw_ali", placeholder="Kirchnerismo")
        with c2:
            tema_tw = st.text_area("✍️ Tema/Texto del tweet:", key="tw_tema", height=120)
            alc_tw = st.number_input("Impresiones/Alcance", min_value=0, value=0, key="tw_alc")
            int_tw = st.number_input("Interacciones", min_value=0, value=0, key="tw_int")

        if st.button("💾 Guardar registro Twitter", use_container_width=True):
            if perfil_tw.strip() and alc_tw > 0 and tema_tw.strip():
                eng = round((int_tw / alc_tw) * 100, 2)
                nuevo = {
                    "Fecha": datetime.now().strftime("%Y-%m-%d"),
                    "Perfil": perfil_tw.strip(), "Cargo": cargo_tw.strip(),
                    "Organización": org_tw.strip(), "Alianzas": ali_tw.strip(),
                    "Plataforma": "Twitter", "Formato": "Tweet",
                    "Tema/Texto": tema_tw.strip(), "Alcance": alc_tw,
                    "Interacciones": int_tw, "Engagement (%)": eng,
                }
                df_aud = pd.concat([df_aud, pd.DataFrame([nuevo])], ignore_index=True)
                ok, msg = guardar_csv_github(PATH_AUDIENCIA, df_aud, f"Registro TW {perfil_tw}")
                if ok:
                    st.success(f"✅ Guardado permanente. Engagement: {eng}%")
                else:
                    st.warning(f"Falló el guardado: {msg}")
            else:
                st.error("Completá perfil, texto y alcance.")

    # ── INSTAGRAM ──
    with tab_ig:
        st.markdown("### Cargar registro de Instagram")
        c1, c2 = st.columns(2)
        with c1:
            perfil_ig = st.text_input("👤 Perfil:", key="ig_perfil", placeholder="@mayra.mendoza")
            cargo_ig = st.text_input("🏛️ Cargo:", key="ig_cargo", placeholder="Diputada Nacional")
            org_ig = st.text_input("🏢 Organización:", key="ig_org", placeholder="Unión por la Patria")
            ali_ig = st.text_input("🤝 Aliado/a a:", key="ig_ali", placeholder="Kirchnerismo")
        with c2:
            formato_ig = st.selectbox("📐 Formato:", ["Reel", "Carrusel de fotos", "Imagen fija", "Historia"], key="ig_fmt")
            tema_ig = st.text_area("✍️ Tema/Descripción:", key="ig_tema", height=80)
            alc_ig = st.number_input("Alcance", min_value=0, value=0, key="ig_alc")
            int_ig = st.number_input("Interacciones", min_value=0, value=0, key="ig_int")

        if st.button("💾 Guardar registro Instagram", use_container_width=True):
            if perfil_ig.strip() and alc_ig > 0 and tema_ig.strip():
                eng = round((int_ig / alc_ig) * 100, 2)
                nuevo = {
                    "Fecha": datetime.now().strftime("%Y-%m-%d"),
                    "Perfil": perfil_ig.strip(), "Cargo": cargo_ig.strip(),
                    "Organización": org_ig.strip(), "Alianzas": ali_ig.strip(),
                    "Plataforma": "Instagram", "Formato": formato_ig,
                    "Tema/Texto": tema_ig.strip(), "Alcance": alc_ig,
                    "Interacciones": int_ig, "Engagement (%)": eng,
                }
                df_aud = pd.concat([df_aud, pd.DataFrame([nuevo])], ignore_index=True)
                ok, msg = guardar_csv_github(PATH_AUDIENCIA, df_aud, f"Registro IG {perfil_ig}")
                if ok:
                    st.success(f"✅ Guardado permanente. Engagement: {eng}%")
                else:
                    st.warning(f"Falló el guardado: {msg}")
            else:
                st.error("Completá perfil, descripción y alcance.")

    st.divider()

    # ── HISTORIAL Y ANÁLISIS ──
    if not df_aud.empty:
        st.markdown("### 📚 Historial guardado")
        st.dataframe(df_aud[["Fecha", "Perfil", "Plataforma", "Formato", "Engagement (%)"]], use_container_width=True)

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
                guardar_csv_github(PATH_AUDIENCIA, pd.DataFrame(columns=COLS_AUD), "Borrado total audiencia")
                st.success("Historial borrado.")
                st.rerun()
    else:
        st.info("Todavía no hay registros guardados. Cargá el primero arriba.")

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: ALERTAS Y REPORTES
# ══════════════════════════════════════════════════════════════════════════════

elif menu == "📧 Alertas y Reportes":
    st.header("📧 Centro de Envíos y Alertas")

    st.markdown("### 1. Escáner de Palabras Clave + Mail")
    st.caption("Palabras gatillo: " + ", ".join(PALABRAS_CLAVE))
    if st.button("Escanear todas las regiones y enviar alertas", use_container_width=True):
        if not GMAIL_APP_PASSWORD:
            st.error("Falta la contraseña de Gmail en los Secrets.")
        else:
            with st.spinner("Rastreando palabras clave en todos los feeds..."):
                alertas = []
                for region, urls in RSS_FEEDS.items():
                    for url in urls:
                        try:
                            feed = feedparser.parse(url)
                            for e in feed.entries[:5]:
                                titulo = e.get("title","").strip()
                                dt = parse_fecha(e)
                                if not es_dentro_ventana(dt):
                                    continue
                                claves = detectar_palabras_clave(titulo)
                                if claves:
                                    alertas.append((titulo, e.get("link","#"), claves))
                        except Exception:
                            continue
            # quitar duplicados
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
    st.markdown("### 2. Sobre el monitoreo automático")
    st.info("""**Próximo paso (otra sesión):** un bot que corra solo cada 15 min en un servidor externo (cron-job.org o GitHub Actions) y te avise por Telegram o Mail cuando salte una palabra clave o tendencia, sin que nadie tenga que abrir la app. El código actual ya queda preparado para conectarse a eso.""")
