
# utils/database_manager.py
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

# Configuración del logger
logger = logging.getLogger(__name__)

# --- Constante para la ruta de la base de datos ---
# Se asume que este archivo está en utils/, y la DB estará en la raíz del proyecto.
DB_PATH = Path(__file__).resolve().parent.parent / "youtube_manager.db"

class DatabaseManager:
    """
    Gestiona todas las operaciones de la base de datos SQLite para el CMS de YouTube.
    """
    def __init__(self, db_path: str = str(DB_PATH)):
        """Inicializa el gestor con la ruta a la base de datos."""
        self.db_path = db_path
        self._initialize_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Crea y devuelve una conexión a la base de datos."""
        try:
            conn = sqlite3.connect(self.db_path)
            # Usar Row factory para obtener resultados como diccionarios
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Error al conectar con la base de datos en {self.db_path}: {e}", exc_info=True)
            raise

    def _initialize_database(self):
        """
        Crea las tablas necesarias si no existen.
        Esta es la definición central de nuestro esquema de datos.
        """
        conn = self._get_connection()
        try:
            with conn:
                # Tabla para los Canales de YouTube
                conn.execute('''
                CREATE TABLE IF NOT EXISTS Canales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    channel_id_youtube TEXT,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Tabla de Publicaciones (estructura simplificada - todo en uno)
                conn.execute('''
                CREATE TABLE IF NOT EXISTS Publicaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    guion TEXT,
                    contexto TEXT,
                    id_canal INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('Pendiente', 'En Batch', 'Generando', 'Generado', 'Programado', 'Publicado', 'Error')),
                    script_type TEXT DEFAULT 'manual',
                    ruta_proyecto TEXT,
                    fecha_planificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_subida TIMESTAMP,
                    FOREIGN KEY (id_canal) REFERENCES Canales (id)
                )
                ''')
                logger.info(f"Base de datos inicializada correctamente en {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Error al inicializar las tablas: {e}", exc_info=True)
        finally:
            conn.close()

    # --- Operaciones para Canales ---
    
    def add_canal(self, nombre: str, channel_id: Optional[str] = None) -> Optional[int]:
        """Añade un nuevo canal. Devuelve el ID del nuevo canal."""
        sql = 'INSERT INTO Canales (nombre, channel_id_youtube) VALUES (?, ?)'
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(sql, (nombre, channel_id))
                logger.info(f"Canal '{nombre}' añadido con éxito.")
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"El canal '{nombre}' ya existe en la base de datos.")
            return None
        except sqlite3.Error as e:
            logger.error(f"Error al añadir el canal '{nombre}': {e}", exc_info=True)
            return None
        finally:
            conn.close()

    def get_all_canales(self) -> List[Dict[str, Any]]:
        """Obtiene todos los canales."""
        sql = 'SELECT * FROM Canales ORDER BY nombre'
        conn = self._get_connection()
        try:
            cursor = conn.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener todos los canales: {e}", exc_info=True)
            return []
        finally:
            conn.close()

    # --- Operaciones para Publicaciones (estructura simplificada) ---

    def add_publicacion(self, titulo: str, guion: str, contexto: str, id_canal: int, script_type: str = 'manual') -> Optional[int]:
        """Crea una nueva publicación con todos los datos."""
        sql = 'INSERT INTO Publicaciones (titulo, guion, contexto, id_canal, script_type, status) VALUES (?, ?, ?, ?, ?, ?)'
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(sql, (titulo, guion, contexto, id_canal, script_type, 'Pendiente'))
                logger.info(f"Publicación '{titulo}' creada para canal {id_canal} ({script_type}).")
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error al crear la publicación '{titulo}': {e}", exc_info=True)
            return None
        finally:
            conn.close()

    def get_all_publicaciones_info(self) -> List[Dict[str, Any]]:
        """Obtiene todas las publicaciones con información enriquecida."""
        sql = '''
        SELECT 
            p.id,
            p.titulo,
            p.guion,
            p.contexto,
            p.id_canal,
            p.status,
            p.script_type,
            p.ruta_proyecto,
            p.fecha_planificacion,
            p.fecha_subida,
            c.nombre as nombre_canal
        FROM Publicaciones p
        JOIN Canales c ON p.id_canal = c.id
        ORDER BY p.fecha_planificacion DESC
        '''
        conn = self._get_connection()
        try:
            cursor = conn.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error al obtener la información de publicaciones: {e}", exc_info=True)
            return []
        finally:
            conn.close()
            
    def get_publicacion_details(self, publicacion_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene todos los detalles de una publicación específica."""
        sql = '''
        SELECT 
            p.*,
            c.nombre as nombre_canal
        FROM Publicaciones p
        JOIN Canales c ON p.id_canal = c.id
        WHERE p.id = ?
        '''
        conn = self._get_connection()
        try:
            cursor = conn.execute(sql, (publicacion_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error al obtener detalles de la publicación {publicacion_id}: {e}", exc_info=True)
            return None
        finally:
            conn.close()

    def update_publicacion(self, publicacion_id: int, titulo: str = None, guion: str = None, contexto: str = None, script_type: str = None) -> bool:
        """Actualiza los datos de una publicación."""
        updates = []
        params = []
        
        if titulo is not None:
            updates.append("titulo = ?")
            params.append(titulo)
        if guion is not None:
            updates.append("guion = ?")
            params.append(guion)
        if contexto is not None:
            updates.append("contexto = ?")
            params.append(contexto)
        if script_type is not None:
            updates.append("script_type = ?")
            params.append(script_type)
            
        if not updates:
            return True  # No hay nada que actualizar
            
        sql = f'UPDATE Publicaciones SET {", ".join(updates)} WHERE id = ?'
        params.append(publicacion_id)
        
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(sql, params)
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Publicación {publicacion_id} actualizada exitosamente.")
                return success
        except sqlite3.Error as e:
            logger.error(f"Error al actualizar la publicación {publicacion_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()
            
    def update_publicacion_status(self, id_publicacion: int, status: str, ruta_proyecto: Optional[str] = None):
        """Actualiza el estado y opcionalmente la ruta de una publicación."""
        # Si el estado es 'Subido', actualizamos también la fecha de subida.
        if status == 'Subido':
            sql = 'UPDATE Publicaciones SET status = ?, fecha_subida = CURRENT_TIMESTAMP WHERE id = ?'
            params = (status, id_publicacion)
        else:
            sql = 'UPDATE Publicaciones SET status = ?, ruta_proyecto = ? WHERE id = ?'
            params = (status, ruta_proyecto, id_publicacion)
        
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(sql, params)
                logger.info(f"Estado de la publicación {id_publicacion} actualizado a '{status}'.")
        except sqlite3.Error as e:
            logger.error(f"Error al actualizar la publicación {id_publicacion}: {e}", exc_info=True)
        finally:
            conn.close()

    def delete_publicacion(self, id_publicacion: int) -> bool:
        """Elimina una publicación de la base de datos. Devuelve True si fue exitoso."""
        sql = 'DELETE FROM Publicaciones WHERE id = ?'
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(sql, (id_publicacion,))
                if cursor.rowcount > 0:
                    logger.info(f"Publicación {id_publicacion} eliminada exitosamente.")
                    return True
                else:
                    logger.warning(f"No se encontró la publicación {id_publicacion} para eliminar.")
                    return False
        except sqlite3.Error as e:
            logger.error(f"Error al eliminar la publicación {id_publicacion}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

# --- Punto de entrada para inicialización manual (opcional) ---
if __name__ == '__main__':
    logger.info("Inicializando DatabaseManager para una ejecución de script.")
    db_manager = DatabaseManager()
    print(f"Base de datos en '{DB_PATH}' inicializada y lista.")
    # Ejemplo de uso:
    # db_manager.add_canal("Mi Primer Canal")
    # print(db_manager.get_all_canales())
