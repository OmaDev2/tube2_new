import streamlit as st
import os
import uuid
from pathlib import Path
from datetime import datetime
import json
import math
import asyncio
from moviepy.editor import AudioFileClip

# Importar funciones necesarias
try:
    from utils.config import load_config
    from utils.ai_services import list_openai_models, list_gemini_models, list_ollama_models
    from pages.prompts_manager_page import list_prompts
    from pages.efectos_ui import show_effects_ui
    from pages.overlays_ui import show_overlays_ui
    from utils.subtitle_utils import get_available_fonts
    import edge_tts
except ImportError as e:
    st.error(f"Error importando dependencias: {e}")

def show_batch_processor():
    st.title("🚀 Procesador por Lotes de Videos")
    
    st.info("""
    **Automatiza completamente** la creación de videos desde título + contexto:
    
    📝 Guión → 🔊 Audio → 🎯 Transcripción → 🎬 Escenas → 🖼️ Imágenes → 🎥 Video → 📝 Subtítulos
    """)
    
    st.markdown("---")
    
    # Cargar configuración de la aplicación
    try:
        app_config = load_config()
    except:
        app_config = {"ai": {"default_models": {}}}
    
    # ===== SECCIÓN 1: GESTIÓN DE PROYECTOS =====
    st.header("1. 📋 Gestión de Proyectos por Lotes")
    
    # Añadir nuevos proyectos
    st.subheader("➕ Añadir Nuevo Proyecto")
    
    # Opción para elegir tipo de guión (fuera del formulario para que sea reactiva)
    script_type = st.radio(
        "📜 Tipo de guión:",
        ["🤖 Generar automáticamente con IA", "✍️ Usar guión manual"],
        index=1,  # Por defecto seleccionar guión manual
        help="Elige si quieres que la IA genere el guión o usar tu propio guión",
        key="script_type_selector"
    )
    
    with st.form("add_project"):
        col1, col2 = st.columns(2)
        
        with col1:
            titulo = st.text_input("📝 Título del proyecto", help="Ej: Cómo hacer pan casero")
            contexto = st.text_area("📖 Contexto/Descripción", help="Información adicional sobre el contenido del video")
        
        with col2:
            guion_manual = None
            if script_type == "✍️ Usar guión manual":
                guion_manual = st.text_area(
                    "📝 Escribe tu guión:",
                    height=100,
                    help="Escribe aquí el guión completo que quieres usar para el video",
                    placeholder="Ejemplo:\n\nHola y bienvenidos a mi canal...\n\nEn el video de hoy vamos a aprender...\n\n¡No olviden suscribirse!"
                )
            else:
                st.info("🤖 El guión se generará automáticamente con IA usando el título y contexto proporcionados.")
        
        if st.form_submit_button("✅ Añadir al Batch", use_container_width=True):
            if titulo and contexto:
                # Validar guión manual si es necesario
                if script_type == "✍️ Usar guión manual" and not guion_manual:
                    st.error("⚠️ Por favor, escribe el guión manual.")
                else:
                    if "batch_projects" not in st.session_state:
                        st.session_state.batch_projects = []
                    
                    nuevo_proyecto = {
                        "titulo": titulo,
                        "contexto": contexto,
                        "script_type": script_type,
                        "guion_manual": guion_manual if script_type == "✍️ Usar guión manual" else None,
                        "id": str(uuid.uuid4())[:8],
                        "fecha_añadido": datetime.now().isoformat()
                    }
                    
                    st.session_state.batch_projects.append(nuevo_proyecto)
                    script_info = "con guión manual" if script_type == "✍️ Usar guión manual" else "con IA"
                    st.success(f"✅ Proyecto '{titulo}' añadido al batch {script_info}!")
                    st.rerun()
            else:
                st.error("⚠️ Por favor, completa el título y contexto.")
    
    # Mostrar proyectos existentes
    if "batch_projects" in st.session_state and st.session_state.batch_projects:
        st.subheader(f"📊 Proyectos en cola ({len(st.session_state.batch_projects)})")
        
        # Mostrar cada proyecto
        for i, proyecto in enumerate(st.session_state.batch_projects):
            # Icono según el tipo de guión
            icon = "✍️" if proyecto.get("script_type") == "✍️ Usar guión manual" else "🤖"
            script_label = "Manual" if proyecto.get("script_type") == "✍️ Usar guión manual" else "IA"
            
            # Detectar si viene del CMS
            is_from_cms = "cms_publicacion_id" in proyecto
            cms_icon = " 📚" if is_from_cms else ""
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"{icon} **{proyecto['titulo']}** ({script_label}){cms_icon}")
                if is_from_cms:
                    st.caption(f"📺 **Canal:** {proyecto.get('cms_canal', 'N/A')} | 🆔 **Pub ID:** {proyecto.get('cms_publicacion_id')}")
                st.caption(f"📖 {proyecto['contexto'][:100]}{'...' if len(proyecto['contexto']) > 100 else ''}")
                
                # Mostrar preview del guión manual si existe
                if proyecto.get("guion_manual"):
                    if st.button("👀 Ver/Ocultar Guión", key=f"toggle_script_{proyecto['id']}"):
                        show_key = f"show_script_{proyecto['id']}"
                        st.session_state[show_key] = not st.session_state.get(show_key, False)
                    
                    if st.session_state.get(f"show_script_{proyecto['id']}", False):
                        st.text_area(
                            "📝 Guión completo:",
                            value=proyecto["guion_manual"],
                            height=100,
                            disabled=True,
                            key=f"preview_script_{proyecto['id']}"
                        )
            
            with col2:
                if st.button("✏️ Editar", key=f"edit_{proyecto['id']}"):
                    st.session_state[f"editing_{proyecto['id']}"] = True
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Eliminar", key=f"delete_{proyecto['id']}"):
                    st.session_state.batch_projects.pop(i)
                    st.success(f"✅ Proyecto '{proyecto['titulo']}' eliminado!")
                    st.rerun()
            
            # Formulario de edición inline
            if st.session_state.get(f"editing_{proyecto['id']}", False):
                st.markdown("---")
                with st.form(f"edit_project_{proyecto['id']}"):
                    st.subheader("✏️ Editar Proyecto")
                    
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        nuevo_titulo = st.text_input("Título", value=proyecto['titulo'])
                        nuevo_contexto = st.text_area("Contexto", value=proyecto['contexto'])
                    
                    with edit_col2:
                        nuevo_script_type = st.radio(
                            "Tipo de guión:",
                            ["🤖 Generar automáticamente con IA", "✍️ Usar guión manual"],
                            index=1 if proyecto.get("script_type") == "✍️ Usar guión manual" else 0
                        )
                        
                        nuevo_guion_manual = None
                        if nuevo_script_type == "✍️ Usar guión manual":
                            nuevo_guion_manual = st.text_area(
                                "Guión manual:",
                                value=proyecto.get("guion_manual", ""),
                                height=100
                            )
                    
                    col_edit1, col_edit2 = st.columns(2)
                    with col_edit1:
                        if st.form_submit_button("💾 Guardar cambios"):
                            proyecto.update({
                                "titulo": nuevo_titulo,
                                "contexto": nuevo_contexto,
                                "script_type": nuevo_script_type,
                                "guion_manual": nuevo_guion_manual if nuevo_script_type == "✍️ Usar guión manual" else None
                            })
                            st.session_state[f"editing_{proyecto['id']}"] = False
                            st.success("✅ Proyecto actualizado!")
                            st.rerun()
                    
                    with col_edit2:
                        if st.form_submit_button("❌ Cancelar"):
                            st.session_state[f"editing_{proyecto['id']}"] = False
                            st.rerun()
            
            st.markdown("---")
        
        # Botón para limpiar todos los proyectos
        if st.button("🧹 Limpiar toda la cola", type="secondary"):
            st.session_state.batch_projects = []
            st.success("✅ Cola de proyectos limpiada!")
            st.rerun()
    else:
        st.info("📝 No hay proyectos en la cola. Añade algunos proyectos para comenzar.")
    
    st.markdown("---")
    
    # ===== SECCIÓN 2: RE-PROCESAR PROYECTOS EXISTENTES =====
    st.header("2. 🔧 Re-procesar o Reparar Proyecto Existente")
    
    # Función para obtener la lista de proyectos existentes
    def get_existing_projects(projects_dir="projects"):
        projects_path = Path(projects_dir)
        if not projects_path.exists():
            return []
        return [d.name for d in projects_path.iterdir() if d.is_dir() and (d / "project_info.json").exists()]
    
    # Obtener la lista de proyectos
    projects_dir = app_config.get("video_generation", {}).get("paths", {}).get("projects_dir", "projects")
    existing_projects = get_existing_projects(projects_dir)
    
    if not existing_projects:
        st.warning("📁 No se encontraron proyectos existentes para re-procesar.")
    else:
        # Crear un selector para que el usuario elija el proyecto
        selected_project_id = st.selectbox(
            "🎯 Selecciona un proyecto para re-procesar",
            options=existing_projects,
            index=None,
            placeholder="Elige un proyecto...",
            help="Selecciona un proyecto existente para reanudar su procesamiento desde donde se quedó"
        )
        
        if selected_project_id:
            # Cargar información del proyecto seleccionado
            project_dir = Path(projects_dir) / selected_project_id
            project_info_path = project_dir / "project_info.json"
            
            try:
                with open(project_info_path, 'r', encoding='utf-8') as f:
                    project_info = json.load(f)
                
                # Mostrar información del proyecto
                st.subheader(f"📋 Información del Proyecto: {selected_project_id}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Título:** {project_info.get('title', 'N/A')}")
                    st.write(f"**Estado:** {project_info.get('status', 'N/A')}")
                    st.write(f"**Fecha:** {project_info.get('created_at', 'N/A')}")
                
                with col2:
                    st.write(f"**Duración Audio:** {project_info.get('audio_duration', 0):.1f}s")
                    st.write(f"**Imágenes:** {len(project_info.get('image_paths', []))}")
                    st.write(f"**Escenas:** {len(project_info.get('scenes', [])) if project_info.get('scenes') else 'N/A'}")
                
                # Mostrar estado detallado
                status = project_info.get('status', 'unknown')
                status_icon = {
                    'script_ok': '📝',
                    'audio_ok': '🔊', 
                    'transcription_ok': '🎯',
                    'scenes_ok': '🎬',
                    'images_ok': '🖼️',
                    'video_ok': '🎥',
                    'error_en_transcription_ok': '⚠️',
                    'unknown': '❓'
                }.get(status, '❓')
                
                st.info(f"{status_icon} **Estado actual:** {status}")
                
                # Mostrar error si existe
                if project_info.get('error'):
                    st.error(f"❌ **Error anterior:** {project_info['error']}")
                
                # Botón de re-procesamiento
                if st.button(f"🚀 Reanudar Procesamiento", type="primary", use_container_width=True):
                    with st.spinner(f"🔄 Reanudando el procesamiento para {selected_project_id}..."):
                        try:
                            # Importar el procesador de video
                            from utils.video_processing import VideoProcessor
                            
                            # Crear la instancia del procesador
                            video_processor = VideoProcessor(config=app_config)
                            
                            # Obtener la configuración completa de la UI
                            full_config = get_full_config_from_ui(app_config)
                            
                            # Reanudar el procesamiento
                            final_video_path = video_processor.process_single_video(
                                full_config=full_config,
                                existing_project_info=project_info
                            )
                            
                            if final_video_path and final_video_path.exists():
                                st.success(f"✅ ¡Proyecto '{selected_project_id}' completado exitosamente!")
                                st.video(str(final_video_path))
                                
                                # Mostrar información del video final
                                st.info(f"📁 **Video guardado en:** {final_video_path}")
                                st.info(f"⏱️ **Duración:** {project_info.get('audio_duration', 0):.1f} segundos")
                            else:
                                st.error(f"❌ El procesamiento para '{selected_project_id}' falló. Revisa los logs.")
                                
                        except Exception as e:
                            st.error(f"❌ Ocurrió un error crítico al re-procesar: {e}")
                            st.exception(e)
                
                # Botón para ver el video existente si existe
                video_path = project_dir / "video" / f"{selected_project_id}_final_subtitled.mp4"
                if video_path.exists():
                    st.subheader("🎥 Video Actual")
                    st.video(str(video_path))
                    
                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        if st.button("📁 Abrir carpeta del proyecto", key=f"open_folder_{selected_project_id}"):
                            import subprocess
                            try:
                                subprocess.run(["open", str(project_dir)])
                                st.success("📁 Carpeta abierta!")
                            except:
                                st.info(f"📁 Ruta del proyecto: {project_dir}")
                    
                    with col_v2:
                        if st.button("🗑️ Eliminar proyecto", key=f"delete_project_{selected_project_id}", type="secondary"):
                            st.warning("⚠️ Esta acción eliminará completamente el proyecto y todos sus archivos.")
                            if st.button("✅ Confirmar eliminación", key=f"confirm_delete_{selected_project_id}", type="primary"):
                                import shutil
                                try:
                                    shutil.rmtree(project_dir)
                                    st.success(f"✅ Proyecto '{selected_project_id}' eliminado!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error al eliminar: {e}")
                
            except Exception as e:
                st.error(f"❌ Error al cargar el proyecto: {e}")
    
    st.markdown("---")
    
    # ===== SECCIÓN 2: CONFIGURACIÓN DE INTELIGENCIA ARTIFICIAL =====
    st.header("2. 🤖 Configuración de Inteligencia Artificial")
    
    with st.expander("🤖 Opciones de IA", expanded=True):
        # Verificar si hay proyectos que necesitan IA para guiones
        proyectos_con_ia = [p for p in st.session_state.get("batch_projects", []) if p.get("script_type") != "✍️ Usar guión manual"]
        
        col1, col2 = st.columns(2)
        
        # CONFIGURACIÓN DE GUIONES
        with col1:
            st.subheader("📝 Generación de Guiones")
            if proyectos_con_ia:
                st.info(f"📊 {len(proyectos_con_ia)} proyecto(s) usarán IA para generar guión.")
                
                script_provider = st.selectbox(
                    "Proveedor de IA para Guiones", 
                    ["OpenAI", "Gemini", "Ollama"], 
                    key="batch_script_provider"
                )
                
                if script_provider == "OpenAI":
                    script_model = st.selectbox("Modelo OpenAI", ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"], key="batch_script_model")
                elif script_provider == "Gemini":
                    script_model = st.selectbox("Modelo Gemini", ["gemini-pro", "gemini-pro-vision"], key="batch_script_model")
                else:
                    script_model = st.text_input("Modelo Ollama", "llama2", key="batch_script_model")
                
                try:
                    prompts_guion_list = list_prompts("guion")
                    prompt_guion_names = [p.get("nombre", f"Prompt Inválido {i}") for i, p in enumerate(prompts_guion_list)]
                    default_script_prompt_name = "Guion Básico (Default)"
                    default_script_index = prompt_guion_names.index(default_script_prompt_name) if default_script_prompt_name in prompt_guion_names else 0
                    selected_prompt_guion_name = st.selectbox("Plantilla de Guión", prompt_guion_names, index=default_script_index, key="batch_script_prompt")
                    script_prompt_obj = next((p for p in prompts_guion_list if p.get("nombre") == selected_prompt_guion_name), None)
                except Exception as e:
                    st.warning(f"No se pudieron cargar los prompts de guión: {e}")
                    script_prompt_obj = None
            else:
                script_provider, script_model, script_prompt_obj = "OpenAI", "gpt-3.5-turbo", None
                st.info("ℹ️ Todos los proyectos usan guión manual.")
        
        # CONFIGURACIÓN DE PROMPTS DE IMAGEN
        with col2:
            st.subheader("🖼️ Generación de Prompts de Imagen")
            
            # Inicializar img_style
            img_style = ""
            
            img_prompt_provider = st.selectbox(
                "Proveedor para Prompts de Imagen", 
                ["gemini", "openai", "ollama"], 
                index=0, 
                key="batch_img_prompt_provider"
            )
            
            if img_prompt_provider == "gemini":
                default_gemini_model = app_config.get('ai', {}).get('default_models', {}).get('image_prompt_generation', 'models/gemini-1.5-flash-latest')
                gemini_models = [
                    "models/gemini-1.5-flash-latest",
                    "models/gemini-1.5-pro-latest", 
                    "models/gemini-2.5-flash-lite-preview-06-17",
                    "gemini-pro",
                    "gemini-pro-vision"
                ]
                default_index = gemini_models.index(default_gemini_model) if default_gemini_model in gemini_models else 0
                img_prompt_model = st.selectbox("Modelo Gemini", gemini_models, index=default_index, key="batch_img_prompt_model")
            elif img_prompt_provider == "openai":
                default_openai_model = app_config.get('ai', {}).get('default_models', {}).get('openai', 'gpt-4o-mini')
                openai_models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o-mini"]
                default_index = openai_models.index(default_openai_model) if default_openai_model in openai_models else 0
                img_prompt_model = st.selectbox("Modelo OpenAI", openai_models, index=default_index, key="batch_img_prompt_model")
            else:
                default_ollama_model = app_config.get('ai', {}).get('default_models', {}).get('ollama', 'llama3')
                img_prompt_model = st.text_input("Modelo Ollama", default_ollama_model, key="batch_img_prompt_model")
            
            try:
                prompts_img_list = list_prompts("imagenes")
                prompt_img_names = [p.get("nombre", f"Prompt Inválido {i}") for i, p in enumerate(prompts_img_list)]
                default_img_prompt_name = "Escenas Fotorrealistas Históricamente Precisas"
                default_img_index = prompt_img_names.index(default_img_prompt_name) if default_img_prompt_name in prompt_img_names else 0
                selected_prompt_img_name = st.selectbox("Plantilla de Imágenes", prompt_img_names, index=default_img_index, key="batch_image_prompt")
                img_prompt_obj = next((p for p in prompts_img_list if p.get("nombre") == selected_prompt_img_name), None)
                
                # 🏛️ CONFIGURACIÓN ESPECIAL PARA PROMPT HISTÓRICO
                if selected_prompt_img_name == "Escenas Fotorrealistas Históricamente Precisas":
                    st.markdown("---")
                    st.subheader("🏛️ Configuración Histórica")
                    st.info("💡 Este prompt requiere información histórica específica para generar imágenes precisas")
                    
                    # Opción de configuración
                    config_mode = st.radio(
                        "¿Cómo quieres configurar el contexto histórico?",
                        ["🤖 Generar automáticamente con IA", "✍️ Configurar manualmente"],
                        key="batch_historical_config_mode",
                        help="IA analizará el título/contexto para extraer información histórica, o puedes configurarla manualmente"
                    )
                    
                    if config_mode == "✍️ Configurar manualmente":
                        col_hist1, col_hist2 = st.columns(2)
                        with col_hist1:
                            periodo_historico = st.text_input(
                                "📅 Período Histórico",
                                placeholder="Ej: Siglo IV d.C., Imperio Romano tardío",
                                key="batch_periodo_historico",
                                help="Especifica la época exacta con fechas aproximadas"
                            )
                            ubicacion = st.text_input(
                                "🌍 Ubicación Geográfica", 
                                placeholder="Ej: Sebastea, Armenia histórica",
                                key="batch_ubicacion",
                                help="Región, ciudad o área geográfica específica"
                            )
                        with col_hist2:
                            contexto_cultural = st.text_area(
                                "🏛️ Contexto Cultural",
                                placeholder="Ej: Cristianismo primitivo bajo persecución...",
                                key="batch_contexto_cultural",
                                help="Contexto religioso, político, social de la época",
                                height=100
                            )
                        
                        # Guardar configuración manual
                        historical_config = {
                            "mode": "manual",
                            "periodo_historico": periodo_historico,
                            "ubicacion": ubicacion, 
                            "contexto_cultural": contexto_cultural
                        }
                    else:
                        st.success("🤖 La IA analizará automáticamente cada proyecto para extraer:")
                        st.write("• 📅 Período histórico exacto")
                        st.write("• 🌍 Ubicación geográfica")
                        st.write("• 🏛️ Contexto cultural específico")
                        
                        # Configuración del LLM para análisis histórico
                        st.markdown("**🤖 Configuración del LLM para Análisis Histórico:**")
                        col_hist_ai1, col_hist_ai2 = st.columns(2)
                        
                        with col_hist_ai1:
                            from utils.ai_services import get_available_providers_info
                            providers_info = get_available_providers_info()
                            available_providers = [name for name, info in providers_info.items() if info['configured']]
                            
                            if available_providers:
                                provider_display_names = {
                                    'openai': 'OpenAI',
                                    'gemini': 'Google Gemini',
                                    'ollama': 'Ollama (Local)'
                                }
                                
                                # Obtener configuración por defecto desde config.yaml
                                historical_config = app_config.get('video_generation', {}).get('historical_analysis', {})
                                config_default_provider = historical_config.get('default_provider', 'gemini')
                                
                                # Usar configuración del config.yaml si está disponible, sino priorizar Gemini
                                default_provider_index = 0
                                if config_default_provider in available_providers:
                                    default_provider_index = available_providers.index(config_default_provider)
                                elif 'gemini' in available_providers:
                                    default_provider_index = available_providers.index('gemini')
                                
                                historical_ai_provider = st.selectbox(
                                    "Proveedor IA", 
                                    available_providers,
                                    index=default_provider_index,
                                    key="batch_historical_ai_provider",
                                    format_func=lambda x: provider_display_names.get(x, x.title())
                                )
                            else:
                                st.error("❌ No hay proveedores de IA configurados")
                                historical_ai_provider = "gemini"  # Fallback
                        
                        with col_hist_ai2:
                            # Modelos según el proveedor seleccionado
                            if available_providers and historical_ai_provider in providers_info:
                                available_models = providers_info[historical_ai_provider]['models']
                                
                                # Configurar modelo por defecto según el proveedor
                                default_model_index = 0
                                
                                # Primero intentar usar configuración específica de análisis histórico
                                historical_config = app_config.get('video_generation', {}).get('historical_analysis', {})
                                config_default_model = historical_config.get('default_model', '')
                                
                                if config_default_model and config_default_model in available_models:
                                    default_model_index = available_models.index(config_default_model)
                                else:
                                    # Fallback a configuración general por proveedor
                                    if historical_ai_provider == 'gemini':
                                        default_gemini_model = app_config.get('ai', {}).get('default_models', {}).get('gemini', 'models/gemini-1.5-flash-latest')
                                        if default_gemini_model in available_models:
                                            default_model_index = available_models.index(default_gemini_model)
                                    elif historical_ai_provider == 'openai':
                                        default_openai_model = app_config.get('ai', {}).get('default_models', {}).get('openai', 'gpt-4o-mini')
                                        if default_openai_model in available_models:
                                            default_model_index = available_models.index(default_openai_model)
                                    elif historical_ai_provider == 'ollama':
                                        default_ollama_model = app_config.get('ai', {}).get('default_models', {}).get('ollama', 'llama3')
                                        if default_ollama_model in available_models:
                                            default_model_index = available_models.index(default_ollama_model)
                                
                                historical_ai_model = st.selectbox(
                                    "Modelo", 
                                    available_models, 
                                    index=default_model_index,
                                    key="batch_historical_ai_model"
                                )
                            else:
                                default_gemini_model = app_config.get('ai', {}).get('default_models', {}).get('gemini', 'models/gemini-1.5-flash-latest')
                                historical_ai_model = default_gemini_model  # Fallback
                        
                        # Configuración automática con LLM seleccionado
                        historical_config = {
                            "mode": "auto",
                            "ai_provider": historical_ai_provider,
                            "ai_model": historical_ai_model
                        }
                    
                    # Guardar en session_state para usar después
                    st.session_state["batch_historical_config"] = historical_config
                else:
                    # Limpiar configuración histórica si no se usa el prompt histórico
                    if "batch_historical_config" in st.session_state:
                        del st.session_state["batch_historical_config"]
                        
            except Exception as e:
                st.warning(f"No se pudieron cargar los prompts de imágenes: {e}")
                img_prompt_obj = None
            
            # Configuración de estilo (movida aquí para mayor coherencia)
            st.markdown("---")
            st.subheader("🎨 Configuración de Estilo para {style}")
            
            # Verificar si la plantilla seleccionada usa la variable {style}
            template_uses_style = False
            if img_prompt_obj and 'style' in img_prompt_obj.get('variables', []):
                template_uses_style = True
            
            if template_uses_style:
                st.info("💡 **La plantilla seleccionada usa la variable `{style}`. Configura qué estilo aplicar:**")
                
                # Importar estilos desde el gestor de prompts para consistencia
                from pages.prompts_manager_page import get_style_options
                
                # Estilos predefinidos (sincronizados con el gestor)
                style_options_from_manager = get_style_options()
                style_options = {
                    "sin_estilo": "Usar el estilo definido en la plantilla (no aplicar {style})",
                    **style_options_from_manager,
                    "personalizado": "Escribir estilo personalizado..."
                }
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    style_preset = st.selectbox(
                        "Aplicar Estilo",
                        options=list(style_options.keys()),
                        format_func=lambda x: "Sin estilo adicional" if x == "sin_estilo" else "Personalizado" if x == "personalizado" else x.title(),
                        key="batch_style_preset",
                        help="Solo disponible si la plantilla usa {style}"
                    )
                
                with col2:
                    if style_preset == "sin_estilo":
                        img_style = ""  # No aplicar estilo
                        st.info("✨ Se usará solo el estilo definido en la plantilla")
                    elif style_preset == "personalizado":
                        img_style = st.text_input(
                            "Estilo Personalizado",
                            value="cinematic, high detail, professional photography",
                            key="batch_img_style"
                        )
                    else:
                        img_style = st.text_input(
                            "Estilo para Variable {style}",
                            value=style_options[style_preset],
                            key="batch_img_style",
                            help="Este texto reemplazará {style} en la plantilla"
                        )
            else:
                st.success("✅ **La plantilla seleccionada ya define su propio estilo.** No necesitas configurar nada más.")
                img_style = ""  # No hay variable {style} en la plantilla
        
        # CONFIGURACIÓN DE OPTIMIZACIÓN YOUTUBE (CONSOLIDADA AQUÍ)
        st.markdown("---")
        st.subheader("🎯 Optimización para YouTube")
        
        optimization_config = {}
        optimization_config['generate_optimized_content'] = st.checkbox(
            "Generar contenido optimizado para TODOS los videos", 
            value=True, 
            key="batch_optimize_content",
            help="Genera títulos alternativos, descripción SEO, tags relevantes y capítulos con timestamps para cada video"
        )
        
        if optimization_config['generate_optimized_content']:
            st.info("💡 Se generarán archivos `content_optimization.txt` y `youtube_metadata.json` en cada carpeta de proyecto")
            
            # Configuración del LLM para optimización (en la misma sección)
            from utils.ai_services import get_available_providers_info
            providers_info = get_available_providers_info()
            available_providers = [name for name, info in providers_info.items() if info['configured']]
            
            if available_providers:
                col_opt1, col_opt2, col_opt3 = st.columns(3)
                
                with col_opt1:
                    provider_display_names = {
                        'openai': 'OpenAI',
                        'gemini': 'Google Gemini',
                        'ollama': 'Ollama (Local)'
                    }
                    
                    # Priorizar Gemini si está disponible
                    default_provider_index = 0
                    if 'gemini' in available_providers:
                        default_provider_index = available_providers.index('gemini')
                    
                    optimization_config['optimization_provider'] = st.selectbox(
                        "Proveedor IA para Optimización", 
                        available_providers,
                        index=default_provider_index,
                        key="batch_opt_provider",
                        format_func=lambda x: provider_display_names.get(x, x.title())
                    )
                
                with col_opt2:
                    # Modelos según el proveedor seleccionado
                    selected_provider = optimization_config['optimization_provider']
                    if selected_provider in providers_info:
                        available_models = providers_info[selected_provider]['models']
                        
                        # Configurar modelo por defecto según el proveedor
                        default_model_index = 0
                        if selected_provider == 'gemini':
                            default_gemini_model = app_config.get('ai', {}).get('default_models', {}).get('gemini', 'models/gemini-1.5-flash-latest')
                            if default_gemini_model in available_models:
                                default_model_index = available_models.index(default_gemini_model)
                        
                        optimization_config['optimization_model'] = st.selectbox(
                            "Modelo", 
                            available_models, 
                            index=default_model_index,
                            key="batch_opt_model"
                        )
                    else:
                        default_openai_model = app_config.get('ai', {}).get('default_models', {}).get('openai', 'gpt-4o-mini')
                        optimization_config['optimization_model'] = default_openai_model  # Fallback
                
                with col_opt3:
                    optimization_config['use_same_style'] = st.checkbox(
                        "Estilo consistente", 
                        value=True,
                        key="batch_opt_consistent",
                        help="Mantener un estilo similar en títulos y descripciones entre videos"
                    )
                    optimization_config['generate_series_tags'] = st.checkbox(
                        "Tags de serie", 
                        value=True,
                        key="batch_opt_series",
                        help="Añadir tags que conecten todos los videos como una serie"
                    )
            else:
                st.warning("⚠️ **No hay proveedores de IA configurados**")
                st.info("Ve a la página de **Configuración** para configurar al menos un proveedor (OpenAI, Gemini o Ollama)")
                default_provider = app_config.get('ai', {}).get('default_models', {}).get('openai', 'gpt-4o-mini')
                optimization_config['optimization_provider'] = 'openai'  # Fallback
                optimization_config['optimization_model'] = default_provider  # Fallback
    
    # Función para obtener la configuración completa de la UI
    def get_full_config_from_ui(app_config):
        """Recolecta toda la configuración de la UI para el procesamiento"""
        full_config = {
            "ai": app_config.get("ai", {}),
            "tts": app_config.get("tts", {}),
            "transcription": app_config.get("transcription", {}),
            "image": app_config.get("image", {}),
            "video": app_config.get("video", {}),
            "audio": app_config.get("audio", {}),
            "subtitles": app_config.get("subtitles", {}),
            "scenes_config": app_config.get("scenes_config", {}),
            "effects": app_config.get("effects", {}),
            "overlays": app_config.get("overlays", {})
        }
        return full_config
    
    # ===== SECCIÓN 3: CONFIGURACIÓN DE CONTENIDO =====
    st.header("3. 🎬 Configuración de Contenido")
    
    # ESCENAS - CONSOLIDADO (Segmentación + Duración)
    with st.expander("🎬 Configuración de Escenas", expanded=True):
        st.subheader("📑 Segmentación de Escenas")
        segmentation_mode = st.selectbox(
            "Método de Segmentación",
            ["Por Párrafos (Híbrido)", "Por Duración (Basado en Audio)", "Automático (Texto)"],
            index=0,
            key="batch_segmentation_mode",
            help="• Por Párrafos (Híbrido): Alinea párrafos del guion con el audio (Recomendado).\n• Por Duración: Agrupa palabras del audio para alcanzar una duración fija.\n• Automático: Divide el texto por párrafos/caracteres."
        )
        
        st.markdown("---")
        st.subheader("⏱️ Duración de Escenas")
        
        max_scene_duration = st.slider(
            "Duración Máxima por Escena (s)",
            min_value=5.0,
            max_value=25.0,
            value=12.0,
            step=0.5,
            key="batch_max_scene_duration",
            help="Define el tiempo máximo para una escena antes de que se subdivida automáticamente. Afecta principalmente a la segmentación 'Híbrida'."
        )

        # Mostrar información contextual según el método de segmentación
        if segmentation_mode == "Por Duración (Basado en Audio)":
            st.info("💡 Con segmentación por duración, se recomienda usar duración automática para consistencia.")
        elif segmentation_mode == "Por Párrafos (Híbrido)":
            st.info("💡 Con segmentación híbrida, la duración automática se adapta mejor al contenido de cada párrafo.")
        
        col1, col2 = st.columns(2)
        with col1:
            use_auto_duration = st.checkbox(
                "Duración automática basada en audio",
                value=True,
                help="Calcular duración por imagen según el audio transcrito. Es la opción recomendada.",
                key="batch_use_auto_duration"
            )
        with col2:
            duration_per_image = st.slider(
                "Duración manual por imagen (s)",
                min_value=1.0,
                max_value=15.0,
                value=10.0,
                step=0.5,
                key="batch_duration_manual",
                disabled=use_auto_duration,
                help="Establece una duración fija para cada imagen si la duración automática está desactivada."
            )
    
    # CONFIGURACIÓN DE IMÁGENES (CONSOLIDADA)
    with st.expander("🖼️ Configuración de Imágenes", expanded=True):
        st.info("Actualmente configurado para usar Replicate (flux-schnell).")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            img_aspect_ratio = st.selectbox("Aspect Ratio", ["16:9", "1:1", "9:16"], index=0, key="batch_img_aspect")
        with col2:
            img_output_format = st.selectbox("Formato", ["webp", "png", "jpeg"], index=0, key="batch_img_format")
        with col3:
            img_output_quality = st.slider("Calidad", 50, 100, 85, 5, key="batch_img_quality")
        with col4:
            img_megapixels = st.select_slider("Megapixels", ["1", "2", "4"], value="1", key="batch_img_mp")
        
        # Configuración movida a la sección de IA
    
    # CONFIGURACIÓN DE VIDEO (Transiciones y Efectos)
    with st.expander("🎥 Transiciones y Efectos de Video", expanded=True):
        # Transiciones y Fades
        st.subheader("🔄 Transiciones y Fades")
        col1, col2, col3 = st.columns(3)
        with col1:
            from utils.transitions import TransitionEffect
            transition_type = st.selectbox(
                "Tipo de transición",
                options=TransitionEffect.get_available_transitions(),
                format_func=lambda x: "Sin transición" if x == "none" else "Disolución" if x == "dissolve" else x.replace('_', ' ').title(),
                index=1,
                key="batch_transition_type"
            )
        with col2:
            transition_duration = st.slider(
                "Duración de transición (s)", 0.0, 5.0, 1.0, 0.1, key="batch_transition_duration"
            )
        with col3:
            fade_in_duration = st.slider(
                "Fade In (s)", 0.0, 5.0, 1.0, 0.1, key="batch_fade_in"
            )
            fade_out_duration = st.slider(
                "Fade Out (s)", 0.0, 5.0, 1.0, 0.1, key="batch_fade_out"
            )

    # EFECTOS Y OVERLAYS
    with st.expander("✨ Efectos y Overlays", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("✨ Efectos Visuales")
            try:
                effects_sequence = show_effects_ui(key_prefix="batch_")
            except Exception as e:
                st.warning(f"⚠️ La interfaz de efectos no está disponible ({e}). Se usará configuración básica.")
                effects_sequence = []
        
        with col2:
            st.subheader("🖼️ Superposiciones (Overlays)")
            try:
                overlay_sequence = show_overlays_ui(key_prefix="batch_")
            except Exception as e:
                st.warning(f"⚠️ La interfaz de overlays no está disponible ({e}). Se usará configuración básica.")
                overlay_sequence = []
        
        # Configuración avanzada de efectos para batch
        st.markdown("---")
        st.subheader("⚙️ Configuración Avanzada para Lotes")
        col1, col2 = st.columns(2)
        with col1:
            randomize_effects = st.checkbox(
                "🎲 Randomizar efectos entre proyectos",
                help="Cada proyecto tendrá efectos ligeramente diferentes",
                key="batch_randomize_effects"
            )
            if randomize_effects:
                effect_variation = st.slider(
                    "Variación de efectos", 0.1, 0.5, 0.2, 0.1, key="batch_effect_variation"
                )
        with col2:
            vary_intensity = st.checkbox(
                "📊 Variar intensidad por proyecto",
                help="La intensidad de efectos aumentará gradualmente",
                key="batch_vary_intensity"
            )
            if vary_intensity:
                intensity_range = st.slider(
                    "Rango de intensidad", 0.5, 2.0, (0.8, 1.5), key="batch_intensity_range"
                )

    # Construir el diccionario de configuración de video
    video_config = {
        'use_auto_duration': use_auto_duration,
        'duration_per_image_manual': duration_per_image if not use_auto_duration else 10.0,
        'transition_type': transition_type,
        'transition_duration': transition_duration,
        'fade_in': fade_in_duration,
        'fade_out': fade_out_duration,
        'effects': effects_sequence,
        'overlays': overlay_sequence
    }

    # ===== SECCIÓN 4: CONFIGURACIÓN DE AUDIO Y SUBTÍTULOS =====
    st.header("4. 🔊 Configuración de Audio y Subtítulos")
    
    # CONFIGURACIÓN DE AUDIO
    with st.expander("🔊 Configuración de Audio", expanded=True):
        audio_config = _render_batch_audio_config(app_config)
    
    # CONFIGURACIÓN DE SUBTÍTULOS
    with st.expander("📝 Configuración de Subtítulos", expanded=True):
        subtitles_config = _render_batch_subtitles_config(app_config)

    # ===== SECCIÓN 5: PROCESAR BATCH =====
    st.header("5. 🎬 Procesar Batch")
    
    # Mostrar resumen antes del procesamiento
    if st.session_state.get("batch_projects"):
        st.subheader("📋 Resumen de Configuración")
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🎬 Proyectos", len(st.session_state.batch_projects))
        with col2:
            efectos_count = len(video_config.get('effects', [])) if video_config.get('effects') else 0
            st.metric("✨ Efectos", efectos_count)
        with col3:
            overlays_count = len(video_config.get('overlays', [])) if video_config.get('overlays') else 0
            st.metric("🖼️ Overlays", overlays_count)
        with col4:
            music_status = "✅ Sí" if audio_config.get('bg_music_selection') else "❌ No"
            st.metric("🎵 Música", music_status)
        
        # Detalles de configuración
        with st.expander("🔍 Ver Detalles de Configuración"):
            col_det1, col_det2 = st.columns(2)
            
            with col_det1:
                st.write("**🎵 Audio:**")
                if audio_config.get('bg_music_selection'):
                    try:
                        music_name = Path(audio_config['bg_music_selection']).name
                    except:
                        music_name = audio_config['bg_music_selection']
                    st.write(f"• Música: {music_name}")
                    st.write(f"• Volumen música: {audio_config.get('music_volume', 0.06)}")
                else:
                    st.write("• ❌ Sin música de fondo")
                
                st.write(f"• Voz: {audio_config.get('tts_voice', 'N/A')}")
                st.write(f"• Velocidad: {audio_config.get('tts_speed_percent', 0)}%")
            
            with col_det2:
                st.write("**✨ Efectos Visuales:**")
                if efectos_count > 0:
                    st.write(f"• {efectos_count} efecto(s) configurado(s)")
                else:
                    st.write("• ❌ Sin efectos configurados")
                
                st.write("**🖼️ Overlays:**")
                if overlays_count > 0:
                    st.write(f"• {overlays_count} overlay(s) configurado(s)")
                else:
                    st.write("• ❌ Sin overlays configurados")
    
    if st.button("🎬 PROCESAR TODOS LOS PROYECTOS", type="primary", use_container_width=True):
        if not st.session_state.batch_projects:
            st.warning("⚠️ No hay proyectos para procesar. Añade al menos un proyecto.")
            return
        
        # ===== VALIDACIONES ANTES DEL PROCESAMIENTO =====
        validaciones_faltantes = []
        validaciones_recomendadas = []
        continuar_sin_config = False  # Inicializar variable
        
        # Verificar música de fondo (recomendado, no obligatorio)
        if not audio_config.get('bg_music_selection'):
            validaciones_recomendadas.append("🎵 **Música de fondo**: No has seleccionado música de fondo")
        
        # Verificar overlays (recomendado, no obligatorio)
        overlays_configurados = video_config.get('overlays', [])
        if not overlays_configurados or len(overlays_configurados) == 0:
            validaciones_recomendadas.append("🖼️ **Overlays**: No has configurado ningún overlay")
        
        # Verificar efectos (recomendado, no obligatorio)
        efectos_configurados = video_config.get('effects', [])
        if not efectos_configurados or len(efectos_configurados) == 0:
            validaciones_recomendadas.append("✨ **Efectos visuales**: No has configurado efectos visuales")
        
        # Mostrar recomendaciones si faltan configuraciones (pero permitir continuar)
        if validaciones_recomendadas:
            st.warning("💡 **Configuraciones recomendadas faltantes:**")
            for validacion in validaciones_recomendadas:
                st.write(f"• {validacion}")
            
            st.info("ℹ️ **Puedes continuar sin estas configuraciones, pero se recomienda configurarlas para mejores resultados.**")
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("⚙️ Configurar Antes de Continuar", type="secondary", use_container_width=True):
                    st.info("💡 **Sugerencias para mejorar tus videos:**")
                    if not audio_config.get('bg_music_selection'):
                        st.write("• Ve a la sección **'🔊 Configuración de Audio'** y selecciona una música de fondo")
                    if not overlays_configurados:
                        st.write("• Ve a la sección **'✨ Efectos y Overlays'** y configura algunos overlays")
                    if not efectos_configurados:
                        st.write("• Ve a la sección **'✨ Efectos y Overlays'** y configura algunos efectos visuales")
                    return
            
            with col2:
                continuar_sin_config = st.button("🚀 Continuar de Todas Formas", type="primary", use_container_width=True)
                if not continuar_sin_config:
                    return
                else:
                    st.success("✅ Continuando con la configuración actual...")
        else:
            st.success("✅ Todas las configuraciones recomendadas están presentes!")
            # Si no hay configuraciones faltantes, procesar directamente
            continuar_sin_config = True
        
        # Solo procesar si se confirmó continuar
        if not continuar_sin_config:
            return
        
        st.info("🔄 Iniciando procesamiento por lotes... Esto puede tardar varios minutos.")
        
        # Crear contenedores para la barra de progreso
        progress_container = st.empty()
        status_container = st.empty()
        progress_bar = progress_container.progress(0)
        
        def update_progress(progress: float, message: str):
            progress_bar.progress(progress)
            status_container.text(message)
        
        # Crear carpeta principal de proyectos
        projects_dir = Path("projects")
        projects_dir.mkdir(exist_ok=True)
        update_progress(0.05, "📁 Preparando estructura de carpetas...")
        
        resultados = []
        total_projects = len(st.session_state.batch_projects)
        
        # Recopilar configuración completa
        batch_config = {
            "script": {
                "provider": script_provider,
                "model": script_model,
                "prompt_obj": script_prompt_obj
            },
            "image": {
                "img_provider": "Replicate",
                "img_model": "black-forest-labs/flux-schnell",
                "img_prompt_provider": img_prompt_provider,
                "img_prompt_model": img_prompt_model,
                "aspect_ratio": img_aspect_ratio,
                "output_format": img_output_format,
                "output_quality": img_output_quality,
                "megapixels": img_megapixels,
                "style": img_style,
                "prompt_obj": img_prompt_obj
            },
            "scenes_config": {
                "segmentation_mode": segmentation_mode,
                "max_scene_duration": max_scene_duration
            },
            "video": video_config,
            "audio": audio_config,
            "subtitles": subtitles_config,
            **optimization_config
        }
        
        # Procesar cada proyecto
        for i, proyecto in enumerate(st.session_state.batch_projects):
            current_progress = (i / total_projects) * 0.9
            update_progress(current_progress, f"🔄 Procesando {i+1}/{total_projects}: {proyecto['titulo']}")
            
            try:
                resultado = procesar_proyecto_individual(
                    proyecto=proyecto,
                    batch_config=batch_config,
                    progress_callback=lambda prog, msg: update_progress(
                        current_progress + (prog * 0.9 / total_projects),
                        f"🔄 {proyecto['titulo']}: {msg}"
                    )
                )
                
                resultados.append(resultado)
                
            except Exception as e:
                st.error(f"❌ Error procesando '{proyecto['titulo']}': {str(e)}")
                resultados.append({
                    "titulo": proyecto["titulo"],
                    "estado": "error",
                    "error": str(e)
                })
        
        # Progreso final
        update_progress(1.0, "🎉 ¡Procesamiento completado!")
        
        # Mostrar resultados
        mostrar_resultados_batch(resultados)
        
        # Limpiar automáticamente proyectos completados del CMS de la cola
        proyectos_completados_cms = [r for r in resultados if r.get("cms_updated", False) and r["estado"] == "completado"]
        if proyectos_completados_cms:
            st.session_state.batch_projects = [
                p for p in st.session_state.batch_projects 
                if not (p.get("cms_publicacion_id") in [r.get("cms_publicacion_id") for r in proyectos_completados_cms])
            ]
            st.info(f"🧹 Limpieza automática: {len(proyectos_completados_cms)} proyecto(s) del CMS eliminados de la cola")
        
        # Limpiar progreso
        progress_container.empty()
        status_container.empty()


def procesar_proyecto_individual(proyecto, batch_config, progress_callback):
    """
    Procesa un proyecto individual del batch con todas las configuraciones reutilizadas.
    """
    try:
        from utils.video_processing import VideoProcessor
        
        progress_callback(0.05, "Preparando procesador de video")
        
        # 🏛️ PROCESAMIENTO ESPECIAL PARA PROMPT HISTÓRICO
        image_config = batch_config["image"].copy()
        
        # Verificar si se está usando el prompt histórico
        prompt_obj = batch_config["image"].get("prompt_obj", {})
        if prompt_obj and prompt_obj.get("nombre") == "Escenas Fotorrealistas Históricamente Precisas":
            progress_callback(0.07, "🏛️ Analizando contexto histórico...")
            
            # Obtener configuración histórica del session_state
            historical_config = st.session_state.get("batch_historical_config", {})
            
            if historical_config.get("mode") == "manual":
                # Usar configuración manual
                periodo_historico = historical_config.get("periodo_historico", "")
                ubicacion = historical_config.get("ubicacion", "")
                contexto_cultural = historical_config.get("contexto_cultural", "")
                
                progress_callback(0.08, "✍️ Usando configuración histórica manual")
                
            elif historical_config.get("mode") == "auto":
                # Extraer automáticamente con IA
                try:
                    from utils.ai_services import extract_historical_context
                    
                    ai_provider = historical_config.get("ai_provider", "gemini")
                    default_gemini_model = app_config.get('ai', {}).get('default_models', {}).get('gemini', 'models/gemini-1.5-flash-latest')
                    ai_model = historical_config.get("ai_model", default_gemini_model)
                    
                    progress_callback(0.08, f"🤖 Extrayendo contexto histórico con {ai_provider}...")
                    
                    historical_data = extract_historical_context(
                        titulo=proyecto["titulo"],
                        contexto=proyecto["contexto"],
                        provider=ai_provider,
                        model=ai_model
                    )
                    
                    periodo_historico = historical_data.get("periodo_historico", "")
                    ubicacion = historical_data.get("ubicacion", "")
                    contexto_cultural = historical_data.get("contexto_cultural", "")
                    
                    progress_callback(0.09, "✅ Contexto histórico extraído exitosamente")
                    
                except Exception as e:
                    progress_callback(0.09, f"⚠️ Error extrayendo contexto histórico: {str(e)}")
                    # Usar valores por defecto si falla
                    periodo_historico = "Información no especificada"
                    ubicacion = "Información no especificada"
                    contexto_cultural = "Información no especificada"
            else:
                # Fallback si no hay configuración
                periodo_historico = "Información no especificada"
                ubicacion = "Información no especificada"
                contexto_cultural = "Información no especificada"
            
            # Actualizar la configuración de imagen con las variables históricas
            image_config["prompt_obj"] = prompt_obj  # Mantener el prompt original
            image_config["historical_context"] = {
                "periodo_historico": periodo_historico,
                "ubicacion": ubicacion,
                "contexto_cultural": contexto_cultural,
                "extraction_mode": historical_config.get("mode", "fallback")
            }
            
            # Añadir las variables históricas a las variables disponibles para el prompt
            image_config["historical_variables"] = {
                "periodo_historico": periodo_historico,
                "ubicacion": ubicacion,
                "contexto_cultural": contexto_cultural
            }

        # Preparar configuración completa para el procesador
        full_config = {
            "titulo": proyecto["titulo"],
            "contexto": proyecto["contexto"],
            "script": {
                "mode": "Proporcionar Manualmente" if proyecto.get("script_type") == "✍️ Usar guión manual" else "Generar con IA",
                "manual_script": proyecto.get("guion_manual"),
                **batch_config["script"]
            },
            "image": image_config,  # Usar la configuración de imagen actualizada
            "scenes_config": batch_config["scenes_config"],
            "video": batch_config["video"],
            "audio": batch_config["audio"],
            "subtitles": batch_config["subtitles"],
            # Añadir configuración de optimización
            "generate_optimized_content": batch_config.get("generate_optimized_content", False),
            "use_same_style": batch_config.get("use_same_style", False),
            "generate_series_tags": batch_config.get("generate_series_tags", False)
        }
        
        progress_callback(0.1, "Iniciando procesamiento con VideoProcessor...")
        
        # Usar el VideoProcessor del generador individual
        processor = VideoProcessor(config=batch_config)
        result_path = processor.process_single_video(full_config)
        
        progress_callback(1.0, "¡Completado!")
        
        # Obtener directorio del proyecto desde el result_path
        if result_path:
            proyecto_dir = Path(result_path).parent.parent  # video/file.mp4 -> project_dir
            
            # Guardar metadata del proyecto
            metadata = {
                "titulo": proyecto["titulo"],
                "contexto": proyecto["contexto"],
                "script_type": proyecto.get("script_type"),
                "fecha_procesado": datetime.now().isoformat(),
                "config_used": full_config,
                "cms_info": {
                    "publicacion_id": proyecto.get("cms_publicacion_id"),
                    "canal": proyecto.get("cms_canal")
                } if "cms_publicacion_id" in proyecto else None
            }
            
            metadata_path = proyecto_dir / "batch_metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Actualizar estado en CMS si el proyecto viene del CMS
            cms_updated = False
            if "cms_publicacion_id" in proyecto:
                try:
                    # Importar y usar DatabaseManager para actualizar estado
                    import sys
                    project_root = Path(__file__).resolve().parent.parent
                    if str(project_root) not in sys.path:
                        sys.path.append(str(project_root))
                    
                    from utils.database_manager import DatabaseManager
                    db_manager = DatabaseManager()
                    db_manager.update_publicacion_status(
                        proyecto["cms_publicacion_id"], 
                        'Generado', 
                        str(proyecto_dir)
                    )
                    cms_updated = True
                    print(f"✅ CMS actualizado: Publicación {proyecto['cms_publicacion_id']} → 'Generado'")
                    
                    # También actualizar el metadata con el resultado
                    metadata["cms_update_result"] = "success"
                    metadata["cms_update_timestamp"] = datetime.now().isoformat()
                    
                except Exception as e:
                    # Si falla la actualización del CMS, continuar pero registrar el error
                    print(f"❌ Error actualizando CMS: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Guardar error en metadata
                    metadata["cms_update_result"] = "error"
                    metadata["cms_update_error"] = str(e)
                    metadata["cms_update_timestamp"] = datetime.now().isoformat()
                    
                # Re-escribir metadata con información de CMS
                try:
                    with open(metadata_path, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Warning: No se pudo actualizar metadata: {e}")
            
            return {
                "titulo": proyecto["titulo"],
                "estado": "completado",
                "video_path": str(result_path) if result_path else None,
                "proyecto_dir": str(proyecto_dir),
                "metadata": metadata,
                "cms_updated": cms_updated,
                "cms_publicacion_id": proyecto.get("cms_publicacion_id")
            }
        else:
            return {
                "titulo": proyecto["titulo"],
                "estado": "error",
                "error": "No se generó video final"
            }
        
    except Exception as e:
        return {
            "titulo": proyecto["titulo"],
            "estado": "error",
            "error": str(e)
        }


def mostrar_resultados_batch(resultados):
    """
    Muestra los resultados del procesamiento por lotes.
    """
    st.header("📊 Resultados del Procesamiento")
    
    # Resumen general
    total = len(resultados)
    completados = len([r for r in resultados if r["estado"] == "completado"])
    errores = len([r for r in resultados if r["estado"] == "error"])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total", total)
    with col2:
        st.metric("✅ Completados", completados)
    with col3:
        st.metric("❌ Errores", errores)
    
    # Mostrar cada resultado
    for resultado in resultados:
        if resultado["estado"] == "completado":
            st.success(f"✅ **{resultado['titulo']}** - ¡Completado exitosamente!")
            
            # Mostrar información del video generado
            if "video_path" in resultado and resultado["video_path"]:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"📁 **Carpeta:** {resultado.get('proyecto_dir', 'N/A')}")
                    st.write(f"🎥 **Video:** {resultado['video_path']}")
                    
                    # Mostrar el video si existe
                    if Path(resultado['video_path']).exists():
                        st.video(resultado['video_path'])
                    
                    # Mostrar metadata si está disponible
                    if "metadata" in resultado:
                        metadata = resultado["metadata"]
                        with st.expander("📋 Detalles del proyecto"):
                            st.json(metadata)
                
                with col2:
                    # Botón para descargar si existe el archivo
                    if Path(resultado['video_path']).exists():
                        with open(resultado['video_path'], "rb") as f:
                            st.download_button(
                                "⬇️ Descargar Video",
                                f,
                                file_name=f"{resultado['titulo']}.mp4",
                                mime="video/mp4",
                                key=f"download_{resultado['titulo']}"
                            )
            
        else:  # Error
            st.error(f"❌ **{resultado['titulo']}** - Error durante el procesamiento")
            if "error" in resultado:
                st.code(resultado["error"])
        
        st.markdown("---")
    
    # Opciones post-procesamiento
    st.subheader("📋 Acciones")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Limpiar cola de proyectos"):
            st.session_state.batch_projects = []
            st.success("✅ Cola limpiada!")
            st.rerun()
    
    with col2:
        if completados > 0:
            st.success(f"🎉 ¡{completados} video(s) generado(s) exitosamente!")
            st.info("💡 Los videos están guardados en la carpeta 'projects/'")

def _render_batch_audio_config(app_config):
    """Configuración de audio específica para batch (sin duplicaciones de UI)"""
    
    # --- SELECCIÓN DE PROVEEDOR TTS ---
    st.markdown("**🎤 Síntesis de Voz (TTS)**")
    
    # Obtener configuración TTS desde config.yaml
    tts_defaults = app_config.get('tts', {})
    default_provider = tts_defaults.get('default_provider', 'edge')
    
    # Seleccionar proveedor TTS
    provider_options = ["Edge TTS", "Fish Audio"]
    provider_mapping = {"edge": "Edge TTS", "fish": "Fish Audio"}
    default_provider_ui = provider_mapping.get(default_provider, "Edge TTS")
    provider_index = provider_options.index(default_provider_ui) if default_provider_ui in provider_options else 0
    
    tts_provider = st.selectbox(
        "Proveedor TTS",
        provider_options,
        index=provider_index,
        key="batch_tts_provider",
        help="Edge TTS: Gratuito, voces de Microsoft. Fish Audio: Calidad premium, requiere API key."
    )
    
    # Configuración específica según el proveedor
    if tts_provider == "Edge TTS":
        # --- CONFIGURACIÓN EDGE TTS ---
        col_voz1, col_voz2, col_voz3, col_voz4 = st.columns(4)
        
        async def obtener_voces_es_tts():
            voces = await edge_tts.list_voices()
            return [(v['ShortName'], v['Name']) for v in voces if v['Locale'].startswith('es-')]

        try:
            voces_esp_tuplas = asyncio.run(obtener_voces_es_tts())
            nombres_cortos = [v[0] for v in voces_esp_tuplas]
            nombres_completos = [v[1] for v in voces_esp_tuplas]
            default_voice_short = app_config.get("ai", {}).get("default_models", {}).get("voice", "es-ES-AlvaroNeural")
            voice_index = nombres_cortos.index(default_voice_short) if default_voice_short in nombres_cortos else 0
        except Exception as e:
            st.warning(f"No se pudieron cargar las voces de EdgeTTS: {e}. Usando default.")
            nombres_cortos = ["es-ES-AlvaroNeural"]
            nombres_completos = ["Microsoft Server Speech Text to Speech Voice (es-ES, AlvaroNeural)"]
            voice_index = 0

        with col_voz1:
            selected_voice_short = st.selectbox("Voz", nombres_cortos, index=voice_index, key="batch_tts_voice")
            tts_voice = nombres_completos[nombres_cortos.index(selected_voice_short)]
             
        with col_voz2:
            edge_defaults = tts_defaults.get('edge', {})
            default_rate = edge_defaults.get('default_rate', '+0%')
            # Convertir formato +X% a número
            rate_value = int(default_rate.replace('%', '').replace('+', '')) if default_rate != '+0%' else 0
            tts_speed_percent = st.slider("Velocidad (%)", -50, 50, rate_value, 1, key="batch_tts_speed")
        with col_voz3:
            default_pitch = edge_defaults.get('default_pitch', '+0Hz')
            # Convertir formato +XHz a número
            pitch_value = int(default_pitch.replace('Hz', '').replace('+', '')) if default_pitch != '+0Hz' else 0
            tts_pitch_hz = st.slider("Tono (Hz)", -50, 50, pitch_value, 1, key="batch_tts_pitch")
        with col_voz4:
            default_volume = app_config.get('video_generation', {}).get('audio', {}).get('default_voice_volume', 1.0)
            tts_volume = st.slider("Volumen Voz", 0.0, 2.0, default_volume, 0.1, key="batch_tts_volume")
        
        # Configuración para Edge TTS
        tts_config = {
            'tts_provider': 'edge',
            'tts_voice': tts_voice,
            'tts_speed_percent': tts_speed_percent,
            'tts_pitch_hz': tts_pitch_hz,
            'tts_volume': tts_volume
        }
        
    else:  # Fish Audio
        # --- CONFIGURACIÓN FISH AUDIO ---
        st.info("🐟 **Fish Audio**: Calidad premium de síntesis de voz. Requiere API key configurada.")
        
        # Verificar si Fish Audio está disponible
        try:
            from utils.audio_services import FISH_AUDIO_AVAILABLE
            if not FISH_AUDIO_AVAILABLE:
                st.error("❌ Fish Audio SDK no está disponible. Instala 'fish-audio-sdk' para usar Fish Audio TTS.")
                st.stop()
        except ImportError:
            st.error("❌ No se pudo verificar la disponibilidad de Fish Audio.")
            st.stop()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Modelo de Fish Audio
            fish_models = [
                ("speech-1.5", "Fish Audio Speech 1.5"),
                ("speech-1.6", "Fish Audio Speech 1.6 (Recomendado)"),
                ("s1", "Fish Audio S1")
            ]
            selected_fish_model = st.selectbox(
                "Modelo",
                [m[0] for m in fish_models],
                index=1,  # speech-1.6 por defecto
                key="batch_fish_model",
                format_func=lambda x: dict(fish_models)[x]
            )
            
            # Formato de salida
            fish_format = st.selectbox(
                "Formato",
                ["mp3", "wav", "pcm"],
                index=0,
                key="batch_fish_format"
            )
            
            # Bitrate para MP3
            fish_defaults = tts_defaults.get('fish_audio', {})
            default_bitrate = fish_defaults.get('default_mp3_bitrate', 128)
            bitrate_options = [64, 128, 192]
            bitrate_index = bitrate_options.index(default_bitrate) if default_bitrate in bitrate_options else 1
            fish_bitrate = st.selectbox(
                "Bitrate MP3",
                bitrate_options,
                index=bitrate_index,
                key="batch_fish_bitrate",
                disabled=(fish_format != "mp3")
            )
        
        with col2:
            # Latencia
            default_latency = fish_defaults.get('default_latency', 'normal')
            latency_options = ["normal", "balanced"]
            latency_index = latency_options.index(default_latency) if default_latency in latency_options else 0
            fish_latency = st.selectbox(
                "Latencia",
                latency_options,
                index=latency_index,
                key="batch_fish_latency",
                help="Normal: Mayor estabilidad. Balanced: Menor latencia (300ms)"
            )
            
            # Normalizar texto
            default_normalize = fish_defaults.get('default_normalize', True)
            fish_normalize = st.checkbox(
                "Normalizar texto",
                default_normalize,
                key="batch_fish_normalize",
                help="Mejora la estabilidad para números y texto en inglés/chino"
            )
            
            # Volumen
            default_volume = app_config.get('video_generation', {}).get('audio', {}).get('default_voice_volume', 1.0)
            tts_volume = st.slider("Volumen Voz", 0.0, 2.0, default_volume, 0.1, key="batch_tts_volume")
        
        # Configuración para Fish Audio
        tts_config = {
            'tts_provider': 'fish',
            'tts_fish_model': selected_fish_model,
            'tts_fish_format': fish_format,
            'tts_fish_bitrate': fish_bitrate,
            'tts_fish_latency': fish_latency,
            'tts_fish_normalize': fish_normalize,
            'tts_volume': tts_volume
        }

    # --- MÚSICA DE FONDO ---
    st.markdown("**🎵 Música de Fondo**")
    col_music1, col_music2 = st.columns(2)
    
    with col_music1:
        bg_music_folder = Path("background_music")
        available_music = ["**Ninguna**"] + ([f.name for f in bg_music_folder.iterdir() if f.suffix.lower() in ['.mp3', '.wav']] if bg_music_folder.exists() else [])
        
        # Obtener música por defecto desde config.yaml
        audio_defaults = app_config.get('video_generation', {}).get('audio', {})
        default_bg_music = audio_defaults.get('background_music', '')
        default_music_name = Path(default_bg_music).name if default_bg_music else None
        
        # Establecer índice por defecto
        default_index = 0  # "**Ninguna**" por defecto
        if default_music_name and default_music_name in available_music:
            default_index = available_music.index(default_music_name)
        
        sel_music = st.selectbox("Música Fondo", available_music, index=default_index, key="batch_bg_music")
        bg_music_selection = str(bg_music_folder / sel_music) if sel_music != "**Ninguna**" else None
        
    with col_music2:
        # Obtener configuración de audio desde config.yaml
        audio_defaults = app_config.get('video_generation', {}).get('audio', {})
        default_music_volume = audio_defaults.get('default_music_volume', 0.08)
        music_volume = st.slider("Volumen Música", 0.0, 1.0, default_music_volume, 0.01, "%.2f", key="batch_music_vol", disabled=(not bg_music_selection))
        music_loop = st.checkbox("Loop Música", True, key="batch_music_loop", disabled=(not bg_music_selection))

    # Combinar configuración TTS con música
    audio_config = {
        **tts_config,
        'bg_music_selection': bg_music_selection,
        'music_volume': music_volume,
        'music_loop': music_loop
    }
    
    return audio_config

def _render_batch_subtitles_config(app_config):
    """Configuración de subtítulos específica para batch usando valores de config.yaml como defaults"""
    
    # Obtener configuración de subtítulos desde config.yaml
    subtitles_defaults = app_config.get('video_generation', {}).get('subtitles', {})
    
    sub_config = {}
    sub_config['enable'] = st.checkbox("Incrustar Subtítulos", subtitles_defaults.get('enable', True), key="batch_sub_enable")
    
    if sub_config['enable']:
        col1, col2, col3 = st.columns(3)
        with col1:
            try:
                available_fonts = get_available_fonts()
                default_font = subtitles_defaults.get('font', 'Arial')
                font_index = available_fonts.index(default_font) if default_font in available_fonts else 0
            except:
                available_fonts = ["Arial", "Helvetica", "Times New Roman", "Calibri", "Impact"]
                default_font = subtitles_defaults.get('font', 'Arial')
                font_index = available_fonts.index(default_font) if default_font in available_fonts else 0
                
            sub_config['font'] = st.selectbox("Fuente", available_fonts, index=font_index, key="batch_sub_font")
            sub_config['size'] = st.slider("Tamaño", 16, 72, subtitles_defaults.get('font_size', 24), key="batch_sub_size")
        with col2:
            sub_config['color'] = st.color_picker("Color Texto", subtitles_defaults.get('font_color', '#FFFFFF'), key="batch_sub_color")
            sub_config['stroke_color'] = st.color_picker("Color Borde", subtitles_defaults.get('stroke_color', '#000000'), key="batch_sub_stroke_color")
        with col3:
            sub_config['stroke_width'] = st.slider("Grosor Borde", 0, 5, int(subtitles_defaults.get('stroke_width', 1.5)), key="batch_sub_stroke_width")
            position_options = ["bottom", "center", "top"]
            default_position = subtitles_defaults.get('position', 'bottom')
            position_index = position_options.index(default_position) if default_position in position_options else 0
            sub_config['position'] = st.selectbox("Posición", position_options, index=position_index, key="batch_sub_pos")
            
        sub_config['max_words'] = st.slider("Máx. Palabras por Segmento", 1, 10, subtitles_defaults.get('max_words', 7), key="batch_sub_max_words")
        st.caption("Controla cuántas palabras aparecen juntas en pantalla.")
        
    return sub_config