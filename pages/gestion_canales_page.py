
# pages/1_gestion_canales.py
import streamlit as st
import sys
from pathlib import Path

# --- Configuración de la Ruta del Proyecto ---
# Añadir el directorio raíz al sys.path para asegurar que podemos importar 'utils'
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.database_manager import DatabaseManager

# --- Configuración de la Página de Streamlit ---
def render_gestion_canales():
    # Importar la versión mejorada
    try:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from tmp_rovodev_enhanced_channels import render_enhanced_gestion_canales
        
        # Usar la versión mejorada
        render_enhanced_gestion_canales()
        return
    except ImportError:
        pass
    
    # Fallback a la versión original
    st.title("📺 Gestión de Canales de YouTube")
    st.markdown("""
    Aquí puedes añadir y ver los canales de YouTube para los que quieres planificar y generar contenido.
    """)

    # --- Inicialización del Gestor de Base de Datos ---
    try:
        # Usamos una función para cachear el objeto y evitar reconexiones innecesarias
        @st.cache_resource
        def get_db_manager():
            return DatabaseManager()
        
        db_manager = get_db_manager()
        
    except Exception as e:
        st.error(f"Error crítico al conectar con la base de datos: {e}")
        st.info("Asegúrate de que el archivo `youtube_manager.db` no esté corrupto o bloqueado.")
        st.stop()

    # --- Formulario para Añadir un Nuevo Canal ---
    with st.form("nuevo_canal_form", clear_on_submit=True):
        st.subheader("Añadir un Nuevo Canal")
        nombre_canal = st.text_input("Nombre del Canal", placeholder="Ej: Biografías Históricas")
        channel_id_youtube = st.text_input("ID del Canal de YouTube (Opcional)", placeholder="Ej: UCx_123ABC...")
        
        submitted = st.form_submit_button("Añadir Canal")
        
        if submitted:
            if not nombre_canal:
                st.warning("El nombre del canal no puede estar vacío.")
            else:
                new_id = db_manager.add_canal(nombre_canal, channel_id_youtube)
                if new_id:
                    st.success(f"¡Canal '{nombre_canal}' añadido con éxito!")
                else:
                    st.error(f"El canal '{nombre_canal}' ya existe o hubo un error al guardarlo.")

    # --- Mostrar la Lista de Canales Existentes ---
    st.header("Mis Canales")

    try:
        canales = db_manager.get_all_canales()
        
        if not canales:
            st.info("Aún no has añadido ningún canal. ¡Usa el formulario de arriba para empezar!")
        else:
            st.dataframe(
                canales,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "nombre": st.column_config.TextColumn("Nombre del Canal", width="large"),
                    "channel_id_youtube": st.column_config.TextColumn("ID de YouTube"),
                    "fecha_creacion": st.column_config.DatetimeColumn(
                        "Fecha de Creación",
                        format="D MMM YYYY, HH:mm"
                    )
                },
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(f"No se pudieron cargar los canales desde la base de datos. Error: {e}")

    # --- Nota al pie ---
    st.markdown("--- ")
    st.info("Para ver esta página, asegúrate de haber reiniciado la aplicación de Streamlit después de la creación del gestor de la base de datos.")

if __name__ == "__main__":
    render_gestion_canales()
