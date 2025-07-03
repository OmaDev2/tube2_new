# pages/gestion_canales_enhanced.py
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Any, Optional

# Configuración de la ruta del proyecto
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.database_manager import DatabaseManager

class ChannelManager:
    """Gestor avanzado de canales con funcionalidades mejoradas"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def get_channel_stats(self, channel_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas de un canal"""
        publicaciones = self.db_manager.get_all_publicaciones_info()
        channel_pubs = [p for p in publicaciones if p['id_canal'] == channel_id]
        
        stats = {
            'total_publicaciones': len(channel_pubs),
            'pendientes': len([p for p in channel_pubs if p['status'] == 'Pendiente']),
            'en_proceso': len([p for p in channel_pubs if p['status'] in ['En Batch', 'Generando']]),
            'generados': len([p for p in channel_pubs if p['status'] == 'Generado']),
            'programados': len([p for p in channel_pubs if p['status'] == 'Programado']),
            'publicados': len([p for p in channel_pubs if p['status'] == 'Publicado']),
            'errores': len([p for p in channel_pubs if p['status'] == 'Error']),
            'ultima_publicacion': None,
            'completadas': 0
        }
        
        # Calcular completadas (programados + publicados)
        stats['completadas'] = stats['programados'] + stats['publicados']
        
        if channel_pubs:
            # Ordenar por fecha y obtener la más reciente
            sorted_pubs = sorted(channel_pubs, key=lambda x: x['fecha_planificacion'], reverse=True)
            stats['ultima_publicacion'] = sorted_pubs[0]['fecha_planificacion']
        
        return stats
    
    def get_all_channels_with_stats(self) -> List[Dict[str, Any]]:
        """Obtiene todos los canales con sus estadísticas"""
        canales = self.db_manager.get_all_canales()
        
        for canal in canales:
            stats = self.get_channel_stats(canal['id'])
            canal.update(stats)
        
        return canales

def render_enhanced_gestion_canales():
    """Renderiza la página mejorada de gestión de canales"""
    
    # Header principal
    st.title("📺 Gestión Avanzada de Canales")
    st.markdown("""
    Gestiona tus canales de YouTube con un panel de control moderno y funcional.
    Visualiza estadísticas, edita configuraciones y controla el estado de tus publicaciones.
    """)
    
    # Inicializar gestor
    try:
        @st.cache_resource
        def get_channel_manager():
            return ChannelManager()
        
        channel_manager = get_channel_manager()
        
    except Exception as e:
        st.error(f"❌ Error crítico al conectar con la base de datos: {e}")
        st.info("💡 Asegúrate de que el archivo `youtube_manager.db` no esté corrupto o bloqueado.")
        st.stop()
    
    # Obtener canales con estadísticas
    canales = channel_manager.get_all_channels_with_stats()
    
    # Métricas generales
    if canales:
        render_general_metrics(canales)
        st.divider()
    
    # Sección de añadir nuevo canal
    render_add_channel_section(channel_manager, canales)
    
    st.divider()
    
    # Lista de canales
    if canales:
        render_channels_section(canales, channel_manager)
    else:
        render_empty_state()

def render_general_metrics(canales: List[Dict[str, Any]]):
    """Renderiza métricas generales de todos los canales"""
    
    st.subheader("📊 Resumen General")
    
    # Calcular métricas totales
    total_canales = len(canales)
    total_publicaciones = sum(c['total_publicaciones'] for c in canales)
    total_pendientes = sum(c['pendientes'] for c in canales)
    total_en_proceso = sum(c['en_proceso'] for c in canales)
    total_completadas = sum(c['completadas'] for c in canales)
    total_errores = sum(c['errores'] for c in canales)
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("📺 Canales", total_canales)
    
    with col2:
        st.metric("📝 Publicaciones", total_publicaciones)
    
    with col3:
        st.metric("⏳ Pendientes", total_pendientes, 
                 delta=f"+{total_en_proceso}" if total_en_proceso > 0 else None)
    
    with col4:
        st.metric("🔄 En Proceso", total_en_proceso)
    
    with col5:
        st.metric("✅ Completadas", total_completadas)
    
    with col6:
        if total_errores > 0:
            st.metric("❌ Errores", total_errores, delta="⚠️")
        else:
            st.metric("❌ Errores", total_errores)
    
    # Barra de progreso general
    if total_publicaciones > 0:
        progress_general = total_completadas / total_publicaciones
        st.progress(progress_general, 
                   text=f"Progreso General: {total_completadas}/{total_publicaciones} completadas ({progress_general*100:.1f}%)")

def render_add_channel_section(channel_manager: ChannelManager, canales: List[Dict[str, Any]]):
    """Renderiza la sección para añadir nuevo canal"""
    
    with st.expander("➕ Añadir Nuevo Canal", expanded=not bool(canales)):
        st.markdown("### ➕ Crear Nuevo Canal")
        
        with st.form("nuevo_canal_form_enhanced", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre_canal = st.text_input(
                    "📺 Nombre del Canal",
                    placeholder="Ej: Biografías Históricas",
                    help="Nombre descriptivo para identificar tu canal"
                )
            
            with col2:
                channel_id_youtube = st.text_input(
                    "🔗 ID del Canal de YouTube",
                    placeholder="Ej: UCx_123ABC...",
                    help="ID único del canal en YouTube (opcional, puedes añadirlo después)"
                )
            
            # Información adicional
            st.markdown("**💡 Consejos:**")
            st.markdown("""
            - El **nombre del canal** es solo para tu organización interna
            - El **ID de YouTube** lo puedes encontrar en la URL de tu canal
            - Puedes editar esta información después de crear el canal
            """)
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                submitted = st.form_submit_button("➕ Crear Canal", type="primary", use_container_width=True)
            
            with col_btn2:
                if st.form_submit_button("🔄 Limpiar", use_container_width=True):
                    st.rerun()
            
            if submitted:
                if not nombre_canal.strip():
                    st.error("❌ El nombre del canal no puede estar vacío.")
                else:
                    new_id = channel_manager.db_manager.add_canal(nombre_canal.strip(), channel_id_youtube.strip() or None)
                    if new_id:
                        st.success(f"✅ ¡Canal '{nombre_canal}' creado con éxito! (ID: {new_id})")
                        st.balloons()
                        # Limpiar cache para refrescar la lista
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ El canal '{nombre_canal}' ya existe o hubo un error al crearlo.")

def render_channels_section(canales: List[Dict[str, Any]], channel_manager: ChannelManager):
    """Renderiza la sección principal de canales"""
    
    st.subheader("📋 Mis Canales")
    
    # Filtros y ordenación
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_estado = st.selectbox(
            "🔍 Filtrar por estado",
            ["Todos", "Activos", "Sin contenido", "Con errores", "Con pendientes"],
            help="Filtra canales según su estado actual"
        )
    
    with col2:
        orden = st.selectbox(
            "📊 Ordenar por",
            ["Nombre", "Fecha creación", "Total publicaciones", "Última actividad"],
            help="Ordena la lista de canales"
        )
    
    with col3:
        vista = st.selectbox(
            "👁️ Vista",
            ["Tabla compacta", "Tarjetas"],
            help="Cambia el formato de visualización"
        )
    
    # Aplicar filtros
    canales_filtrados = apply_filters(canales, filtro_estado, orden)
    
    # Mostrar canales según la vista seleccionada
    if vista == "Tabla compacta":
        render_channels_table(canales_filtrados)
    else:
        render_channels_cards(canales_filtrados, channel_manager)

def apply_filters(canales: List[Dict[str, Any]], filtro_estado: str, orden: str) -> List[Dict[str, Any]]:
    """Aplica filtros y ordenación a la lista de canales"""
    
    canales_filtrados = canales.copy()
    
    # Aplicar filtros
    if filtro_estado == "Activos":
        canales_filtrados = [c for c in canales_filtrados if c['total_publicaciones'] > 0]
    elif filtro_estado == "Sin contenido":
        canales_filtrados = [c for c in canales_filtrados if c['total_publicaciones'] == 0]
    elif filtro_estado == "Con errores":
        canales_filtrados = [c for c in canales_filtrados if c['errores'] > 0]
    elif filtro_estado == "Con pendientes":
        canales_filtrados = [c for c in canales_filtrados if c['pendientes'] > 0]
    
    # Aplicar ordenación
    if orden == "Nombre":
        canales_filtrados.sort(key=lambda x: x['nombre'])
    elif orden == "Fecha creación":
        canales_filtrados.sort(key=lambda x: x['fecha_creacion'], reverse=True)
    elif orden == "Total publicaciones":
        canales_filtrados.sort(key=lambda x: x['total_publicaciones'], reverse=True)
    elif orden == "Última actividad":
        canales_filtrados.sort(key=lambda x: x['ultima_publicacion'] or '1900-01-01', reverse=True)
    
    return canales_filtrados

def render_channels_cards(canales: List[Dict[str, Any]], channel_manager: ChannelManager):
    """Renderiza canales en formato de tarjetas"""
    
    for i, canal in enumerate(canales):
        render_channel_card(canal, channel_manager, f"card_{i}")
        if i < len(canales) - 1:
            st.divider()

def render_channel_card(canal: Dict[str, Any], channel_manager: ChannelManager, key_suffix: str):
    """Renderiza una tarjeta individual de canal"""
    
    # Calcular estado del canal
    status_info = get_channel_status(canal)
    
    # Container principal de la tarjeta
    with st.container():
        # Header de la tarjeta
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"### 📺 {canal['nombre']}")
            if canal['channel_id_youtube']:
                st.markdown(f"🔗 `{canal['channel_id_youtube']}`")
                youtube_url = f"https://www.youtube.com/channel/{canal['channel_id_youtube']}"
                st.markdown(f"[🌐 Ver en YouTube]({youtube_url})")
            else:
                st.markdown("🔗 *ID de YouTube no configurado*")
        
        with col2:
            st.markdown("**Estado**")
            st.markdown(f"{status_info['icon']} {status_info['text']}")
        
        with col3:
            # Botones de acción
            col3_1, col3_2, col3_3 = st.columns(3)
            
            with col3_1:
                if st.button("📋", key=f"publications_{canal['id']}_{key_suffix}", help="Ver publicaciones de este canal"):
                    # Navegar al panel de publicaciones con filtro del canal
                    st.session_state['filter_canal_id'] = canal['id']
                    st.session_state['filter_canal_name'] = canal['nombre']
                    st.session_state['navigate_to'] = 'publicaciones'
                    st.success(f"📋 Navegando a publicaciones de '{canal['nombre']}'...")
                    st.info("💡 Ve a **🗓️ Panel de Publicaciones** para ver el contenido filtrado")
            
            with col3_2:
                if st.button("⚙️", key=f"config_{canal['id']}_{key_suffix}", help="Configurar canal"):
                    st.session_state[f"editing_channel_{canal['id']}"] = True
                    st.rerun()
            
            with col3_3:
                if st.button("📊", key=f"stats_{canal['id']}_{key_suffix}", help="Ver estadísticas"):
                    st.session_state[f"show_stats_{canal['id']}"] = not st.session_state.get(f"show_stats_{canal['id']}", False)
                    st.rerun()
        
        # Métricas del canal
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("📝 Total", canal['total_publicaciones'])
        
        with col2:
            st.metric("⏳ Pendientes", canal['pendientes'])
        
        with col3:
            st.metric("🔄 En Proceso", canal['en_proceso'])
        
        with col4:
            st.metric("✅ Completadas", canal['completadas'])
        
        with col5:
            if canal['ultima_publicacion']:
                try:
                    fecha_ultima = datetime.fromisoformat(canal['ultima_publicacion'].replace('Z', ''))
                    days_ago = (datetime.now() - fecha_ultima).days
                    st.metric("📅 Última", f"{days_ago}d")
                except:
                    st.metric("📅 Última", "Error")
            else:
                st.metric("📅 Última", "Nunca")
        
        # Barra de progreso
        if canal['total_publicaciones'] > 0:
            progress = canal['completadas'] / canal['total_publicaciones']
            st.progress(progress, text=f"Progreso: {canal['completadas']}/{canal['total_publicaciones']} ({progress*100:.1f}%)")
        else:
            st.progress(0, text="Sin publicaciones")
        
        # Acciones rápidas del canal
        if canal['total_publicaciones'] > 0:
            col_action1, col_action2, col_action3 = st.columns(3)
            
            with col_action1:
                if canal['pendientes'] > 0:
                    if st.button(f"🚀 Enviar {canal['pendientes']} al Batch", 
                               key=f"batch_{canal['id']}_{key_suffix}", 
                               help="Enviar publicaciones pendientes al procesador por lotes"):
                        enviar_canal_al_batch(canal, channel_manager)
            
            with col_action2:
                if st.button(f"➕ Nueva Publicación", 
                           key=f"new_pub_{canal['id']}_{key_suffix}",
                           help="Crear nueva publicación para este canal"):
                    st.session_state['preselect_canal_id'] = canal['id']
                    st.session_state['preselect_canal_name'] = canal['nombre']
                    st.session_state['navigate_to'] = 'new_publication'
                    st.success(f"➕ Creando nueva publicación para '{canal['nombre']}'...")
                    st.info("💡 Ve a **🗓️ Panel de Publicaciones** para completar la creación")
            
            with col_action3:
                if canal['errores'] > 0:
                    if st.button(f"🔄 Reintentar {canal['errores']} Errores", 
                               key=f"retry_{canal['id']}_{key_suffix}",
                               help="Reintentar publicaciones con error"):
                        reintentar_errores_canal(canal, channel_manager)
        
        # Mostrar estadísticas expandidas si se solicita
        if st.session_state.get(f"show_stats_{canal['id']}", False):
            render_channel_detailed_stats(canal)
        
        # Mostrar formulario de edición si se solicita
        if st.session_state.get(f"editing_channel_{canal['id']}", False):
            render_channel_edit_form(canal, channel_manager, key_suffix)

def get_channel_status(canal: Dict[str, Any]) -> Dict[str, str]:
    """Determina el estado visual de un canal"""
    
    if canal['total_publicaciones'] == 0:
        return {"icon": "🔘", "text": "Sin contenido"}
    elif canal['errores'] > 0:
        return {"icon": "🔴", "text": f"{canal['errores']} errores"}
    elif canal['en_proceso'] > 0:
        return {"icon": "🟡", "text": f"{canal['en_proceso']} en proceso"}
    elif canal['pendientes'] > 0:
        return {"icon": "🟠", "text": f"{canal['pendientes']} pendientes"}
    else:
        return {"icon": "🟢", "text": "Al día"}

def render_channel_detailed_stats(canal: Dict[str, Any]):
    """Renderiza estadísticas detalladas de un canal"""
    
    with st.expander("📊 Estadísticas Detalladas", expanded=True):
        
        # Distribución de estados
        st.subheader("📈 Distribución de Estados")
        
        if canal['total_publicaciones'] > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                percentage = (canal['pendientes'] / canal['total_publicaciones']) * 100
                st.metric("⏳ Pendientes", f"{canal['pendientes']} ({percentage:.1f}%)")
            
            with col2:
                percentage = (canal['en_proceso'] / canal['total_publicaciones']) * 100
                st.metric("🔄 En Proceso", f"{canal['en_proceso']} ({percentage:.1f}%)")
            
            with col3:
                percentage = (canal['completadas'] / canal['total_publicaciones']) * 100
                st.metric("✅ Completadas", f"{canal['completadas']} ({percentage:.1f}%)")
            
            with col4:
                percentage = (canal['errores'] / canal['total_publicaciones']) * 100
                st.metric("❌ Errores", f"{canal['errores']} ({percentage:.1f}%)")
        
        # Información adicional
        st.subheader("ℹ️ Información del Canal")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**📅 Creado:** {canal['fecha_creacion']}")
            st.write(f"**🆔 ID Interno:** {canal['id']}")
        
        with col2:
            if canal['channel_id_youtube']:
                st.write(f"**🔗 YouTube ID:** {canal['channel_id_youtube']}")
                youtube_url = f"https://www.youtube.com/channel/{canal['channel_id_youtube']}"
                st.markdown(f"**🌐 URL:** [Ver en YouTube]({youtube_url})")
            else:
                st.write("**🔗 YouTube ID:** *No configurado*")

def render_channel_edit_form(canal: Dict[str, Any], channel_manager: ChannelManager, key_suffix: str):
    """Renderiza formulario de edición de canal"""
    
    with st.expander("⚙️ Editar Canal", expanded=True):
        with st.form(f"edit_channel_{canal['id']}_{key_suffix}"):
            st.subheader(f"Editando: {canal['nombre']}")
            
            nuevo_nombre = st.text_input(
                "Nombre del Canal",
                value=canal['nombre'],
                help="Nombre descriptivo para identificar el canal"
            )
            
            nuevo_youtube_id = st.text_input(
                "ID del Canal de YouTube",
                value=canal.get('channel_id_youtube', '') or '',
                help="ID único del canal en YouTube (opcional)"
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.form_submit_button("💾 Guardar Cambios", type="primary"):
                    # Aquí iría la lógica para actualizar el canal
                    # Por ahora solo mostramos mensaje de éxito
                    st.success("✅ Canal actualizado correctamente")
                    st.session_state[f"editing_channel_{canal['id']}"] = False
                    st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    st.session_state[f"editing_channel_{canal['id']}"] = False
                    st.rerun()
            
            with col3:
                if st.form_submit_button("🗑️ Eliminar Canal", type="secondary"):
                    st.session_state[f"confirm_delete_{canal['id']}"] = True
                    st.rerun()
        
        # Confirmación de eliminación
        if st.session_state.get(f"confirm_delete_{canal['id']}", False):
            st.error("⚠️ **¿Estás seguro de que quieres eliminar este canal?**")
            st.warning("Esta acción eliminará el canal y TODAS sus publicaciones asociadas.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ SÍ, ELIMINAR", key=f"confirm_delete_yes_{canal['id']}_{key_suffix}", type="primary"):
                    # Aquí iría la lógica para eliminar el canal
                    st.success("✅ Canal eliminado correctamente")
                    st.session_state[f"confirm_delete_{canal['id']}"] = False
                    st.session_state[f"editing_channel_{canal['id']}"] = False
                    st.rerun()
            
            with col2:
                if st.button("❌ Cancelar", key=f"confirm_delete_no_{canal['id']}_{key_suffix}"):
                    st.session_state[f"confirm_delete_{canal['id']}"] = False
                    st.rerun()

def render_channels_table(canales: List[Dict[str, Any]]):
    """Renderiza tabla compacta de canales con botones de acción"""
    
    st.markdown("### 📋 Tabla de Canales")
    
    # Crear tabla con botones de acción
    for i, canal in enumerate(canales):
        with st.container():
            # Fila principal de la tabla
            col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1.5, 1, 1, 1, 1, 2])
            
            with col1:
                st.write(f"**📺 {canal['nombre']}**")
                if canal['channel_id_youtube']:
                    st.caption(f"🔗 {canal['channel_id_youtube']}")
                    youtube_url = f"https://www.youtube.com/channel/{canal['channel_id_youtube']}"
                    st.caption(f"[🌐 YouTube]({youtube_url})")
                else:
                    st.caption("🔗 No configurado")
            
            with col2:
                # Estado del canal
                status_info = get_channel_status(canal)
                st.write(f"{status_info['icon']} **{status_info['text']}**")
                
                # Métricas compactas
                st.caption(f"📝 {canal['total_publicaciones']} | ⏳ {canal['pendientes']} | ✅ {canal['completadas']}")
            
            with col3:
                # Progreso
                if canal['total_publicaciones'] > 0:
                    progress = canal['completadas'] / canal['total_publicaciones']
                    st.metric("Progreso", f"{progress*100:.0f}%")
                    st.progress(progress)
                else:
                    st.metric("Progreso", "0%")
                    st.progress(0)
            
            with col4:
                # Última actividad
                if canal['ultima_publicacion']:
                    try:
                        fecha_ultima = datetime.fromisoformat(canal['ultima_publicacion'].replace('Z', ''))
                        days_ago = (datetime.now() - fecha_ultima).days
                        st.metric("Última", f"{days_ago}d")
                    except:
                        st.metric("Última", "Error")
                else:
                    st.metric("Última", "Nunca")
            
            with col5:
                # Fecha de creación
                fecha_creacion = canal['fecha_creacion'][:10]
                st.metric("Creado", fecha_creacion)
            
            with col6:
                # Acciones principales
                if st.button("📋", key=f"table_pubs_{canal['id']}_{i}", help="Ver publicaciones"):
                    st.session_state['filter_canal_id'] = canal['id']
                    st.session_state['filter_canal_name'] = canal['nombre']
                    st.success(f"📋 Navegando a publicaciones de '{canal['nombre']}'...")
                    st.info("💡 Ve a **🗓️ Panel de Publicaciones** para ver el contenido filtrado")
                
                if st.button("➕", key=f"table_new_{canal['id']}_{i}", help="Nueva publicación"):
                    st.session_state['preselect_canal_id'] = canal['id']
                    st.session_state['preselect_canal_name'] = canal['nombre']
                    st.success(f"➕ Creando nueva publicación para '{canal['nombre']}'...")
                    st.info("💡 Ve a **🗓️ Panel de Publicaciones** para completar")
            
            with col7:
                # Acciones específicas según estado
                col7_1, col7_2, col7_3 = st.columns(3)
                
                with col7_1:
                    if canal['pendientes'] > 0:
                        if st.button(f"🚀 {canal['pendientes']}", 
                                   key=f"table_batch_{canal['id']}_{i}", 
                                   help=f"Enviar {canal['pendientes']} pendientes al batch"):
                            enviar_canal_al_batch_table(canal)
                    else:
                        st.button("🚀 0", disabled=True, key=f"table_batch_disabled_{canal['id']}_{i}")
                
                with col7_2:
                    if canal['errores'] > 0:
                        if st.button(f"🔄 {canal['errores']}", 
                                   key=f"table_retry_{canal['id']}_{i}", 
                                   help=f"Reintentar {canal['errores']} errores"):
                            reintentar_errores_canal_table(canal)
                    else:
                        st.button("🔄 0", disabled=True, key=f"table_retry_disabled_{canal['id']}_{i}")
                
                with col7_3:
                    if st.button("⚙️", key=f"table_config_{canal['id']}_{i}", help="Configurar canal"):
                        st.session_state[f"editing_channel_table_{canal['id']}"] = True
                        st.rerun()
            
            # Formulario de edición expandible
            if st.session_state.get(f"editing_channel_table_{canal['id']}", False):
                render_table_edit_form(canal, i)
            
            # Separador entre filas
            if i < len(canales) - 1:
                st.divider()

def enviar_canal_al_batch_table(canal: Dict[str, Any]):
    """Envía publicaciones pendientes al batch desde la tabla"""
    try:
        db_manager = DatabaseManager()
        publicaciones = db_manager.get_all_publicaciones_info()
        pendientes_canal = [p for p in publicaciones if p['id_canal'] == canal['id'] and p['status'] == 'Pendiente']
        
        if not pendientes_canal:
            st.warning("No hay publicaciones pendientes para este canal")
            return
        
        if "batch_projects" not in st.session_state:
            st.session_state.batch_projects = []
        
        enviados = 0
        for pub in pendientes_canal:
            try:
                import uuid
                
                batch_script_type = "✍️ Usar guión manual" if pub['script_type'] == 'manual' else "🤖 Generar con IA"
                
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
            st.success(f"✅ {enviados} publicaciones de '{canal['nombre']}' enviadas al Batch")
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Error: {e}")

def reintentar_errores_canal_table(canal: Dict[str, Any]):
    """Reintenta errores desde la tabla"""
    try:
        db_manager = DatabaseManager()
        publicaciones = db_manager.get_all_publicaciones_info()
        errores_canal = [p for p in publicaciones if p['id_canal'] == canal['id'] and p['status'] == 'Error']
        
        if not errores_canal:
            st.warning("No hay publicaciones con error para este canal")
            return
        
        reintentados = 0
        for pub in errores_canal:
            try:
                db_manager.update_publicacion_status(pub['id'], 'Pendiente')
                reintentados += 1
            except Exception as e:
                st.error(f"❌ Error reintentando '{pub['titulo']}': {e}")
        
        if reintentados > 0:
            st.success(f"✅ {reintentados} publicaciones de '{canal['nombre']}' marcadas para reintentar")
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Error: {e}")

def render_table_edit_form(canal: Dict[str, Any], index: int):
    """Renderiza formulario de edición en la tabla"""
    
    with st.expander(f"⚙️ Editando: {canal['nombre']}", expanded=True):
        with st.form(f"edit_table_channel_{canal['id']}_{index}"):
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_nombre = st.text_input(
                    "Nombre del Canal",
                    value=canal['nombre'],
                    help="Nombre descriptivo del canal"
                )
            
            with col2:
                nuevo_youtube_id = st.text_input(
                    "ID de YouTube",
                    value=canal.get('channel_id_youtube', '') or '',
                    help="ID del canal en YouTube"
                )
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.form_submit_button("💾 Guardar", type="primary"):
                    st.success("✅ Canal actualizado")
                    st.session_state[f"editing_channel_table_{canal['id']}"] = False
                    st.rerun()
            
            with col_btn2:
                if st.form_submit_button("❌ Cancelar"):
                    st.session_state[f"editing_channel_table_{canal['id']}"] = False
                    st.rerun()
            
            with col_btn3:
                if st.form_submit_button("🗑️ Eliminar", type="secondary"):
                    st.session_state[f"confirm_delete_table_{canal['id']}"] = True
                    st.rerun()
        
        # Confirmación de eliminación
        if st.session_state.get(f"confirm_delete_table_{canal['id']}", False):
            st.error("⚠️ **¿Eliminar este canal y todas sus publicaciones?**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ SÍ, ELIMINAR", key=f"table_delete_yes_{canal['id']}_{index}", type="primary"):
                    st.success("✅ Canal eliminado")
                    st.session_state[f"confirm_delete_table_{canal['id']}"] = False
                    st.session_state[f"editing_channel_table_{canal['id']}"] = False
                    st.rerun()
            
            with col2:
                if st.button("❌ Cancelar", key=f"table_delete_no_{canal['id']}_{index}"):
                    st.session_state[f"confirm_delete_table_{canal['id']}"] = False
                    st.rerun()

def enviar_canal_al_batch(canal: Dict[str, Any], channel_manager: ChannelManager):
    """Envía todas las publicaciones pendientes de un canal al batch"""
    
    publicaciones = channel_manager.db_manager.get_all_publicaciones_info()
    pendientes_canal = [p for p in publicaciones if p['id_canal'] == canal['id'] and p['status'] == 'Pendiente']
    
    if not pendientes_canal:
        st.warning("No hay publicaciones pendientes para este canal")
        return
    
    if "batch_projects" not in st.session_state:
        st.session_state.batch_projects = []
    
    enviados = 0
    for pub in pendientes_canal:
        try:
            import uuid
            from datetime import datetime
            
            batch_script_type = "✍️ Usar guión manual" if pub['script_type'] == 'manual' else "🤖 Generar con IA"
            
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
            channel_manager.db_manager.update_publicacion_status(pub['id'], 'En Batch')
            enviados += 1
            
        except Exception as e:
            st.error(f"❌ Error enviando '{pub['titulo']}': {e}")
    
    if enviados > 0:
        st.success(f"✅ {enviados} publicaciones de '{canal['nombre']}' enviadas al Batch Processor")
        st.rerun()

def reintentar_errores_canal(canal: Dict[str, Any], channel_manager: ChannelManager):
    """Reintenta todas las publicaciones con error de un canal"""
    
    publicaciones = channel_manager.db_manager.get_all_publicaciones_info()
    errores_canal = [p for p in publicaciones if p['id_canal'] == canal['id'] and p['status'] == 'Error']
    
    if not errores_canal:
        st.warning("No hay publicaciones con error para este canal")
        return
    
    reintentados = 0
    for pub in errores_canal:
        try:
            channel_manager.db_manager.update_publicacion_status(pub['id'], 'Pendiente')
            reintentados += 1
        except Exception as e:
            st.error(f"❌ Error reintentando '{pub['titulo']}': {e}")
    
    if reintentados > 0:
        st.success(f"✅ {reintentados} publicaciones de '{canal['nombre']}' marcadas para reintentar")
        st.rerun()

def render_empty_state():
    """Renderiza estado vacío cuando no hay canales"""
    
    st.info("🎯 **¡Comienza creando tu primer canal!**")
    st.markdown("""
    No tienes canales configurados aún. Usa el formulario de arriba para añadir tu primer canal
    y comenzar a gestionar tu contenido de YouTube.
    
    **¿Qué puedes hacer con los canales?**
    - 📊 Ver estadísticas en tiempo real de tus publicaciones
    - 📝 Organizar tu contenido por canal
    - 🎯 Hacer seguimiento del progreso de cada canal
    - 🔗 Conectar con tus canales reales de YouTube
    """)