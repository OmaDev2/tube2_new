
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
    # Importar la versión mejorada
    try:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from tmp_rovodev_enhanced_publications import render_enhanced_panel_publicaciones
        
        # Usar la versión mejorada
        render_enhanced_panel_publicaciones(app_config)
        return
    except ImportError:
        pass
    
    # Fallback a la versión original
    st.title("🗓️ Panel de Publicaciones")
    st.markdown("""
    Aquí puedes planificar, generar y gestionar el estado de tus vídeos para cada canal.
    """)

    # --- Inicialización del Gestor de Base de Datos ---
    @st.cache_resource
    def get_db_manager():
        return DatabaseManager()
    
    db_manager = get_db_manager()



    # --- Formulario para Crear Nueva Publicación ---
    st.subheader("➕ Crear Nueva Publicación")
    canales = db_manager.get_all_canales()

    if not canales:
        st.warning("No hay canales disponibles. Por favor, añade canales en la sección 'Gestión de Canales'.")
        return

    canal_options = {c['nombre']: c['id'] for c in canales}

    with st.form("nueva_publicacion_form", clear_on_submit=True):
        col_form1, col_form2 = st.columns([2, 1])
        
        with col_form1:
            titulo = st.text_input("📝 Título del Video", placeholder="Ej: La vida de Santa Teresa de Ávila")
            contexto = st.text_area("🎯 Contexto/Tema", placeholder="Describe brevemente el tema del video", height=100)
        
        with col_form2:
            selected_canal_name = st.selectbox("📺 Canal", list(canal_options.keys()))
            script_type = st.selectbox(
                "🤖 Tipo de Guión",
                ["✍️ Guión Manual", "🤖 Generar con IA"],
                help="Manual: Escribes el guión completo. IA: Se genera automáticamente desde el contexto."
            )
        
        # Mostrar campo de guión solo si es manual
        if script_type == "✍️ Guión Manual":
            guion = st.text_area("📜 Guión del Video", placeholder="Escribe aquí el guión completo del video...", height=200)
        else:
            guion = ""  # Para IA, el guión se genera automáticamente
            st.info("🤖 **Modo IA activado**: El guión se generará automáticamente basado en el contexto/tema que escribas arriba.")
        
        submitted = st.form_submit_button("➕ Crear Publicación", type="primary")
        
        if submitted:
            if not titulo.strip():
                st.error("❌ El título es obligatorio")
            elif not contexto.strip():
                st.error("❌ El contexto/tema es obligatorio")
            elif script_type == "✍️ Guión Manual" and not guion.strip():
                st.error("❌ El guión es obligatorio para modo manual")
            else:
                id_canal = canal_options[selected_canal_name]
                script_type_db = 'manual' if script_type == "✍️ Guión Manual" else 'ai'
                
                new_id = db_manager.add_publicacion(
                    titulo.strip(), 
                    guion.strip() if script_type == "✍️ Guión Manual" else "", 
                    contexto.strip(), 
                    id_canal, 
                    script_type_db
                )
                if new_id:
                    modo_texto = "con guión manual" if script_type_db == 'manual' else "con generación por IA"
                    st.success(f"✅ Publicación '{titulo}' creada para '{selected_canal_name}' {modo_texto}.")
                    st.rerun() # Recargar para mostrar la nueva publicación
                else:
                    st.error("❌ Hubo un error al crear la publicación.")

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
        # Preparar datos para tabla estilo Excel
        import pandas as pd
        
        # Convertir a DataFrame para mejor manipulación
        df = pd.DataFrame(publicaciones)
        
        # Añadir iconos de estado
        status_icons = {
            'Pendiente': '⏳ Pendiente',
            'En Batch': '🚀 En Batch',
            'Generando': '⚙️ Generando',
            'Generado': '✅ Generado',
            'Subido': '📺 Subido',
            'Error': '❌ Error'
        }
        df['estado_visual'] = df['status'].map(status_icons)
        
        # Añadir iconos de tipo de script
        script_icons = {
            'manual': '✍️ Manual',
            'ai': '🤖 IA'
        }
        df['script_visual'] = df['script_type'].map(script_icons)
        
        # Formatear fechas para mejor visualización
        if 'fecha_planificacion' in df.columns:
            df['fecha_planificacion'] = pd.to_datetime(df['fecha_planificacion']).dt.strftime('%d/%m/%Y %H:%M')
        if 'fecha_subida' in df.columns:
            df['fecha_subida'] = pd.to_datetime(df['fecha_subida'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
        
        # Crear tabla estilo Excel con st.data_editor
        edited_df = st.data_editor(
            df,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small", disabled=True),
                "titulo": st.column_config.TextColumn("📝 Título del Video", width="large", disabled=True),
                "script_visual": st.column_config.TextColumn("🤖 Tipo", width="small", disabled=True),
                "nombre_canal": st.column_config.TextColumn("📺 Canal", width="medium", disabled=True),
                "estado_visual": st.column_config.TextColumn("📊 Estado", width="medium", disabled=True),
                "fecha_planificacion": st.column_config.TextColumn("📅 Planificado", width="medium", disabled=True),
                "fecha_subida": st.column_config.TextColumn("📤 Subido", width="medium", disabled=True),
                "ruta_proyecto": st.column_config.TextColumn("📁 Proyecto", width="large", disabled=True),
                # Ocultar columnas técnicas y de contenido
                "id_canal": None,
                "status": None,
                "script_type": None,
                "guion": None,
                "contexto": None,
            },
            hide_index=True,
            use_container_width=True,
            key="publicaciones_table"
        )
        
        # Botones de acción debajo de la tabla
        st.subheader("🎬 Acciones Rápidas")
        
        # Selector para acciones
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Obtener publicaciones pendientes
            pendientes = [p for p in publicaciones if p['status'] == 'Pendiente']
            if pendientes:
                st.markdown("**🚀 Enviar al Batch**")
                selected_pendiente = st.selectbox(
                    "Selecciona publicación pendiente:",
                    options=[f"{p['id']} - {p['titulo']}" for p in pendientes],
                    key="select_pendiente"
                )
                
                if st.button("🚀 Enviar al Batch Processor", key="batch_action"):
                    pub_id = int(selected_pendiente.split(' - ')[0])
                    pub = next(p for p in publicaciones if p['id'] == pub_id)
                    
                    # Inicializar batch_projects si no existe
                    if "batch_projects" not in st.session_state:
                        st.session_state.batch_projects = []
                    
                    # Crear proyecto para el batch processor
                    import uuid
                    from datetime import datetime
                    
                    # Determinar tipo de script para el batch processor
                    batch_script_type = "✍️ Usar guión manual" if pub['script_type'] == 'manual' else "🤖 Generar con IA"
                    
                    nuevo_proyecto_batch = {
                        "titulo": pub['titulo'],
                        "contexto": pub['contexto'],
                        "script_type": batch_script_type,
                        "guion_manual": pub['guion'] if pub['script_type'] == 'manual' else None,
                        "id": str(uuid.uuid4())[:8],
                        "fecha_añadido": datetime.now().isoformat(),
                        "cms_publicacion_id": pub['id'],
                        "cms_canal": pub['nombre_canal']
                    }
                    
                    st.session_state.batch_projects.append(nuevo_proyecto_batch)
                    db_manager.update_publicacion_status(pub['id'], 'En Batch')
                    
                    st.success(f"✅ '{pub['titulo']}' enviado al Batch!")
                    st.rerun()
            else:
                st.info("No hay publicaciones pendientes")
        
        with col2:
            # Publicaciones generadas listas para marcar como subidas
            generados = [p for p in publicaciones if p['status'] == 'Generado']
            if generados:
                st.markdown("**✅ Marcar como Subido**")
                selected_generado = st.selectbox(
                    "Selecciona publicación generada:",
                    options=[f"{p['id']} - {p['titulo']}" for p in generados],
                    key="select_generado"
                )
                
                if st.button("✅ Marcar como Subido", key="upload_action"):
                    pub_id = int(selected_generado.split(' - ')[0])
                    db_manager.update_publicacion_status(pub_id, 'Subido')
                    st.success("✅ Publicación marcada como subida!")
                    st.rerun()
            else:
                st.info("No hay publicaciones generadas")
        
        with col3:
            # Publicaciones con error para reintentar
            errores = [p for p in publicaciones if p['status'] == 'Error']
            if errores:
                st.markdown("**🔄 Reintentar Errores**")
                selected_error = st.selectbox(
                    "Selecciona publicación con error:",
                    options=[f"{p['id']} - {p['titulo']}" for p in errores],
                    key="select_error"
                )
                
                if st.button("🔄 Reintentar", key="retry_action"):
                    pub_id = int(selected_error.split(' - ')[0])
                    db_manager.update_publicacion_status(pub_id, 'Pendiente')
                    st.success("🔄 Estado cambiado a 'Pendiente'")
                    st.rerun()
            else:
                st.info("No hay publicaciones con error")
        
        # Sección de eliminación con confirmación
        st.subheader("🗑️ Eliminar Publicaciones")
        
        # Dividir en dos columnas para la eliminación
        col_del1, col_del2 = st.columns(2)
        
        with col_del1:
            st.markdown("**⚠️ Eliminar Publicación**")
            
            # Crear mapeo de estado para mostrar iconos
            status_icons = {
                'Pendiente': '⏳ Pendiente',
                'En Batch': '🚀 En Batch',
                'Generando': '⚙️ Generando',
                'Generado': '✅ Generado',
                'Subido': '📺 Subido',
                'Error': '❌ Error'
            }
            
            selected_to_delete = st.selectbox(
                "Selecciona publicación a eliminar:",
                options=[f"{p['id']} - {p['titulo']} ({status_icons.get(p['status'], p['status'])})" for p in publicaciones],
                key="select_delete"
            )
        
        with col_del2:
            st.markdown("**Confirmación requerida**")
            confirmar_eliminacion = st.checkbox("✅ Confirmo que quiero eliminar esta publicación", key="confirm_delete")
            
            if st.button("🗑️ ELIMINAR PUBLICACIÓN", key="delete_action", type="secondary"):
                if confirmar_eliminacion:
                    pub_id = int(selected_to_delete.split(' - ')[0])
                    success = db_manager.delete_publicacion(pub_id)
                    if success:
                        # También eliminar del batch processor si está ahí
                        if "batch_projects" in st.session_state:
                            st.session_state.batch_projects = [
                                p for p in st.session_state.batch_projects 
                                if p.get("cms_publicacion_id") != pub_id
                            ]
                        st.success("🗑️ Publicación eliminada exitosamente!")
                        st.rerun()
                    else:
                        st.error("❌ Error al eliminar la publicación")
                else:
                    st.warning("⚠️ Marca la casilla de confirmación para eliminar")
        
        # Resumen estadístico
        st.subheader("📊 Resumen")
        col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
        
        with col_stats1:
            pendientes_count = len([p for p in publicaciones if p['status'] == 'Pendiente'])
            st.metric("⏳ Pendientes", pendientes_count)
        
        with col_stats2:
            en_batch_count = len([p for p in publicaciones if p['status'] in ['En Batch', 'Generando']])
            st.metric("🚀 En Proceso", en_batch_count)
        
        with col_stats3:
            generados_count = len([p for p in publicaciones if p['status'] == 'Generado'])
            st.metric("✅ Generados", generados_count)
        
        with col_stats4:
            subidos_count = len([p for p in publicaciones if p['status'] == 'Subido'])
            st.metric("📺 Subidos", subidos_count)

    # --- Nota al pie ---
    st.markdown("--- ")
    st.info("🎯 **Flujo de trabajo integrado:** Este panel te permite gestionar el ciclo de vida de tus vídeos. Los videos se envían automáticamente al Batch Processor para aprovechar todas sus funcionalidades avanzadas de configuración, IA, efectos y monitoreo de progreso.")

# --- Ejecución directa para pruebas (opcional) ---
if __name__ == "__main__":
    render_panel_publicaciones()
