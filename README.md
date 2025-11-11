# 🏛️ Córdoba de Antaño - Búsqueda Semántica

Sistema de búsqueda semántica para archivo fotográfico histórico de Córdoba.

## 📋 Requisitos

- Python 3.10+
- SQLite3
- ~500MB de espacio para el modelo CLIP

## 🚀 Instalación inicial

```bash
cd ~/Documentos/buentek/visuales/busqueda

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install fastapi uvicorn sentence-transformers pillow python-multipart pandas
```

## 🔧 Estructura del proyecto

```
busqueda/
├── backend/
│   ├── app.py                    # API principal
│   ├── index_from_csv.py         # Indexar desde CSV
│   └── additional_index.py       # Indexar carpetas específicas
├── frontend/
│   └── index.html                # Interfaz web
├── images/                       # Imágenes copiadas (generado)
├── cordoba.db                    # Base de datos SQLite (generado)
├── metadata_cordoba.csv          # Metadata de imágenes
└── venv/                         # Entorno virtual
```

## ⚡ Levantar el sistema

### 1. Backend (Terminal 1)

```bash
cd ~/Documentos/buentek/visuales/busqueda/backend
source ../venv/bin/activate
python app.py
```

El backend corre en: **http://localhost:8000**

### 2. Frontend (Terminal 2)

```bash
cd ~/Documentos/buentek/visuales/busqueda/frontend
python3 -m http.server 3000
```

El frontend está en: **http://localhost:3000**

## 📝 Scripts principales

### `backend/app.py`
**API principal del sistema**

- **Puerto**: 8000
- **Endpoints**:
  - `GET /` - Health check
  - `POST /index` - Indexar una imagen
  - `GET /search?query=X&mode=hybrid` - Buscar imágenes
  - `GET /filters` - Obtener filtros (barrios, localidades, categorías)
  - `GET /stats` - Estadísticas generales
  - `GET /analytics` - Analytics detallado

**Modos de búsqueda**:
- `hybrid` (default): Texto + Visual con fallback
- `text`: Solo búsqueda de texto (rápido)
- `semantic`: Solo similitud visual

### `backend/index_from_csv.py`
**Indexa todas las imágenes desde metadata_cordoba.csv**

```bash
cd backend
python index_from_csv.py
```

**Qué hace**:
1. Lee `metadata_cordoba.csv`
2. Por cada imagen:
   - Copia a `images/`
   - Genera embedding con CLIP
   - Guarda en `cordoba.db`
3. Muestra progreso cada 50 imágenes

**Tiempo estimado**: ~5-10 segundos por imagen

### `backend/additional_index.py`
**Indexa carpetas específicas usando el nombre de carpeta como categoría**

```bash
cd backend
python additional_index.py
```

**Carpetas configuradas**:
- `comparativas/` → Categoría "Comparativas"
- `mapas/` → Categoría "Mapas y Planos"
- `cordobazo/` → Categoría "Historia - Cordobazo"
- `favoritas/` → Categoría "Destacadas"

**Para agregar carpetas**: Editá el diccionario `FOLDERS_TO_INDEX` en el script.

## 🔄 Reindexar todo desde cero

Si borraste/modificaste imágenes:

```bash
cd ~/Documentos/buentek/visuales/busqueda

# 1. Borrar base de datos e imágenes
rm cordoba.db
rm -rf images/*

# 2. (Opcional) Regenerar CSV si cambiaste nombres de archivo
# python generate_csv_cordoba.py

# 3. Levantar backend
cd backend
source ../venv/bin/activate
python app.py

# 4. En otra terminal, indexar
cd backend
python index_from_csv.py

# 5. (Opcional) Indexar carpetas adicionales
python additional_index.py
```

## 🎨 Frontend - Controles

### Búsqueda
- **Input**: Busca al escribir (debounce 300ms)
- **Mínimo**: 3 caracteres

### Modos de visualización
- **Grid**: Columnas tipo masonry (configurable 1-10)
- **Espiral**: Posicionamiento matemático desde el centro

### Modos de búsqueda
- **Híbrida**: Busca por texto, si no encuentra hace búsqueda visual
- **Solo texto**: Más rápido, busca en descripción/barrio/localidad
- **Solo visual**: Búsqueda semántica por similitud de imagen

### Filtros
- Barrio (solo Córdoba Capital)
- Localidad
- Categoría

### Historial
- Guarda últimas 10 búsquedas en localStorage
- Click para repetir búsqueda

## 🔍 Ver qué tenés indexado

```bash
cd ~/Documentos/buentek/visuales/busqueda

# Ver categorías
sqlite3 cordoba.db "SELECT categoria, COUNT(*) FROM imagenes GROUP BY categoria ORDER BY COUNT(*) DESC;"

# Ver barrios
sqlite3 cordoba.db "SELECT barrio, COUNT(*) FROM imagenes WHERE barrio != '' GROUP BY barrio ORDER BY COUNT(*) DESC;"

# Ver total
sqlite3 cordoba.db "SELECT COUNT(*) FROM imagenes;"

# Analytics completo (en el navegador)
http://localhost:8000/analytics
```

## 🐛 Troubleshooting

### "No se puede conectar al backend"
```bash
# Verificar que el backend esté corriendo
curl http://localhost:8000/

# Si no responde, levantalo:
cd backend
python app.py
```

### "No encuentra imágenes con nombres obvios"
- Verificá el modo de búsqueda (usar Híbrida o Solo texto)
- Verificá que la imagen esté indexada:
```bash
sqlite3 cordoba.db "SELECT descripcion FROM imagenes WHERE descripcion LIKE '%nombre%';"
```

### "Búsqueda muy lenta"
- Usa modo "Solo texto" para búsquedas rápidas
- Reduce el límite de resultados (default: 100)

### "Error al indexar"
- Verificá que el path en el CSV sea correcto
- Verificá permisos de lectura en las imágenes
- Verificá que la imagen no esté corrupta

## 📊 Performance

- **Indexación**: ~5-10 seg/imagen (primera vez genera embeddings)
- **Búsqueda texto**: ~50ms para 10k imágenes
- **Búsqueda híbrida**: ~200-500ms (depende de matches de texto)
- **Búsqueda visual pura**: ~1-3 seg para 10k imágenes

## 💡 Tips

1. **Usa modo híbrido** para búsquedas generales
2. **Usa modo texto** si sabés exactamente qué buscás
3. **Usa modo visual** para conceptos (ej: "afiche", "dibujo", "noche")
4. **Columnas en Grid**: 3-4 para proyectar, 5-6 para monitor
5. **Historial**: Click en búsquedas pasadas para repetir
6. **Lightbox**: Click en imagen para ver fullscreen, ESC para cerrar

## 🗂️ Backup

Para hacer backup del sistema:

```bash
# Backup de la base de datos
cp cordoba.db cordoba_backup_$(date +%Y%m%d).db

# Backup de imágenes (opcional, pesan mucho)
tar -czf images_backup.tar.gz images/

# Backup del CSV
cp metadata_cordoba.csv metadata_backup_$(date +%Y%m%d).csv
```

## 🔐 Datos persistentes

Los datos persisten mientras existan:
- `cordoba.db` (embeddings + metadata)
- `images/` (imágenes copiadas)

Podés bajar y subir el backend sin perder datos.

## 📚 Tecnologías

- **Backend**: FastAPI + SQLite + sentence-transformers
- **Frontend**: HTML + CSS + JavaScript vanilla
- **Modelo**: CLIP ViT-B/32 (OpenAI)
- **Embeddings**: Vectores de 512 dimensiones

---

**Proyecto**: Archivo visual histórico de Córdoba  
**Última actualización**: Noviembre 2024
