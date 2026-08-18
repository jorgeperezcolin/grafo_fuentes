import html
import itertools
from difflib import SequenceMatcher

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

st.set_page_config(page_title="Grafo bibliográfico | IA y decisor", layout="wide")

ARTICLES = [
    {"id":"A01","priority":1,"title":"Does using artificial intelligence assistance accelerate skill decay and hinder skill development without performers’ awareness?","authors":"B. N. Macnamara et al.","year":2024,"subtopic":"Deskilling y deterioro de capacidades","doi":"10.1186/s41235-024-00572-8","level":"Núcleo central"},
    {"id":"A02","priority":2,"title":"The dependency dilemma: How machine learning decision aids can undermine skill growth","authors":"K. Bauer; M. Nofer; B. Henrich; H. Drachsler; O. Hinz","year":2026,"subtopic":"Deskilling y deterioro de capacidades","doi":"10.1007/s12599-026-01014-z","level":"Núcleo central"},
    {"id":"A03","priority":3,"title":"AI deskilling is a structural problem","authors":"A. Ferdman","year":2026,"subtopic":"Gobernanza y capacidades","doi":"10.1007/s00146-025-02686-z","level":"Núcleo central"},
    {"id":"A04","priority":4,"title":"AI-induced deskilling in medicine: A mixed-method review and research agenda for healthcare and beyond","authors":"C. Natali; L. Marconi; L. D. Dias Duran; F. Cabitza","year":2025,"subtopic":"Deskilling y deterioro de capacidades","doi":"10.1007/s10462-025-11352-1","level":"Núcleo central"},
    {"id":"A05","priority":5,"title":"Endoscopist deskilling risk after exposure to artificial intelligence in colonoscopy: A multicentre, observational study","authors":"K. Budzyń; M. Romańczyk; D. Kitala; et al.","year":2025,"subtopic":"Deskilling y deterioro de capacidades","doi":"10.1016/S2468-1253(25)00133-5","level":"Núcleo central"},
    {"id":"A06","priority":6,"title":"To trust or to think: Cognitive forcing functions can reduce overreliance on AI in AI-assisted decision-making","authors":"Z. Buçinca; M. B. Malaya; K. Z. Gajos","year":2021,"subtopic":"Interacción humano–IA","doi":"10.1145/3449287","level":"Núcleo central"},
    {"id":"A07","priority":7,"title":"Offloading wisdom: Four technological relations that mediate phronesis","authors":"A. Zelny","year":2025,"subtopic":"Phronesis y juicio directivo","doi":"10.1007/s13347-025-00889-2","level":"Núcleo central"},
    {"id":"A08","priority":8,"title":"Artificial intelligence and the future of practical wisdom in business management","authors":"S. R. Clegg; M. Berti; A. V. Simpson; M. Pina e Cunha","year":2020,"subtopic":"Phronesis y juicio directivo","doi":"10.1007/978-3-030-00140-7_2","level":"Núcleo central"},
    {"id":"A09","priority":9,"title":"Shadow learning: Building robotic surgical skill when approved means fail","authors":"M. Beane","year":2019,"subtopic":"Formación y aprendizaje profesional","doi":"10.1177/0001839217751692","level":"Núcleo central"},
    {"id":"A10","priority":10,"title":"Artificial intelligence and management: The automation–augmentation paradox","authors":"S. Raisch; S. Krakowski","year":2021,"subtopic":"Gobernanza y capacidades","doi":"10.5465/amr.2018.0072","level":"Núcleo central"},
    {"id":"A11","priority":11,"title":"The flaws of policies requiring human oversight of government algorithms","authors":"B. Green","year":2022,"subtopic":"Gobernanza y capacidades","doi":"10.1016/j.clsr.2022.105681","level":"Núcleo central"},
    {"id":"A12","priority":12,"title":"Ironies of automation","authors":"L. Bainbridge","year":1983,"subtopic":"Deskilling y deterioro de capacidades","doi":"10.1016/0005-1098(83)90046-8","level":"Complementaria"},
    {"id":"A13","priority":13,"title":"Humans and automation: Use, misuse, disuse, abuse","authors":"R. Parasuraman; V. Riley","year":1997,"subtopic":"Interacción humano–IA","doi":"10.1518/001872097778543886","level":"Complementaria"},
    {"id":"A14","priority":14,"title":"A formal model of how artificial intelligence erodes human agency","authors":"A. Moon; B. Boudreaux","year":2026,"subtopic":"Gobernanza y capacidades","doi":"10.7249/RRA4817-1","level":"Complementaria"},
    {"id":"A15","priority":15,"title":"Scaling AI with adaptive governance","authors":"G. Lanzolla; M. Pagani; C. L. Tucci","year":2026,"subtopic":"Gobernanza y capacidades","doi":"","level":"Complementaria","source_url":"https://sloanreview.mit.edu/article/scaling-ai-with-adaptive-governance/"},
    {"id":"A16","priority":16,"title":"The AI pace gap: Anticipatory governance and the asymmetry of e-government transformation","authors":"Z. Belkhamza","year":2026,"subtopic":"Asimetría adopción–gobernanza","doi":"10.1007/978-3-032-34304-8_9","level":"Complementaria"},
    {"id":"A17","priority":17,"title":"The governance gap behind AI deployment in high-informality economies: Explaining institutional dependency in AI adoption","authors":"I. Velarde","year":2026,"subtopic":"Asimetría adopción–gobernanza","doi":"10.5281/zenodo.20217978","level":"Complementaria"},
]

SUBTOPICS = [
    "Deskilling y deterioro de capacidades",
    "Interacción humano–IA",
    "Phronesis y juicio directivo",
    "Formación y aprendizaje profesional",
    "Gobernanza y capacidades",
    "Asimetría adopción–gobernanza",
]

FALLBACK_DIRECT = [
    ("A02", "A13", "Cita directa verificada"),
    ("A02", "A06", "Cita directa verificada"),
    ("A05", "A01", "Cita directa verificada"),
    ("A03", "A12", "Cita directa verificada"),
    ("A03", "A05", "Cita directa verificada"),
    ("A03", "A04", "Cita directa verificada"),
    ("A03", "A07", "Cita directa verificada"),
    ("A11", "A06", "Cita directa verificada"),
]

VERSION_EQUIVALENT = [
    ("A04", "A12", "Cita una versión/proceedings equivalente de 'Ironies of automation'"),
]

HEADERS = {"User-Agent": "ia-decisor-literature-graph/1.0"}
OA_API = "https://api.openalex.org/works"


def _short_oa_id(value):
    if not value:
        return ""
    return value.rstrip("/").split("/")[-1]


def _title_similarity(a, b):
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


@st.cache_data(ttl=86400, show_spinner=False)
def resolve_openalex(title, doi=""):
    try:
        if doi:
            endpoint = f"{OA_API}/https://doi.org/{doi}"
            r = requests.get(endpoint, headers=HEADERS, timeout=15)
            if r.ok:
                w = r.json()
                return {
                    "id": w.get("id", ""),
                    "display_name": w.get("display_name", ""),
                    "publication_year": w.get("publication_year"),
                    "doi": w.get("doi", ""),
                    "referenced_works": w.get("referenced_works", []) or [],
                    "cited_by_count": w.get("cited_by_count", 0) or 0,
                    "match": "DOI exacto",
                }
        r = requests.get(OA_API, params={"search": title, "per-page": 3}, headers=HEADERS, timeout=15)
        if not r.ok:
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        ranked = sorted(results, key=lambda w: _title_similarity(title, w.get("display_name", "")), reverse=True)
        w = ranked[0]
        similarity = _title_similarity(title, w.get("display_name", ""))
        if similarity < 0.72:
            return None
        return {
            "id": w.get("id", ""),
            "display_name": w.get("display_name", ""),
            "publication_year": w.get("publication_year"),
            "doi": w.get("doi", ""),
            "referenced_works": w.get("referenced_works", []) or [],
            "cited_by_count": w.get("cited_by_count", 0) or 0,
            "match": f"Título ({similarity:.0%})",
        }
    except requests.RequestException:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_reference_metadata(openalex_ids):
    ids = [_short_oa_id(x) for x in openalex_ids if x]
    rows = []
    for start in range(0, len(ids), 40):
        chunk = ids[start:start + 40]
        try:
            r = requests.get(
                OA_API,
                params={"filter": "openalex_id:" + "|".join(chunk), "per-page": 40},
                headers=HEADERS,
                timeout=20,
            )
            if not r.ok:
                continue
            for w in r.json().get("results", []):
                rows.append({
                    "OpenAlex": _short_oa_id(w.get("id", "")),
                    "Título": w.get("display_name", ""),
                    "Año": w.get("publication_year"),
                    "DOI": w.get("doi", "") or "",
                    "Citas recibidas": w.get("cited_by_count", 0) or 0,
                })
        except requests.RequestException:
            continue
    return rows


def resolve_corpus(use_live):
    resolved = {}
    if not use_live:
        return resolved
    progress = st.progress(0, text="Consultando OpenAlex…")
    for i, article in enumerate(ARTICLES):
        resolved[article["id"]] = resolve_openalex(article["title"], article.get("doi", ""))
        progress.progress((i + 1) / len(ARTICLES), text=f"OpenAlex: {i + 1}/{len(ARTICLES)} obras")
    progress.empty()
    return resolved


def build_relations(resolved, selected_ids, min_shared):
    id_to_article = {a["id"]: a for a in ARTICLES}
    selected_set = set(selected_ids)
    live_direct = set()
    oa_to_seed = {}
    for seed_id, data in resolved.items():
        if data and data.get("id"):
            oa_to_seed[data["id"]] = seed_id
    for src, data in resolved.items():
        if src not in selected_set or not data:
            continue
        refs = set(data.get("referenced_works", []))
        for oa_target in refs:
            target = oa_to_seed.get(oa_target)
            if target and target in selected_set and target != src:
                live_direct.add((src, target, "Cita directa — OpenAlex"))

    direct = set(live_direct)
    for src, dst, label in FALLBACK_DIRECT:
        if src in selected_set and dst in selected_set:
            direct.add((src, dst, label))

    coupling = []
    for left, right in itertools.combinations(selected_ids, 2):
        dl, dr = resolved.get(left), resolved.get(right)
        if not dl or not dr:
            continue
        shared = set(dl.get("referenced_works", [])) & set(dr.get("referenced_works", []))
        if len(shared) >= min_shared:
            coupling.append((left, right, len(shared)))

    version_edges = [e for e in VERSION_EQUIVALENT if e[0] in selected_set and e[1] in selected_set]
    direct_rows = [{"Origen": id_to_article[s]["title"], "Destino": id_to_article[d]["title"], "Tipo": label} for s, d, label in sorted(direct)]
    coupling_rows = [{"Artículo A": id_to_article[a]["title"], "Artículo B": id_to_article[b]["title"], "Referencias compartidas": n} for a, b, n in sorted(coupling, key=lambda x: x[2], reverse=True)]
    return direct, coupling, version_edges, direct_rows, coupling_rows


def make_graph(selected_articles, direct, coupling, version_edges, show_topics, edge_types):
    topic_palette = {
        "Deskilling y deterioro de capacidades": "#4C78A8",
        "Interacción humano–IA": "#F58518",
        "Phronesis y juicio directivo": "#54A24B",
        "Formación y aprendizaje profesional": "#E45756",
        "Gobernanza y capacidades": "#B279A2",
        "Asimetría adopción–gobernanza": "#72B7B2",
    }
    net = Network(height="720px", width="100%", directed=True, bgcolor="#FFFFFF", font_color="#222222", cdn_resources="in_line")
    net.barnes_hut(gravity=-7000, central_gravity=0.25, spring_length=175, spring_strength=0.035, damping=0.82)
    selected_ids = {a["id"] for a in selected_articles}
    for a in selected_articles:
        label = f"#{a['priority']} · {a['authors'].split(';')[0]} ({a['year']})"
        tooltip = f"<b>{html.escape(a['title'])}</b><br>{html.escape(a['authors'])}<br>Subtema: {html.escape(a['subtopic'])}<br>Nivel: {html.escape(a['level'])}<br>DOI: {html.escape(a.get('doi',''))}"
        net.add_node(a["id"], label=label, title=tooltip, color=topic_palette[a["subtopic"]], size=28 if a["level"] == "Núcleo central" else 20, shape="dot")

    if show_topics and "Subtema" in edge_types:
        used_topics = sorted({a["subtopic"] for a in selected_articles})
        for topic in used_topics:
            tid = "T::" + topic
            net.add_node(tid, label=topic, title="Subtema MECE", color=topic_palette[topic], shape="box", size=34, physics=True)
        for a in selected_articles:
            net.add_edge(a["id"], "T::" + a["subtopic"], title="Pertenece al subtema", color="#B8B8B8", width=1, arrows="")

    if "Cita directa" in edge_types:
        for src, dst, label in direct:
            if src in selected_ids and dst in selected_ids:
                net.add_edge(src, dst, title=label, color="#C23B33", width=2.6, arrows="to")
    if "Acoplamiento bibliográfico" in edge_types:
        for left, right, shared in coupling:
            if left in selected_ids and right in selected_ids:
                net.add_edge(left, right, title=f"{shared} referencias compartidas", color="#7C7C7C", width=min(1 + shared / 2, 7), dashes=True, arrows="")
    if "Versión equivalente" in edge_types:
        for src, dst, label in version_edges:
            if src in selected_ids and dst in selected_ids:
                net.add_edge(src, dst, title=label, color="#D6A600", width=2, dashes=True, arrows="to")
    return net.generate_html()


st.title("Grafo bibliográfico — IA, capacidades humanas y juicio directivo")
st.caption("Red interactiva de los 17 artículos priorizados. Combina citas cruzadas, acoplamiento bibliográfico y los seis subtemas MECE del proyecto.")

with st.sidebar:
    st.header("Filtros")
    max_priority = st.slider("Prioridad máxima", 1, 17, 17)
    chosen_topics = st.multiselect("Subtemas", SUBTOPICS, default=SUBTOPICS)
    chosen_levels = st.multiselect("Nivel", ["Núcleo central", "Complementaria"], default=["Núcleo central", "Complementaria"])
    edge_types = st.multiselect("Relaciones", ["Cita directa", "Acoplamiento bibliográfico", "Subtema", "Versión equivalente"], default=["Cita directa", "Acoplamiento bibliográfico", "Subtema"])
    min_shared = st.slider("Mínimo de referencias compartidas", 1, 10, 2)
    use_live = st.toggle("Consultar OpenAlex en vivo", value=True, help="Resuelve cada obra y compara sus listas de referencias. Los resultados se almacenan 24 horas en caché.")
    show_topics = st.toggle("Mostrar nodos de subtema", value=True)

selected_articles = [a for a in ARTICLES if a["priority"] <= max_priority and a["subtopic"] in chosen_topics and a["level"] in chosen_levels]
selected_ids = [a["id"] for a in selected_articles]
resolved = resolve_corpus(use_live)
direct, coupling, version_edges, direct_rows, coupling_rows = build_relations(resolved, selected_ids, min_shared)
resolved_count = sum(1 for a in selected_articles if resolved.get(a["id"])) if use_live else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Artículos visibles", len(selected_articles))
m2.metric("Citas cruzadas", len(direct))
m3.metric("Pares acoplados", len(coupling))
m4.metric("Resueltos en OpenAlex", f"{resolved_count}/{len(selected_articles)}" if use_live else "Desactivado")

if use_live and resolved_count < len(selected_articles):
    st.info("Algunas obras no fueron resueltas por OpenAlex. El grafo conserva las citas cruzadas verificadas manualmente como respaldo; el acoplamiento bibliográfico sólo se calcula para obras resueltas.")

tab_graph, tab_rel, tab_refs, tab_cov = st.tabs(["Grafo", "Relaciones", "Referencias por artículo", "Cobertura"])
with tab_graph:
    if not selected_articles:
        st.warning("No hay artículos con los filtros actuales.")
    else:
        graph_html = make_graph(selected_articles, direct, coupling, version_edges, show_topics, edge_types)
        components.html(graph_html, height=740, scrolling=False)
        st.caption("Aristas rojas con flecha: cita directa. Grises discontinuas: referencias compartidas. Amarillas discontinuas: versión bibliográfica equivalente. Los nodos se colorean por subtema.")

with tab_rel:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Citas cruzadas")
        if direct_rows:
            df_direct = pd.DataFrame(direct_rows)
            st.dataframe(df_direct, use_container_width=True, hide_index=True)
            st.download_button("Descargar citas CSV", df_direct.to_csv(index=False).encode("utf-8"), "citas_cruzadas.csv", "text/csv")
        else:
            st.write("No hay citas cruzadas visibles con estos filtros.")
    with col_b:
        st.subheader("Acoplamiento bibliográfico")
        if coupling_rows:
            df_coupling = pd.DataFrame(coupling_rows)
            st.dataframe(df_coupling, use_container_width=True, hide_index=True)
            st.download_button("Descargar acoplamiento CSV", df_coupling.to_csv(index=False).encode("utf-8"), "acoplamiento_bibliografico.csv", "text/csv")
        else:
            st.write("No hay pares que alcancen el umbral seleccionado, o faltan datos OpenAlex.")

with tab_refs:
    st.subheader("Fuentes citadas por cada artículo")
    options = {f"#{a['priority']} · {a['authors'].split(';')[0]} · {a['title']}": a for a in selected_articles}
    if options:
        selected_label = st.selectbox("Artículo", list(options.keys()))
        chosen = options[selected_label]
        oa = resolved.get(chosen["id"]) if use_live else None
        if oa:
            refs = oa.get("referenced_works", [])
            st.write(f"OpenAlex registra **{len(refs)} referencias** para esta obra. Coincidencia: **{oa.get('match','')}**.")
            if refs and st.button("Resolver títulos de las referencias", type="primary"):
                rows = fetch_reference_metadata(refs)
                if rows:
                    rdf = pd.DataFrame(rows).sort_values(["Año", "Título"], ascending=[False, True])
                    st.dataframe(rdf, use_container_width=True, hide_index=True)
                    st.download_button("Descargar referencias CSV", rdf.to_csv(index=False).encode("utf-8"), f"referencias_{chosen['id']}.csv", "text/csv")
                else:
                    st.warning("No fue posible recuperar metadatos de las referencias en esta consulta.")
        else:
            st.info("Activa OpenAlex en vivo para consultar la lista de referencias de esta obra.")

with tab_cov:
    rows = []
    for a in selected_articles:
        oa = resolved.get(a["id"]) if use_live else None
        rows.append({"Prioridad": a["priority"], "Artículo": a["title"], "Subtema": a["subtopic"], "Nivel": a["level"], "OpenAlex": "Sí" if oa else "No", "Tipo de match": oa.get("match", "") if oa else "", "Referencias OpenAlex": len(oa.get("referenced_works", [])) if oa else 0, "Citas recibidas": oa.get("cited_by_count", 0) if oa else 0})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("**Interpretación:** la cita directa es direccional; el acoplamiento bibliográfico no implica que un artículo cite al otro, sino que ambos comparten fuentes. El vínculo de subtema es una clasificación analítica del proyecto.")

st.divider()
st.caption("Datos bibliográficos base: corpus priorizado del proyecto. Relaciones dinámicas: OpenAlex. Fallback: citas cruzadas verificadas manualmente en las fuentes originales consultadas.")
