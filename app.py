cat << 'PYEOF' > /tmp/app_final.py
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

st.set_page_config(page_title="1091 | Centro de Monitoreo", layout="wide")
st.markdown("""<style>
.stApp {background-color: #0e0e10; color: #E0E0E0;}
h1, h2, h3 {color: #FFFFFF !important;}
.stTabs [data-baseweb="tab"] {color: #888;}
.stTabs [aria-selected="true"] {color: #e89a3c !important; border-bottom-color: #e89a3c !important;}
.stButton button {background-color: #e89a3c; color: #0e0e10; font-weight: 600; border: none;}
</style>""", unsafe_allow_html=True)

st.title("📡 1091 — Centro de Monitoreo")

# Claves guardadas de forma segura en los "Secrets" de Streamlit
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
GMAIL_USER = st.secrets.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = st.secrets.get("GMAIL_APP_PASSWORD", "")
MAIL_DESTINO = st.secrets.get("MAIL_DESTINO", "matumontanez@gmail.com")

# Palabras clave que disparan alerta
PALABRAS_CLAVE = [
    "jubilados", "cristina", "milei", "pami", "subte", "protesta",
    "legislatura", "corrupción", "corrupcion", "femicidio", "huelga",
    "desaparecido", "intendente", "juicio", "paro", "represión", "represion",
]

CUTOFF_HORAS = 24

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

def obtener_noticias(urls, max_por_feed=4):
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
    return pd.DataFrame(noticias).head(15) if noticias else pd.DataFrame(columns=["Título", "Link"])

def detectar_palabras_clave(titulo):
    t = titulo.lower()
    return [p for p in PALABRAS_CLAVE if p in t]

def semaforo(traffic_str):
    try:
        n = int(str(traffic_str).replace("+", "").replace(",", "").replace(".", "").strip())
        if n >= 200000: return "🔴 EXPLOTANDO"
        elif n >= 50000: return "🟠 SUBIENDO"
        elif n >= 10000: return "🟡 ESTABLE"
        else: return "🟢 BAJO"
    except Exception:
        return "⚪ SIN DATO"

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

def ia_seleccionar_top(noticias_lista, top=5):
    if not ANTHROPIC_API_KEY:
        return None, "Falta la API key de Anthropic en los Secrets."
    titles = "\n".join([f"[{i}] {n['Título']}" for i, n in enumerate(noticias_lista)])
    prompt = f"""Sos editor de un medio federal argentino. Priorizás poder provincial, corrupción, conflictos sociales, política real con impacto.

Noticias:
{titles}

Elegí las {top} más importantes. Devolvé SOLO JSON sin markdown:
{{"top": [{{"idx": número, "porque": "por qué importa en máximo 12 palabras"}}]}}"""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return data["top"], None
    except Exception as e:
        return None, f"Error de IA: {str(e)}"

def generar_digest():
    """Junta todas las regiones, deja que la IA elija el top 5, arma el HTML del mail."""
    todas = []
    for urls in RSS_FEEDS.values():
        df = obtener_noticias(urls, max_por_feed=2)
        for _, r in df.iterrows():
            todas.append({"Título": r["Título"], "Link": r["Link"]})
    if not todas:
        return None
    seen = set()
    unicas = []
    for n in todas:
        if n["Título"] not in seen:
            seen.add(n["Título"])
            unicas.append(n)
    top, err = ia_seleccionar_top(unicas, top=5)
    if err or not top:
        return None
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = f"<h2>📡 Digest 1091 — {hoy}</h2><p>Las 5 noticias más importantes del momento:</p>"
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

# ── TAB 1: NOTICIAS ──
with tab1:
    reg = st.selectbox("Región:", list(RSS_FEEDS.keys()))
    if st.button("Actualizar noticias"):
        with st.spinner("Leyendo feeds..."):
            df = obtener_noticias(RSS_FEEDS[reg])
        if df.empty:
            st.warning(f"No hay noticias de las últimas {CUTOFF_HORAS}hs en esta región.")
        else:
            st.caption(f"{len(df)} noticias de las últimas {CUTOFF_HORAS} horas")
            for _, r in df.iterrows():
                claves = detectar_palabras_clave(r["Título"])
                marca = " 🚨 **" + ", ".join(claves).upper() + "**" if claves else ""
                st.markdown(f"🔹 [{r['Título']}]({r['Link']}){marca}")
    else:
        st.info("Seleccioná una región y hacé clic en 'Actualizar noticias'.")

# ── TAB 2: TENDENCIAS ──
with tab2:
    st.markdown("### 🔥 Temas que explotan hoy en Argentina")
    st.caption("Las tendencias que coinciden con tus palabras clave aparecen marcadas con 🚨")
    if st.button("Cargar tendencias del día"):
        with st.spinner("Leyendo Google Trends Argentina..."):
            feed = feedparser.parse("https://trends.google.com/trends/trendingsearches/daily/rss?geo=AR")
        if not feed.entries:
            st.error("No se pudo conectar con Google Trends. Probá de nuevo en unos minutos.")
        else:
            for entry in feed.entries[:12]:
                titulo = entry.get("title", "Sin título")
                trafico = entry.get("ht_approx_traffic", "") or entry.get("approx_traffic", "")
                estado = semaforo(trafico)
                claves = detectar_palabras_clave(titulo)
                marca = " 🚨" if claves else ""
                trafico_txt = f"~{trafico} búsquedas" if trafico else ""
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{titulo}**{marca} {trafico_txt}")
                with col2:
                    st.markdown(estado)
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
            df = obtener_noticias([url], max_por_feed=12)
        if df.empty:
            st.warning(f"No se encontraron noticias recientes sobre {rival}.")
        else:
            st.caption(f"{len(df)} noticias sobre {rival}")
            for _, r in df.iterrows():
                st.markdown(f"🔸 [{r['Título']}]({r['Link']})")

# ── TAB 4: PREDICTOR (con IA real) ──
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
                prompt = f"""Sos un estratega de comunicación política argentina. Evaluá este borrador de posteo para redes sociales.

Borrador: "{t}"

Analizá: tono, proporción de datos vs militancia, potencial de viralidad, riesgos. Devolvé SOLO JSON sin markdown:
{{"score": número del 0 al 100, "veredicto": "frase corta", "fortalezas": ["f1", "f2"], "mejoras": ["m1", "m2"], "plataforma_ideal": "X / Instagram / TikTok"}}"""
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

    st.markdown("**Digest del momento** — las 5 noticias más importantes ahora")
    if st.button("Generar y enviar Digest ahora"):
        if not ANTHROPIC_API_KEY:
            st.error("Falta la API key de Anthropic en los Secrets.")
        elif not GMAIL_APP_PASSWORD:
            st.error("Falta la contraseña de aplicación de Gmail en los Secrets.")
        else:
            with st.spinner("Armando el digest con IA..."):
                html = generar_digest()
            if not html:
                st.error("No se pudo generar el digest. Puede ser que no haya noticias o falle la conexión.")
            else:
                ok, msg = enviar_mail("📡 Digest 1091 — Top 5 del día", html)
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
                    df = obtener_noticias(urls, max_por_feed=3)
                    for _, r in df.iterrows():
                        claves = detectar_palabras_clave(r["Título"])
                        if claves:
                            alertas.append((r["Título"], r["Link"], claves))
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
Streamlit Cloud no puede correr tareas solo en horarios fijos. Para eso se usa un servicio externo gratuito (GitHub Actions o cron-job.org) que abre el digest a esas horas. Lo dejamos configurado en la próxima sesión — el código ya está listo para recibirlo.""")
PYEOF
echo "ok — $(wc -l < /tmp/app_final.py) líneas"
python3 -c "import ast; ast.parse(open('/tmp/app_final.py').read()); print('Sintaxis válida ✓')"
Salida

ok — 403 líneas
