# pages/panel_publicaciones_enhanced.py
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import os

# Configuración de la ruta del proyecto
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.database_manager import DatabaseManager

def render_enhanced_panel_publicaciones(app_config: Dict):
    """Renderiza el panel mejorado de publicaciones"""
    
    st.title("📋 Panel de Publicaciones")
    st.markdown("""
    Gestiona el estado de tus videos de forma simple y directa. 
    Controla manualmente cada paso del proceso desde la creación hasta la publicación.
    """)
    
    # Manejar navegación desde Canales
    handle_navigation_from_channels()

    # Inicialización del gestor de base de datos
    @st.cache_resource
    def get_db_manager():
        return DatabaseManager()
    
    db_manager = get_db_manager()

    # Obtener datos
    canales = db_manager.get_all_canales()
    publicaciones = db_manager.get_all_publicaciones_info()

    # Verificar si hay canales
    if not canales:
        st.warning("⚠️ No hay canales disponibles. Ve a **📺 Gestión de Canales** para crear uno primero.")
        return

    # Dashboard de resumen
    render_publications_summary(publicaciones)
    
    st.divider()

    # Formulario para nueva publicación
    render_new_publication_form(db_manager, canales)
    
    st.divider()

    # Tabla principal de publicaciones
    if publicaciones:
        render_publications_table(db_manager, publicaciones)
        
        st.divider()
        
        # Acciones rápidas
        render_quick_actions(db_manager, publicaciones)
    else:
        st.info("📝 **No hay publicaciones aún.** Usa el formulario de arriba para crear tu primera publicación.")

def render_publications_summary(publicaciones: List[Dict]):
    """Renderiza el resumen de publicaciones"""
    
    st.subheader("📊 Resumen General")
    
    if not publicaciones:
        st.info("No hay datos para mostrar")
        return
    
    # Calcular métricas
    total = len(publicaciones)
    pendientes = len([p for p in publicaciones if p['status'] == 'Pendiente'])
    en_batch = len([p for p in publicaciones if p['status'] == 'En Batch'])
    generando = len([p for p in publicaciones if p['status'] == 'Generando'])
    generados = len([p for p in publicaciones if p['status'] == 'Generado'])
    programados = len([p for p in publicaciones if p['status'] == 'Programado'])
    publicados = len([p for p in publicaciones if p['status'] == 'Publicado'])
    errores = len([p for p in publicaciones if p['status'] == 'Error'])
    
    # Mostrar métricas en columnas
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("📝 Total", total)
    
    with col2:
        st.metric("⏳ Pendientes", pendientes, 
                 delta=f"+{en_batch + generando}" if (en_batch + generando) > 0 else None)
    
    with col3:
        st.metric("✅ Generados", generados)
    
    with col4:
        st.metric("📅 Programados", programados)
    
    with col5:
        st.metric("📺 Publicados", publicados)
    
    with col6:
        if errores > 0:
            st.metric("❌ Errores", errores, delta="⚠️")
        else:
            st.metric("❌ Errores", errores)
    
    # Barra de progreso general
    if total > 0:
        completados = publicados + programados
        progreso = completados / total
        st.progress(progreso, text=f"Progreso General: {completados}/{total} completados ({progreso*100:.1f}%)")

def handle_navigation_from_channels():
    """Maneja la navegación desde el panel de canales"""
    
    # Verificar si hay filtro de canal activo
    if 'filter_canal_id' in st.session_state:
        canal_id = st.session_state['filter_canal_id']
        canal_name = st.session_state.get('filter_canal_name', 'Canal')
        
        st.info(f"🔍 **Mostrando publicaciones de: {canal_name}**")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"Filtrado por canal: **{canal_name}** (ID: {canal_id})")
        with col2:
            if st.button("❌ Quitar Filtro", help="Mostrar todas las publicaciones"):
                del st.session_state['filter_canal_id']
                if 'filter_canal_name' in st.session_state:
                    del st.session_state['filter_canal_name']
                st.rerun()
        
        st.divider()
    
    # Verificar si hay preselección para nueva publicación
    if 'preselect_canal_id' in st.session_state:
        st.success(f"✨ **Canal preseleccionado: {st.session_state.get('preselect_canal_name', 'Canal')}**")
        st.info("👇 El canal ya está seleccionado en el formulario de abajo")

def render_new_publication_form(db_manager: DatabaseManager, canales: List[Dict]):
    """Renderiza el formulario para nueva publicación"""
    
    # Verificar si hay preselección de canal
    expanded_form = 'preselect_canal_id' in st.session_state
    
    with st.expander("➕ Crear Nueva Publicación", expanded=expanded_form):
        st.markdown("### ➕ Nueva Publicación")
        
        with st.form("nueva_publicacion_enhanced", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                titulo = st.text_input(
                    "📝 Título del Video",
                    placeholder="Ej: La vida de Santa Teresa de Ávila",
                    help="Título que aparecerá en YouTube"
                )
                
                contexto = st.text_area(
                    "🎯 Contexto/Tema",
                    placeholder="Describe el tema del video...",
                    height=100,
                    help="Información base para generar el contenido"
                )
            
            with col2:
                canal_options = {c['nombre']: c['id'] for c in canales}
                
                # Preseleccionar canal si viene desde navegación
                default_index = 0
                if 'preselect_canal_id' in st.session_state:
                    preselect_id = st.session_state['preselect_canal_id']
                    for i, (name, id_canal) in enumerate(canal_options.items()):
                        if id_canal == preselect_id:
                            default_index = i
                            break
                
                selected_canal_name = st.selectbox(
                    "📺 Canal",
                    list(canal_options.keys()),
                    index=default_index,
                    help="Canal donde se publicará el video"
                )
                
                script_type = st.selectbox(
                    "🤖 Tipo de Guión",
                    ["✍️ Manual", "🤖 Generar con IA"],
                    help="Manual: escribes el guión. IA: se genera automáticamente"
                )
            
            # Campo de guión (solo si es manual)
            if script_type == "✍️ Manual":
                guion = st.text_area(
                    "📜 Guión del Video",
                    placeholder="Escribe aquí el guión completo...",
                    height=150,
                    help="Texto completo que se convertirá en audio"
                )
            else:
                guion = ""
                st.info("🤖 **Modo IA**: El guión se generará automáticamente desde el contexto")
            
            # Botones del formulario
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                submitted = st.form_submit_button("➕ Crear Publicación", type="primary", use_container_width=True)
            
            with col_btn2:
                if st.form_submit_button("🔄 Limpiar", use_container_width=True):
                    st.rerun()
            
            # Procesar envío
            if submitted:
                if not titulo.strip():
                    st.error("❌ El título es obligatorio")
                elif not contexto.strip():
                    st.error("❌ El contexto/tema es obligatorio")
                elif script_type == "✍️ Manual" and not guion.strip():
                    st.error("❌ El guión es obligatorio para modo manual")
                else:
                    # Crear publicación
                    id_canal = canal_options[selected_canal_name]
                    script_type_db = 'manual' if script_type == "✍️ Manual" else 'ai'
                    
                    new_id = db_manager.add_publicacion(
                        titulo.strip(),
                        guion.strip() if script_type == "✍️ Manual" else "",
                        contexto.strip(),
                        id_canal,
                        script_type_db
                    )
                    
                    if new_id:
                        modo_texto = "con guión manual" if script_type_db == 'manual' else "con generación por IA"
                        st.success(f"✅ Publicación '{titulo}' creada para '{selected_canal_name}' {modo_texto}")
                        st.balloons()
                        
                        # Limpiar preselección después de crear
                        if 'preselect_canal_id' in st.session_state:
                            del st.session_state['preselect_canal_id']
                        if 'preselect_canal_name' in st.session_state:
                            del st.session_state['preselect_canal_name']
                        
                        st.rerun()
                    else:
                        st.error("❌ Error al crear la publicación")

def render_publications_table(db_manager: DatabaseManager, publicaciones: List[Dict]):
    """Renderiza la tabla principal de publicaciones"""
    
    # Aplicar filtro de canal si está activo
    if 'filter_canal_id' in st.session_state:
        canal_id = st.session_state['filter_canal_id']
        publicaciones = [p for p in publicaciones if p['id_canal'] == canal_id]
        
        if not publicaciones:
            canal_name = st.session_state.get('filter_canal_name', 'este canal')
            st.warning(f"📭 No hay publicaciones para {canal_name}")
            return
    
    st.subheader("📋 Gestión de Publicaciones")
    
    # Opciones de estado disponibles
    status_options = [
        "Pendiente",
        "En Batch", 
        "Generando",
        "Generado",
        "Programado",
        "Publicado",
        "Error"
    ]
    
    # Iconos para cada estado
    status_icons = {
        'Pendiente': '⏳',
        'En Batch': '🚀',
        'Generando': '⚙️',
        'Generado': '✅',
        'Programado': '📅',
        'Publicado': '📺',
        'Error': '❌'
    }
    
    # Crear tabla editable
    for i, pub in enumerate(publicaciones):
        with st.container():
            # Fila de la publicación
            col1, col2, col3, col4, col5, col6 = st.columns([0.5, 3, 1.5, 1.5, 2, 1])
            
            with col1:
                st.write(f"**{pub['id']}**")
            
            with col2:
                st.write(f"**{pub['titulo']}**")
                canal_info = f"📺 {pub['nombre_canal']} | 🤖 {pub['script_type'].title()}"
                
                # Añadir botón para ver canal si no estamos filtrados
                if 'filter_canal_id' not in st.session_state:
                    col2_1, col2_2 = st.columns([3, 1])
                    with col2_1:
                        st.caption(canal_info)
                    with col2_2:
                        if st.button("📺", key=f"goto_canal_{pub['id']}", help=f"Ver canal {pub['nombre_canal']}"):
                            st.session_state['goto_canal_id'] = pub['id_canal']
                            st.session_state['goto_canal_name'] = pub['nombre_canal']
                            st.success(f"📺 Ve a **📺 Gestión de Canales** para ver '{pub['nombre_canal']}'")
                else:
                    st.caption(canal_info)
            
            with col3:
                # Selector de estado
                current_status = pub['status']
                current_index = status_options.index(current_status) if current_status in status_options else 0
                
                new_status = st.selectbox(
                    "Estado",
                    status_options,
                    index=current_index,
                    format_func=lambda x: f"{status_icons.get(x, '•')} {x}",
                    key=f"status_{pub['id']}",
                    label_visibility="collapsed"
                )
                
                # Actualizar estado si cambió
                if new_status != current_status:
                    db_manager.update_publicacion_status(pub['id'], new_status)
                    st.success(f"✅ Estado actualizado a '{new_status}'")
                    st.rerun()
            
            with col4:
                # Mostrar fecha de creación
                fecha_creacion = pub.get('fecha_planificacion', '')
                if fecha_creacion:
                    fecha_formateada = datetime.fromisoformat(fecha_creacion.replace('Z', '')).strftime('%d/%m/%Y')
                    st.caption(f"📅 {fecha_formateada}")
                else:
                    st.caption("📅 -")
            
            with col5:
                # Ruta del proyecto
                ruta_proyecto = pub.get('ruta_proyecto', '')
                if ruta_proyecto and ruta_proyecto.strip():
                    # Verificar si la ruta existe
                    if os.path.exists(ruta_proyecto):
                        st.markdown(f"📁 `{ruta_proyecto}`")
                        if st.button("🔗", key=f"open_{pub['id']}", help="Abrir carpeta del proyecto"):
                            try:
                                # Abrir carpeta en el explorador
                                if os.name == 'nt':  # Windows
                                    os.startfile(ruta_proyecto)
                                elif os.name == 'posix':  # macOS/Linux
                                    os.system(f'open "{ruta_proyecto}"')
                                st.success("📁 Carpeta abierta")
                            except Exception as e:
                                st.error(f"❌ Error abriendo carpeta: {e}")
                    else:
                        st.caption(f"📁 {ruta_proyecto}")
                        st.caption("⚠️ Ruta no encontrada")
                else:
                    st.caption("📁 Sin proyecto")
            
            with col6:
                # Botones de acción
                if st.button("✏️", key=f"edit_{pub['id']}", help="Editar publicación"):
                    st.session_state[f"editing_{pub['id']}"] = True
                    st.rerun()
                
                if st.button("🗑️", key=f"delete_{pub['id']}", help="Eliminar publicación"):
                    st.session_state[f"confirm_delete_{pub['id']}"] = True
                    st.rerun()
            
            # Formulario de edición expandible
            if st.session_state.get(f"editing_{pub['id']}", False):
                render_edit_publication_form(db_manager, pub, i)
            
            # Confirmación de eliminación
            if st.session_state.get(f"confirm_delete_{pub['id']}", False):
                render_delete_confirmation(db_manager, pub, i)
            
            # Separador entre filas
            if i < len(publicaciones) - 1:
                st.divider()

def render_edit_publication_form(db_manager: DatabaseManager, pub: Dict, index: int):
    """Renderiza formulario de edición de publicación"""
    
    with st.expander(f"✏️ Editando: {pub['titulo']}", expanded=True):
        with st.form(f"edit_pub_{pub['id']}_{index}"):
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_titulo = st.text_input(
                    "Título",
                    value=pub['titulo'],
                    help="Título del video"
                )
                
                nuevo_contexto = st.text_area(
                    "Contexto",
                    value=pub.get('contexto', ''),
                    height=100,
                    help="Contexto o tema del video"
                )
            
            with col2:
                nuevo_guion = st.text_area(
                    "Guión",
                    value=pub.get('guion', ''),
                    height=100,
                    help="Guión del video"
                )
                
                nueva_ruta = st.text_input(
                    "Ruta del Proyecto",
                    value=pub.get('ruta_proyecto', ''),
                    help="Ruta donde está el proyecto del video"
                )
            
            # Botones del formulario
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.form_submit_button("💾 Guardar Cambios", type="primary"):
                    # Actualizar publicación
                    success = db_manager.update_publicacion(
                        pub['id'],
                        titulo=nuevo_titulo,
                        guion=nuevo_guion,
                        contexto=nuevo_contexto
                    )
                    
                    # Actualizar ruta si cambió
                    if nueva_ruta != pub.get('ruta_proyecto', ''):
                        db_manager.update_publicacion_status(pub['id'], pub['status'], nueva_ruta)
                    
                    if success:
                        st.success("✅ Publicación actualizada")
                        st.session_state[f"editing_{pub['id']}"] = False
                        st.rerun()
                    else:
                        st.error("❌ Error actualizando publicación")
            
            with col_btn2:
                if st.form_submit_button("❌ Cancelar"):
                    st.session_state[f"editing_{pub['id']}"] = False
                    st.rerun()

def render_delete_confirmation(db_manager: DatabaseManager, pub: Dict, index: int):
    """Renderiza confirmación de eliminación"""
    
    st.error(f"⚠️ **¿Eliminar '{pub['titulo']}'?**")
    st.warning("Esta acción no se puede deshacer.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ SÍ, ELIMINAR", key=f"confirm_yes_{pub['id']}_{index}", type="primary"):
            success = db_manager.delete_publicacion(pub['id'])
            if success:
                # También eliminar del batch si está ahí
                if "batch_projects" in st.session_state:
                    st.session_state.batch_projects = [
                        p for p in st.session_state.batch_projects 
                        if p.get("cms_publicacion_id") != pub['id']
                    ]
                st.success("🗑️ Publicación eliminada")
                st.session_state[f"confirm_delete_{pub['id']}"] = False
                st.rerun()
            else:
                st.error("❌ Error eliminando publicación")
    
    with col2:
        if st.button("❌ Cancelar", key=f"confirm_no_{pub['id']}_{index}"):
            st.session_state[f"confirm_delete_{pub['id']}"] = False
            st.rerun()

def render_quick_actions(db_manager: DatabaseManager, publicaciones: List[Dict]):
    """Renderiza acciones rápidas"""
    
    st.subheader("🎬 Acciones Rápidas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Enviar pendientes al batch
        pendientes = [p for p in publicaciones if p['status'] == 'Pendiente']
        if pendientes:
            if st.button(f"🚀 Batch: {len(pendientes)} Pendientes", type="primary"):
                enviar_pendientes_al_batch(db_manager, pendientes)
        else:
            st.button("🚀 Batch: 0 Pendientes", disabled=True)
    
    with col2:
        # Marcar generados como programados
        generados = [p for p in publicaciones if p['status'] == 'Generado']
        if generados:
            if st.button(f"📅 Programar: {len(generados)} Generados"):
                marcar_como_programados(db_manager, generados)
        else:
            st.button("📅 Programar: 0 Generados", disabled=True)
    
    with col3:
        # Reintentar errores
        errores = [p for p in publicaciones if p['status'] == 'Error']
        if errores:
            if st.button(f"🔄 Reintentar: {len(errores)} Errores"):
                reintentar_errores(db_manager, errores)
        else:
            st.button("🔄 Reintentar: 0 Errores", disabled=True)
    
    with col4:
        # Actualizar estados
        if st.button("🔄 Actualizar Todo"):
            st.rerun()

def enviar_pendientes_al_batch(db_manager: DatabaseManager, pendientes: List[Dict]):
    """Envía publicaciones pendientes al batch processor"""
    
    if "batch_projects" not in st.session_state:
        st.session_state.batch_projects = []
    
    enviados = 0
    for pub in pendientes:
        try:
            import uuid
            
            # Determinar tipo de script
            batch_script_type = "✍️ Usar guión manual" if pub['script_type'] == 'manual' else "🤖 Generar con IA"
            
            # Crear proyecto para batch
            nuevo_proyecto = {
                "titulo": pub['titulo'],
                "contexto": pub['contexto'],
                "script_type": batch_script_type,
                "guion_manual": pub['guion'] if pub['script_type'] == 'manual' else None,
                "id": str(uuid.uuid4())[:8],
                "fecha_añadido": datetime.now().isoformat(),
                "cms_publicacion_id": pub['id'],
                "cms_canal": pub['nombre_canal']
            }
            
            st.session_state.batch_projects.append(nuevo_proyecto)
            db_manager.update_publicacion_status(pub['id'], 'En Batch')
            enviados += 1
            
        except Exception as e:
            st.error(f"❌ Error enviando '{pub['titulo']}': {e}")
    
    if enviados > 0:
        st.success(f"✅ {enviados} publicaciones enviadas al Batch Processor")
        st.rerun()

def marcar_como_programados(db_manager: DatabaseManager, generados: List[Dict]):
    """Marca videos generados como programados"""
    
    marcados = 0
    for pub in generados:
        try:
            db_manager.update_publicacion_status(pub['id'], 'Programado')
            marcados += 1
        except Exception as e:
            st.error(f"❌ Error marcando '{pub['titulo']}': {e}")
    
    if marcados > 0:
        st.success(f"✅ {marcados} videos marcados como programados")
        st.rerun()

def reintentar_errores(db_manager: DatabaseManager, errores: List[Dict]):
    """Reintenta publicaciones con error"""
    
    reintentados = 0
    for pub in errores:
        try:
            db_manager.update_publicacion_status(pub['id'], 'Pendiente')
            reintentados += 1
        except Exception as e:
            st.error(f"❌ Error reintentando '{pub['titulo']}': {e}")
    
    if reintentados > 0:
        st.success(f"✅ {reintentados} publicaciones reintentadas")
        st.rerun()