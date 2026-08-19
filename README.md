# Grafo bibliográfico — IA afecta al decisor

Aplicación Streamlit para explorar el corpus de 17 fuentes priorizadas del proyecto.

## Estructura del repositorio

- `sources.csv`: **fuente maestra** del corpus. Contiene las 17 referencias y los metadatos bibliográficos utilizados por la aplicación.
- `app.py`: aplicación Streamlit. Lee `sources.csv`, construye el grafo y consulta OpenAlex para enriquecer relaciones, referencias y abstracts.
- `requirements.txt`: dependencias de Python.

## Esquema de `sources.csv`

El archivo usa diez columnas estables:

1. `priority`: prioridad analítica de 1 a 17.
2. `title`: título completo de la fuente.
3. `authors`: autores según el corpus maestro disponible.
4. `year`: año de publicación.
5. `subtopic`: uno de los seis subtemas MECE del proyecto.
6. `publication`: revista, libro, proceedings, institución o medio.
7. `doi_url`: DOI en formato URL o URL de la publicación cuando no hay DOI registrado.
8. `origin`: documento del proyecto desde el que se incorporó la referencia.
9. `level`: `Núcleo central` o `Complementaria`.
10. `description`: descripción breve curada del aporte de la obra al corpus.

`app.py` deriva automáticamente el identificador interno `A01`–`A17` a partir de `priority` y extrae el DOI desde `doi_url` cuando corresponde. De esta forma, los datos bibliográficos no quedan duplicados dentro del código.

## Qué muestra la aplicación

- Grafo interactivo de las 17 fuentes.
- **Tarjeta de detalle al hacer clic en una obra**, con título, autores, año, publicación, subtema, nivel, descripción, abstract y DOI/URL.
- El abstract se reconstruye dinámicamente desde `abstract_inverted_index` de OpenAlex cuando está disponible; si OpenAlex no ofrece abstract, la tarjeta lo indica expresamente.
- Citas directas entre fuentes del corpus.
- Acoplamiento bibliográfico: pares de fuentes que comparten referencias.
- Relación de cada fuente con uno de seis subtemas MECE.
- Tabla completa del corpus maestro, con publicación, DOI/URL, origen documental, nivel y descripción.
- Cobertura y resolución bibliográfica en OpenAlex, incluida la disponibilidad de abstract.
- Referencias de una fuente seleccionada, recuperadas dinámicamente desde OpenAlex.

## Ejecución

Requiere Python 3.10 o superior.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Fuentes y método

El corpus base contiene 17 fuentes priorizadas. `sources.csv` es la única fuente de verdad para sus metadatos. La aplicación valida al iniciar que existan exactamente 17 filas y que estén presentes las diez columnas requeridas.

La aplicación consulta OpenAlex en vivo para resolver cada trabajo mediante DOI o similitud de título, recuperar `referenced_works`, `abstract_inverted_index`, detectar citas directas dentro del corpus y calcular acoplamiento bibliográfico mediante intersección de referencias.

La red distingue cuatro relaciones:

- **Cita directa:** A referencia bibliográficamente a B.
- **Acoplamiento bibliográfico:** A y B comparten N referencias; no implica que se citen entre sí.
- **Subtema:** clasificación analítica MECE del proyecto.
- **Versión equivalente:** una fuente cita otra versión bibliográfica del mismo trabajo.

## Interacción con las obras

Al hacer clic en un nodo de obra del grafo, aparece una tarjeta superpuesta dentro de la visualización. La tarjeta contiene:

- prioridad y año;
- título y autores;
- publicación;
- subtema y nivel;
- descripción curada almacenada en `sources.csv`;
- abstract recuperado de OpenAlex;
- DOI o URL de la obra.

Los nodos de subtema no abren tarjeta. La tarjeta puede cerrarse con el botón `×`.

## Subtemas MECE

- Deskilling y deterioro de capacidades
- Interacción humano–IA
- Phronesis y juicio directivo
- Formación y aprendizaje profesional
- Gobernanza y capacidades
- Asimetría adopción–gobernanza

## Mantenimiento del corpus

Para agregar, corregir o reclasificar fuentes, modifica únicamente `sources.csv`. Mientras el esquema de diez columnas se conserve, `app.py` tomará los cambios automáticamente al reiniciar Streamlit.

## Notas

OpenAlex puede no resolver algunas publicaciones recientes, capítulos o documentos no indexados y no siempre ofrece un abstract para todas las obras. Por ello `app.py` conserva un conjunto reducido de citas cruzadas verificadas manualmente como fallback y muestra de forma explícita cuando no hay abstract disponible. El acoplamiento bibliográfico sólo se calcula cuando OpenAlex devuelve listas de referencias.
