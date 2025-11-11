#!/usr/bin/env python3
"""
Script para indexar imágenes usando el nombre de la carpeta como categoría
"""

import requests
import os
from pathlib import Path

# Configuración
API_URL = 'http://localhost:8000'
BASE_PATH = "/home/kpalacio/Documentos/buentek/cordoba_de_antaño/www.xn--cordobadeantao-2nb.com.ar/images/igallery"

# Carpetas a indexar (nombre_carpeta: categoría_a_usar)
FOLDERS_TO_INDEX = {
    'comparativas': 'Comparativas',
    'mapas': 'Mapas y Planos',
    'cordobazo': 'Historia - Cordobazo',
    'favoritas': 'Destacadas'
}

def inferir_metadata_basica(filename):
    """Infiere metadata básica del nombre del archivo"""
    import re
    
    filename_lower = filename.lower()
    
    # Inferir localidad
    localidad = 'Córdoba Capital'
    if 'villa_carlos_paz' in filename_lower or 'carlos_paz' in filename_lower:
        localidad = 'Villa Carlos Paz'
    elif 'cosquin' in filename_lower:
        localidad = 'Cosquín'
    elif 'alta_gracia' in filename_lower:
        localidad = 'Alta Gracia'
    # ... agregar más según necesites
    
    # Inferir barrio (solo para Córdoba Capital)
    barrio = ''
    if localidad == 'Córdoba Capital':
        if 'nueva_cordoba' in filename_lower or 'nueva cordoba' in filename_lower:
            barrio = 'Nueva Córdoba'
        elif 'alberdi' in filename_lower:
            barrio = 'Alberdi'
        elif 'guemes' in filename_lower:
            barrio = 'Güemes'
        elif 'centro' in filename_lower:
            barrio = 'Centro'
    
    # Generar descripción limpia
    descripcion = Path(filename).stem.replace('_', ' ').replace('-', ' ').title()
    # Limpiar números al final
    descripcion = re.sub(r'\s+\d+$', '', descripcion)
    
    return localidad, barrio, descripcion

def indexar_carpeta(folder_name, categoria):
    """Indexa todas las imágenes de una carpeta"""
    folder_path = Path(BASE_PATH) / folder_name
    
    if not folder_path.exists():
        print(f"❌ No existe la carpeta: {folder_path}")
        return
    
    # Buscar todas las imágenes
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    images = []
    
    for ext in valid_extensions:
        images.extend(folder_path.glob(f'*{ext}'))
        images.extend(folder_path.glob(f'*{ext.upper()}'))
    
    if not images:
        print(f"⚠️  No se encontraron imágenes en {folder_name}")
        return
    
    print(f"\n📁 Indexando carpeta: {folder_name}")
    print(f"   Categoría: {categoria}")
    print(f"   Imágenes encontradas: {len(images)}")
    print("-" * 60)
    
    indexed = 0
    errors = 0
    
    for img_path in images:
        try:
            # Inferir metadata básica
            localidad, barrio, descripcion = inferir_metadata_basica(img_path.name)
            
            # Preparar datos
            with open(img_path, 'rb') as f:
                files = {'file': (img_path.name, f, 'image/jpeg')}
                data = {
                    'original_path': str(img_path),
                    'barrio': barrio,
                    'localidad': localidad,
                    'categoria': categoria,
                    'descripcion': descripcion
                }
                
                response = requests.post(f'{API_URL}/index', files=files, data=data)
                response.raise_for_status()
                indexed += 1
                
                if indexed % 10 == 0:
                    print(f"   ✅ Indexadas: {indexed}/{len(images)}")
                    
        except requests.exceptions.ConnectionError:
            print(f"\n❌ Error: No se puede conectar al backend en {API_URL}")
            print("   Asegurate de que el backend esté corriendo (python backend/app.py)")
            return
        except Exception as e:
            print(f"   ❌ Error en {img_path.name}: {e}")
            errors += 1
    
    print("-" * 60)
    print(f"✅ Carpeta '{folder_name}' completada:")
    print(f"   Éxitos: {indexed}")
    print(f"   Errores: {errors}")

def main():
    print("=" * 60)
    print("INDEXADOR DE CARPETAS CATEGORIZADAS")
    print("=" * 60)
    
    # Verificar que el backend esté corriendo
    try:
        response = requests.get(f'{API_URL}/')
        print(f"✅ Backend conectado: {response.json()['message']}\n")
    except:
        print(f"❌ No se puede conectar al backend en {API_URL}")
        print("   Ejecutá primero: cd backend && python app.py")
        return
    
    # Indexar cada carpeta
    total_indexed = 0
    for folder_name, categoria in FOLDERS_TO_INDEX.items():
        indexar_carpeta(folder_name, categoria)
    
    print("\n" + "=" * 60)
    print("🎉 INDEXACIÓN COMPLETA")
    print("=" * 60)

if __name__ == '__main__':
    main()
