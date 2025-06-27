
# pages/panel_publicaciones_page.py
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict

# --- Configuración de la Ruta del Proyecto ---
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.database_manager import DatabaseManager

# --- Función Principal de la Página ---
def render_panel_publicaciones(app_config: Dict):
    st.title("🗓️ Panel de Publicaciones")
    st.markdown("""
    Aquí puedes planificar, generar y gestionar el estado de tus vídeos para cada canal.
    """)

    # --- Inicialización del Gestor de Base de Datos ---
    @st.cache_resource
    def get_db_manager():
        return DatabaseManager()
    
    db_manager = get_db_manager()



    # --- Formulario para Planificar Nueva Publicación ---
    st.subheader("Planificar Nueva Publicación")
    canales = db_manager.get_all_canales()
    videos = db_manager.get_all_videos()

    if not canales:
        st.warning("No hay canales disponibles. Por favor, añade canales en la sección 'Gestión de Canales'.")
        return
    if not videos:
        st.warning("No hay vídeos en la biblioteca. Por favor, añade vídeos en la sección 'Biblioteca de Vídeos'.")
        return

    canal_options = {c['nombre']: c['id'] for c in canales}
    video_options = {v['titulo_base']: v['id'] for v in videos}

    with st.form("nueva_publicacion_form", clear_on_submit=True):
        selected_canal_name = st.selectbox("Selecciona un Canal", list(canal_options.keys()))
        selected_video_title = st.selectbox("Selecciona un Vídeo de la Biblioteca", list(video_options.keys()))
        
        submitted = st.form_submit_button("Planificar Publicación")
        
        if submitted:
            id_canal = canal_options[selected_canal_name]
            id_video = video_options[selected_video_title]
            
            new_id = db_manager.add_publicacion(id_canal, id_video)
            if new_id:
                st.success(f"Publicación planificada para '{selected_video_title}' en '{selected_canal_name}'.")
                st.rerun() # Recargar para mostrar la nueva publicación
            else:
                st.error("Hubo un error al planificar la publicación.")

    # --- Mostrar estado del Batch Processor ---
    if "batch_projects" in st.session_state and st.session_state.batch_projects:
        cms_projects_in_batch = [p for p in st.session_state.batch_projects if "cms_publicacion_id" in p]
        if cms_projects_in_batch:
            st.info(f"🚀 **{len(cms_projects_in_batch)} video(s) del CMS** en cola del Batch Processor. Ve a la pestaña 'Batch Processor' para procesarlos.")

    # --- Mostrar la Lista de Publicaciones ---
    st.header("Mis Publicaciones")

    publicaciones = db_manager.get_all_publicaciones_info()
    
    if not publicaciones:
        st.info("Aún no hay publicaciones planificadas. ¡Usa el formulario de arriba para empezar!")
    else:
        # Mostrar publicaciones con botones inline más intuitivos
        for idx, pub in enumerate(publicaciones):
            with st.container():
                # Crear columnas para la información y botones
                col_info, col_actions = st.columns([4, 1])
                
                with col_info:
                    # Icono según el estado
                    status_icons = {
                        'Pendiente': '⏳',
                        'En Batch': '🚀',
                        'Generando': '⚙️',
                        'Generado': '✅',
                        'Subido': '📺',
                        'Error': '❌'
                    }
                    status_icon = status_icons.get(pub['status'], '❓')
                    
                    st.markdown(f"**{status_icon} {pub['titulo_video']}**")
                    st.caption(f"📺 **{pub['nombre_canal']}** | 🆔 ID: {pub['id']} | 📅 {pub['fecha_planificacion']}")
                    
                    # Mostrar info adicional según el estado
                    if pub['status'] == 'Generado' and pub.get('ruta_proyecto'):
                        st.caption(f"📁 **Proyecto:** {pub['ruta_proyecto']}")
                    elif pub['status'] == 'Subido' and pub.get('fecha_subida'):
                        st.caption(f"📤 **Subido:** {pub['fecha_subida']}")
                
                with col_actions:
                    # Botones según el estado actual
                    if pub['status'] == 'Pendiente':
                        if st.button("🚀 A Batch", key=f"batch_{pub['id']}", help="Enviar al Batch Processor"):
                            # Lógica para enviar al batch
                            video_details = db_manager.get_video_details(pub['id_video'])
                            if video_details:
                                # Inicializar batch_projects si no existe
                                if "batch_projects" not in st.session_state:
                                    st.session_state.batch_projects = []
                                
                                # Crear proyecto para el batch processor
                                import uuid
                                from datetime import datetime
                                
                                nuevo_proyecto_batch = {
                                    "titulo": video_details['titulo_base'],
                                    "contexto": video_details['contexto'],
                                    "script_type": "✍️ Usar guión manual",
                                    "guion_manual": video_details['guion'],
                                    "id": str(uuid.uuid4())[:8],
                                    "fecha_añadido": datetime.now().isoformat(),
                                    "cms_publicacion_id": pub['id'],
                                    "cms_canal": pub['nombre_canal']
                                }
                                
                                st.session_state.batch_projects.append(nuevo_proyecto_batch)
                                db_manager.update_publicacion_status(pub['id'], 'En Batch')
                                
                                st.success(f"✅ '{video_details['titulo_base']}' enviado al Batch!")
                                st.rerun()
                    
                    elif pub['status'] == 'En Batch':
                        st.markdown("🚀 **En cola**")
                        if st.button("📋 Ver Batch", key=f"view_batch_{pub['id']}", help="Ir al Batch Processor"):
                            st.info("🔄 Ve a la pestaña 'Batch Processor' para procesar este video.")
                    
                    elif pub['status'] == 'Generado':
                        if st.button("✅ Subido", key=f"upload_{pub['id']}", help="Marcar como subido a YouTube"):
                            db_manager.update_publicacion_status(pub['id'], 'Subido')
                            st.success("✅ Marcado como subido!")
                            st.rerun()
                    
                    elif pub['status'] == 'Subido':
                        st.markdown("📺 **Subido**")
                    
                    elif pub['status'] == 'Error':
                        if st.button("🔄 Reintentar", key=f"retry_{pub['id']}", help="Reintentar envío al Batch"):
                            db_manager.update_publicacion_status(pub['id'], 'Pendiente')
                            st.info("🔄 Estado cambiado a 'Pendiente'. Puedes volver a enviar al Batch.")
                            st.rerun()
                
                # Línea separadora
                if idx < len(publicaciones) - 1:
                    st.markdown("---")

    # --- Nota al pie ---
    st.markdown("--- ")
    st.info("🎯 **Flujo de trabajo integrado:** Este panel te permite gestionar el ciclo de vida de tus vídeos. Los videos se envían automáticamente al Batch Processor para aprovechar todas sus funcionalidades avanzadas de configuración, IA, efectos y monitoreo de progreso.")

# --- Ejecución directa para pruebas (opcional) ---
if __name__ == "__main__":
    render_panel_publicaciones()
