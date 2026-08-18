# Grafo bibliográfico — IA afecta al decisor

Aplicación Streamlit para explorar el corpus de 17 artículos priorizados del proyecto.

## Qué muestra
- Citas directas entre artículos del corpus.
- Acoplamiento bibliográfico: pares de artículos que comparten referencias.
- Relación de cada artículo con uno de seis subtemas MECE.
- Cobertura y resolución bibliográfica en OpenAlex.
- Referencias de un artículo seleccionado, recuperadas dinámicamente desde OpenAlex.

## Ejecución
1. Instala Python 3.10 o superior.
2. En la carpeta del proyecto ejecuta:

   `pip install -r requirements.txt`

   `streamlit run app.py`

3. Abre la URL local que muestre Streamlit.

## Fuentes y método
El corpus base contiene 17 artículos priorizados. La aplicación consulta OpenAlex en vivo para resolver cada trabajo mediante DOI o similitud de título, recupera `referenced_works`, detecta citas directas dentro del corpus y calcula acoplamiento bibliográfico mediante intersección de referencias.

La red distingue cuatro relaciones:
- Cita directa: A referencia bibliográficamente a B.
- Acoplamiento bibliográfico: A y B comparten N referencias; no implica que se citen entre sí.
- Subtema: clasificación analítica MECE del proyecto.
- Versión equivalente: una obra cita otra versión bibliográfica del mismo trabajo.

## Subtemas MECE
- Deskilling y deterioro de capacidades
- Interacción humano–IA
- Phronesis y juicio directivo
- Formación y aprendizaje profesional
- Gobernanza y capacidades
- Asimetría adopción–gobernanza

## Notas
OpenAlex puede no resolver algunas publicaciones recientes, capítulos o documentos no indexados. Por ello `app.py` conserva un conjunto reducido de citas cruzadas verificadas manualmente como fallback. El acoplamiento bibliográfico sólo se calcula cuando OpenAlex devuelve listas de referencias.