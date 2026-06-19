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

# Base de datos temporal robusta (Lista de diccionarios para evitar errores de Pandas)
if 'db_rendimiento' not in st.session_state:
    st.session_state['db_rendimiento'] = []

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
    MAIL_DESTINO = st.secrets.get("MAIL_DESTINO", "correo@ejemplo.com")
except:
    GMAIL_USER = ""
    GMAIL_APP_PASSWORD = ""
    MAIL_DESTINO = "correo@ejemplo.com"

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

def extraer_json_seguro(texto):
    """Extrae el JSON de la respuesta de Claude de forma segura para evitar crashes."""
    try:
        start = texto.find("{")
        end = texto.rfind("}")
        if start != -1 and end != -1:
            return json.loads(texto[start:end+1])
    except Exception:
        pass
    return None

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
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1000, messages=[{"role": "user", "content": prompt}])
        data = extraer_json_seguro(msg.content[0].text)
        return data["top"] if data else [], None
    except Exception as e: return None, str(e)

def ia_buscar_tendencias_web():
    """Busca tendencias reales del día con web search (reemplaza el feed muerto de Google Trends)."""
    if not ANTHROPIC_API_KEY: return None, "Falta la API key de Anthropic."
    hoy = datetime.now().strftime("%d/%m/%Y")
    prompt = f"""Hoy es {hoy}. Buscá en la web qué temas están siendo tendencia HOY en Argentina, en redes sociales (X/Twitter) y medios digitales. Enfocate en lo político, económico, social y tragedias/conflictos con conversación caliente.

IGNORÁ por completo fútbol, deportes y farándula salvo que tengan derivada política real.

Devolvé SOLO JSON sin markdown, con esta estructura exacta:
{{"tendencias_utiles": [{{"tema": "tema o palabra", "busquedas": "nivel: explotando/subiendo/estable", "angulo": "por qué impacta y ángulo de contenido en 1 oración"}}]}}

Dame entre 6 y 8 tendencias reales y verificadas de hoy."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        texto = "".join([b.text for b in msg.content if hasattr(b, "text")])
        data = extraer_json_seguro(texto)
        return (data["tendencias_utiles"] if data else []), None
    except Exception as e:
        return None, str(e)

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
        "🔮 Predicción y Agenda",
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
    st.markdown("La IA busca en la web qué está caliente hoy en redes y medios, y descarta el ruido de deportes y farándula.")
    if st.button("Escanear Tendencias del Día", use_container_width=True):
        if not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic.")
        else:
            with st.spinner("Buscando tendencias reales en la web..."):
                utiles, err = ia_buscar_tendencias_web()
            if err:
                st.error(f"No se pudieron obtener tendencias: {err}")
            elif not utiles:
                st.info("Hoy la agenda viral es puro deporte o farándula. No hay tendencias duras.")
            else:
                for u in utiles:
                    st.success(f"**{u.get('tema', 'Tema')}**  ·  {u.get('busquedas', '')}")
                    st.markdown(f"💡 **Relevancia:** {u.get('angulo', '')}")
                    st.divider()

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
                    
                    TAREA 1 (CALENDARIO DE EVENTOS): Detecta eventos futuros explícitos o implícitos en las noticias (Ej: un debate de presupuesto, un paro anunciado, una indagatoria, una sesión legislativa).
                    TAREA 2 (EJES ESTRATÉGICOS): Deduce 3 temas/conflictos que dominarán la conversación.
                    
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
                        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500, messages=[{"role": "user", "content": prompt}])
                        data = extraer_json_seguro(msg.content[0].text)
                        
                        if not data:
                            st.error("Hubo un error interpretando los datos. Intentá de nuevo.")
                        else:
                            st.success("✅ Agenda extraída de las noticias con éxito.")
                            
                            st.markdown("### 📅 Calendario de Eventos Detectados")
                            if not data.get("agenda_concreta"):
                                st.info("No se detectaron eventos con fecha exacta (sesiones, marchas) en los titulares de hoy.")
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
                    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=600, messages=[{"role": "user", "content": prompt}])
                    data = extraer_json_seguro(msg.content[0].text)
                    
                    if data:
                        score = data.get("score", 0)
                        if score >= 75: st.success(f"✅ Score: {score}/100 — {data.get('veredicto', '')}")
                        elif score >= 50: st.warning(f"⚠️ Score: {score}/100 — {data.get('veredicto', '')}")
                        else: st.error(f"❌ Score: {score}/100 — {data.get('veredicto', '')}")
                        
                        st.info(f"📱 **Plataforma ideal:** {data.get('plataforma_ideal', '')}")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("👍 **Puntos Fuertes:**")
                            for f in data.get("fortalezas", []): st.markdown(f"- {f}")
                        with c2:
                            st.markdown("🔧 **Correcciones Sugeridas:**")
                            for m in data.get("mejoras", []): st.markdown(f"- {m}")
                    else:
                        st.error("No se pudo procesar la respuesta.")
                except Exception as e: st.error(f"Error: {str(e)}")

elif menu == "🧠 Laboratorio de Audiencias":
    st.header("🧠 Laboratorio de Perfiles y Audiencias")
    st.markdown("Personalizá y analizá cualquier perfil de redes sociales con IA. Subí capturas y cargá datos para encontrar el patrón de éxito.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 1. Nueva Carga de Datos")
        
        # 1. Input libre en lugar de lista predefinida
        perfil = st.text_input("👤 Nombre de Usuario o Perfil (Ej: @MairaMendoza, @Kicillofok):")
        
        # 2. Uploader de imágenes (Para tener registro visual en el historial)
        imagen_subida = st.file_uploader("📸 Subir captura del posteo (Opcional)", type=["png", "jpg", "jpeg"])
        if imagen_subida:
            st.image(imagen_subida, caption="Captura lista para asociar a este registro", use_container_width=True)
            
        tema_texto = st.text_area("✍️ Tema o texto breve del tuit:", placeholder="Ej: Recorrida por obras hidráulicas...")
        
        col_imp, col_int = st.columns(2)
        with col_imp:
            imp = st.number_input("Impresiones", min_value=0, value=0)
        with col_int:
            int_ = st.number_input("Interacciones (Likes+RTs)", min_value=0, value=0)
        
        if st.button("Guardar en Historial", use_container_width=True):
            if perfil.strip() == "":
                st.error("Tenés que escribir el nombre del perfil.")
            elif imp > 0 and tema_texto:
                eng = round((int_ / imp) * 100, 2)
                nuevo_registro = {
                    "Perfil": perfil.strip(),
                    "Tema/Texto": tema_texto,
                    "Impresiones": imp,
                    "Interacciones": int_,
                    "Engagement (%)": eng,
                    "Imagen": "Sí" if imagen_subida else "No"
                }
                # Guardamos como diccionario dentro de la lista (Evita el error de pandas .concat)
                st.session_state['db_rendimiento'].append(nuevo_registro)
                st.success(f"Dato guardado con éxito. Engagement calculado: {eng}%")
            else:
                st.error("Asegurate de cargar el texto y que las impresiones sean mayores a 0.")
                
    with col2:
        st.markdown("### 2. Base de Datos Histórica")
        df_mostrar = pd.DataFrame(st.session_state['db_rendimiento'])
        if not df_mostrar.empty:
            st.dataframe(df_mostrar, use_container_width=True)
            
            st.markdown("### 3. Extraer Manual de Estilo (IA)")
            perfiles_cargados = df_mostrar['Perfil'].unique().tolist()
            perfil_a_analizar = st.selectbox("¿De quién querés armar el manual de estilo?", perfiles_cargados)
            
            if st.button("Generar Patrón de Rendimiento", use_container_width=True):
                if not ANTHROPIC_API_KEY: st.error("Falta API Key para procesar los datos.")
                else:
                    datos_filtrados = df_mostrar[df_mostrar['Perfil'] == perfil_a_analizar]
                    textos_historicos = datos_filtrados.to_csv(index=False)
                    
                    with st.spinner("La IA está leyendo los datos y buscando el patrón de audiencia..."):
                        prompt = f"""Sos un analista de datos y estratega político. Aquí tienes el historial de posteos de {perfil_a_analizar} con su nivel de Engagement Rate (Interacciones/Impresiones):\n\n{textos_historicos}\n\nTu tarea: Analiza estos datos y dime QUÉ FUNCIONA y QUÉ NO FUNCIONA para este perfil específico. Redacta un 'Manual de Estilo' en 3 viñetas claras indicando qué temas o tonos generan más atención en su audiencia y qué temas los aburren."""
                        try:
                            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                            msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=800, messages=[{"role": "user", "content": prompt}])
                            st.info(f"🧠 **Insight para {perfil_a_analizar}:**")
                            st.markdown(msg.content[0].text)
                        except Exception as e: st.error(str(e))
        else:
            st.info("La base de datos está vacía. Empezá a cargar ejemplos a la izquierda para poder analizarlos.")

elif menu == "📧 Alertas y Reportes":
    st.header("📧 Centro de Envíos y Alertas")
    st.markdown("### 1. Generar Reporte General (Digest)")
    if st.button("Generar y Enviar Digest", use_container_width=True):
        if not ANTHROPIC_API_KEY or not GMAIL_APP_PASSWORD: st.error("Faltan claves de API o Mail.")
        else:
            with st.spinner("Compilando información a nivel nacional..."): html = generar_digest()
            if html:
                ok, msg = enviar_mail(f"📡 Digest Monitoreo — Top {TOP_NOTICIAS} Impacto", html)
                if ok: st.success(msg); st.markdown(html, unsafe_allow_html=True)
                else: st.error(msg)
            else: st.error("No se pudo generar.")
            
    st.divider()
    st.markdown("### 2. Escáner de Peligro Inminente")
    st.caption("Palabras gatillo: " + ", ".join(PALABRAS_CLAVE))
    if st.button("Escanear Palabras Clave Ahora", use_container_width=True):
        with st.spinner("Rastreando palabras clave en todas las regiones..."):
            alertas = []
            for urls in RSS_FEEDS.values():
                for n in obtener_noticias_crudas(urls, 5):
                    claves = detectar_palabras_clave(n["Título"])
                    if claves: alertas.append((n["Título"], n["Link"], claves))
            if alertas:
                html = "<h2>🚨 Alertas de Impacto Detectadas</h2>" + "".join([f"<p><b><a href='{l}'>{t}</a></b> <span style='color:#D32F2F'>[{', '.join(c).upper()}]</span></p>" for t, l, c in alertas])
                ok, msg = enviar_mail(f"🚨 {len(alertas)} Alertas", html)
                if ok: st.success(f"Enviado al correo. {len(alertas)} coincidencias.")
            else: st.info("No se detectaron palabras de alerta.")
