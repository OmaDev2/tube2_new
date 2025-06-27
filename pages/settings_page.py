# pages/settings_page.py
import streamlit as st
from pathlib import Path
from utils.config import load_config, save_config



def show_settings_page():
    """Renderiza la página de configuración completa y centralizada."""
    st.title("⚙️ Configuración Central del Proyecto")
    st.markdown("Aquí puedes gestionar todos los ajustes de la aplicación. Los cambios se guardan en `config.yaml`.")

    config = load_config()

    # Usar pestañas para una organización clara
    tab_ai, tab_video, tab_subtitles, tab_paths = st.tabs([
        "🤖 Inteligencia Artificial",
        "🎬 Calidad de Video y Audio",
        "📝 Subtítulos y Transiciones",
        "📁 Rutas y Directorios"
    ])

    # --- Pestaña de IA ---
    with tab_ai:
        st.header("Claves de API y Modelos por Defecto")
        ai_config = config.get("ai", {})
        
        with st.expander("🔑 Claves de API", expanded=True):
            ai_config["openai_api_key"] = st.text_input("OpenAI API Key", value=ai_config.get("openai_api_key", ""), type="password")
            ai_config["gemini_api_key"] = st.text_input("Gemini API Key", value=ai_config.get("gemini_api_key", ""), type="password")
            ai_config["replicate_api_key"] = st.text_input("Replicate API Key", value=ai_config.get("replicate_api_key", ""), type="password")
            ai_config["ollama_base_url"] = st.text_input("Ollama Base URL", value=ai_config.get("ollama_base_url", "http://localhost:11434"))

        st.divider()
        st.subheader("🤖 Modelos de IA por Defecto")
        models_config = ai_config.get("default_models", {})
        col1, col2 = st.columns(2)
        with col1:
            models_config["openai"] = st.text_input("Modelo OpenAI (Guiones)", value=models_config.get("openai", ""))
            models_config["gemini"] = st.text_input("Modelo Gemini (Guiones)", value=models_config.get("gemini", ""))
            models_config["ollama"] = st.text_input("Modelo Ollama (Guiones)", value=models_config.get("ollama", ""))
        with col2:
            models_config["image_generation"] = st.text_input("Modelo Generación de Imágenes (Replicate)", value=models_config.get("image_generation", ""))
            models_config["image_prompt_generation"] = st.text_input("Modelo para Prompts de Imagen (Gemini/OpenAI)", value=models_config.get("image_prompt_generation", ""))
            models_config["default_voice"] = st.text_input("Voz por Defecto (TTS)", value=models_config.get("default_voice", ""))
        
        ai_config["default_models"] = models_config
        config["ai"] = ai_config

    # --- Pestaña de Vídeo y Audio ---
    with tab_video:
        st.header("Ajustes de Generación de Vídeo y Audio")
        video_config = config.get("video_generation", {})
        quality_config = video_config.get("quality", {})
        audio_config = video_config.get("audio", {})

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📹 Calidad de Vídeo")
            quality_config["resolution"] = st.selectbox("Resolución", ["1920x1080", "1280x720", "1080x1920"], index=["1920x1080", "1280x720", "1080x1920"].index(quality_config.get("resolution", "1920x1080")))
            quality_config["fps"] = st.slider("Frames por Segundo (FPS)", 15, 60, quality_config.get("fps", 24))
            quality_config["bitrate"] = st.text_input("Bitrate de Vídeo", value=quality_config.get("bitrate", "5000k"))
        
        with col2:
            st.subheader("🔊 Calidad de Audio")
            quality_config["audio_bitrate"] = st.text_input("Bitrate de Audio", value=quality_config.get("audio_bitrate", "192k"))
            audio_config["normalize_audio"] = st.checkbox("Normalizar Audio", value=audio_config.get("normalize_audio", True))
            audio_config["default_music_volume"] = st.slider("Volumen Música de Fondo (por defecto)", 0.0, 1.0, audio_config.get("default_music_volume", 0.08))

        video_config["quality"] = quality_config
        video_config["audio"] = audio_config
        config["video_generation"] = video_config

    # --- Pestaña de Subtítulos y Transiciones ---
    with tab_subtitles:
        st.header("Ajustes de Subtítulos y Transiciones")
        video_config = config.get("video_generation", {})
        subs_config = video_config.get("subtitles", {})
        trans_config = video_config.get("transitions", {})

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📝 Subtítulos")
            subs_config["enable"] = st.checkbox("Habilitar Subtítulos por Defecto", value=subs_config.get("enable", True))
            subs_config["font"] = st.text_input("Fuente", value=subs_config.get("font", "Arial"))
            subs_config["font_size"] = st.slider("Tamaño de Fuente", 10, 50, subs_config.get("font_size", 24))
            subs_config["font_color"] = st.color_picker("Color de Fuente", value=subs_config.get("font_color", "#FFFFFF"))
            subs_config["stroke_color"] = st.color_picker("Color de Borde", value=subs_config.get("stroke_color", "#000000"))
            subs_config["stroke_width"] = st.slider("Ancho de Borde", 0.0, 5.0, subs_config.get("stroke_width", 1.5))
            subs_config["position"] = st.selectbox("Posición", ["bottom", "center", "top"], index=["bottom", "center", "top"].index(subs_config.get("position", "bottom")))
            subs_config["max_words"] = st.slider("Máximo de Palabras por Línea", 1, 15, subs_config.get("max_words", 7))

        with col2:
            st.subheader("✨ Transiciones")
            trans_config["default_type"] = st.selectbox("Tipo de Transición por Defecto", ["dissolve", "fade", "wipe", "slide_in", "none"], index=["dissolve", "fade", "wipe", "slide_in", "none"].index(trans_config.get("default_type", "dissolve")))
            trans_config["default_duration"] = st.slider("Duración de Transición por Defecto (s)", 0.1, 5.0, trans_config.get("default_duration", 1.0))

        video_config["subtitles"] = subs_config
        video_config["transitions"] = trans_config
        config["video_generation"] = video_config

    # --- Pestaña de Rutas ---
    with tab_paths:
        st.header("Configuración de Rutas")
        paths_config = config.get("video_generation", {}).get("paths", {})
        st.info("Las rutas son relativas al directorio principal del proyecto.")
        
        paths_config["projects_dir"] = st.text_input("Directorio de Proyectos", value=paths_config.get("projects_dir", "projects"))
        paths_config["output_dir"] = st.text_input("Directorio de Salida (Videos Finales)", value=paths_config.get("output_dir", "output"))
        paths_config["assets_dir"] = st.text_input("Directorio de Assets (Overlays, etc.)", value=paths_config.get("assets_dir", "overlays"))
        paths_config["background_music_dir"] = st.text_input("Directorio de Música de Fondo", value=paths_config.get("background_music_dir", "background_music"))
        
        config["video_generation"]["paths"] = paths_config

    # --- Botón de Guardado --- 
    st.divider()
    if st.button("💾 Guardar Toda la Configuración", type="primary", use_container_width=True):
        if save_config(config):
            # Opcional: forzar un rerun para que toda la app recargue la nueva config
            st.rerun()

# Para poder llamar a esta página desde app.py
if __name__ == "__main__":
    show_settings_page()
