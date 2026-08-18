# Grafo bibliográfico — IA afecta al decisor

Repositorio del corpus bibliográfico y sus visualizaciones interactivas.

## Entrega principal: HTML5

`index.html` es una versión **autónoma para navegador**. No requiere Python, Streamlit ni servidor de aplicaciones. Incluye dentro del propio archivo las 17 fuentes priorizadas, sus nueve campos bibliográficos, los seis subtemas y las relaciones cruzadas verificadas utilizadas en el grafo.

Puede servirse directamente desde cualquier hosting estático, incluido GitHub Pages. También puede abrirse como archivo HTML en un navegador moderno.

La interfaz HTML5 incluye:

- grafo SVG interactivo de las 17 fuentes;
- búsqueda por título, autor, publicación u origen;
- filtros por subtema y nivel;
- citas directas verificadas y relación de versión equivalente;
- nodos de los seis subtemas MECE;
- zoom, desplazamiento y reposicionamiento de nodos;
- panel de detalle con metadatos y enlace DOI/URL;
- tabla completa del corpus maestro.

## Estructura del repositorio

- `index.html`: entrega HTML5 autónoma para navegador.
- `sources.csv`: **fuente maestra** del corpus y referencia para mantenimiento de datos.
- `app.py`: versión Streamlit enriquecida con consultas a OpenAlex.
- `requirements.txt`: dependencias de la versión Streamlit.

## Esquema de `sources.csv`

El archivo usa nueve columnas estables:

1. `priority`: prioridad analítica de 1 a 17.
2. `title`: título completo de la fuente.
3. `authors`: autores según el corpus maestro disponible.
4. `year`: año de publicación.
5. `subtopic`: uno de los seis subtemas MECE del proyecto.
6. `publication`: revista, libro, proceedings, institución o medio.
7. `doi_url`: DOI en formato URL o URL de la publicación cuando no hay DOI registrado.
8. `origin`: documento del proyecto desde el que se incorporó la referencia.
9. `level`: `Núcleo central` o `Complementaria`.

## Versiones de la visualización

### HTML5

Abrir `index.html` en un navegador o publicar el repositorio como sitio estático. Esta versión privilegia portabilidad: todos los datos necesarios para visualizar el corpus están embebidos en el HTML.

### Streamlit / OpenAlex

La versión Python utiliza `sources.csv` como fuente de verdad y consulta OpenAlex para enriquecer referencias y calcular relaciones dinámicas.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Relaciones representadas

- **Cita directa verificada:** A referencia bibliográficamente a B.
- **Versión equivalente:** una fuente cita una versión bibliográfica equivalente del mismo trabajo.
- **Subtema:** clasificación analítica MECE del proyecto.
- **Acoplamiento bibliográfico:** disponible en la versión Streamlit cuando OpenAlex devuelve listas de referencias.

## Subtemas MECE

- Deskilling y deterioro de capacidades
- Interacción humano–IA
- Phronesis y juicio directivo
- Formación y aprendizaje profesional
- Gobernanza y capacidades
- Asimetría adopción–gobernanza

## Mantenimiento

`sources.csv` continúa siendo la fuente maestra para modificaciones bibliográficas. Cuando el corpus cambie, la versión Streamlit lo leerá automáticamente; `index.html` debe regenerarse o actualizarse para reflejar el nuevo snapshot estático.

## Nota metodológica

La versión HTML5 muestra las relaciones cruzadas que habían sido verificadas para el corpus: ocho citas directas y una relación de versión equivalente. No inventa nuevas citas ni depende de una consulta externa al momento de visualizarse.