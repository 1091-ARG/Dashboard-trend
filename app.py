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
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Centro de Monitoreo", layout="wide")
st.markdown("""<style>
.stApp {background-color: #0e0e10; color: #E0E0E0;}
h1, h2, h3 {color: #FFFFFF !important;}
.stTabs [data-baseweb="tab"] {color: #888;}
.stTabs [aria-selected="true"] {color: #e89a3c !important; border-bottom-color: #e89a3c !important;}
.stButton button {background-color: #e89a3c; color: #0e0e10; font-weight: 600; border: none;}
</style>""", unsafe_allow_html=True)

st.title("📡 1091 — Centro de Monitoreo")

ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
GMAIL_USER = st.secrets.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = st.secrets.get("GMAIL_APP_PASSWORD", "")
MAIL_DESTINO = st.secrets.get("MAIL_DESTINO", "matumontanez@gmail.com")

PALABRAS_CLAVE = [
    "jubilados", "cristina", "milei", "pami", "subte", "protesta",
    "legislatura", "corrupción", "corrupcion", "femicidio", "huelga",
    "desaparecido", "intendente", "juicio", "paro", "represión", "represion",
]

CUTOFF_HORAS = 24
TOP_NOTICIAS = 8

# ══════════════════════════════════════════════════════════════════════════════
#  FEEDS RSS
# ══════════════════════════════════════════════════════════════════════════════

RSS_FEEDS = {
    "EL ESPINAZO": [
        "https://news.google.com/rss/search?q=site:lavoz.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:lagaceta.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:rionegro.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:losandes.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:lacapital.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:cadena3.com&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "LITORAL": [
        "https://news.google.com/rss/search?q=site:rosario3.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:ellitoral.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:airedesantafe.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:unoentrerios.com.ar&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "CUYO": [
        "https://news.google.com/rss/search?q=site:mdzol.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:diariodecuyo.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:eldiariodelarepublica.com&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "NOA": [
        "https://news.google.com/rss/search?q=site:eltribuno.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:elliberal.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:elancasti.com.ar&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "NEA": [
        "https://news.google.com/rss/search?q=site:elterritorio.com.ar&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:diarionorte.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:diarioepoca.com&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "PATAGONIA": [
        "https://news.google.com/rss/search?q=site:lmneuquen.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:diariojornada.com.ar&hl=es-419&gl=AR&ceid=AR:es",
    ],
    "INTERIOR BONAERENSE": [
        "https://news.google.com/rss/search?q=site:lanueva.com&hl=es-419&gl=AR&ceid=AR:es",
        "https://news.google.com/rss/search?q=site:0223.com.ar&hl=es-419&gl=AR&ceid=AR:es",
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
    ],
}

# Contexto geográfico de cada región: qué SÍ es local y qué descartar
REGION_CONTEXTO = {
    "EL ESPINAZO": "las provincias de Córdoba, Tucumán, Mendoza, Río Negro/Neuquén y Santa Fe (Rosario)",
    "LITORAL": "las provincias de Santa Fe y Entre Ríos",
    "CUYO": "las provincias de Mendoza, San Juan y San Luis",
    "NOA": "las provincias de Salta, Jujuy, Tucumán, Santiago del Estero y Catamarca",
    "NEA": "las provincias de Misiones, Chaco, Corrientes y Formosa",
    "PATAGONIA": "las provincias de Neuquén, Río Negro, Chubut, Santa Cruz y Tierra del Fuego",
    "INTERIOR BONAERENSE": "el interior de la provincia de Buenos Aires (Bahía Blanca, Mar del Plata, La Plata), NO la Ciudad de Buenos Aires",
    "CABA y Rosca": "la Ciudad Autónoma de Buenos Aires: Legislatura porteña, comunas, legisladores",
    "POLÍTICA NACIONAL": "la política nacional argentina",
}

# ══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES
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
        except Exception:
            continue
    return True

def obtener_noticias_crudas(urls, max_por_feed=6):
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
        except Exception:
            continue
    # Quitar duplicados por título
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
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return False, "Faltan las credenciales de Gmail en los Secrets."
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = GMAIL_USER
        msg["To"] = MAIL_DESTINO
        msg.attach(MIMEText(cuerpo_html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True, "Mail enviado correctamente."
    except Exception as e:
        return False, f"Error al enviar: {str(e)}"

def ia_curar_regional(noticias_lista, contexto_region, top=TOP_NOTICIAS):
    """La IA filtra: deja solo lo verdaderamente regional y políticamente jugoso, descarta lo nacional/porteño replicado."""
    if not ANTHROPIC_API_KEY:
        return None, "Falta la API key de Anthropic en los Secrets."
    if not noticias_lista:
        return [], None
    titles = "\n".join([f"[{i}] {n['Título']}" for i, n in enumerate(noticias_lista)])
    prompt = f"""Sos el editor político de un medio federal argentino. Estás cubriendo {contexto_region}.

Tu trabajo es elegir las {top} noticias MÁS JUGOSAS POLÍTICAMENTE de esta lista. Buscás: poder provincial y local, corrupción, internas políticas, conflictos sociales, decisiones de gobierno con impacto, peleas de poder, escándalos, gremios, obra pública, justicia.

REGLAS ESTRICTAS DE FILTRADO:
- DESCARTÁ noticias nacionales, internacionales, o de la Ciudad de Buenos Aires que cualquier diario replica (ej: dólar, Milei en cadena nacional, fútbol, farándula, clima, efemérides).
- DESCARTÁ noticias blandas sin filo político (espectáculos, deportes, salud genérica, turismo, gastronomía).
- QUEDATE solo con lo que tenga valor político real y sea propio del territorio que cubrís.
- Si una noticia es nacional pero tiene un ángulo local concreto, sirve. Si es nacional pura replicada, descartala.

Noticias disponibles:
{titles}

Elegí las mejores {top} (o menos si no hay suficientes que cumplan). Ordenalas de más a menos importante. Devolvé SOLO JSON sin markdown:
{{"top": [{{"idx": número, "porque": "el ángulo político o por qué tiene jugo, máximo 12 palabras"}}]}}"""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return data["top"], None
    except Exception as e:
        return None, f"Error de IA: {str(e)}"

def ia_buscar_tendencias():
    """Reemplazo del feed muerto de Google Trends: la IA busca tendencias reales con web search."""
    if not ANTHROPIC_API_KEY:
        return None, "Falta la API key de Anthropic en los Secrets."
    hoy = datetime.now().strftime("%d/%m/%Y")
    prompt = f"""Hoy es {hoy}. Buscá en la web qué temas están en tendencia HOY en Argentina, en redes sociales (X/Twitter) y medios digitales. Enfocate en lo político, social y económico que tenga conversación caliente.

Para cada tendencia devolvé el nivel de conversación y un ángulo para producir contenido propio. Devolvé SOLO JSON sin markdown:
{{"tendencias": [{{"titulo": "tema", "nivel": "explotando"|"subiendo"|"estable", "descripcion": "qué pasa en 1-2 oraciones", "angulo": "idea para contenido propio en máximo 12 palabras"}}]}}

Dame entre 6 y 8 tendencias reales y verificadas de hoy."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join([b.text for b in msg.content if hasattr(b, "text")])
        raw = raw.replace("```json", "").replace("```", "").strip()
        # Buscar el JSON dentro de la respuesta
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end >= 0:
            data = json.loads(raw[start:end+1])
            return data["tendencias"], None
        return None, "No se pudo leer la respuesta de la IA."
    except Exception as e:
        return None, f"Error: {str(e)}"

def emoji_nivel(nivel):
    n = str(nivel).lower()
    if "explot" in n: return "🔴 EXPLOTANDO"
    if "sub" in n: return "🟠 SUBIENDO"
    if "estable" in n: return "🟡 ESTABLE"
    return "🟢 BAJO"

def generar_digest():
    """Junta todas las regiones, la IA elige el top 8 más jugoso a nivel nacional, arma el HTML."""
    todas = []
    for region, urls in RSS_FEEDS.items():
        crudas = obtener_noticias_crudas(urls, max_por_feed=2)
        for n in crudas:
            todas.append(n)
    if not todas:
        return None
    seen, unicas = set(), []
    for n in todas:
        if n["Título"] not in seen:
            seen.add(n["Título"])
            unicas.append(n)
    top, err = ia_curar_regional(unicas, "toda la Argentina, con prioridad en lo político y federal", top=TOP_NOTICIAS)
    if err or not top:
        return None
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = f"<h2>📡 Digest 1091 — {hoy}</h2><p>Las {TOP_NOTICIAS} noticias más jugosas del momento:</p>"
    for item in top:
        n = unicas[item["idx"]]
        html += f"<p><b><a href='{n['Link']}'>{n['Título']}</a></b><br><i style='color:#888'>{item['porque']}</i></p>"
    return html

# ══════════════════════════════════════════════════════════════════════════════
#  SOLAPAS
# ══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📰 Radar Noticias",
    "🔥 Tendencias",
    "🎯 Radar Rival",
    "🤖 Predictor",
    "📊 Métricas",
    "📧 Alertas y Digest",
])

# ── TAB 1: NOTICIAS (con filtrado IA regional) ──
with tab1:
    st.caption(f"La IA filtra y deja solo las {TOP_NOTICIAS} noticias políticamente más jugosas de la región, descartando lo nacional/porteño replicado.")
    reg = st.selectbox("Región:", list(RSS_FEEDS.keys()))
    if st.button("Analizar región"):
        if not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic en los Secrets.")
        else:
            with st.spinner("Leyendo feeds y curando con IA..."):
                crudas = obtener_noticias_crudas(RSS_FEEDS[reg])
                top, err = ia_curar_regional(crudas, REGION_CONTEXTO[reg])
            if err:
                st.error(err)
            elif not top:
                st.warning(f"No se encontraron noticias políticamente relevantes de las últimas {CUTOFF_HORAS}hs en esta región.")
            else:
                st.caption(f"{len(top)} noticias seleccionadas de {len(crudas)} leídas (últimas {CUTOFF_HORAS}hs)")
                for item in top:
                    n = crudas[item["idx"]]
                    claves = detectar_palabras_clave(n["Título"])
                    marca = " 🚨 **" + ", ".join(claves).upper() + "**" if claves else ""
                    st.markdown(f"🔹 **[{n['Título']}]({n['Link']})**{marca}")
                    st.caption(f"   → {item['porque']}")
    else:
        st.info("Seleccioná una región y hacé clic en 'Analizar región'.")

# ── TAB 2: TENDENCIAS (con IA + web search) ──
with tab2:
    st.markdown("### 🔥 Tendencias del día en Argentina")
    st.caption("La IA busca en la web qué está caliente hoy. Las que coinciden con tus palabras clave salen con 🚨")
    if st.button("Buscar tendencias ahora"):
        if not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic en los Secrets.")
        else:
            with st.spinner("Buscando tendencias reales en la web..."):
                tendencias, err = ia_buscar_tendencias()
            if err:
                st.error(err)
            elif not tendencias:
                st.warning("No se pudieron obtener tendencias en este momento.")
            else:
                for t in tendencias:
                    titulo = t.get("titulo", "")
                    claves = detectar_palabras_clave(titulo + " " + t.get("descripcion", ""))
                    marca = " 🚨" if claves else ""
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{titulo}**{marca}")
                        st.caption(t.get("descripcion", ""))
                        st.caption(f"💡 Ángulo: {t.get('angulo', '')}")
                    with col2:
                        st.markdown(emoji_nivel(t.get("nivel", "")))
                    st.divider()
    else:
        st.info("Hacé clic para ver qué está explotando ahora en Argentina.")

# ── TAB 3: RADAR RIVAL ──
with tab3:
    st.caption("Buscá la cobertura de cualquier figura pública en las últimas 24hs")
    rival = st.text_input("Nombre a monitorear:", placeholder="Ej: Cristina Kirchner, Mauricio Macri...")
    if st.button("Buscar cobertura") and rival.strip():
        url = f"https://news.google.com/rss/search?q=%22{rival.replace(' ', '+')}%22&hl=es-419&gl=AR&ceid=AR:es"
        with st.spinner(f"Buscando noticias sobre {rival}..."):
            crudas = obtener_noticias_crudas([url], max_por_feed=12)
        if not crudas:
            st.warning(f"No se encontraron noticias recientes sobre {rival}.")
        else:
            st.caption(f"{len(crudas)} noticias sobre {rival} (últimas {CUTOFF_HORAS}hs)")
            for n in crudas:
                st.markdown(f"🔸 [{n['Título']}]({n['Link']})")

# ── TAB 4: PREDICTOR (IA real) ──
with tab4:
    st.caption("La IA evalúa tu borrador según tono, datos y potencial de viralidad")
    t = st.text_area("Pegá el borrador del tuit o texto:")
    if st.button("Evaluar con IA"):
        if not t.strip():
            st.warning("Escribí algo primero.")
        elif not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic en los Secrets.")
        else:
            with st.spinner("La IA está analizando..."):
                prompt = f"""Sos un estratega de comunicación política argentina. Evaluá este borrador de posteo para redes.

Borrador: "{t}"

Analizá tono, datos vs militancia, potencial de viralidad, riesgos. Devolvé SOLO JSON sin markdown:
{{"score": número 0-100, "veredicto": "frase corta", "fortalezas": ["f1", "f2"], "mejoras": ["m1", "m2"], "plataforma_ideal": "X / Instagram / TikTok"}}"""
                try:
                    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                    msg = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=600,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    raw = msg.content[0].text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(raw)
                    score = data["score"]
                    if score >= 75:
                        st.success(f"✅ Score: {score}/100 — {data['veredicto']}")
                    elif score >= 50:
                        st.warning(f"⚠️ Score: {score}/100 — {data['veredicto']}")
                    else:
                        st.error(f"❌ Score: {score}/100 — {data['veredicto']}")
                    st.markdown(f"**Plataforma ideal:** {data['plataforma_ideal']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Fortalezas:**")
                        for f in data["fortalezas"]:
                            st.markdown(f"- {f}")
                    with col2:
                        st.markdown("**A mejorar:**")
                        for m in data["mejoras"]:
                            st.markdown(f"- {m}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ── TAB 5: MÉTRICAS ──
with tab5:
    col1, col2 = st.columns(2)
    with col1:
        imp = st.number_input("Impresiones", min_value=0, value=0)
    with col2:
        int_ = st.number_input("Interacciones", min_value=0, value=0)
    if st.button("Calcular engagement"):
        if imp > 0:
            eng = round((int_ / imp) * 100, 2)
            st.metric("Engagement Rate", f"{eng}%")
            if eng >= 5: st.success("🔥 Excelente (>5%)")
            elif eng >= 2: st.warning("📊 Aceptable (2-5%)")
            else: st.error("📉 Bajo (<2%)")
        else:
            st.warning("Ingresá las impresiones primero.")

# ── TAB 6: ALERTAS Y DIGEST ──
with tab6:
    st.markdown("### 📧 Envío de Digest por Mail")
    st.caption(f"Destino configurado: {MAIL_DESTINO}")
    st.markdown(f"**Digest del momento** — las {TOP_NOTICIAS} noticias más jugosas ahora")
    if st.button("Generar y enviar Digest ahora"):
        if not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic en los Secrets.")
        elif not GMAIL_APP_PASSWORD:
            st.error("Falta la contraseña de aplicación de Gmail en los Secrets.")
        else:
            with st.spinner("Armando el digest con IA..."):
                html = generar_digest()
            if not html:
                st.error("No se pudo generar el digest. Puede que no haya noticias o falle la conexión.")
            else:
                ok, msg = enviar_mail(f"📡 Digest 1091 — Top {TOP_NOTICIAS} del día", html)
                if ok:
                    st.success("✅ " + msg)
                    with st.expander("Ver lo que se envió"):
                        st.markdown(html, unsafe_allow_html=True)
                else:
                    st.error("❌ " + msg)

    st.divider()
    st.markdown("**Prueba de alerta por palabra clave**")
    st.caption("Escaneá los feeds ahora y enviá un mail si hay noticias con tus palabras clave")
    st.markdown("Palabras vigiladas: " + ", ".join(PALABRAS_CLAVE))
    if st.button("Escanear y alertar"):
        if not GMAIL_APP_PASSWORD:
            st.error("Falta la contraseña de Gmail en los Secrets.")
        else:
            with st.spinner("Escaneando todos los feeds..."):
                alertas = []
                for urls in RSS_FEEDS.values():
                    crudas = obtener_noticias_crudas(urls, max_por_feed=3)
                    for n in crudas:
                        claves = detectar_palabras_clave(n["Título"])
                        if claves:
                            alertas.append((n["Título"], n["Link"], claves))
            if not alertas:
                st.info("No hay noticias con palabras clave en este momento.")
            else:
                html = "<h2>🚨 Alertas 1091</h2>"
                for titulo, link, claves in alertas:
                    html += f"<p><b><a href='{link}'>{titulo}</a></b><br><span style='color:#e89a3c'>[{', '.join(claves).upper()}]</span></p>"
                ok, msg = enviar_mail(f"🚨 {len(alertas)} alertas — 1091", html)
                if ok:
                    st.success(f"✅ {len(alertas)} alertas enviadas por mail")
                else:
                    st.error("❌ " + msg)

    st.divider()
    st.info("""**Para los envíos automáticos (8:30, 12:30 y 18:00):**
Streamlit Cloud no puede correr tareas solo en horarios fijos. Para eso se usa un servicio externo gratuito (cron-job.org) que despierta el digest a esas horas. Lo configuramos en la próxima sesión — el código ya está listo.""")
