# pages/settings.py
import streamlit as st
import yaml
from pathlib import Path
import os
# Importar funciones de utils y config
from utils.ai_services import list_openai_models, list_gemini_models, list_ollama_models, generate_openai_script, generate_gemini_script, generate_ollama_script
from utils.config import load_config, save_config # <-- Importar desde utils.config

# YA NO SE DEFINEN load_config ni save_config AQUÍ

def show_settings():
    st.title("⚙️ Configuración")
    # Usa la función importada
    config = load_config()
    if not config:
        st.error("Error Crítico: No se pudo cargar la configuración inicial.")
        return

    st.info(f"Editando configuración desde: {Path('config.yaml').resolve()}")

    # Usar pestañas para organizar
    tab_keys, tab_models, tab_storage, tab_video, tab_test = st.tabs([
        "🔑 Claves API", "🤖 Modelos IA", "📁 Almacenamiento", "🎬 Video", "🔎 Prueba Modelos"
    ])

    with tab_keys:
        st.subheader("Claves y Endpoints de IA")
        ai = config.get("ai", {}) # Obtener sección AI o dict vacío
        # Usar get para evitar errores si una clave no existe en el yaml
        openai_api_key = st.text_input("OpenAI API Key", value=ai.get("openai_api_key", ""), type="password", help="Tu clave secreta de OpenAI.")
        gemini_api_key = st.text_input("Gemini API Key", value=ai.get("gemini_api_key", ""), type="password", help="Tu clave secreta de Google AI Studio.")
        replicate_api_key = st.text_input("Replicate API Key", value=ai.get("replicate_api_key", ""), type="password", help="Tu token de API de Replicate.")
        ollama_base_url = st.text_input("Ollama Base URL", value=ai.get("ollama_base_url", "http://localhost:11434"), help="La dirección donde corre tu servidor Ollama.")

    with tab_models:
        st.subheader("Modelos Favoritos y Por Defecto")
        # Asegurar que default_models existe
        default_models = ai.setdefault("default_models", {})

        # --- OpenAI ---
        st.markdown("#### OpenAI")
        openai_list = default_models.get("openai_list", [])
        openai_models_available = [m[0] for m in list_openai_models(openai_api_key) if not m[0].startswith("[ERROR]")]
        if not openai_models_available: st.warning("No se pudieron obtener modelos de OpenAI. Verifica la API Key.")
        openai_list_valid = [m for m in openai_list if m in openai_models_available] # Favoritos que aún existen
        openai_list_new = st.multiselect(
            "Modelos favoritos OpenAI", options=openai_models_available, default=openai_list_valid, key="openai_fav_select"
        )
        openai_options_default = openai_list_new if openai_list_new else openai_models_available # Opciones para default
        openai_current_default = default_models.get("openai", "")
        openai_default_index = 0
        if openai_current_default in openai_options_default:
            openai_default_index = openai_options_default.index(openai_current_default)
        elif openai_options_default: # Si hay opciones pero el default no está, seleccionar el primero
             openai_current_default = openai_options_default[0]
        else: # No hay opciones
             openai_current_default = ""

        openai_model_new = st.selectbox(
            "Modelo OpenAI por defecto", options=openai_options_default, index=openai_default_index, key="openai_def_select"
        ) if openai_options_default else st.text_input("Modelo OpenAI por defecto", value=openai_current_default, disabled=True)

        # --- Gemini ---
        st.markdown("#### Gemini")
        gemini_list = default_models.get("gemini_list", [])
        gemini_models_available = [m[0] for m in list_gemini_models(gemini_api_key) if not m[0].startswith("[ERROR]")]
        if not gemini_models_available: st.warning("No se pudieron obtener modelos de Gemini. Verifica la API Key.")
        gemini_list_valid = [m for m in gemini_list if m in gemini_models_available]
        gemini_list_new = st.multiselect(
            "Modelos favoritos Gemini", options=gemini_models_available, default=gemini_list_valid, key="gemini_fav_select"
        )
        gemini_options_default = gemini_list_new if gemini_list_new else gemini_models_available
        gemini_current_default = default_models.get("gemini", "")
        gemini_default_index = 0
        if gemini_current_default in gemini_options_default:
             gemini_default_index = gemini_options_default.index(gemini_current_default)
        elif gemini_options_default:
             gemini_current_default = gemini_options_default[0]
        else:
             gemini_current_default = ""

        gemini_model_new = st.selectbox(
            "Modelo Gemini por defecto", options=gemini_options_default, index=gemini_default_index, key="gemini_def_select"
        ) if gemini_options_default else st.text_input("Modelo Gemini por defecto", value=gemini_current_default, disabled=True)


        # --- Ollama ---
        st.markdown("#### Ollama")
        ollama_list = default_models.get("ollama_list", []) # Favoritos guardados
        ollama_models_available = [m[0] for m in list_ollama_models(ollama_base_url) if not m[0].startswith("[ERROR]")]
        if not ollama_models_available: st.warning(f"No se pudieron obtener modelos de Ollama en {ollama_base_url}. ¿Está corriendo?")
        ollama_list_valid = [m for m in ollama_list if m in ollama_models_available]
        ollama_list_new = st.multiselect(
             "Modelos favoritos Ollama", options=ollama_models_available, default=ollama_list_valid, key="ollama_fav_select"
        )
        ollama_options_default = ollama_list_new if ollama_list_new else ollama_models_available
        ollama_current_default = default_models.get("ollama", "")
        ollama_default_index = 0
        if ollama_current_default in ollama_options_default:
             ollama_default_index = ollama_options_default.index(ollama_current_default)
        elif ollama_options_default:
             ollama_current_default = ollama_options_default[0]
        else:
             ollama_current_default = "" # No poner 'llama3' si no está disponible

        ollama_model_new = st.selectbox(
             "Modelo Ollama por defecto", options=ollama_options_default, index=ollama_default_index, key="ollama_def_select"
        ) if ollama_options_default else st.text_input("Modelo Ollama por defecto", value=ollama_current_default, help="Escribe el nombre si no aparece en la lista", disabled=(not ollama_models_available and not ollama_current_default))


        # --- Otros Modelos ---
        st.markdown("#### Otros Modelos")
        # Usar get con fallback por si no existen en el config
        image_model_new = st.text_input("Modelo Imágenes (Replicate - ej: stability-ai/stable-diffusion-3)", value=default_models.get("image", "stability-ai/stable-diffusion-3"))
        voice_model_new = st.text_input("Voz TTS por defecto (ej: es-ES-AlvaroNeural)", value=default_models.get("voice", "es-ES-AlvaroNeural"))


    with tab_storage:
        st.subheader("Almacenamiento de Proyectos")
        # Asegurar que storage existe
        storage = config.setdefault("storage", {"type": "local", "local_path": "./proyectos_generados"})
        storage_type_new = st.selectbox("Tipo (Solo 'local' soportado actualmente)", ["local"], index=0) # Forzar local por ahora
        local_path_new = st.text_input("Ruta local de proyectos", value=storage.get("local_path", "./proyectos_generados"), help="Ruta relativa al directorio de la app o absoluta donde se guardarán las carpetas de los proyectos.")
        # Crear directorio si no existe al guardar? Se hace en save_config y get_projects_dir

    with tab_video:
        st.subheader("Configuración de Video por Defecto")
        # Asegurar que video existe
        video = config.setdefault("video", {"default_resolution": "1080p", "default_fps": 30})
        default_resolution_new = st.selectbox("Resolución", ["1080p", "720p"], index=["1080p", "720p"].index(video.get("default_resolution", "1080p")))
        default_fps_new = st.number_input("FPS", min_value=15, max_value=60, value=video.get("default_fps", 30))


    # --- Guardar configuración ---
    st.markdown("---")
    if st.button("💾 Guardar Toda la Configuración", type="primary"):
        # Actualizar el diccionario 'config' COMPLETO antes de guardar
        config["ai"] = {
            "openai_api_key": openai_api_key,
            "gemini_api_key": gemini_api_key,
            "replicate_api_key": replicate_api_key,
            "ollama_base_url": ollama_base_url,
            "default_models": {
                "openai": openai_model_new,
                "openai_list": openai_list_new,
                "gemini": gemini_model_new,
                "gemini_list": gemini_list_new,
                "ollama": ollama_model_new,
                "ollama_list": ollama_list_new, # Guardar favoritos de ollama también
                "image": image_model_new,
                "voice": voice_model_new
            }
        }
        config["storage"] = {
            "type": storage_type_new, # Aunque forzamos 'local' arriba
            "local_path": local_path_new,
            # Mantener config de firebase si existía, aunque no se use por ahora
            "firebase_config": storage.get("firebase_config", {})
        }
        config["video"] = {
            "default_resolution": default_resolution_new,
            "default_fps": default_fps_new
        }

        # Llama a la función importada de utils.config
        save_config(config)
        # El mensaje de éxito se muestra desde save_config


    with tab_test:
        # --- Prueba rápida de modelos ---
        st.subheader("🔎 Prueba Rápida de Modelos de Texto")
        prompt_test = st.text_area("Prompt de prueba", "Dime una curiosidad sobre los Pirineos catalanes.", key="test_prompt_area")
        col_test1, col_test2, col_test3 = st.columns(3)

        with col_test1:
            st.markdown("**OpenAI**")
            model_to_test_openai = config.get("ai",{}).get("default_models",{}).get("openai")
            key_openai = config.get("ai",{}).get("openai_api_key")
            if model_to_test_openai and key_openai:
                if st.button(f"Probar ({model_to_test_openai})", key="test_openai"):
                     with st.spinner("Consultando OpenAI..."):
                          respuesta = generate_openai_script("", prompt_test, model=model_to_test_openai, api_key=key_openai)
                          st.text_area("Respuesta OpenAI", respuesta, height=150, key="resp_openai", disabled=True)
            else:
                 st.caption("Configura la clave y modelo por defecto.")

        with col_test2:
             st.markdown("**Gemini**")
             model_to_test_gemini = config.get("ai",{}).get("default_models",{}).get("gemini")
             key_gemini = config.get("ai",{}).get("gemini_api_key")
             if model_to_test_gemini and key_gemini:
                  if st.button(f"Probar ({model_to_test_gemini})", key="test_gemini"):
                       with st.spinner("Consultando Gemini..."):
                            respuesta = generate_gemini_script("", prompt_test, model=model_to_test_gemini, api_key=key_gemini)
                            st.text_area("Respuesta Gemini", respuesta, height=150, key="resp_gemini", disabled=True)
             else:
                  st.caption("Configura la clave y modelo por defecto.")

        with col_test3:
             st.markdown("**Ollama**")
             model_to_test_ollama = config.get("ai",{}).get("default_models",{}).get("ollama")
             host_ollama = config.get("ai",{}).get("ollama_base_url")
             if model_to_test_ollama and host_ollama:
                  if st.button(f"Probar ({model_to_test_ollama})", key="test_ollama"):
                       with st.spinner("Consultando Ollama..."):
                            respuesta = generate_ollama_script("", prompt_test, model=model_to_test_ollama, ollama_host=host_ollama)
                            st.text_area("Respuesta Ollama", respuesta, height=150, key="resp_ollama", disabled=True)
             else:
                  st.caption("Configura el host y modelo por defecto.")