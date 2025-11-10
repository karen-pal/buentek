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
    limit: int = Query(20)
):
    # Generar embedding de la query
    query_embedding = model.encode(query)
    
    # Buscar en DB
    conn = sqlite3.connect('../cordoba.db')
    c = conn.cursor()
    
    sql = "SELECT * FROM imagenes WHERE 1=1"
    params = []
    
    if barrio:
        sql += " AND barrio = ?"
        params.append(barrio)
    if localidad:
        sql += " AND localidad = ?"
        params.append(localidad)
    if categoria:
        sql += " AND categoria = ?"
        params.append(categoria)
    
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    
    # Calcular similitud
    results = []
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
