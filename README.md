# ChatPDF Backend

Backend en FastAPI para subir archivos PDF, extraer su contenido, generar embeddings con Ollama, almacenarlos en PostgreSQL con `pgvector` y responder preguntas usando recuperacion semantica con fuentes.

## Que hace este proyecto

- Sube uno o varios archivos PDF
- Extrae texto por pagina
- Parte el contenido en fragmentos con solapamiento
- Genera embeddings con Ollama
- Guarda documentos y chunks en PostgreSQL con `pgvector`
- Busca contexto relevante por similitud semantica
- Genera respuestas con trazabilidad por archivo, pagina y fragmento

## Stack

- Python 3.11+
- FastAPI
- PostgreSQL 16 + `pgvector`
- Ollama
- Docker Compose para la base de datos

## Estructura del proyecto

```text
app/
  api/routes/        # Endpoints
  core/              # Configuracion y motor SQLAlchemy
  db/                # Inicializacion y modelos
  schemas/           # Esquemas Pydantic
  services/          # Ingestion, embeddings, chat y busqueda
  static/            # Interfaz web simple
docker/
  postgres/init/     # SQL de arranque para pgvector y tablas
storage/uploads/     # PDFs subidos en local
tests/               # Pruebas automatizadas
```

## Requisitos previos

Antes de arrancar, necesitas tener instalado:

- Python 3.11 o superior
- Docker Desktop
- Ollama

Modelos recomendados en Ollama:

```bash
ollama pull nomic-embed-text
ollama pull llama3
```

Luego deja Ollama corriendo en segundo plano. Por defecto este proyecto usa `http://localhost:11434`.

## 1. Descargar el proyecto

Si quieres clonarlo desde GitHub:

```bash
git clone https://github.com/Aleixein466/chat-pdf.git
cd chat-pdf
```

Si ya tienes los archivos descargados manualmente, entra a la carpeta raiz del proyecto antes de seguir.

## 2. Crear el entorno virtual e instalar dependencias

### PowerShell (Windows)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### CMD (Windows)

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

## 3. Configurar variables de entorno

Copia el archivo de ejemplo:

```powershell
Copy-Item .env.example .env
```

Variables importantes:

- `DATABASE_URL`: conexion a PostgreSQL
- `OLLAMA_BASE_URL`: URL local de Ollama
- `OLLAMA_EMBED_MODEL`: modelo de embeddings
- `OLLAMA_CHAT_MODEL`: modelo de chat
- `UPLOAD_DIR`: carpeta donde se guardan los PDFs

## 4. Levantar PostgreSQL con Docker

Este proyecto trae una configuracion lista para una base local con `pgvector`:

```bash
docker compose up -d postgres
```

Servicios y valores por defecto:

- Host: `localhost`
- Puerto: `5432`
- Base de datos: `chatpdf`
- Usuario: `postgres`
- Password: `postgres`

El script [`docker/postgres/init/01-init-chatpdf.sql`](docker/postgres/init/01-init-chatpdf.sql) crea:

- Extension `vector`
- Tabla `documents`
- Tabla `document_chunks`
- Indices relacionales y vectoriales

Para apagar la base:

```bash
docker compose down
```

## 5. Ejecutar la API

Con el entorno virtual activo:

```bash
uvicorn app.main:app --reload
```

La aplicacion queda disponible en:

- App web: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`

## Flujo de uso

1. Arranca PostgreSQL con Docker.
2. Verifica que Ollama este corriendo.
3. Ejecuta `uvicorn`.
4. Abre `http://localhost:8000/`.
5. Sube uno o varios PDFs.
6. Haz preguntas sobre los documentos indexados.

## Endpoints principales

### `POST /api/v1/documents/upload`

Sube un PDF, extrae texto, genera chunks, calcula embeddings y persiste el resultado.

### `POST /api/v1/documents/upload-many`

Procesa varios PDFs en una sola solicitud.

### `POST /api/v1/chat/ask`

Recibe una pregunta, busca los fragmentos mas relevantes y devuelve una respuesta con fuentes.

Ejemplo de respuesta:

```json
{
  "answer": "respuesta generada",
  "sources": [
    {
      "file_name": "manual.pdf",
      "page_number": 3,
      "snippet": "fragmento relevante..."
    }
  ]
}
```

## Ejecutar pruebas

Con el entorno virtual activo:

```bash
pytest
```

## Problemas comunes

### Error conectando a PostgreSQL

Revisa que el contenedor este arriba:

```bash
docker ps
```

Y valida que `DATABASE_URL` coincida con las credenciales reales.

### Ollama no responde

Confirma que Ollama este iniciado y que los modelos ya fueron descargados:

```bash
ollama list
```

### La API arranca pero no responde preguntas bien

Normalmente pasa por una de estas causas:

- no se cargaron PDFs todavia
- Ollama no tiene el modelo configurado
- la base no pudo crear la extension `vector`

## Desarrollo

Archivos utiles para extender el proyecto:

- [`app/main.py`](app/main.py)
- [`app/api/routes/documents.py`](app/api/routes/documents.py)
- [`app/api/routes/chat.py`](app/api/routes/chat.py)
- [`app/services/ingestion_service.py`](app/services/ingestion_service.py)
- [`app/services/semantic_search.py`](app/services/semantic_search.py)
- [`app/services/chat_service.py`](app/services/chat_service.py)

## Licencia

Si vas a publicar este proyecto para terceros, agrega aqui la licencia que quieras usar.
