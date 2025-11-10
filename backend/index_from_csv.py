import requests
import pandas as pd
import os
from pathlib import Path
import shutil

# Leer CSV
df = pd.read_csv('../metadata_cordoba.csv')

print(f"📁 Encontradas {len(df)} imágenes en el CSV\n")

# Filtrar solo las primeras 100 para probar (después sacamos esto)
# df = df.head(100)  # Descomentá esto para probar con pocas imágenes primero

indexed = 0
errors = 0

for idx, row in df.iterrows():
    path = row['path']
    
    if not os.path.exists(path):
        print(f"❌ No existe: {path}")
        errors += 1
        continue
    
    # Preparar datos
    try:
        with open(path, 'rb') as f:
            files = {'file': (os.path.basename(path), f, 'image/jpeg')}
            data = {
                'original_path': path,
                'barrio': row['barrio'] if pd.notna(row['barrio']) else '',
                'localidad': row['localidad'],
                'categoria': row['categoria'],
                'descripcion': row['descripcion'] if pd.notna(row['descripcion']) else ''
            }
            
            response = requests.post('http://localhost:8000/index', files=files, data=data)
            response.raise_for_status()
            indexed += 1
            
            if indexed % 50 == 0:
                print(f"✅ Indexadas: {indexed}/{len(df)}")
                
    except Exception as e:
        print(f"❌ Error en {path}: {e}")
        errors += 1

print(f"\n🎉 Indexación completa!")
print(f"✅ Éxitos: {indexed}")
print(f"❌ Errores: {errors}")
