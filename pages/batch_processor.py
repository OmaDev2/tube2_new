import streamlit as st
import os
import uuid
from pathlib import Path
from datetime import datetime
import json
import math
import asyncio
from moviepy.editor import AudioFileClip

# Importar funciones del generador de videos para reutilizar
try:
    from pages.video_generator_page import (
        _render_video_audio_options_section,
        _render_subtitles_options_section
    )
    from utils.config import load_config
    from utils.ai_services import list_openai_models, list_gemini_models, list_ollama_models
    from pages.prompts_manager_page import list_prompts
    from utils.audio_services import generate_edge_tts_audio
    from pages.efectos_ui import show_effects_ui
    from pages.overlays_ui import show_overlays_ui
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
    
    # Sección 1: Gestión de Proyectos por Lotes
    st.header("1. Gestión de Proyectos por Lotes")
    
    # Añadir nuevos proyectos
    st.subheader("➕ Añadir Nuevo Proyecto")
    
    # Opción para elegir tipo de guión (fuera del formulario para que sea reactiva)
    script_type = st.radio(
        "📜 Tipo de guión:",
        ["🤖 Generar automáticamente con IA", "✍️ Usar guión manual"],
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
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"{icon} **{proyecto['titulo']}** ({script_label})")
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
    
    # Sección 2: Configuración del Video
    st.header("2. Configuración del Video")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        duration_per_image = st.slider(
            "Duración por imagen (segundos)",
            min_value=1.0,
            max_value=30.0,
            value=10.0,
            step=0.5,
            key="batch_duration_per_image"
        )
    
    with col2:
        transition_duration = st.slider(
            "Duración de la transición (segundos)",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.1,
            key="batch_transition_duration"
        )
    
    with col3:
        from utils.transitions import TransitionEffect
        transition_type = st.selectbox(
            "Tipo de transición",
            options=TransitionEffect.get_available_transitions(),
            format_func=lambda x: "Sin transición" if x == "none" else "Disolución" if x == "dissolve" else x,
            index=1,  # 'dissolve' está en la posición 1 de la lista
            key="batch_transition_type"
        )
    
    # Controles de fade in/out
    st.subheader("Efectos de entrada y salida")
    col1, col2 = st.columns(2)
    with col1:
        fade_in_duration = st.slider(
            "Fade In (segundos)",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.1,
            key="batch_fade_in"
        )
    with col2:
        fade_out_duration = st.slider(
            "Fade Out (segundos)",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.1,
            key="batch_fade_out"
        )
    
    # Sección 3: Efectos
    st.header("3. Efectos")
    try:
        effects_sequence = show_effects_ui(key_prefix="batch_")
    except:
        st.warning("⚠️ La interfaz de efectos no está disponible. Se usará configuración básica.")
        effects_sequence = []
        
        # Configuración manual de efectos como fallback
        col1, col2 = st.columns(2)
        with col1:
            enable_zoom = st.checkbox("Activar zoom", key="batch_enable_zoom")
            if enable_zoom:
                zoom_factor = st.slider("Factor de zoom", 1.0, 2.0, 1.2, key="batch_zoom_factor")
        with col2:
            enable_pan = st.checkbox("Activar paneo", key="batch_enable_pan")
            if enable_pan:
                pan_direction = st.selectbox("Dirección", ["left", "right", "up", "down"], key="batch_pan_direction")
    
    # Sección 4: Overlays
    st.header("4. Overlays")
    try:
        overlay_sequence = show_overlays_ui(key_prefix="batch_")
    except:
        st.warning("⚠️ La interfaz de overlays no está disponible. Se usará configuración básica.")
        overlay_sequence = []
        
        # Configuración manual de overlays como fallback
        enable_overlay = st.checkbox("Activar overlay", key="batch_enable_overlay")
        if enable_overlay:
            overlay_opacity = st.slider("Opacidad del overlay", 0.0, 1.0, 0.3, key="batch_overlay_opacity")
    
    # Configuración avanzada de efectos y overlays para batch
    st.subheader("Configuración Avanzada para Batch")
    col1, col2 = st.columns(2)
    with col1:
        randomize_effects = st.checkbox(
            "🎲 Randomizar efectos entre proyectos",
            help="Cada proyecto tendrá efectos ligeramente diferentes",
            key="batch_randomize_effects"
        )
        if randomize_effects:
            effect_variation = st.slider(
                "Variación de efectos",
                min_value=0.1,
                max_value=0.5,
                value=0.2,
                step=0.1,
                key="batch_effect_variation"
            )
    
    with col2:
        vary_intensity = st.checkbox(
            "📊 Variar intensidad por proyecto",
            help="La intensidad de efectos aumentará gradualmente",
            key="batch_vary_intensity"
        )
        if vary_intensity:
            intensity_range = st.slider(
                "Rango de intensidad",
                min_value=0.5,
                max_value=2.0,
                value=(0.8, 1.5),
                key="batch_intensity_range"
            )
    
    # Sección 5: Configuración de IA y Voz
    st.header("5. Configuración de IA y Voz")
    
    col1, col2 = st.columns(2)
    
    # Verificar si hay proyectos que necesitan IA
    proyectos_con_ia = [p for p in st.session_state.get("batch_projects", []) 
                       if p.get("script_type") != "✍️ Usar guión manual"]
    
    if proyectos_con_ia:
        st.info(f"📊 {len(proyectos_con_ia)} proyecto(s) usarán IA para generar guión")
        
        with col1:
            script_provider = st.selectbox(
                "Proveedor de IA para Guiones",
                ["OpenAI", "Gemini", "Ollama"],
                help="Selecciona el proveedor de IA para generar guiones automáticos",
                key="batch_script_provider"
            )
        
        with col2:
            # Modelos según el proveedor
            if script_provider == "OpenAI":
                script_model = st.selectbox("Modelo OpenAI", ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"], key="batch_script_model")
            elif script_provider == "Gemini":
                script_model = st.selectbox("Modelo Gemini", ["gemini-pro", "gemini-pro-vision"], key="batch_script_model")
            else:  # Ollama
                script_model = st.text_input("Modelo Ollama", value="llama2", help="Nombre del modelo local", key="batch_script_model")
        
        # Selección de plantilla de prompt para guiones
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
        script_provider = "OpenAI"  # Valor por defecto
        script_model = "gpt-3.5-turbo"  # Valor por defecto
        script_prompt_obj = None
        st.info("ℹ️ Todos los proyectos usan guión manual - La configuración de IA no se usará")
    
    # Sección 6: Configuración de Escenas y Imágenes
    st.header("6. Configuración de Escenas y Imágenes")
    
    # Configuración del método de segmentación
    st.write("**Método de Segmentación de Escenas:**")
    col_seg1, col_seg2 = st.columns([2, 1])
    
    with col_seg1:
        segmentation_mode = st.selectbox(
            "Método de Segmentación",
            ["Por Duración (Basado en Audio)", "Automático (Texto)"],
            index=0,  # Por defecto el mejor método
            key="batch_segmentation_mode",
            help="• Por Duración: Usa timestamps de transcripción para sincronizar perfectamente (RECOMENDADO)\n• Automático: Divide el texto por párrafos/caracteres"
        )
    
    with col_seg2:
        if segmentation_mode == "Por Duración (Basado en Audio)":
            st.success("🎯 Método Óptimo")
            st.caption("✅ Sincronización perfecta\n✅ Compensa transiciones\n✅ Timestamps precisos")
        else:
            st.warning("⚠️ Método Básico")
            st.caption("❌ Sin sincronización temporal\n❌ Duración fija por escena")
    
    # Configuración de proveedor de prompts de imagen (reutilizando del generador individual)
    st.write("**Generación de Prompts de Imagen:**")
    col1, col2 = st.columns(2)
    
    with col1:
        img_prompt_provider = st.selectbox(
            "Proveedor para Prompts", 
            ["gemini", "openai", "ollama"], 
            index=0,  # Por defecto Gemini
            key="batch_img_prompt_provider",
            help="Servicio de IA para generar los prompts de las imágenes"
        )
    
    with col2:
        # Modelos por proveedor
        if img_prompt_provider == "gemini":
            img_prompt_model = st.text_input(
                "Modelo Gemini", 
                value="models/gemini-2.5-flash-lite-preview-06-17",
                key="batch_img_prompt_model",
                help="Modelo de Gemini para generar prompts"
            )
        elif img_prompt_provider == "openai":
            img_prompt_model = st.selectbox(
                "Modelo OpenAI",
                ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
                index=1,
                key="batch_img_prompt_model"
            )
        else:  # ollama
            img_prompt_model = st.text_input(
                "Modelo Ollama",
                value="llama3.2",
                key="batch_img_prompt_model",
                help="Modelo local de Ollama"
            )
    
    st.write("**Generación de Imágenes:**")
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
    
    img_style = st.text_input("Estilo de Imagen (Opcional)", value="cinematic, high detail, professional photography", key="batch_img_style")
    
    # Selección de plantilla de prompt para imágenes
    try:
        prompts_img_list = list_prompts("imagenes")
        prompt_img_names = [p.get("nombre", f"Prompt Inválido {i}") for i, p in enumerate(prompts_img_list)]
        default_img_prompt_name = "Imágenes Detalladas (Default)"
        default_img_index = prompt_img_names.index(default_img_prompt_name) if default_img_prompt_name in prompt_img_names else 0
        selected_prompt_img_name = st.selectbox("Plantilla de Imágenes", prompt_img_names, index=default_img_index, key="batch_image_prompt")
        img_prompt_obj = next((p for p in prompts_img_list if p.get("nombre") == selected_prompt_img_name), None)
    except Exception as e:
        st.warning(f"No se pudieron cargar los prompts de imágenes: {e}")
        img_prompt_obj = None
    
    # Sección 7: Configuración de Video y Audio (USANDO configuración del batch)
    try:
        # Usar la configuración de audio del generador individual pero video del batch
        _, audio_config = _render_video_audio_options_section(app_config)
        
        # Configurar video con los efectos y overlays del batch
        st.header("7. Configuración de Video")
        
        col1, col2 = st.columns(2)
        with col1:
            use_auto_duration = st.checkbox(
                "Duración automática basada en audio",
                value=True,
                help="Calcular duración por imagen según el audio transcrito",
                key="batch_use_auto_duration"
            )
        with col2:
            if not use_auto_duration:
                duration_per_image_manual = st.slider(
                    "Duración manual por imagen (s)",
                    min_value=1.0,
                    max_value=15.0,
                    value=10.0,
                    step=0.5,
                    key="batch_duration_manual"
                )
            else:
                duration_per_image_manual = 10.0
        
        # Usar las configuraciones ya definidas en las secciones 3 y 4 del batch
        video_config = {
            'use_auto_duration': use_auto_duration,
            'duration_per_image_manual': duration_per_image_manual,
            'transition_type': transition_type,
            'transition_duration': 1.0,
            'fade_in': fade_in_duration,
            'fade_out': fade_out_duration,
            'effects': effects_sequence,  # De la sección 3
            'overlays': overlay_sequence  # De la sección 4
        }
        
        # Debug: Mostrar configuración de overlays
        if overlay_sequence:
            st.info(f"🖼️ Configuración de overlays detectada: {len(overlay_sequence)} overlay(s)")
            for i, overlay in enumerate(overlay_sequence):
                st.caption(f"  • Overlay {i+1}: {overlay}")
        else:
            st.warning("⚠️ No se detectaron overlays configurados")
        
    except Exception as e:
        st.error(f"Error cargando configuración de video/audio: {e}")
        # Fallback básico
        video_config = {
            'use_auto_duration': True,
            'duration_per_image_manual': 10.0,
            'transition_type': 'dissolve',
            'transition_duration': 1.0,
            'fade_in': 1.0,
            'fade_out': 1.0,
            'effects': effects_sequence if 'effects_sequence' in locals() else [],
            'overlays': overlay_sequence if 'overlay_sequence' in locals() else []
        }
        audio_config = {
            'tts_voice': 'es-ES-AlvaroNeural',
            'tts_speed_percent': -5,
            'tts_pitch_hz': -5,
            'tts_volume': 1.0,
            'bg_music_selection': None,
            'music_volume': 0.06,
            'music_loop': True
        }
    
    # Sección 8: Subtítulos (REUTILIZANDO función del generador individual)
    try:
        # Usar la misma función del generador individual (ya incluye su propio header)
        subtitles_config = _render_subtitles_options_section()
    except Exception as e:
        st.error(f"Error cargando configuración de subtítulos: {e}")
        # Fallback básico
        subtitles_config = {
            'enable': True,
            'font': 'Arial',
            'size': 54,
            'color': '#FFFFFF',
            'stroke_color': '#000000',
            'stroke_width': 2,
            'position': 'bottom',
            'max_words': 7
        }
    
    # Sección 9: Optimización para YouTube (BATCH)
    st.header("9. Optimización para YouTube")
    st.markdown("Genera automáticamente contenido optimizado para todos los videos del batch.")
    
    optimization_config = {}
    optimization_config['generate_optimized_content'] = st.checkbox(
        "🎯 Generar contenido optimizado para TODOS los videos", 
        value=False, 
        key="batch_optimize_content",
        help="Genera títulos alternativos, descripción SEO, tags relevantes y capítulos con timestamps para cada video"
    )
    
    if optimization_config['generate_optimized_content']:
        st.info("💡 Se generarán archivos `content_optimization.txt` y `youtube_metadata.json` en cada carpeta de proyecto")
        
        # Configuración del LLM para optimización
        st.markdown("**Configuración del LLM para Optimización:**")
        
        # Obtener proveedores disponibles
        from utils.ai_services import get_available_providers_info
        providers_info = get_available_providers_info()
        available_providers = [name for name, info in providers_info.items() if info['configured']]
        
        if available_providers:
            col_llm1, col_llm2 = st.columns(2)
            
            with col_llm1:
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
                    "Proveedor IA", 
                    available_providers,
                    index=default_provider_index,
                    key="batch_opt_provider",
                    format_func=lambda x: provider_display_names.get(x, x.title()),
                    help="Proveedor de IA para generar el contenido optimizado (🔵 Gemini recomendado)"
                )
            
            with col_llm2:
                # Modelos según el proveedor seleccionado
                selected_provider = optimization_config['optimization_provider']
                if selected_provider in providers_info:
                    available_models = providers_info[selected_provider]['models']
                    
                    # Configurar modelo por defecto según el proveedor
                    default_model_index = 0
                    if selected_provider == 'gemini' and 'models/gemini-2.5-flash-lite-preview-06-17' in available_models:
                        default_model_index = available_models.index('models/gemini-2.5-flash-lite-preview-06-17')
                    
                    optimization_config['optimization_model'] = st.selectbox(
                        "Modelo", 
                        available_models, 
                        index=default_model_index,
                        key="batch_opt_model",
                        help=f"Modelo específico de {provider_display_names.get(selected_provider, selected_provider)} a usar"
                    )
                else:
                    st.error("Error: Proveedor no encontrado")
                    optimization_config['optimization_model'] = 'gpt-3.5-turbo'  # Fallback
        else:
            st.warning("⚠️ **No hay proveedores de IA configurados**")
            st.info("Ve a la página de **Configuración** para configurar al menos un proveedor (OpenAI, Gemini o Ollama)")
            optimization_config['optimization_provider'] = 'openai'  # Fallback
            optimization_config['optimization_model'] = 'gpt-3.5-turbo'  # Fallback
        
        # Opciones adicionales para batch
        st.markdown("**Opciones de Batch:**")
        col1, col2 = st.columns(2)
        with col1:
            optimization_config['use_same_style'] = st.checkbox(
                "Usar estilo consistente", 
                value=True,
                key="batch_opt_consistent",
                help="Mantener un estilo similar en títulos y descripciones entre videos"
            )
        with col2:
            optimization_config['generate_series_tags'] = st.checkbox(
                "Tags de serie", 
                value=True,
                key="batch_opt_series",
                help="Añadir tags que conecten todos los videos como una serie"
            )
    
    # Botón para procesar el batch
    st.header("10. Procesar Batch")
    
    # Mostrar resumen antes del procesamiento
    if st.session_state.get("batch_projects"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🎬 Proyectos", len(st.session_state.batch_projects))
        with col2:
            efectos_count = len(video_config.get('effects', [])) if video_config.get('effects') else 0
            st.metric("✨ Efectos", efectos_count)
        with col3:
            overlays_count = len(video_config.get('overlays', [])) if video_config.get('overlays') else 0
            st.metric("🖼️ Overlays", overlays_count)
    
    if st.button("🎬 PROCESAR TODOS LOS PROYECTOS", type="primary", use_container_width=True):
        if not st.session_state.batch_projects:
            st.warning("⚠️ No hay proyectos para procesar. Añade al menos un proyecto.")
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
                "segmentation_mode": segmentation_mode
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
        
        # Preparar configuración completa para el procesador
        full_config = {
            "titulo": proyecto["titulo"],
            "contexto": proyecto["contexto"],
            "script": {
                "mode": "Proporcionar Manualmente" if proyecto.get("script_type") == "✍️ Usar guión manual" else "Generar con IA",
                "manual_script": proyecto.get("guion_manual"),
                **batch_config["script"]
            },
            "image": batch_config["image"],
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
                "config_used": full_config
            }
            
            metadata_path = proyecto_dir / "batch_metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return {
                "titulo": proyecto["titulo"],
                "estado": "completado",
                "video_path": str(result_path) if result_path else None,
                "proyecto_dir": str(proyecto_dir),
                "metadata": metadata
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