import pygame
import os
from pathlib import Path
from typing import List, Tuple
import sys
import random

class ImageGridViewer:
    def __init__(self, image_dir: str, columnas: int = 3, filas: int = 5, fade_speed: float = 3.0):
        """
        Inicializa el visualizador de imágenes en grilla.
        
        Args:
            image_dir: Directorio con las imágenes
            columnas: Número de columnas en la grilla
            filas: Número de filas en la grilla
            fade_speed: Velocidad del fade in (1.0 = lento, 10.0 = muy rápido)
        """
        pygame.init()
        
        # Configuración de pantalla
        self.SCREEN_WIDTH = 1920
        self.SCREEN_HEIGHT = 1080
        self.fullscreen = False
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), 
                                               pygame.NOFRAME)
        pygame.display.set_caption("Image Grid Viewer")
        
        # Configuración de grilla
        self.columnas = columnas
        self.filas = filas
        self.images_per_page = columnas * filas
        
        # Configuración de animación
        self.fade_speed = fade_speed
        self.image_alphas = []  # Alpha actual de cada imagen
        self.current_fade_index = 0  # Índice de la imagen que está haciendo fade
        self.fade_active = False  # Si hay una animación de fade en curso
        self.fade_order = []  # Orden en que aparecerán las imágenes
        self.random_order = False  # Toggle para orden aleatorio
        self.spiral_mode = False  # Toggle para modo espiral
        self.spiral_positions = []  # Posiciones de las imágenes en modo espiral
        
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
        self.image_alphas = []
        start_idx = self.current_page * self.images_per_page
        end_idx = min(start_idx + self.images_per_page, len(self.image_paths))
        
        for i in range(start_idx, end_idx):
            try:
                img = pygame.image.load(self.image_paths[i])
                img = self._fit_image_to_cell(img)
                # Convertir a formato que soporte alpha
                img = img.convert_alpha()
                self.loaded_images.append(img)
                self.image_alphas.append(0)  # Empezar invisible
            except Exception as e:
                print(f"Error cargando {self.image_paths[i]}: {e}")
                # Crear una imagen placeholder en caso de error
                placeholder = pygame.Surface((100, 100), pygame.SRCALPHA)
                placeholder.fill((50, 50, 50, 255))
                self.loaded_images.append(placeholder)
                self.image_alphas.append(0)
        
        # Generar orden de aparición
        self._generate_fade_order()
        
        # Calcular posiciones en espiral
        self._calculate_spiral_positions()
        
        # Iniciar animación de fade in
        self.current_fade_index = 0
        self.fade_active = True if self.loaded_images else False
    
    def _generate_fade_order(self):
        """Genera el orden en que aparecerán las imágenes."""
        num_images = len(self.loaded_images)
        
        if self.random_order:
            # Orden aleatorio
            self.fade_order = list(range(num_images))
            random.shuffle(self.fade_order)
        else:
            # Orden secuencial (izq a der, arriba a abajo)
            self.fade_order = list(range(num_images))
    
    def _calculate_spiral_positions(self):
        """Calcula las posiciones de las imágenes en modo espiral."""
        import math
        
        num_images = len(self.loaded_images)
        self.spiral_positions = []
        
        # Centro de la pantalla
        center_x = self.SCREEN_WIDTH / 2
        center_y = self.SCREEN_HEIGHT / 2
        
        # Parámetros de la espiral de Arquímedes
        # r = a + b * theta
        a = 50  # Radio inicial
        b = 30  # Separación entre vueltas
        
        for i in range(num_images):
            # Ángulo en radianes (más vueltas = más separación)
            theta = i * 0.5  # Ajustar para más o menos apretado
            
            # Radio en la espiral
            r = a + b * theta
            
            # Convertir coordenadas polares a cartesianas
            x = center_x + r * math.cos(theta)
            y = center_y + r * math.sin(theta)
            
            self.spiral_positions.append((x, y))
    
    def _update_fade(self, delta_time):
        """Actualiza el estado de la animación de fade in."""
        if not self.fade_active:
            return
        
        # Obtener el índice real de la imagen que debe aparecer ahora
        if self.current_fade_index < len(self.fade_order):
            actual_image_index = self.fade_order[self.current_fade_index]
            
            # Incrementar el alpha de la imagen actual
            self.image_alphas[actual_image_index] += self.fade_speed * delta_time * 255
            
            # Si esta imagen completó su fade, pasar a la siguiente
            if self.image_alphas[actual_image_index] >= 255:
                self.image_alphas[actual_image_index] = 255
                self.current_fade_index += 1
                
                # Si terminamos todas las imágenes, desactivar fade
                if self.current_fade_index >= len(self.loaded_images):
                    self.fade_active = False
    
    def _draw_grid(self):
        """Dibuja todas las imágenes en la grilla con su alpha correspondiente."""
        for idx, img in enumerate(self.loaded_images):
            # Solo dibujar imágenes que ya tienen algo de alpha
            if idx < len(self.image_alphas) and self.image_alphas[idx] > 0:
                
                if self.spiral_mode:
                    # Modo espiral: usar posiciones calculadas
                    if idx < len(self.spiral_positions):
                        spiral_x, spiral_y = self.spiral_positions[idx]
                        img_width, img_height = img.get_size()
                        
                        # Centrar la imagen en la posición espiral
                        x = spiral_x - img_width / 2
                        y = spiral_y - img_height / 2
                else:
                    # Modo grilla normal
                    row = idx // self.columnas
                    col = idx % self.columnas
                    
                    # Calcular posición de la celda
                    cell_x = self.margin + col * (self.cell_width + self.margin)
                    cell_y = self.margin + row * (self.cell_height + self.margin)
                    
                    # Centrar la imagen dentro de la celda
                    img_width, img_height = img.get_size()
                    x = cell_x + (self.cell_width - img_width) // 2
                    y = cell_y + (self.cell_height - img_height) // 2
                
                # Aplicar alpha a la imagen
                img_copy = img.copy()
                img_copy.set_alpha(int(self.image_alphas[idx]))
                
                self.screen.blit(img_copy, (x, y))
    
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
                elif event.key == pygame.K_UP:
                    # Aumentar velocidad de fade
                    self.fade_speed = min(self.fade_speed + 0.5, 20.0)
                    print(f"Velocidad fade: {self.fade_speed:.1f}")
                elif event.key == pygame.K_DOWN:
                    # Disminuir velocidad de fade
                    self.fade_speed = max(self.fade_speed - 0.5, 0.5)
                    print(f"Velocidad fade: {self.fade_speed:.1f}")
                elif event.key == pygame.K_r:
                    # Reiniciar animación de la página actual
                    self._restart_fade()
                    print("Reiniciando animación...")
                elif event.key == pygame.K_o:
                    # Toggle orden de aparición
                    self.random_order = not self.random_order
                    order_text = "ALEATORIO" if self.random_order else "SECUENCIAL"
                    print(f"Orden de aparición: {order_text}")
                    # Reiniciar la animación con el nuevo orden
                    self._restart_fade()
                elif event.key == pygame.K_f:
                    # Toggle fullscreen
                    self._toggle_fullscreen()
                elif event.key == pygame.K_e:
                    # Toggle modo espiral
                    self.spiral_mode = not self.spiral_mode
                    mode_text = "ESPIRAL 🌀" if self.spiral_mode else "GRILLA"
                    print(f"Modo de visualización: {mode_text}")
                    # Reiniciar la animación para ver el efecto
                    self._restart_fade()
    
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
    
    def _restart_fade(self):
        """Reinicia la animación de fade de la página actual."""
        for i in range(len(self.image_alphas)):
            self.image_alphas[i] = 0
        
        # Regenerar el orden de aparición
        self._generate_fade_order()
        
        # Recalcular posiciones espirales
        self._calculate_spiral_positions()
        
        self.current_fade_index = 0
        self.fade_active = True
    
    def _toggle_fullscreen(self):
        """Alterna entre modo fullscreen y windowed."""
        self.fullscreen = not self.fullscreen
        
        if self.fullscreen:
            self.screen = pygame.display.set_mode(
                (self.SCREEN_WIDTH, self.SCREEN_HEIGHT), 
                pygame.FULLSCREEN
            )
            print("Modo: FULLSCREEN")
        else:
            self.screen = pygame.display.set_mode(
                (self.SCREEN_WIDTH, self.SCREEN_HEIGHT), 
                pygame.NOFRAME
            )
            print("Modo: VENTANA")
    
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
        print("  FLECHA ARRIBA: Aumentar velocidad de fade")
        print("  FLECHA ABAJO: Disminuir velocidad de fade")
        print("  O: Toggle orden (secuencial ↔ aleatorio)")
        print("  E: Toggle modo espiral 🌀")
        print("  F: Toggle fullscreen")
        print("  R: Reiniciar animación de página actual")
        print("  ESC / Q: Salir")
        print(f"\nVelocidad fade inicial: {self.fade_speed:.1f}")
        print(f"Orden inicial: {'ALEATORIO' if self.random_order else 'SECUENCIAL'}")
        print(f"Modo inicial: {'ESPIRAL 🌀' if self.spiral_mode else 'GRILLA'}")
        
        while self.running:
            # Calcular delta time para animaciones suaves
            delta_time = self.clock.tick(60) / 1000.0  # Convertir a segundos
            
            self._handle_events()
            
            # Actualizar animaciones
            self._update_fade(delta_time)
            
            # Dibujar
            self.screen.fill(self.BG_COLOR)
            self._draw_grid()
            pygame.display.flip()
        
        pygame.quit()


def main():
    # Configuración
    columnas_imagenes = 3
    filas_imagenes = 5*2
    fade_speed = 0.5  # Velocidad del fade (ajustable con flechas arriba/abajo)
    
    # Directorio de imágenes (ajustar según necesidad)
    if len(sys.argv) > 1:
        image_directory = sys.argv[1]
    else:
        image_directory = "./"  # Directorio por defecto
    
    # Crear y ejecutar el visualizador
    viewer = ImageGridViewer(
        image_dir=image_directory,
        columnas=columnas_imagenes,
        filas=filas_imagenes,
        fade_speed=fade_speed
    )
    viewer.run()


if __name__ == "__main__":
    main()
