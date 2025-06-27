
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
        # Crear un DataFrame para mostrar y permitir acciones
        df_publicaciones = st.dataframe(
            publicaciones,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "nombre_canal": st.column_config.TextColumn("Canal", width="medium"),
                "titulo_video": st.column_config.TextColumn("Título del Vídeo", width="large"),
                "status": st.column_config.TextColumn("Estado"),
                "fecha_planificacion": st.column_config.DatetimeColumn("Planificado", format="D MMM YYYY, HH:mm"),
                "fecha_subida": st.column_config.DatetimeColumn("Subido", format="D MMM YYYY, HH:mm"),
                "ruta_proyecto": st.column_config.TextColumn("Ruta Proyecto"),
            },
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Acciones sobre Publicaciones")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Obtener el ID de la primera publicación si está disponible, sino por defecto 1
            default_pub_id = publicaciones[0]['id'] if publicaciones else 1
            publicacion_id_generar = st.number_input("ID de Publicación para Enviar al Batch", min_value=1, format="%d", value=default_pub_id, key="gen_id_input")
            if st.button("🚀 Enviar al Batch Processor"): # Botón para enviar al batch
                if publicacion_id_generar:
                    # Obtener detalles del video para enviar al batch
                    pub_info = next((p for p in publicaciones if p['id'] == publicacion_id_generar), None)
                    if pub_info:
                        video_details = db_manager.get_video_details(pub_info['id_video'])
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
                                "script_type": "✍️ Usar guión manual",  # Siempre manual desde la biblioteca
                                "guion_manual": video_details['guion'],
                                "id": str(uuid.uuid4())[:8],
                                "fecha_añadido": datetime.now().isoformat(),
                                "cms_publicacion_id": publicacion_id_generar,  # Para tracking
                                "cms_canal": pub_info['nombre_canal']  # Info adicional
                            }
                            
                            # Añadir al batch processor
                            st.session_state.batch_projects.append(nuevo_proyecto_batch)
                            
                            # Actualizar estado en el CMS
                            db_manager.update_publicacion_status(publicacion_id_generar, 'En Batch')
                            
                            st.success(f"✅ '{video_details['titulo_base']}' enviado al Batch Processor!")
                            st.info("🔄 Ve a la pestaña 'Batch Processor' para configurar y procesar el video.")
                            st.rerun()
                        else:
                            st.error("No se encontraron detalles del vídeo para enviar al batch.")
                    else:
                        st.error("Publicación no encontrada.")
                else:
                    st.warning("Por favor, selecciona una publicación válida.")

        with col2:
            publicacion_id_subir = st.number_input("ID de Publicación para Marcar como Subida", min_value=1, format="%d")
            if st.button("✅ Marcar como Subido"): # Botón para marcar como subido
                if publicacion_id_subir:
                    db_manager.update_publicacion_status(publicacion_id_subir, 'Subido')
                    st.success(f"Publicación ID: {publicacion_id_subir} marcada como Subida.")
                    st.rerun()

        with col3:
            publicacion_id_eliminar = st.number_input("ID de Publicación para Eliminar", min_value=1, format="%d")
            if st.button("🗑️ Eliminar Publicación"): # Botón para eliminar
                if publicacion_id_eliminar:
                    # Aquí podrías añadir lógica para eliminar archivos del proyecto si ruta_proyecto está definida
                    # db_manager.delete_publicacion(publicacion_id_eliminar) # Necesitaríamos implementar este método
                    st.warning("Funcionalidad de eliminación no implementada aún.")

    # --- Nota al pie ---
    st.markdown("--- ")
    st.info("🎯 **Flujo de trabajo integrado:** Este panel te permite gestionar el ciclo de vida de tus vídeos. Los videos se envían automáticamente al Batch Processor para aprovechar todas sus funcionalidades avanzadas de configuración, IA, efectos y monitoreo de progreso.")

# --- Ejecución directa para pruebas (opcional) ---
if __name__ == "__main__":
    render_panel_publicaciones()
