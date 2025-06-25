# pages/video_generator_page.py
import streamlit as st
import sys
from pathlib import Path
import asyncio
import numpy as np
import logging # Importar logging

# Configurar logging básico para esta página
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Añadir el directorio raíz del proyecto al sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Importaciones necesarias (asegúrate de que estos módulos/funciones existan)
try:
    from utils.config import load_config
    from utils.ai_services import list_openai_models, list_gemini_models, list_ollama_models, AIServices
    from pages.prompts_manager_page import list_prompts # Asumiendo que list_prompts está aquí ahora
    from utils.audio_services import generate_edge_tts_audio
    from utils.subtitle_utils import get_available_fonts
    #from utils.transitions import TransitionEffect # Quitado si no existe
    from pages.efectos_ui import show_effects_ui # Reubicado o necesita ajuste
    from pages.overlays_ui import show_overlays_ui # Reubicado o necesita ajuste
except ImportError as e:
    st.error(f"Error importando dependencias para video_generator_page: {e}. Verifica que los módulos existan en las rutas correctas.")
    st.stop()

# --- Funciones auxiliares para renderizar secciones de la UI ---

def _render_project_config_section():
    """Renderiza la sección de configuración básica del proyecto."""
    st.subheader("1. Información Básica")
    titulo = st.text_input("Título del Video", key="vg_titulo")
    contexto = st.text_area("Contexto o Tema General", key="vg_contexto")
    return {"titulo": titulo, "contexto": contexto}

def _render_script_options_section(app_config, project_info):
    """Renderiza las opciones para generar o proporcionar el guion."""
    st.subheader("2. Guion")
    script_mode = st.radio("Modo de Guion", ["Generar con IA", "Proporcionar Manualmente"], key="vg_script_mode")
    
    script_config = {"mode": script_mode}
    
    if script_mode == "Generar con IA":
        col1, col2 = st.columns([1, 2])
        with col1:
            script_config['provider'] = st.selectbox("Proveedor IA (Guion)", ["OpenAI", "Gemini", "Ollama"], key="vg_script_provider")
        with col2:
            # Lógica para seleccionar modelo (simplificada, necesita claves API)
            # Esta parte necesita acceso a las claves API desde app_config o un gestor de secretos
            ai_config = app_config.get("ai", {})
            default_models = ai_config.get("default_models", {})
            model_options = default_models.get(f"{script_config['provider'].lower()}_list", [])
            default_model = default_models.get(script_config['provider'].lower(), model_options[0] if model_options else None)
            script_config['model'] = st.selectbox(
                f"Modelo {script_config['provider']}", 
                model_options, 
                index=model_options.index(default_model) if default_model and default_model in model_options else 0,
                key="vg_script_model"
            )
            
        # Selección de Plantilla de Prompt de Guion
        try:
            prompts_guion_list = list_prompts("guion")
            prompt_guion_names = [p.get("nombre", f"Prompt Inválido {i}") for i, p in enumerate(prompts_guion_list)]
            default_script_prompt_name = "Guion Básico (Default)"
            default_script_index = prompt_guion_names.index(default_script_prompt_name) if default_script_prompt_name in prompt_guion_names else 0
            selected_prompt_guion_name = st.selectbox("Plantilla Guion", prompt_guion_names, index=default_script_index, key="vg_script_prompt_name")
            script_config['prompt_obj'] = next((p for p in prompts_guion_list if p.get("nombre") == selected_prompt_guion_name), None)
        except Exception as e:
            st.warning(f"No se pudieron cargar los prompts de guion: {e}")
            script_config['prompt_obj'] = None
            
    else: # Proporcionar Manualmente
        script_config['manual_script'] = st.text_area("Pega tu guion aquí", height=250, key="vg_manual_script")
        
    return script_config

def _render_image_options_section(app_config):
    """Renderiza las opciones para la generación de imágenes."""
    st.subheader("3. Imágenes")
    
    # Configuración de proveedor de prompts de imagen
    st.write("**Generación de Prompts de Imagen:**")
    col1, col2 = st.columns(2)
    
    with col1:
        img_prompt_provider = st.selectbox(
            "Proveedor para Prompts", 
            ["gemini", "openai", "ollama"], 
            index=0,  # Por defecto Gemini
            key="vg_img_prompt_provider",
            help="Servicio de IA para generar los prompts de las imágenes"
        )
    
    with col2:
        # Modelos por proveedor
        if img_prompt_provider == "gemini":
            img_prompt_model = st.text_input(
                "Modelo Gemini", 
                value="models/gemini-2.5-flash-lite-preview-06-17",
                key="vg_img_prompt_model",
                help="Modelo de Gemini para generar prompts (ej: models/gemini-2.5-flash-lite-preview-06-17)"
            )
        elif img_prompt_provider == "openai":
            img_prompt_model = st.selectbox(
                "Modelo OpenAI",
                ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
                index=1,
                key="vg_img_prompt_model"
            )
        else:  # ollama
            img_prompt_model = st.text_input(
                "Modelo Ollama",
                value="llama3.2",
                key="vg_img_prompt_model",
                help="Modelo local de Ollama (ej: llama3.2, mistral)"
            )
    
    st.write("**Generación de Imágenes:**")
    st.info("Actualmente configurado para usar Replicate (flux-schnell).")
    
    image_config = {
        "img_provider": "Replicate", 
        "img_model": "black-forest-labs/flux-schnell",
        "img_prompt_provider": img_prompt_provider,
        "img_prompt_model": img_prompt_model
    }
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        image_config['aspect_ratio'] = st.selectbox("Aspect Ratio", ["16:9", "1:1", "9:16"], index=0, key="vg_img_aspect")
    with col2:
        image_config['output_format'] = st.selectbox("Formato", ["webp", "png", "jpeg"], index=0, key="vg_img_format")
    with col3:
        image_config['output_quality'] = st.slider("Calidad", 50, 100, 85, 5, key="vg_img_quality")
    with col4:
        # Megapixels podría requerir ajuste si el modelo no lo soporta
        image_config['megapixels'] = st.select_slider("Megapixels", ["1", "2", "4"], value="1", key="vg_img_mp")
        
    image_config['style'] = st.text_input("Estilo de Imagen (Opcional)", value="cinematic, high detail, professional photography", key="vg_img_style")
    
    # Selección de Plantilla de Prompt de Imágenes (similar a guion)
    try:
        prompts_img_list = list_prompts("imagenes")
        prompt_img_names = [p.get("nombre", f"Prompt Inválido {i}") for i, p in enumerate(prompts_img_list)]
        default_img_prompt_name = "Imágenes Detalladas (Default)"
        default_img_index = prompt_img_names.index(default_img_prompt_name) if default_img_prompt_name in prompt_img_names else 0
        selected_prompt_img_name = st.selectbox("Plantilla Imágenes", prompt_img_names, index=default_img_index, key="vg_image_prompt_name")
        image_config['prompt_obj'] = next((p for p in prompts_img_list if p.get("nombre") == selected_prompt_img_name), None)
    except Exception as e:
        st.warning(f"No se pudieron cargar los prompts de imágenes: {e}")
        image_config['prompt_obj'] = None
        
    return image_config

def _render_video_audio_options_section(app_config):
    """Renderiza las opciones de configuración de video y audio."""
    st.subheader("4. Configuración de Video y Audio")
    
    video_config = {}
    audio_config = {}
    
    # --- VOZ (TTS) ---
    st.markdown("**Voz (EdgeTTS)**")
    col_voz1, col_voz2, col_voz3, col_voz4 = st.columns(4)
    
    async def obtener_voces_es_tts():
        import edge_tts # Importar aquí para que funcione la función async
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
        selected_voice_short = st.selectbox("Voz", nombres_cortos, index=voice_index, key="vg_tts_voice")
        audio_config['tts_voice'] = nombres_completos[nombres_cortos.index(selected_voice_short)]
        if st.button("Preview Voz", key="vg_tts_preview"): # Placeholder para preview
             # Lógica para generar preview audio
             st.info("Preview de voz aún no implementado en esta página.")
             pass 
             
    with col_voz2:
        audio_config['tts_speed_percent'] = st.slider("Velocidad (%)", -50, 50, -5, 1, key="vg_tts_speed")
    with col_voz3:
        audio_config['tts_pitch_hz'] = st.slider("Tono (Hz)", -50, 50, -5, 1, key="vg_tts_pitch")
    with col_voz4:
        audio_config['tts_volume'] = st.slider("Volumen Voz", 0.0, 2.0, 1.0, 0.1, key="vg_tts_volume")

    # --- TIMING & TRANSICIONES ---
    st.markdown("**Timing y Transiciones**")
    col_vid_t1, col_vid_t2 = st.columns(2)
    with col_vid_t1:
        video_config['use_auto_duration'] = st.checkbox("Duración Auto (basada en audio)", True, key="vg_vid_auto_dur")
        video_config['duration_per_image_manual'] = st.slider("Duración Manual por Imagen (s)", 1.0, 30.0, 10.0, 0.5, key="vg_vid_manual_dur", disabled=video_config['use_auto_duration'])
    with col_vid_t2:
        # Usar TransitionEffect para obtener las transiciones disponibles
        try:
            from utils.transitions import TransitionEffect
            available_transitions = TransitionEffect.get_available_transitions()
            transition_labels = {
                'none': 'Sin transición',
                'dissolve': 'Disolución',
                'fade': 'Fade'
            }
            video_config['transition_type'] = st.selectbox(
                "Transición", 
                available_transitions,
                format_func=lambda x: transition_labels.get(x, x),
                index=1 if 'dissolve' in available_transitions else 0,
                key="vg_vid_trans_type"
            )
        except ImportError:
            video_config['transition_type'] = st.selectbox("Transición", ["fade", "none"], index=0, key="vg_vid_trans_type")
        video_config['transition_duration'] = st.slider("Duración Transición (s)", 0.0, 5.0, 1.0, 0.1, key="vg_vid_trans_dur", disabled=(video_config['transition_type'] == 'none'))

    # --- MÚSICA y FADES ---
    st.markdown("**Música y Fades**")
    col_vid_m1, col_vid_m2 = st.columns(2)
    with col_vid_m1:
        bg_music_folder = Path("background_music")
        available_music = ["**Ninguna**"] + ([f.name for f in bg_music_folder.iterdir() if f.suffix.lower() in ['.mp3', '.wav']] if bg_music_folder.exists() else [])
        sel_music = st.selectbox("Música Fondo", available_music, key="vg_bg_music")
        audio_config['bg_music_selection'] = str(bg_music_folder / sel_music) if sel_music != "**Ninguna**" else None
        audio_config['music_volume'] = st.slider("Volumen Música", 0.0, 1.0, 0.1, 0.01, "%.2f", key="vg_music_vol", disabled=(not audio_config['bg_music_selection']))
        audio_config['music_loop'] = st.checkbox("Loop Música", True, key="vg_music_loop", disabled=(not audio_config['bg_music_selection']))
    with col_vid_m2:
        video_config['fade_in'] = st.slider("Fade In Video (s)", 0.0, 5.0, 1.0, 0.1, key="vg_fade_in")
        video_config['fade_out'] = st.slider("Fade Out Video (s)", 0.0, 5.0, 1.0, 0.1, key="vg_fade_out")

    # --- EFECTOS Y OVERLAYS (Usando funciones de UI separadas) ---
    st.markdown("**Efectos y Overlays**")
    # Eliminado key_prefix="vg" ya que las funciones no lo esperan
    video_config['effects'] = show_effects_ui() 
    video_config['overlays'] = show_overlays_ui() 

    return video_config, audio_config

def _render_subtitles_options_section():
    """Renderiza las opciones para los subtítulos."""
    st.subheader("5. Subtítulos")
    sub_config = {}
    sub_config['enable'] = st.checkbox("Incrustar Subtítulos", True, key="vg_sub_enable")
    
    if sub_config['enable']:
        col1, col2, col3 = st.columns(3)
        with col1:
            avalaible_fonts = get_available_fonts() # Asegúrate que esta función exista y funcione
            default_font = "Impact" # O leer desde config
            font_index = avalaible_fonts.index(default_font) if default_font in avalaible_fonts else 0
            sub_config['font'] = st.selectbox("Fuente", avalaible_fonts, index=font_index, key="vg_sub_font")
            sub_config['size'] = st.slider("Tamaño", 16, 72, 54, key="vg_sub_size")
        with col2:
            sub_config['color'] = st.color_picker("Color Texto", "#FFFFFF", key="vg_sub_color")
            sub_config['stroke_color'] = st.color_picker("Color Borde", "#000000", key="vg_sub_stroke_color")
        with col3:
            sub_config['stroke_width'] = st.slider("Grosor Borde", 0, 5, 2, key="vg_sub_stroke_width")
            sub_config['position'] = st.selectbox("Posición", ["bottom", "center", "top"], index=0, key="vg_sub_pos")
            
        sub_config['max_words'] = st.slider("Máx. Palabras por Segmento", 1, 10, 7, key="vg_sub_max_words")
        st.caption("Controla cuántas palabras aparecen juntas en pantalla.")
        
    return sub_config

# --- Función Principal de Renderizado de la Página ---

def render_video_generator(app_config):
    st.title("🎬 Generador de Video Individual")
    st.markdown("Crea un video único con guion, imágenes, voz, música y subtítulos personalizados.")
    st.divider()

    # Renderizar secciones
    project_info = _render_project_config_section()
    script_config = _render_script_options_section(app_config, project_info)
    image_config = _render_image_options_section(app_config)
    video_config, audio_config = _render_video_audio_options_section(app_config)
    subtitles_config = _render_subtitles_options_section()
    
    st.divider()
    
    # Recopilar toda la configuración
    full_config = {
        **project_info,
        "script": script_config,
        "image": image_config,
        "video": video_config,
        "audio": audio_config,
        "subtitles": subtitles_config
    }

    # Botón de Generación
    if st.button("🚀 Generar Video", type="primary"):
        # Validación básica (ejemplo)
        if not full_config["titulo"]:
            st.error("Por favor, introduce un título para el video.")
        elif full_config["script"]["mode"] == "Proporcionar Manualmente" and not full_config["script"]["manual_script"]:
            st.error("Por favor, pega el guion manual o selecciona generar con IA.")
        else:
            # --- Llamada al Procesador Real ---
            try:
                # Importar el procesador aquí para asegurar que las dependencias estén listas
                from utils.video_processing import VideoProcessor 
                
                # Instanciar el procesador (pasa app_config si necesita config global)
                processor = VideoProcessor(config=app_config) 
                
                st.info("Iniciando generación de video...")
                logger.info(f"Iniciando proceso para video: {full_config['titulo']}")
                
                with st.spinner("Generando video, esto puede tardar varios minutos... ⏳"):
                    # Llamar a la función de procesamiento principal
                    result_path = processor.process_single_video(full_config)
                    
                if result_path and Path(result_path).exists():
                    st.success(f"¡Video generado exitosamente!")
                    st.video(str(result_path))
                    logger.info(f"Video generado y mostrado: {result_path}")
                    # Opcional: Mostrar un enlace de descarga
                    # with open(result_path, "rb") as fp:
                    #     st.download_button("Descargar Video", data=fp, file_name=Path(result_path).name, mime="video/mp4")
                else:
                     st.error("La generación del video falló o no se encontró el archivo final. Revisa los logs.")
                     logger.error("La generación del video falló o no devolvió una ruta válida.")

            except ImportError as import_err:
                 st.error(f"Error de importación necesario para procesar: {import_err}. Asegúrate de que todos los módulos utils existen.")
                 logger.error(f"ImportError al intentar procesar: {import_err}", exc_info=True)
            except Exception as e:
                st.error(f"Ocurrió un error durante la generación del video.")
                st.exception(e) # Muestra el traceback completo en la UI
                logger.error(f"Error fatal durante process_single_video: {e}", exc_info=True)
            # --- Fin Llamada al Procesador ---
            
    # Opción para ver la configuración recopilada (útil para depurar)
    if st.checkbox("Ver Configuración Completa Recopilada", key="vg_show_config"):
        # Convertir Paths a strings para mostrar en JSON si es necesario
        import json
        st.json(json.dumps(full_config, default=str))
