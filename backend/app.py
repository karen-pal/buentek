from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from PIL import Image
import sqlite3
import numpy as np
import io
import json
import os

app = FastAPI()

# CORS para desarrollo local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear carpeta para imágenes
os.makedirs("../images", exist_ok=True)
app.mount("/images", StaticFiles(directory="../images"), name="images")

# Cargar modelo CLIP (se descarga una vez y queda en cache)
print("🔄 Cargando modelo CLIP (puede tardar la primera vez)...")
model = SentenceTransformer('clip-ViT-B-32')
print("✅ Modelo listo!")

# Inicializar SQLite
def init_db():
    conn = sqlite3.connect('../cordoba.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS imagenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            original_path TEXT,
            barrio TEXT,
            localidad TEXT,
            categoria TEXT,
            descripcion TEXT,
            embedding TEXT
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_original_path ON imagenes(original_path)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_barrio ON imagenes(barrio)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_localidad ON imagenes(localidad)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_categoria ON imagenes(categoria)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_descripcion ON imagenes(descripcion)')
    conn.commit()
    conn.close()

init_db()

@app.get("/")
async def root():
    return {"message": "API Córdoba de Antaño funcionando! 🏛️"}

@app.post("/index")
async def index_image(
    file: UploadFile = File(...),
    original_path: str = Form(...),
    barrio: str = Form(""),
    localidad: str = Form(...),
    categoria: str = Form(...),
    descripcion: str = Form("")
):
    # Guardar imagen con nombre único
    import hashlib
    file_hash = hashlib.md5(original_path.encode()).hexdigest()[:8]
    extension = os.path.splitext(file.filename)[1]
    stored_filename = f"{file_hash}_{file.filename}"
    image_path = f"../images/{stored_filename}"
    
    with open(image_path, "wb") as f:
        f.write(await file.read())
    
    # Generar embedding
    image = Image.open(image_path)
    embedding = model.encode(image).tolist()
    
    # Guardar en DB
    conn = sqlite3.connect('../cordoba.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO imagenes (filename, original_path, barrio, localidad, categoria, descripcion, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (stored_filename, original_path, barrio, localidad, categoria, descripcion, json.dumps(embedding)))
    conn.commit()
    conn.close()
    
    return {"status": "ok", "filename": stored_filename}

@app.get("/search")
async def search(
    query: str = Query(...),
    barrio: str = Query(None),
    localidad: str = Query(None),
    categoria: str = Query(None),
    limit: int = Query(100),
    mode: str = Query("hybrid")  # hybrid, semantic, text
):
    conn = sqlite3.connect('../cordoba.db')
    c = conn.cursor()
    
    # Construir filtros SQL base
    sql_base = "SELECT * FROM imagenes WHERE 1=1"
    params_base = []
    
    if barrio:
        sql_base += " AND barrio = ?"
        params_base.append(barrio)
    if localidad:
        sql_base += " AND localidad = ?"
        params_base.append(localidad)
    if categoria:
        sql_base += " AND categoria = ?"
        params_base.append(categoria)
    
    results = []
    
    if mode == "text":
        # Solo búsqueda de texto
        query_normalized = query.lower().strip()
        sql = sql_base + " AND (LOWER(descripcion) LIKE ? OR LOWER(barrio) LIKE ? OR LOWER(localidad) LIKE ? OR LOWER(categoria) LIKE ?)"
        search_pattern = f"%{query_normalized}%"
        params = params_base + [search_pattern, search_pattern, search_pattern, search_pattern]
        
        c.execute(sql, params)
        rows = c.fetchall()
        
        for row in rows:
            results.append({
                "filename": row[1],
                "original_path": row[2],
                "barrio": row[3],
                "localidad": row[4],
                "categoria": row[5],
                "descripcion": row[6],
                "similarity": 1.0
            })
    
    elif mode == "semantic":
        # Solo búsqueda visual
        c.execute(sql_base, params_base)
        rows = c.fetchall()
        
        query_embedding = model.encode(query)
        
        for row in rows:
            img_embedding = np.array(json.loads(row[7]))
            similarity = np.dot(query_embedding, img_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(img_embedding)
            )
            
            results.append({
                "filename": row[1],
                "original_path": row[2],
                "barrio": row[3],
                "localidad": row[4],
                "categoria": row[5],
                "descripcion": row[6],
                "similarity": float(similarity)
            })
    
    elif mode == "hybrid":
        # Búsqueda híbrida con fallback
        query_normalized = query.lower().strip()
        sql_text = sql_base + " AND (LOWER(descripcion) LIKE ? OR LOWER(barrio) LIKE ? OR LOWER(localidad) LIKE ? OR LOWER(categoria) LIKE ?)"
        search_pattern = f"%{query_normalized}%"
        params_text = params_base + [search_pattern, search_pattern, search_pattern, search_pattern]
        
        c.execute(sql_text, params_text)
        rows_text = c.fetchall()
        
        if len(rows_text) > 0:
            # Hay matches de texto → calcular similitud visual + boost
            query_embedding = model.encode(query)
            
            for row in rows_text:
                img_embedding = np.array(json.loads(row[7]))
                similarity = np.dot(query_embedding, img_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(img_embedding)
                )
                
                # Boost para match de texto exacto
                text_boost = 0.3 if query_normalized in row[6].lower() else 0.15
                
                results.append({
                    "filename": row[1],
                    "original_path": row[2],
                    "barrio": row[3],
                    "localidad": row[4],
                    "categoria": row[5],
                    "descripcion": row[6],
                    "similarity": float(min(similarity + text_boost, 1.0))
                })
        else:
            # NO hay matches de texto → fallback a búsqueda visual pura
            print(f"No text matches for '{query}', falling back to semantic search")
            c.execute(sql_base, params_base)
            rows_all = c.fetchall()
            
            query_embedding = model.encode(query)
            
            for row in rows_all:
                img_embedding = np.array(json.loads(row[7]))
                similarity = np.dot(query_embedding, img_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(img_embedding)
                )
                
                results.append({
                    "filename": row[1],
                    "original_path": row[2],
                    "barrio": row[3],
                    "localidad": row[4],
                    "categoria": row[5],
                    "descripcion": row[6],
                    "similarity": float(similarity)
                })
    
    conn.close()
    
    # Ordenar por similitud
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    return results[:limit]

@app.get("/filters")
async def get_filters():
    conn = sqlite3.connect('../cordoba.db')
    c = conn.cursor()
    
    c.execute("SELECT DISTINCT barrio FROM imagenes WHERE barrio != ''")
    barrios = [r[0] for r in c.fetchall()]
    
    c.execute("SELECT DISTINCT localidad FROM imagenes")
    localidades = [r[0] for r in c.fetchall()]
    
    c.execute("SELECT DISTINCT categoria FROM imagenes")
    categorias = [r[0] for r in c.fetchall()]
    
    conn.close()
    
    return {
        "barrios": sorted(barrios),
        "localidades": sorted(localidades),
        "categorias": sorted(categorias)
    }

@app.get("/stats")
async def stats():
    conn = sqlite3.connect('../cordoba.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM imagenes")
    total = c.fetchone()[0]
    conn.close()
    return {"total_imagenes": total}

@app.get("/analytics")
async def analytics():
    """Endpoint para ver estadísticas detalladas"""
    conn = sqlite3.connect('../cordoba.db')
    c = conn.cursor()
    
    # Categorías
    c.execute("SELECT categoria, COUNT(*) as total FROM imagenes GROUP BY categoria ORDER BY total DESC")
    categorias = [{"categoria": r[0], "total": r[1]} for r in c.fetchall()]
    
    # Barrios
    c.execute("SELECT barrio, COUNT(*) as total FROM imagenes WHERE barrio != '' GROUP BY barrio ORDER BY total DESC")
    barrios = [{"barrio": r[0], "total": r[1]} for r in c.fetchall()]
    
    # Localidades
    c.execute("SELECT localidad, COUNT(*) as total FROM imagenes GROUP BY localidad ORDER BY total DESC")
    localidades = [{"localidad": r[0], "total": r[1]} for r in c.fetchall()]
    
    # Estadísticas generales
    c.execute("SELECT COUNT(*) FROM imagenes")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM imagenes WHERE descripcion = '[REVISAR]'")
    revisar = c.fetchone()[0]
    
    conn.close()
    
    return {
        "total_imagenes": total,
        "pendientes_revisar": revisar,
        "categorias": categorias,
        "barrios": barrios,
        "localidades": localidades
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
