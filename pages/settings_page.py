# pages/settings_page.py
import streamlit as st
from pathlib import Path
from utils.config import load_config, save_config



def show_settings_page():
    """Renderiza la página de configuración completa y centralizada."""
    st.title("⚙️ Configuración Central del Proyecto")
    st.markdown("Aquí puedes gestionar todos los ajustes de la aplicación. Los cambios se guardan en `config.yaml`.")

    config = load_config()

    # Crear pestañas
    tab_general, tab_ai, tab_tts, tab_transcription, tab_fish_audio_monitoring = st.tabs([
        "⚙️ General", 
        "🤖 IA", 
        "🎤 Síntesis de Voz (TTS)",
        "🎙️ Transcripción",
        "🐟 Monitoreo Fish Audio"
    ])

    # --- Pestaña General ---
    with tab_general:
        st.header("Configuración General")
        
        # Configuración de directorios
        st.subheader("📁 Directorios")
        col1, col2 = st.columns(2)
        
        with col1:
            config["output_dir"] = st.text_input(
                "Directorio de Salida",
                value=config.get("output_dir", "output"),
                help="Directorio donde se guardarán los videos generados"
            )
            
            config["projects_dir"] = st.text_input(
                "Directorio de Proyectos",
                value=config.get("projects_dir", "projects"),
                help="Directorio donde se guardarán los proyectos"
            )
        
        with col2:
            config["temp_dir"] = st.text_input(
                "Directorio Temporal",
                value=config.get("temp_dir", "temp"),
                help="Directorio para archivos temporales"
            )
            
            config["background_music_dir"] = st.text_input(
                "Directorio de Música",
                value=config.get("background_music_dir", "background_music"),
                help="Directorio con música de fondo"
            )

    # --- Pestaña de IA ---
    with tab_ai:
        st.header("Configuración de Servicios de IA")
        
        # Configuración de OpenAI
        st.subheader("🔑 OpenAI")
        ai_config = config.get("ai", {})
        
        ai_config["openai_api_key"] = st.text_input(
            "OpenAI API Key",
            value=ai_config.get("openai_api_key", ""),
            type="password",
            help="API key de OpenAI. Obtén una en https://platform.openai.com"
        )
        
        # Configuración de Gemini
        st.subheader("🔑 Google Gemini")
        ai_config["gemini_api_key"] = st.text_input(
            "Gemini API Key",
            value=ai_config.get("gemini_api_key", ""),
            type="password",
            help="API key de Google Gemini. Obtén una en https://makersuite.google.com"
        )
        
        # Configuración de Replicate
        st.subheader("🔑 Replicate")
        ai_config["replicate_api_key"] = st.text_input(
            "Replicate API Key",
            value=ai_config.get("replicate_api_key", ""),
            type="password",
            help="API key de Replicate. Obtén una en https://replicate.com"
        )
        
        # Configuración de Ollama
        st.subheader("🔑 Ollama")
        ai_config["ollama_base_url"] = st.text_input(
            "Ollama Base URL",
            value=ai_config.get("ollama_base_url", "http://localhost:11434"),
            help="URL base de Ollama (por defecto: http://localhost:11434)"
        )
        
        # Modelos por defecto
        st.subheader("🤖 Modelos por Defecto")
        default_models = ai_config.get("default_models", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            default_models["openai"] = st.text_input(
                "Modelo OpenAI",
                value=default_models.get("openai", "gpt-4o-mini"),
                help="Modelo de OpenAI por defecto"
            )
            
            default_models["gemini"] = st.text_input(
                "Modelo Gemini",
                value=default_models.get("gemini", "models/gemini-1.5-flash-latest"),
                help="Modelo de Gemini por defecto"
            )
        
        with col2:
            default_models["ollama"] = st.text_input(
                "Modelo Ollama",
                value=default_models.get("ollama", "llama3"),
                help="Modelo de Ollama por defecto"
            )
            
            default_models["image_generation"] = st.text_input(
                "Modelo de Generación de Imágenes",
                value=default_models.get("image_generation", "black-forest-labs/flux-schnell"),
                help="Modelo para generación de imágenes"
            )
        
        ai_config["default_models"] = default_models
        config["ai"] = ai_config

    # --- Pestaña de TTS ---
    with tab_tts:
        st.header("Configuración de Síntesis de Voz (TTS)")
        
        # Inicializar configuración TTS si no existe
        if "tts" not in config:
            config["tts"] = {
                "default_provider": "edge",
                "edge": {
                    "default_voice": "es-ES-AlvaroNeural",
                    "default_rate": "+0%",
                    "default_pitch": "+0Hz"
                },
                "fish_audio": {
                    "api_key": "TU_CLAVE_FISH_AUDIO_AQUI",
                    "default_model": "speech-1.6",
                    "default_format": "mp3",
                    "default_mp3_bitrate": 128,
                    "default_normalize": True,
                    "default_latency": "normal",
                    "reference_id": None
                }
            }
        
        tts_config = config["tts"]
        
        # Proveedor por defecto
        st.subheader("🔧 Configuración General")
        tts_config["default_provider"] = st.selectbox(
            "Proveedor TTS por Defecto",
            ["edge", "fish"],
            index=0 if tts_config.get("default_provider", "edge") == "edge" else 1,
            format_func=lambda x: "Edge TTS" if x == "edge" else "Fish Audio",
            help="Proveedor de síntesis de voz que se usará por defecto"
        )
        
        st.divider()
        
        # Configuración de Edge TTS
        st.subheader("🔊 Edge TTS (Gratuito)")
        edge_config = tts_config.get("edge", {})
        col1, col2, col3 = st.columns(3)
        
        with col1:
            edge_config["default_voice"] = st.text_input(
                "Voz por Defecto",
                value=edge_config.get("default_voice", "es-ES-AlvaroNeural"),
                help="Voz de Edge TTS por defecto"
            )
        
        with col2:
            edge_config["default_rate"] = st.text_input(
                "Velocidad por Defecto",
                value=edge_config.get("default_rate", "+0%"),
                help="Formato: +X% o -X%"
            )
        
        with col3:
            edge_config["default_pitch"] = st.text_input(
                "Tono por Defecto",
                value=edge_config.get("default_pitch", "+0Hz"),
                help="Formato: +XHz o -XHz"
            )
        
        tts_config["edge"] = edge_config
        
        st.divider()
        
        # Configuración de Fish Audio
        st.subheader("🐟 Fish Audio (Premium)")
        st.info("Fish Audio ofrece calidad premium de síntesis de voz. Requiere una API key válida.")
        
        fish_config = tts_config.get("fish_audio", {})
        
        # API Key
        fish_config["api_key"] = st.text_input(
            "Fish Audio API Key",
            value=fish_config.get("api_key", ""),
            type="password",
            help="API key de Fish Audio. Obtén una en https://fish.audio"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Modelo por defecto
            fish_models = [
                ("speech-1.5", "Fish Audio Speech 1.5"),
                ("speech-1.6", "Fish Audio Speech 1.6 (Recomendado)"),
                ("s1", "Fish Audio S1")
            ]
            default_model = fish_config.get("default_model", "speech-1.6")
            model_index = [m[0] for m in fish_models].index(default_model) if default_model in [m[0] for m in fish_models] else 1
            fish_config["default_model"] = st.selectbox(
                "Modelo por Defecto",
                [m[0] for m in fish_models],
                index=model_index,
                format_func=lambda x: dict(fish_models)[x]
            )
            
            # Formato por defecto
            fish_config["default_format"] = st.selectbox(
                "Formato por Defecto",
                ["mp3", "wav", "pcm"],
                index=0 if fish_config.get("default_format", "mp3") == "mp3" else (1 if fish_config.get("default_format") == "wav" else 2)
            )
            
            # Bitrate por defecto
            fish_config["default_mp3_bitrate"] = st.selectbox(
                "Bitrate MP3 por Defecto",
                [64, 128, 192],
                index=1 if fish_config.get("default_mp3_bitrate", 128) == 128 else (0 if fish_config.get("default_mp3_bitrate") == 64 else 2)
            )
        
        with col2:
            # Latencia por defecto
            fish_config["default_latency"] = st.selectbox(
                "Latencia por Defecto",
                ["normal", "balanced"],
                index=0 if fish_config.get("default_latency", "normal") == "normal" else 1,
                help="Normal: Mayor estabilidad. Balanced: Menor latencia (300ms)"
            )
            
            # Normalizar por defecto
            fish_config["default_normalize"] = st.checkbox(
                "Normalizar Texto por Defecto",
                value=fish_config.get("default_normalize", True),
                help="Mejora la estabilidad para números y texto en inglés/chino"
            )
            
            # Reference ID (opcional)
            fish_config["reference_id"] = st.text_input(
                "Reference ID (Opcional)",
                value=fish_config.get("reference_id", ""),
                help="ID del modelo de referencia personalizado (opcional)"
            )
        
        tts_config["fish_audio"] = fish_config
        config["tts"] = tts_config

    # --- Pestaña de Transcripción ---
    with tab_transcription:
        st.header("🎙️ Configuración de Transcripción")
        
        # Inicializar configuración de transcripción si no existe
        if "transcription" not in config:
            config["transcription"] = {
                "service_type": "local",
                "local": {
                    "model_size": "medium",
                    "device": "cpu",
                    "compute_type": "int8",
                    "default_language": "es",
                    "beam_size": 5
                },
                "replicate": {
                    "default_language": "es",
                    "task": "transcribe",
                    "timestamp": "chunk",
                    "batch_size": 24,
                    "diarise_audio": False,
                    "hf_token": None
                }
            }
        
        transcription_config = config["transcription"]
        
        # Tipo de servicio
        st.subheader("🔧 Configuración General")
        transcription_config["service_type"] = st.selectbox(
            "Servicio de Transcripción",
            ["local", "replicate"],
            index=0 if transcription_config.get("service_type", "local") == "local" else 1,
            format_func=lambda x: "Whisper Local" if x == "local" else "Replicate (Incredibly Fast Whisper)",
            help="Whisper Local: Gratuito, requiere descarga de modelo. Replicate: Más rápido, requiere API key."
        )
        
        st.divider()
        
        # Configuración de Whisper Local
        st.subheader("🔊 Whisper Local (Gratuito)")
        st.info("Whisper local funciona sin conexión a internet pero requiere descargar el modelo.")
        
        local_config = transcription_config.get("local", {})
        col1, col2 = st.columns(2)
        
        with col1:
            # Tamaño del modelo
            model_sizes = [
                ("tiny", "Tiny (39MB) - Más rápido, menos preciso"),
                ("base", "Base (74MB) - Equilibrio velocidad/precisión"),
                ("small", "Small (244MB) - Bueno para la mayoría de casos"),
                ("medium", "Medium (769MB) - Recomendado"),
                ("large-v2", "Large V2 (1550MB) - Muy preciso, lento"),
                ("large-v3", "Large V3 (1550MB) - Más preciso, más lento")
            ]
            default_model = local_config.get("model_size", "medium")
            model_index = [m[0] for m in model_sizes].index(default_model) if default_model in [m[0] for m in model_sizes] else 3
            local_config["model_size"] = st.selectbox(
                "Tamaño del Modelo",
                [m[0] for m in model_sizes],
                index=model_index,
                format_func=lambda x: dict(model_sizes)[x],
                help="Modelos más grandes son más precisos pero más lentos"
            )
            
            # Dispositivo
            local_config["device"] = st.selectbox(
                "Dispositivo",
                ["cpu", "cuda"],
                index=0 if local_config.get("device", "cpu") == "cpu" else 1,
                help="CPU: Más lento pero funciona en cualquier máquina. CUDA: Más rápido si tienes GPU NVIDIA"
            )
        
        with col2:
            # Tipo de cómputo
            compute_types = [
                ("int8", "Int8 - Más rápido, menos preciso"),
                ("float16", "Float16 - Equilibrio velocidad/precisión"),
                ("int8_float16", "Int8 Float16 - Optimizado"),
                ("float32", "Float32 - Más preciso, más lento")
            ]
            default_compute = local_config.get("compute_type", "int8")
            compute_index = [c[0] for c in compute_types].index(default_compute) if default_compute in [c[0] for c in compute_types] else 0
            local_config["compute_type"] = st.selectbox(
                "Tipo de Cómputo",
                [c[0] for c in compute_types],
                index=compute_index,
                format_func=lambda x: dict(compute_types)[x]
            )
            
            # Beam size
            local_config["beam_size"] = st.slider(
                "Beam Size",
                min_value=1,
                max_value=10,
                value=local_config.get("beam_size", 5),
                help="Valores más altos mejoran la precisión pero son más lentos"
            )
        
        # Idioma por defecto
        default_lang = local_config.get("default_language", "es")
        lang_options = ["es", "en", "fr", "pt", "it"]
        lang_names = {"es": "Español", "en": "Inglés", "fr": "Francés", "pt": "Portugués", "it": "Italiano"}
        lang_index = lang_options.index(default_lang) if default_lang in lang_options else 0
        
        local_config["default_language"] = st.selectbox(
            "Idioma por Defecto (Local)",
            lang_options,
            index=lang_index,
            format_func=lambda x: lang_names[x],
            help="Idioma por defecto para transcripción local"
        )
        
        transcription_config["local"] = local_config
        
        st.divider()
        
        # Configuración de Replicate
        st.subheader("🚀 Replicate (Incredibly Fast Whisper)")
        st.info("Replicate ofrece transcripción mucho más rápida y precisa. Requiere API key de Replicate.")
        
        replicate_config = transcription_config.get("replicate", {})
        
        # Verificar si Replicate está disponible
        try:
            import replicate
            replicate_available = True
        except ImportError:
            replicate_available = False
            st.error("❌ Replicate no está disponible. Instala 'replicate' para usar este servicio.")
        
        if replicate_available:
            col1, col2 = st.columns(2)
            
            with col1:
                # Idioma por defecto
                replicate_languages = {
                    "es": "Español",
                    "en": "Inglés", 
                    "fr": "Francés",
                    "pt": "Portugués",
                    "pt-BR": "Portugués Brasileño",
                    "it": "Italiano"
                }
                default_replicate_lang = replicate_config.get("default_language", "es")
                lang_index = list(replicate_languages.keys()).index(default_replicate_lang) if default_replicate_lang in replicate_languages else 0
                replicate_config["default_language"] = st.selectbox(
                    "Idioma por Defecto (Replicate)",
                    list(replicate_languages.keys()),
                    index=lang_index,
                    format_func=lambda x: replicate_languages[x],
                    help="Idioma por defecto para transcripción con Replicate"
                )
                
                # Tarea
                replicate_config["task"] = st.selectbox(
                    "Tarea",
                    ["transcribe", "translate"],
                    index=0 if replicate_config.get("task", "transcribe") == "transcribe" else 1,
                    format_func=lambda x: "Transcribir" if x == "transcribe" else "Traducir",
                    help="Transcribir: Mantener idioma original. Traducir: Convertir a inglés"
                )
            
            with col2:
                # Timestamp
                replicate_config["timestamp"] = st.selectbox(
                    "Tipo de Timestamp",
                    ["chunk", "word"],
                    index=0 if replicate_config.get("timestamp", "chunk") == "chunk" else 1,
                    format_func=lambda x: "Por Chunk" if x == "chunk" else "Por Palabra",
                    help="Chunk: Timestamps por segmentos. Word: Timestamps por palabra (más preciso)"
                )
                
                # Batch size
                replicate_config["batch_size"] = st.slider(
                    "Batch Size",
                    min_value=8,
                    max_value=64,
                    value=replicate_config.get("batch_size", 24),
                    help="Tamaño del batch. Reducir si hay problemas de memoria"
                )
            
            # Diarización de audio
            replicate_config["diarise_audio"] = st.checkbox(
                "Diarización de Audio",
                value=replicate_config.get("diarise_audio", False),
                help="Identificar diferentes hablantes en el audio (requiere Hugging Face token)"
            )
            
            # Hugging Face token (solo si diarización está habilitada)
            if replicate_config["diarise_audio"]:
                replicate_config["hf_token"] = st.text_input(
                    "Hugging Face Token",
                    value=replicate_config.get("hf_token", ""),
                    type="password",
                    help="Token de Hugging Face para diarización. Obtén uno en https://huggingface.co/settings/tokens"
                )
            
            # Información de costos
            st.info("""
            **Costos estimados de Replicate:**
            - Aproximadamente $0.01-0.05 por minuto de audio
            - Más rápido que Whisper local
            - Mejor precisión en múltiples idiomas
            """)
        
        transcription_config["replicate"] = replicate_config
        config["transcription"] = transcription_config

    # --- Pestaña de Monitoreo Fish Audio ---
    with tab_fish_audio_monitoring:
        st.header("🐟 Monitoreo de Créditos Fish Audio")
        
        try:
            from utils.audio_services import get_fish_audio_tracker, FISH_AUDIO_AVAILABLE
            
            if not FISH_AUDIO_AVAILABLE:
                st.error("❌ Fish Audio SDK no está disponible. Instala 'fish-audio-sdk' para usar el monitoreo.")
                st.stop()
            
            tracker = get_fish_audio_tracker()
            usage_summary = tracker.get_usage_summary()
            
            # Información general
            st.subheader("📊 Resumen de Uso")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "💰 Costo Total",
                    f"${usage_summary['total']['cost_usd']:.2f}",
                    f"${usage_summary['total']['cost_usd'] - usage_summary['yesterday']['cost_usd']:.2f}"
                )
            
            with col2:
                st.metric(
                    "📈 Bytes Procesados",
                    f"{usage_summary['total']['bytes_processed']:,}",
                    f"{usage_summary['total']['bytes_processed'] - usage_summary['yesterday']['bytes_processed']:,}"
                )
            
            with col3:
                st.metric(
                    "🎯 Presupuesto Restante",
                    f"${usage_summary['total']['budget_remaining']:.2f}",
                    f"de ${usage_summary['budget_limit']:.2f}"
                )
            
            with col4:
                percentage_used = (usage_summary['total']['cost_usd'] / usage_summary['budget_limit']) * 100
                st.metric(
                    "📊 Porcentaje Usado",
                    f"{percentage_used:.1f}%"
                )
            
            # Barra de progreso del presupuesto
            st.progress(min(percentage_used / 100, 1.0))
            
            # Uso de hoy vs ayer
            st.subheader("📅 Uso Diario")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "📅 Hoy",
                    f"${usage_summary['today']['cost_usd']:.2f}",
                    f"{usage_summary['today']['requests']} requests"
                )
            
            with col2:
                st.metric(
                    "📅 Ayer",
                    f"${usage_summary['yesterday']['cost_usd']:.2f}",
                    f"{usage_summary['yesterday']['requests']} requests"
                )
            
            # Estimaciones
            st.subheader("🔮 Estimaciones")
            
            # Calcular estimaciones
            estimation = tracker.estimate_remaining_usage()
            
            if estimation['can_process']:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "📝 Caracteres Restantes",
                        f"{estimation['estimated_characters']:,}"
                    )
                
                with col2:
                    st.metric(
                        "📖 Palabras Restantes",
                        f"{estimation['estimated_words']:,}"
                    )
                
                with col3:
                    st.metric(
                        "⏱️ Minutos de Audio",
                        f"{estimation['estimated_minutes']}"
                    )
            else:
                st.warning("⚠️ No hay presupuesto restante para procesar más texto.")
            
            # Configuración de alertas
            st.subheader("⚙️ Configuración de Alertas")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Límite de presupuesto
                new_budget_limit = st.number_input(
                    "Límite de Presupuesto ($)",
                    min_value=1.0,
                    max_value=1000.0,
                    value=float(usage_summary['budget_limit']),
                    step=1.0,
                    help="Límite de presupuesto mensual en dólares"
                )
                
                if st.button("💾 Guardar Límite"):
                    tracker.set_budget_limit(new_budget_limit)
                    st.success("✅ Límite de presupuesto actualizado")
                    st.rerun()
            
            with col2:
                # Estimador de texto
                st.subheader("🧮 Estimador de Texto")
                
                sample_text = st.text_area(
                    "Ingresa texto para estimar costo:",
                    placeholder="Escribe aquí el texto que quieres procesar...",
                    height=100
                )
                
                if sample_text:
                    text_estimation = tracker.estimate_remaining_usage(len(sample_text))
                    
                    if text_estimation.get('can_process_text', False):
                        st.success(f"✅ Costo estimado: ${text_estimation['text_cost']:.4f}")
                    else:
                        st.error(f"❌ Costo estimado: ${text_estimation['text_cost']:.4f} - Excede el presupuesto")
            
            # Acciones
            st.subheader("🛠️ Acciones")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Actualizar Datos", type="secondary"):
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Reiniciar Estadísticas", type="secondary"):
                    if st.checkbox("Confirmar reinicio de estadísticas"):
                        tracker.reset_usage()
                        st.success("✅ Estadísticas reiniciadas")
                        st.rerun()
            
            # Información adicional
            st.subheader("ℹ️ Información")
            
            st.info(f"""
            **Precio**: ${usage_summary['cost_per_million_bytes']:.2f} por millón de bytes UTF-8
            
            **Cálculo**: 1 millón de bytes ≈ 500,000 caracteres ≈ 83,000 palabras ≈ 5-6 horas de audio
            
            **Recomendación**: Monitorea tu uso regularmente para optimizar costos.
            """)
            
        except ImportError as e:
            st.error(f"❌ Error importando módulos de Fish Audio: {e}")
        except Exception as e:
            st.error(f"❌ Error cargando datos de monitoreo: {e}")
            st.exception(e)

    # --- Botón de Guardado --- 
    st.divider()
    if st.button("💾 Guardar Toda la Configuración", type="primary", use_container_width=True):
        if save_config(config):
            # Opcional: forzar un rerun para que toda la app recargue la nueva config
            st.rerun()

# Para poder llamar a esta página desde app.py
if __name__ == "__main__":
    show_settings_page()
