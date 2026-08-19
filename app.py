import html
import itertools
import json
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

st.set_page_config(page_title="Grafo bibliográfico | IA y decisor", layout="wide")

DATA_FILE = Path(__file__).with_name("sources.csv")
HEADERS = {"User-Agent": "ia-decisor-literature-graph/1.2"}
OA_API = "https://api.openalex.org/works"

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

TOPIC_COLORS = {
    "Deskilling y deterioro de capacidades": "#4C78A8",
    "Interacción humano–IA": "#F58518",
    "Phronesis y juicio directivo": "#54A24B",
    "Formación y aprendizaje profesional": "#E45756",
    "Gobernanza y capacidades": "#B279A2",
    "Asimetría adopción–gobernanza": "#72B7B2",
}


def extract_doi(value: str) -> str:
    value = str(value or "").strip()
    if "doi.org/" in value.lower():
        return value.split("doi.org/", 1)[1]
    return value if value.startswith("10.") else ""


def reconstruct_abstract(inverted_index) -> str:
    """Reconstruct OpenAlex abstract_inverted_index into readable text."""
    if not inverted_index:
        return ""
    positioned_words = []
    for word, positions in inverted_index.items():
        for position in positions:
            positioned_words.append((position, word))
    positioned_words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned_words)


@st.cache_data(show_spinner=False)
def load_sources() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE, dtype=str).fillna("")
    required = [
        "priority", "title", "authors", "year", "subtopic",
        "publication", "doi_url", "origin", "level", "description",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en sources.csv: {', '.join(missing)}")
    if len(df) != 17:
        raise ValueError(f"Se esperaban 17 fuentes y se encontraron {len(df)}")
    df["priority"] = df["priority"].astype(int)
    df["year"] = df["year"].astype(int)
    df["id"] = df["priority"].map(lambda n: f"A{n:02d}")
    df["doi"] = df["doi_url"].map(extract_doi)
    return df.sort_values("priority").reset_index(drop=True)


SOURCES_DF = load_sources()
ARTICLES = SOURCES_DF.to_dict("records")
SUBTOPICS = list(dict.fromkeys(SOURCES_DF["subtopic"].tolist()))


def _short_oa_id(value):
    if not value:
        return ""
    return value.rstrip("/").split("/")[-1]


def _title_similarity(a, b):
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def _openalex_payload(work, match):
    return {
        "id": work.get("id", ""),
        "display_name": work.get("display_name", ""),
        "publication_year": work.get("publication_year"),
        "doi": work.get("doi", ""),
        "referenced_works": work.get("referenced_works", []) or [],
        "cited_by_count": work.get("cited_by_count", 0) or 0,
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
        "match": match,
    }


@st.cache_data(ttl=86400, show_spinner=False)
def resolve_openalex(title, doi=""):
    try:
        if doi:
            endpoint = f"{OA_API}/https://doi.org/{doi}"
            r = requests.get(endpoint, headers=HEADERS, timeout=15)
            if r.ok:
                return _openalex_payload(r.json(), "DOI exacto")

        r = requests.get(OA_API, params={"search": title, "per-page": 3}, headers=HEADERS, timeout=15)
        if not r.ok:
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        ranked = sorted(results, key=lambda w: _title_similarity(title, w.get("display_name", "")), reverse=True)
        work = ranked[0]
        similarity = _title_similarity(title, work.get("display_name", ""))
        if similarity < 0.72:
            return None
        return _openalex_payload(work, f"Título ({similarity:.0%})")
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
        resolved[article["id"]] = resolve_openalex(article["title"], article["doi"])
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
        for oa_target in set(data.get("referenced_works", [])):
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
    direct_rows = [
        {"Origen": id_to_article[s]["title"], "Destino": id_to_article[d]["title"], "Tipo": label}
        for s, d, label in sorted(direct)
    ]
    coupling_rows = [
        {"Artículo A": id_to_article[a]["title"], "Artículo B": id_to_article[b]["title"], "Referencias compartidas": n}
        for a, b, n in sorted(coupling, key=lambda x: x[2], reverse=True)
    ]
    return direct, coupling, version_edges, direct_rows, coupling_rows


def make_graph(selected_articles, resolved, direct, coupling, version_edges, show_topics, edge_types):
    net = Network(height="720px", width="100%", directed=True, bgcolor="#FFFFFF", font_color="#222222", cdn_resources="in_line")
    net.barnes_hut(gravity=-7000, central_gravity=0.25, spring_length=175, spring_strength=0.035, damping=0.82)
    selected_ids = {a["id"] for a in selected_articles}
    work_details = {}

    for a in selected_articles:
        label = f"#{a['priority']} · {a['authors'].split(';')[0]} ({a['year']})"
        tooltip = (
            f"<b>{html.escape(a['title'])}</b><br>"
            f"Autores: {html.escape(a['authors'])}<br>"
            f"Publicación: {html.escape(a['publication'])}<br>"
            f"Subtema: {html.escape(a['subtopic'])}<br>"
            f"Nivel: {html.escape(a['level'])}<br>"
            f"Origen documental: {html.escape(a['origin'])}<br>"
            f"DOI/URL: {html.escape(a['doi_url'])}"
        )
        net.add_node(
            a["id"], label=label, title=tooltip,
            color=TOPIC_COLORS.get(a["subtopic"], "#777777"),
            size=28 if a["level"] == "Núcleo central" else 20,
            shape="dot",
        )
        oa = resolved.get(a["id"]) or {}
        work_details[a["id"]] = {
            "priority": a["priority"],
            "title": a["title"],
            "authors": a["authors"],
            "year": a["year"],
            "subtopic": a["subtopic"],
            "publication": a["publication"],
            "level": a["level"],
            "doi_url": a["doi_url"],
            "description": a.get("description", ""),
            "abstract": oa.get("abstract", ""),
            "openalex_match": oa.get("match", ""),
        }

    if show_topics and "Subtema" in edge_types:
        for topic in sorted({a["subtopic"] for a in selected_articles}):
            tid = "T::" + topic
            net.add_node(tid, label=topic, title="Subtema MECE", color=TOPIC_COLORS.get(topic, "#777777"), shape="box", size=34)
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

    graph_html = net.generate_html()
    details_json = json.dumps(work_details, ensure_ascii=False).replace("</", "<\\/")
    card_html = f"""
<style>
#work-detail-card {{
    display: none;
    position: absolute;
    top: 18px;
    right: 18px;
    z-index: 9999;
    width: min(390px, calc(100% - 36px));
    max-height: 665px;
    overflow-y: auto;
    box-sizing: border-box;
    padding: 18px 20px;
    border: 1px solid #d9d9d9;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.98);
    box-shadow: 0 10px 35px rgba(0, 0, 0, 0.16);
    color: #222;
    font-family: Arial, sans-serif;
}}
#work-detail-card h3 {{ margin: 6px 28px 8px 0; font-size: 18px; line-height: 1.3; }}
#work-detail-card .meta {{ color: #666; font-size: 12px; line-height: 1.5; margin-bottom: 12px; }}
#work-detail-card .badge {{ display: inline-block; padding: 4px 8px; margin: 0 5px 6px 0; border-radius: 999px; background: #f0f2f5; font-size: 11px; }}
#work-detail-card h4 {{ margin: 14px 0 6px; font-size: 13px; }}
#work-detail-card p {{ margin: 0; font-size: 13px; line-height: 1.5; }}
#work-detail-card a {{ color: #2457a6; word-break: break-all; }}
#work-detail-close {{
    position: absolute;
    top: 10px;
    right: 12px;
    border: 0;
    background: transparent;
    font-size: 22px;
    cursor: pointer;
    color: #666;
}}
#work-card-empty {{ color: #777; font-style: italic; }}
</style>
<div id="work-detail-card" role="dialog" aria-live="polite" aria-label="Detalle de la obra seleccionada">
  <button id="work-detail-close" type="button" aria-label="Cerrar">×</button>
  <div id="work-detail-content"></div>
</div>
<script>
const workDetails = {details_json};
const workCard = document.getElementById("work-detail-card");
const workContent = document.getElementById("work-detail-content");
const closeButton = document.getElementById("work-detail-close");

function escapeText(value) {{
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}}

function renderWorkCard(item) {{
  const abstractText = item.abstract || "Abstract no disponible en OpenAlex para esta obra.";
  const matchText = item.openalex_match ? ` · OpenAlex: ${{escapeText(item.openalex_match)}}` : "";
  const link = item.doi_url
    ? `<a href="${{escapeText(item.doi_url)}}" target="_blank" rel="noopener noreferrer">${{escapeText(item.doi_url)}}</a>`
    : "No registrado";
  workContent.innerHTML = `
    <div class="meta">Prioridad #${{escapeText(item.priority)}} · ${{escapeText(item.year)}}${{matchText}}</div>
    <h3>${{escapeText(item.title)}}</h3>
    <div class="meta">${{escapeText(item.authors)}}<br>${{escapeText(item.publication)}}</div>
    <span class="badge">${{escapeText(item.subtopic)}}</span>
    <span class="badge">${{escapeText(item.level)}}</span>
    <h4>Descripción</h4>
    <p>${{escapeText(item.description) || '<span id="work-card-empty">Sin descripción.</span>'}}</p>
    <h4>Abstract</h4>
    <p>${{escapeText(abstractText)}}</p>
    <h4>DOI / URL</h4>
    <p>${{link}}</p>
  `;
  workCard.style.display = "block";
}}

closeButton.addEventListener("click", () => {{
  workCard.style.display = "none";
}});

network.on("click", function(params) {{
  const nodeId = params.nodes && params.nodes.length ? params.nodes[0] : null;
  if (nodeId && workDetails[nodeId]) {{
    renderWorkCard(workDetails[nodeId]);
  }} else if (nodeId && String(nodeId).startsWith("T::")) {{
    workCard.style.display = "none";
  }}
}});
</script>
"""
    return graph_html.replace("</body>", card_html + "</body>")


st.title("Grafo bibliográfico — IA, capacidades humanas y juicio directivo")
st.caption("Las 17 fuentes y sus metadatos se cargan desde sources.csv, que funciona como fuente maestra del repositorio.")

with st.sidebar:
    st.header("Filtros")
    max_priority = st.slider("Prioridad máxima", 1, 17, 17)
    chosen_topics = st.multiselect("Subtemas", SUBTOPICS, default=SUBTOPICS)
    chosen_levels = st.multiselect("Nivel", ["Núcleo central", "Complementaria"], default=["Núcleo central", "Complementaria"])
    edge_types = st.multiselect(
        "Relaciones",
        ["Cita directa", "Acoplamiento bibliográfico", "Subtema", "Versión equivalente"],
        default=["Cita directa", "Acoplamiento bibliográfico", "Subtema"],
    )
    min_shared = st.slider("Mínimo de referencias compartidas", 1, 10, 2)
    use_live = st.toggle("Consultar OpenAlex en vivo", value=True)
    show_topics = st.toggle("Mostrar nodos de subtema", value=True)

selected_articles = [
    a for a in ARTICLES
    if a["priority"] <= max_priority and a["subtopic"] in chosen_topics and a["level"] in chosen_levels
]
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
    st.info("Algunas obras no fueron resueltas por OpenAlex. Las citas verificadas manualmente se mantienen como respaldo.")

tab_graph, tab_sources, tab_rel, tab_refs, tab_cov = st.tabs([
    "Grafo", "Fuentes maestras", "Relaciones", "Referencias por artículo", "Cobertura"
])

with tab_graph:
    if selected_articles:
        components.html(
            make_graph(selected_articles, resolved, direct, coupling, version_edges, show_topics, edge_types),
            height=740,
            scrolling=False,
        )
        st.caption("Haz clic en una obra para abrir su tarjeta con descripción y abstract. Rojo: cita directa. Gris discontinuo: referencias compartidas. Amarillo discontinuo: versión equivalente. Color del nodo: subtema.")
    else:
        st.warning("No hay artículos con los filtros actuales.")

with tab_sources:
    st.subheader("Corpus maestro")
    display_df = SOURCES_DF[["priority", "title", "authors", "year", "subtopic", "publication", "doi_url", "origin", "level", "description"]].copy()
    display_df.columns = ["Prioridad", "Título", "Autores", "Año", "Subtema", "Publicación / medio", "DOI / URL", "Origen documental", "Nivel", "Descripción"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.download_button("Descargar sources.csv", DATA_FILE.read_bytes(), "sources.csv", "text/csv")

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
        st.markdown(
            f"**Descripción:** {chosen['description']}  \n"
            f"**Publicación:** {chosen['publication']}  \n"
            f"**Origen documental:** {chosen['origin']}  \n"
            f"**DOI/URL:** {chosen['doi_url'] or 'No registrado'}"
        )
        oa = resolved.get(chosen["id"]) if use_live else None
        if oa:
            abstract_text = oa.get("abstract") or "Abstract no disponible en OpenAlex para esta obra."
            with st.expander("Abstract de la obra", expanded=False):
                st.write(abstract_text)
            refs = oa.get("referenced_works", [])
            st.write(f"OpenAlex registra **{len(refs)} referencias** para esta obra. Coincidencia: **{oa.get('match', '')}**.")
            if refs and st.button("Resolver títulos de las referencias", type="primary"):
                rows = fetch_reference_metadata(refs)
                if rows:
                    rdf = pd.DataFrame(rows).sort_values(["Año", "Título"], ascending=[False, True])
                    st.dataframe(rdf, use_container_width=True, hide_index=True)
                    st.download_button("Descargar referencias CSV", rdf.to_csv(index=False).encode("utf-8"), f"referencias_{chosen['id']}.csv", "text/csv")
                else:
                    st.warning("No fue posible recuperar metadatos de las referencias en esta consulta.")
        else:
            st.info("Activa OpenAlex en vivo para consultar el abstract y la lista de referencias de esta obra.")

with tab_cov:
    rows = []
    for a in selected_articles:
        oa = resolved.get(a["id"]) if use_live else None
        rows.append({
            "Prioridad": a["priority"],
            "Artículo": a["title"],
            "Subtema": a["subtopic"],
            "Nivel": a["level"],
            "Publicación": a["publication"],
            "Origen documental": a["origin"],
            "OpenAlex": "Sí" if oa else "No",
            "Abstract OpenAlex": "Sí" if oa and oa.get("abstract") else "No",
            "Tipo de match": oa.get("match", "") if oa else "",
            "Referencias OpenAlex": len(oa.get("referenced_works", [])) if oa else 0,
            "Citas recibidas": oa.get("cited_by_count", 0) if oa else 0,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("**Interpretación:** la cita directa es direccional; el acoplamiento bibliográfico indica fuentes compartidas; el vínculo de subtema es una clasificación analítica del proyecto.")

st.divider()
st.caption("Fuente maestra: sources.csv. Relaciones y abstracts dinámicos: OpenAlex. Fallback: citas cruzadas verificadas manualmente en las fuentes originales consultadas.")
