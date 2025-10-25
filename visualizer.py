import pygame
import os
from pathlib import Path
from typing import List, Tuple
import sys

class ImageGridViewer:
    def __init__(self, image_dir: str, columnas: int = 3, filas: int = 5):
        """
        Inicializa el visualizador de imágenes en grilla.
        
        Args:
            image_dir: Directorio con las imágenes
            columnas: Número de columnas en la grilla
            filas: Número de filas en la grilla
        """
        pygame.init()
        
        # Configuración de pantalla
        self.SCREEN_WIDTH = 1920
        self.SCREEN_HEIGHT = 1080
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), 
                                               pygame.NOFRAME)
        pygame.display.set_caption("Image Grid Viewer")
        
        # Configuración de grilla
        self.columnas = columnas
        self.filas = filas
        self.images_per_page = columnas * filas
        
        # Colores
        self.BG_COLOR = (0, 0, 0)  # Negro
        
        # Cargar imágenes del directorio
        self.image_paths = self._load_image_paths(image_dir)
        self.current_page = 0
        self.loaded_images = []
        
        # Calcular dimensiones de celdas y márgenes
        self._calculate_grid_dimensions()
        
        # Clock para controlar FPS
        self.clock = pygame.time.Clock()
        self.running = True
        
    def _load_image_paths(self, directory: str) -> List[str]:
        """Carga todas las rutas de imágenes válidas del directorio."""
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
        image_paths = []
        
        path = Path(directory)
        if not path.exists():
            print(f"Error: El directorio {directory} no existe")
            return []
        
        for file in sorted(path.iterdir()):
            if file.suffix.lower() in valid_extensions:
                image_paths.append(str(file))
        
        print(f"Encontradas {len(image_paths)} imágenes en {directory}")
        return image_paths
    
    def _calculate_grid_dimensions(self):
        """Calcula las dimensiones de cada celda y los márgenes."""
        # Márgenes adaptativos según cantidad de elementos
        # A más elementos, menos margen proporcional
        base_margin = 20
        margin_factor = max(0.5, 1.0 - (self.images_per_page / 30))
        self.margin = int(base_margin * margin_factor)
        
        # Espacio total disponible después de los márgenes
        total_width = self.SCREEN_WIDTH - (self.margin * (self.columnas + 1))
        total_height = self.SCREEN_HEIGHT - (self.margin * (self.filas + 1))
        
        # Dimensiones de cada celda (bounding box)
        self.cell_width = total_width // self.columnas
        self.cell_height = total_height // self.filas
        
        print(f"Grilla: {self.columnas}x{self.filas}")
        print(f"Celda: {self.cell_width}x{self.cell_height}px")
        print(f"Margen: {self.margin}px")
    
    def _fit_image_to_cell(self, image: pygame.Surface) -> pygame.Surface:
        """
        Escala la imagen para que quepa en la celda sin deformarla.
        Mantiene el aspect ratio original.
        """
        img_width, img_height = image.get_size()
        
        # Calcular el factor de escala para mantener el aspect ratio
        scale_w = self.cell_width / img_width
        scale_h = self.cell_height / img_height
        scale = min(scale_w, scale_h)  # Usar el menor para que quepa completa
        
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        return pygame.transform.smoothscale(image, (new_width, new_height))
    
    def _load_page_images(self):
        """Carga y procesa las imágenes de la página actual."""
        self.loaded_images = []
        start_idx = self.current_page * self.images_per_page
        end_idx = min(start_idx + self.images_per_page, len(self.image_paths))
        
        for i in range(start_idx, end_idx):
            try:
                img = pygame.image.load(self.image_paths[i])
                img = self._fit_image_to_cell(img)
                self.loaded_images.append(img)
            except Exception as e:
                print(f"Error cargando {self.image_paths[i]}: {e}")
                # Crear una imagen placeholder en caso de error
                placeholder = pygame.Surface((100, 100))
                placeholder.fill((50, 50, 50))
                self.loaded_images.append(placeholder)
    
    def _draw_grid(self):
        """Dibuja todas las imágenes en la grilla."""
        for idx, img in enumerate(self.loaded_images):
            row = idx // self.columnas
            col = idx % self.columnas
            
            # Calcular posición de la celda
            cell_x = self.margin + col * (self.cell_width + self.margin)
            cell_y = self.margin + row * (self.cell_height + self.margin)
            
            # Centrar la imagen dentro de la celda
            img_width, img_height = img.get_size()
            x = cell_x + (self.cell_width - img_width) // 2
            y = cell_y + (self.cell_height - img_height) // 2
            
            self.screen.blit(img, (x, y))
    
    def _handle_events(self):
        """Maneja los eventos de pygame."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    self.running = False
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_SPACE:
                    self._next_page()
                elif event.key == pygame.K_LEFT:
                    self._prev_page()
    
    def _next_page(self):
        """Avanza a la siguiente página de imágenes."""
        max_pages = (len(self.image_paths) + self.images_per_page - 1) // self.images_per_page
        if self.current_page < max_pages - 1:
            self.current_page += 1
            self._load_page_images()
            print(f"Página {self.current_page + 1}/{max_pages}")
    
    def _prev_page(self):
        """Retrocede a la página anterior."""
        if self.current_page > 0:
            self.current_page -= 1
            self._load_page_images()
            max_pages = (len(self.image_paths) + self.images_per_page - 1) // self.images_per_page
            print(f"Página {self.current_page + 1}/{max_pages}")
    
    def run(self):
        """Loop principal del visualizador."""
        if not self.image_paths:
            print("No hay imágenes para mostrar")
            return
        
        # Cargar primera página
        self._load_page_images()
        
        print("\nControles:")
        print("  ESPACIO / FLECHA DERECHA: Siguiente página")
        print("  FLECHA IZQUIERDA: Página anterior")
        print("  ESC / Q: Salir")
        
        while self.running:
            self._handle_events()
            
            # Dibujar
            self.screen.fill(self.BG_COLOR)
            self._draw_grid()
            pygame.display.flip()
            
            # Controlar FPS
            self.clock.tick(60)
        
        pygame.quit()


def main():
    # Configuración
    columnas_imagenes = 3
    filas_imagenes = 5
    
    # Directorio de imágenes (ajustar según necesidad)
    if len(sys.argv) > 1:
        image_directory = sys.argv[1]
    else:
        image_directory = "./"  # Directorio por defecto
    
    # Crear y ejecutar el visualizador
    viewer = ImageGridViewer(
        image_dir=image_directory,
        columnas=columnas_imagenes,
        filas=filas_imagenes
    )
    viewer.run()


if __name__ == "__main__":
    main()
