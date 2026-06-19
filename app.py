import streamlit as st
import feedparser
import pandas as pd
import anthropic
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN, ESTÉTICA Y BASE DE DATOS EN MEMORIA
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Centro de Monitoreo", layout="wide", initial_sidebar_state="expanded")

# Base de datos temporal para el Laboratorio de Audiencias
if 'db_rendimiento' not in st.session_state:
    st.session_state['db_rendimiento'] = pd.DataFrame(columns=["Perfil", "Tema/Texto", "Impresiones", "Interacciones", "Engagement (%)"])

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1E1E1E; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E0E0E0; }
    h1, h2, h3, h4 { color: #1E1E1E !important; font-weight: 600; }
    p, span, div { color: #333333 !important; }
    a { color: #2B547E !important; font-weight: 500; text-decoration: none; }
    a:hover { text-decoration: underline; }
    
    /* Botones azules con texto forzado a blanco */
    .stButton > button { background-color: #2C3E50 !important; color: #FFFFFF !important; font-weight: bold !important; border-radius: 6px !important; border: none !important; transition: all 0.3s; }
    .stButton > button * { color: #FFFFFF !important; } 
    .stButton > button:hover { background-color: #1A252F !important; color: #FFFFFF !important; }
    .stButton > button:hover * { color: #FFFFFF !important; }
    
    .stTextInput input, .stTextArea textarea, .stNumberInput input { background-color: #FFFFFF !important; color: #1E1E1E !important; border: 1px solid #CCCCCC !important; }
    hr { border-color: #E0E0E0; }
    .sidebar-title { font-size: 22px; font-weight: bold; color: #2C3E50; padding-bottom: 20px; text-align: center; text-transform: uppercase; letter-spacing: 1px;}
    .evento-card { background-color: #FFFFFF; padding: 15px; border-radius: 8px; border-left: 5px solid #e89a3c; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  VARIABLES Y FEEDS
# ══════════════════════════════════════════════════════════════════════════════

try:
    ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
except:
    ANTHROPIC_API_KEY = ""

try:
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]
    MAIL_DESTINO = st.secrets.get("MAIL_DESTINO", "matumontanez@gmail.com")
except:
    GMAIL_USER = ""
    GMAIL_APP_PASSWORD = ""
    MAIL_DESTINO = "matumontanez@gmail.com"

PALABRAS_CLAVE = ["jubilados", "femicidio", "terremoto", "tragedia", "muerte", "protesta", "corrupción", "paro", "represión", "escándalo", "inundación"]
CUTOFF_HORAS = 24
TOP_NOTICIAS = 8

RSS_FEEDS = {
    "CENTRO Y ESPINAZO": ["https://news.google.com/rss/search?q=site:lavoz.com.ar&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:lagaceta.com.ar&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:rionegro.com.ar&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:losandes.com.ar&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:lacapital.com.ar&hl=es-419&gl=AR&ceid=AR:es"],
    "LITORAL": ["https://news.google.com/rss/search?q=site:rosario3.com&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:ellitoral.com&hl=es-419&gl=AR&ceid=AR:es"],
    "CUYO": ["https://news.google.com/rss/search?q=site:mdzol.com&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:diariodecuyo.com.ar&hl=es-419&gl=AR&ceid=AR:es"],
    "NOA": ["https://news.google.com/rss/search?q=site:eltribuno.com&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:elliberal.com.ar&hl=es-419&gl=AR&ceid=AR:es"],
    "NEA": ["https://news.google.com/rss/search?q=site:elterritorio.com.ar&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:diarionorte.com&hl=es-419&gl=AR&ceid=AR:es"],
    "PATAGONIA": ["https://news.google.com/rss/search?q=site:lmneuquen.com&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:diariojornada.com.ar&hl=es-419&gl=AR&ceid=AR:es"],
    "INTERIOR BONAERENSE": ["https://news.google.com/rss/search?q=site:lanueva.com&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:eldia.com&hl=es-419&gl=AR&ceid=AR:es"],
    "CABA y Rosca": ["https://news.google.com/rss/search?q=Legislatura+Buenos+Aires+pol%C3%ADtica&hl=es-419&gl=AR&ceid=AR:es", "https://news.google.com/rss/search?q=site:lapoliticaonline.com+CABA&hl=es-419&gl=AR&ceid=AR:es"],
    "POLÍTICA NACIONAL": ["https://www.infobae.com/politica/feed/", "https://www.pagina12.com.ar/rss/secciones/el-pais/notas", "https://www.ambito.com/rss/politica.xml"],
}

REGION_CONTEXTO = {
    "CENTRO Y ESPINAZO": "las provincias de Córdoba, Tucumán, Mendoza, Río Negro/Neuquén y Santa Fe (Rosario)",
    "LITORAL": "las provincias de Santa Fe y Entre Ríos",
    "CUYO": "las provincias de Mendoza, San Juan y San Luis",
    "NOA": "las provincias de Salta, Jujuy, Tucumán, Santiago del Estero y Catamarca",
    "NEA": "las provincias de Misiones, Chaco, Corrientes y Formosa",
    "PATAGONIA": "las provincias de Neuquén, Río Negro, Chubut, Santa Cruz y Tierra del Fuego",
    "INTERIOR BONAERENSE": "el interior de la provincia de Buenos Aires (Bahía Blanca, Mar del Plata, La Plata)",
    "CABA y Rosca": "la Ciudad Autónoma de Buenos Aires: Legislatura porteña, comunas, legisladores",
    "POLÍTICA NACIONAL": "la política nacional argentina",
}

# ══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES
# ══════════════════════════════════════════════════════════════════════════════

def es_reciente(entry):
    for campo in ("published", "updated"):
        raw = entry.get(campo, "")
        if not raw: continue
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt) <= timedelta(hours=CUTOFF_HORAS)
        except: continue
    return True

def obtener_noticias_crudas(urls, max_por_feed=8):
    noticias = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= max_por_feed: break
                if not es_reciente(entry): continue
                noticias.append({"Título": entry.get("title", "Sin título").strip(), "Link": entry.get("link", "#")})
                count += 1
        except: continue
    seen, unicas = set(), []
    for n in noticias:
        if n["Título"] not in seen:
            seen.add(n["Título"])
            unicas.append(n)
    return unicas

def detectar_palabras_clave(titulo):
    t = titulo.lower()
    return [p for p in PALABRAS_CLAVE if p in t]

def enviar_mail(asunto, cuerpo_html):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD: return False, "Faltan credenciales de Gmail."
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"], msg["From"], msg["To"] = asunto, GMAIL_USER, MAIL_DESTINO
        msg.attach(MIMEText(cuerpo_html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True, "Mail enviado correctamente."
    except Exception as e: return False, str(e)

def ia_curar_regional(noticias_lista, contexto_region, top=TOP_NOTICIAS):
    if not ANTHROPIC_API_KEY: return None, "Falta API key de Anthropic."
    if not noticias_lista: return [], None
    titles = "\n".join([f"[{i}] {n['Título']}" for i, n in enumerate(noticias_lista)])
    prompt = f"""Sos el Jefe de Redacción escaneando medios de {contexto_region}.
    Elegí las {top} noticias de MAYOR IMPACTO. Buscás eventos graves que puedan replicarse a nivel nacional.
    PRIORIDAD: Tragedias, femicidios, desastres naturales, crímenes violentos, protestas masivas, escándalos de corrupción.
    DESCARTÁ: Noticias locales blandas, fútbol, farándula o temas nacionales replicados genéricamente.
    Devolvé SOLO JSON sin markdown: {{"top": [{{"idx": número, "porque": "impacto, max 12 palabras"}}]}}\n\nNoticias:\n{titles}"""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(model="claude-3-5-sonnet-20240620", max_tokens=1000, messages=[{"role": "user", "content": prompt}])
        raw = msg.content[0].text.replace("```json", "").replace("```", "").strip()
        start, end = raw.find("{"), raw.rfind("}")
        return json.loads(raw[start:end+1])["top"], None
    except Exception as e: return None, str(e)

def obtener_20_tendencias_oficiales():
    feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    url_trends = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=AR"
    feed = feedparser.parse(url_trends)
    tendencias_diarias = []
    for entry in feed.entries[:20]:
        tendencias_diarias.append(f"- Tema: {entry.title} | Tráfico: {entry.get('ht_approx_traffic', 'N/A')} | Contexto: {getattr(entry, 'ht_news_item_title', 'Sin titular')}")
    return tendencias_diarias

def ia_analizar_tendencias(lista_20_tendencias):
    if not ANTHROPIC_API_KEY: return None, "Falta la API key de Anthropic."
    tendencias_texto = "\n".join(lista_20_tendencias)
    prompt = f"""Aquí tienes las 20 búsquedas más virales de Google Argentina HOY:\n{tendencias_texto}\n
    Filtra SOLO los temas que tengan impacto nacional: Política, Economía, Tragedias, Conflictos o Gestión. 
    IGNORA por completo partidos de fútbol, deportes, farándula. Si todo es fútbol, devuelve lista vacía.
    Devuelve SOLO JSON: {{"tendencias_utiles": [{{"tema": "palabra buscada", "busquedas": "tráfico", "angulo": "por qué impacta en 1 oración"}}]}}"""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(model="claude-3-5-sonnet-20240620", max_tokens=1000, messages=[{"role": "user", "content": prompt}])
        raw = msg.content[0].text.replace("```json", "").replace("```", "").strip()
        start, end = raw.find("{"), raw.rfind("}")
        return json.loads(raw[start:end+1])["tendencias_utiles"], None
    except Exception as e: return None, str(e)

def generar_digest():
    todas = []
    for region, urls in RSS_FEEDS.items():
        for n in obtener_noticias_crudas(urls, max_por_feed=2): todas.append(n)
    if not todas: return None
    seen, unicas = set(), []
    for n in todas:
        if n["Título"] not in seen: seen.add(n["Título"]); unicas.append(n)
    top, err = ia_curar_regional(unicas, "toda la Argentina, buscando impacto nacional fuerte", top=TOP_NOTICIAS)
    if err or not top: return None
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = f"<h2>📡 Digest Monitoreo — {hoy}</h2><p>Las {TOP_NOTICIAS} noticias de mayor impacto del momento:</p>"
    for item in top:
        n = unicas[item["idx"]]
        html += f"<p><b><a href='{n['Link']}'>{n['Título']}</a></b><br><i style='color:#555'>{item['porque']}</i></p>"
    return html

# ══════════════════════════════════════════════════════════════════════════════
#  MENÚ LATERAL (SIDEBAR)
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<p class="sidebar-title">CENTRO DE MONITOREO</p>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Panel de Control</p>", unsafe_allow_html=True)
    st.divider()
    menu = st.radio("", [
        "📰 Radar de Impacto Federal",
        "🔥 Tendencias (Top 20)",
        "🎯 Radar de Menciones",
        "🔮 Predicción y Agenda",  # <--- ACÁ ESTÁ LA OPCIÓN DE LA AGENDA
        "🤖 Evaluador de Contenido",
        "🧠 Laboratorio de Audiencias",
        "📧 Alertas y Reportes"
    ])
    st.divider()
    st.caption("Actualización: Tiempo Real")
    st.caption("Motor de Filtro: IA Activa")

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINAS (VISTAS)
# ══════════════════════════════════════════════════════════════════════════════

if menu == "📰 Radar de Impacto Federal":
    st.header("📰 Radar de Impacto Federal")
    st.markdown("La IA filtra los medios regionales buscando noticias de alto impacto (tragedias, femicidios, protestas).")
    reg = st.selectbox("Seleccionar Región a Monitorear:", list(RSS_FEEDS.keys()))
    if st.button("Escanear Región", use_container_width=True):
        if not ANTHROPIC_API_KEY: st.error("Falta la API key de Anthropic para filtrar.")
        else:
            with st.spinner(f"📡 Escaneando medios en {reg} buscando noticias de impacto..."):
                crudas = obtener_noticias_crudas(RSS_FEEDS[reg], max_por_feed=10)
                top, err = ia_curar_regional(crudas, REGION_CONTEXTO[reg])
            if err: st.error(err)
            elif not top: st.info(f"Tranquilidad en {reg}: No se detectaron noticias de impacto extremo en las últimas {CUTOFF_HORAS}hs.")
            else:
                for item in top:
                    n = crudas[item["idx"]]
                    claves = detectar_palabras_clave(n["Título"])
                    marca = " 🚨 **" + ", ".join(claves).upper() + "**" if claves else ""
                    st.markdown(f"#### [{n['Título']}]({n['Link']}){marca}")
                    st.markdown(f"> *{item['porque']}*")
                    st.divider()

elif menu == "🔥 Tendencias (Top 20)":
    st.header("🔥 Tendencias Virales de Argentina")
    if st.button("Escanear Tendencias Diarias", use_container_width=True):
        with st.spinner("Conectando con Google Trends..."):
            top_20_brutas = obtener_20_tendencias_oficiales()
        if not top_20_brutas: st.error("No se pudo conectar a Google Trends.")
        else:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("### 🌐 Top 20 Crudo de Google")
                for t in top_20_brutas: st.markdown(t)
            with col2:
                st.markdown("### 🤖 Curaduría de Impacto IA")
                if not ANTHROPIC_API_KEY: st.error("Falta API Key.")
                else:
                    with st.spinner("Limpiando agenda..."):
                        utiles, err = ia_analizar_tendencias(top_20_brutas)
                    if err: st.error(err)
                    elif not utiles: st.info("Hoy la agenda viral es puro deporte o farándula. No hay tendencias duras.")
                    else:
                        for u in utiles:
                            st.success(f"**{u.get('tema', 'Tema')}** ({u.get('busquedas', '')})")
                            st.markdown(f"💡 **Relevancia:** {u.get('angulo', '')}")

elif menu == "🎯 Radar de Menciones":
    st.header("🎯 Radar de Menciones")
    rival = st.text_input("Palabra clave o Nombre a monitorear:", placeholder="Ej: Jorge Macri, Inundación...")
    if st.button("Rastrear Menciones", use_container_width=True) and rival.strip():
        url = f"https://news.google.com/rss/search?q=%22{rival.replace(' ', '+')}%22&hl=es-419&gl=AR&ceid=AR:es"
        with st.spinner(f"Buscando noticias recientes sobre {rival}..."):
            crudas = obtener_noticias_crudas([url], max_por_feed=12)
        if not crudas: st.warning(f"No se encontraron noticias recientes sobre {rival}.")
        else:
            for n in crudas: st.markdown(f"🔸 [{n['Título']}]({n['Link']})")

elif menu == "🔮 Predicción y Agenda":
    st.header("🔮 Calendario de Agenda y Predicción")
    st.markdown("El sistema lee los medios de CABA y Nacionales de HOY, detecta eventos próximos (sesiones, marchas, debates) y te arma el calendario táctico.")
    
    if st.button("Generar Calendario y Predicción", use_container_width=True):
        if not ANTHROPIC_API_KEY: st.error("Falta API key de Anthropic.")
        else:
            with st.spinner("Rastreando fechas, sesiones y armando la agenda en base a las noticias de hoy..."):
                urls_contexto = RSS_FEEDS["POLÍTICA NACIONAL"] + RSS_FEEDS["CABA y Rosca"]
                noticias_contexto = obtener_noticias_crudas(urls_contexto, max_por_feed=8)
                contexto_texto = "\n".join([f"- {n['Título']}" for n in noticias_contexto])
                
                if not contexto_texto:
                    st.warning("No hay suficientes noticias frescas hoy para armar una agenda.")
                else:
                    prompt = f"""Sos un secretario de inteligencia política armando la agenda de la semana próxima.
                    Aquí tienes los titulares políticos de Argentina en las últimas 24 horas:
                    
                    {contexto_texto}
                    
                    TAREA 1 (CALENDARIO DE EVENTOS): Detecta eventos futuros que se mencionen implícita o explícitamente en los titulares (Ej: si se habla de un proyecto, agenda el debate; si hay enojo social, agenda una posible marcha o declaración).
                    TAREA 2 (EJES DE CONFLICTO): Deduce 3 temas que dominarán la conversación.
                    
                    Devuelve SOLO un JSON válido sin markdown, con esta estructura exacta:
                    {{
                      "agenda_concreta": [
                        {{
                          "tiempo": "Ej: Próxima semana / Martes / Mañana",
                          "evento": "Ej: Debate de Presupuesto en Legislatura / Informe de Adorni",
                          "explicacion": "Por qué es importante y qué implica para la estrategia."
                        }}
                      ],
                      "ejes_estrategicos": [
                        {{
                          "titulo": "Ej: Conflicto Salarial",
                          "conflicto": "Qué va a pasar",
                          "tip": "Qué debe hacer tu espacio político"
                        }}
                      ]
                    }}"""
                    
                    try:
                        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                        msg = client.messages.create(model="claude-3-5-sonnet-20240620", max_tokens=1500, messages=[{"role": "user", "content": prompt}])
                        raw = msg.content[0].text.replace("```json", "").replace("```", "").strip()
                        start, end = raw.find("{"), raw.rfind("}")
                        data = json.loads(raw[start:end+1])
                        
                        st.success("✅ Agenda extraída de las noticias con éxito.")
                        
                        st.markdown("### 📅 Calendario de Eventos Detectados")
                        if not data.get("agenda_concreta"):
                            st.info("No se detectaron eventos con fecha exacta en las noticias de hoy.")
                        else:
                            for ev in data["agenda_concreta"]:
                                st.markdown(f"""
                                <div class="evento-card">
                                    <span style='color:#e89a3c; font-weight:bold; font-size:15px;'>🗓️ {ev['tiempo'].upper()}</span><br>
                                    <span style='font-size:18px; font-weight:bold; color:#2C3E50;'>{ev['evento']}</span><br>
                                    <span style='color:#555;'>📝 <i>{ev['explicacion']}</i></span>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        st.divider()
                        
                        st.markdown("### 🎯 Predicción de Ejes de Conflicto")
                        for eje in data.get("ejes_estrategicos", []):
                            st.markdown(f"#### {eje['titulo']}")
                            st.markdown(f"**💥 El Conflicto:** {eje['conflicto']}")
                            st.markdown(f"**💡 Tip Estratégico:** {eje['tip']}")
                            st.markdown("")
                            
                    except Exception as e:
                        st.error(f"Error procesando el informe: {str(e)}")

elif menu == "🤖 Evaluador de Contenido":
    st.header("🤖 Evaluador Estratégico de Contenido")
    t = st.text_area("Pegá el borrador del texto:", height=150)
    if st.button("Evaluar Texto", use_container_width=True):
        if not t.strip(): st.warning("Escribí algo primero.")
        elif not ANTHROPIC_API_KEY: st.error("Falta API key de Anthropic.")
        else:
            with st.spinner("Analizando impacto y tono..."):
                prompt = f"""Sos un editor de contenidos de impacto. Evaluá este texto: "{t}". 
                Devolvé SOLO JSON: {{"score": número 0-100, "veredicto": "frase corta", "fortalezas": ["f1", "f2"], "mejoras": ["m1", "m2"], "plataforma_ideal": "X / Instagram / LinkedIn"}}"""
                try:
                    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                    msg = client.messages.create(model="claude-3-5-sonnet-20240620", max_tokens=600, messages=[{"role": "user", "content": prompt}])
                    raw = msg.content[0].text.replace("```json", "").replace("```", "").strip()
                    start, end = raw.find("{"), raw.rfind("}")
                    data = json.loads(raw[start:end+1])
                    score = data["score"]
                    if score >= 75: st.success(f"✅ Score: {score}/100 — {data['veredicto']}")
                    elif score >= 50: st.warning(f"⚠️ Score: {score}/100 — {data['veredicto']}")
                    else: st.error(f"❌ Score: {score}/100 — {data['veredicto']}")
                    st.info(f"📱 **Plataforma ideal:** {data['plataforma_ideal']}")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("👍 **Puntos Fuertes:**")
                        for f in data["fortalezas"]: st.markdown(f"- {f}")
                    with c2:
