import streamlit as st
import os
from utils.video_services import VideoServices
from pages.efectos_ui import show_effects_ui
from moviepy.editor import AudioFileClip, concatenate_audioclips
from moviepy.audio.fx import all as afx
from utils.transitions import TransitionEffect
import math
from pages.overlays_ui import show_overlays_ui

def show_batch_generator():
    st.title("🎥 Generador de Videos")
    
    # Inicializar el servicio de video
    video_service = VideoServices()
    
    # Sección 1: Cargar imágenes
    st.header("1. Cargar Imágenes")
    uploaded_images = st.file_uploader(
        "Selecciona las imágenes para el video",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )
    
    if not uploaded_images:
        st.warning("Por favor, carga al menos una imagen.")
        return
    
    # Ordenar imágenes alfabéticamente
    uploaded_images = sorted(uploaded_images, key=lambda x: x.name)
    
    # Sección 2: Configuración del video
    st.header("2. Configuración del Video")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        duration_per_image = st.slider(
            "Duración por imagen (segundos)",
            min_value=1.0,
            max_value=30.0,
            value=10.0,
            step=0.5,
            key="duration_per_image"
        )
    
    with col2:
        transition_duration = st.slider(
            "Duración de la transición (segundos)",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.1
        )
    
    with col3:
        transition_type = st.selectbox(
            "Tipo de transición",
            options=TransitionEffect.get_available_transitions(),
            format_func=lambda x: "Sin transición" if x == "none" else "Disolución" if x == "dissolve" else x,
            index=1  # 'dissolve' está en la posición 1 de la lista
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
            step=0.1
        )
    with col2:
        fade_out_duration = st.slider(
            "Fade Out (segundos)",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.1
        )
    
    # Sección 3: Efectos
    st.header("3. Efectos")
    effects_sequence = show_effects_ui()
    
    # Sección 4: Overlays
    overlay_sequence = show_overlays_ui()
    # Asegurar que la duración de cada overlay sea igual a la duración de la imagen
    if overlay_sequence:
        overlay_sequence = [
            (name, opacity, start, duration_per_image)
            for name, opacity, start, _ in overlay_sequence
        ]
    
    # Sección 5: Audio
    st.header("4. Audio (Opcional)")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎵 Música de Fondo")
        
        # Subir nueva música
        new_music = st.file_uploader(
            "Sube un archivo de música",
            type=["mp3", "wav"],
            key="background_music"
        )
        
        if new_music:
            # Guardar en la carpeta background_music
            music_path = os.path.join("background_music", new_music.name)
            with open(music_path, "wb") as f:
                f.write(new_music.getbuffer())
            st.success(f"Música {new_music.name} guardada correctamente!")
            st.experimental_rerun()
        
        # Seleccionar música de fondo
        if os.path.exists("background_music") and os.listdir("background_music"):
            background_music = st.selectbox(
                "Selecciona la música de fondo",
                options=os.listdir("background_music"),
                format_func=lambda x: x
            )
            
            if background_music:
                music_volume = st.slider(
                    "Volumen de la música",
                    min_value=0.0,
                    max_value=0.3,
                    value=0.1,
                    step=0.01,
                    format="%.2f"
                )
                normalize_music = st.checkbox("Normalizar volumen de música", value=True)
                music_loop = st.checkbox("Repetir música", value=True)
        else:
            background_music = None
    
    with col2:
        st.subheader("🎤 Voz en Off")
        voice_over = st.file_uploader(
            "Sube un archivo de voz",
            type=["mp3", "wav"],
            key="voice_over"
        )
        
        if voice_over:
            voice_volume = st.slider(
                "Volumen de la voz",
                min_value=0.0,
                max_value=2.0,
                value=1.0,
                step=0.1
            )
            normalize_voice = st.checkbox("Normalizar volumen de voz", value=True)
            
            # Calcular duración del video
            video_duration = len(uploaded_images) * duration_per_image
            if transition_type != "none":
                video_duration += (len(uploaded_images) - 1) * transition_duration
            
            # Calcular duración del audio
            temp_voice = os.path.join("temp", voice_over.name)
            with open(temp_voice, "wb") as f:
                f.write(voice_over.getbuffer())
            voice_clip = AudioFileClip(temp_voice)
            audio_duration = voice_clip.duration
            os.remove(temp_voice)
            
            # Mostrar información de duración
            st.info(f"""
            Duración del video: {video_duration:.1f} segundos
            Duración del audio: {audio_duration:.1f} segundos
            Diferencia: {abs(video_duration - audio_duration):.1f} segundos
            """)
            
            if video_duration < audio_duration:
                st.warning("⚠️ El video es más corto que el audio. Considera:")
                
                # Calcular duración necesaria por imagen
                needed_duration = (audio_duration - ((len(uploaded_images) - 1) * transition_duration)) / len(uploaded_images)
                
                # Opción de ajuste automático
                auto_adjust = st.checkbox("Ajustar duración automáticamente", value=False)
                if auto_adjust:
                    duration_per_image = needed_duration
                    st.success(f"Duración por imagen ajustada a {needed_duration:.1f} segundos")
                else:
                    st.markdown(f"""
                    - Aumentar la duración por imagen a **{needed_duration:.1f}** segundos
                    - Añadir **{math.ceil((audio_duration - video_duration) / duration_per_image)}** imágenes más
                    - Reducir la duración de las transiciones
                    """)
            elif video_duration > audio_duration * 1.1:  # 10% más largo
                st.warning("⚠️ El video es significativamente más largo que el audio. Considera:")
                
                # Calcular duración óptima por imagen
                optimal_duration = (audio_duration - ((len(uploaded_images) - 1) * transition_duration)) / len(uploaded_images)
                
                # Opción de ajuste automático
                auto_adjust = st.checkbox("Ajustar duración automáticamente", value=False)
                if auto_adjust:
                    duration_per_image = optimal_duration
                    st.success(f"Duración por imagen ajustada a {optimal_duration:.1f} segundos")
                else:
                    st.markdown(f"""
                    - Reducir la duración por imagen a **{optimal_duration:.1f}** segundos
                    - Eliminar **{math.floor((video_duration - audio_duration) / duration_per_image)}** imágenes
                    - Aumentar la duración de las transiciones
                    """)
    
    # Sección 6: Texto
    st.header("5. Texto (Opcional)")
    text = st.text_area("Texto a mostrar en el video")
    if text:
        col1, col2, col3 = st.columns(3)
        with col1:
            text_position = st.selectbox(
                "Posición del texto",
                ["top", "center", "bottom"]
            )
        with col2:
            text_color = st.color_picker("Color del texto", "#FFFFFF")
        with col3:
            text_size = st.slider(
                "Tamaño del texto",
                min_value=10,
                max_value=100,
                value=30
            )
    
    # Botón para generar el video
    if st.button("Generar Video"):
        # Crear contenedor para la barra de progreso
        progress_container = st.empty()
        status_container = st.empty()
        progress_bar = progress_container.progress(0)
        
        def update_progress(progress: float, message: str):
            progress_bar.progress(progress)
            status_container.text(message)
        
        try:
            # Guardar imágenes temporalmente
            temp_images = []
            for uploaded_file in uploaded_images:
                temp_path = os.path.join("temp", uploaded_file.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                temp_images.append(temp_path)
            
            # Procesar música de fondo si se proporciona
            background_music_clip = None
            if background_music:
                music_path = os.path.join("background_music", background_music)
                background_music_clip = AudioFileClip(music_path)
                if normalize_music:
                    background_music_clip = afx.audio_normalize(background_music_clip)
                background_music_clip = background_music_clip.volumex(music_volume)
            
            # Procesar voz en off si se proporciona
            voice_over_clip = None
            if voice_over:
                temp_voice = os.path.join("temp", voice_over.name)
                with open(temp_voice, "wb") as f:
                    f.write(voice_over.getbuffer())
                voice_over_clip = AudioFileClip(temp_voice)
                if normalize_voice:
                    voice_over_clip = afx.audio_normalize(voice_over_clip)
                voice_over_clip = voice_over_clip.volumex(voice_volume)
            
            # Crear el video con callback de progreso
            output_path = video_service.create_video_from_images(
                images=temp_images,
                duration_per_image=duration_per_image,
                transition_duration=transition_duration,
                transition_type=transition_type,
                background_music=background_music_clip,
                voice_over=voice_over_clip,
                text=text if text else None,
                text_position=text_position if text else 'bottom',
                text_color=text_color if text else 'white',
                text_size=text_size if text else 30,
                effects_sequence=effects_sequence,
                overlay_sequence=overlay_sequence,
                fade_in_duration=fade_in_duration,
                fade_out_duration=fade_out_duration,
                music_volume=music_volume if background_music else 0.5,
                music_loop=music_loop if background_music else True,
                progress_callback=update_progress
            )
            
            # Limpiar archivos temporales
            for temp_file in temp_images:
                try:
                    os.remove(temp_file)
                except Exception as e:
                    st.warning(f"No se pudo eliminar el archivo temporal: {e}")
            
            if background_music:
                try:
                    os.remove(music_path)
                except Exception as e:
                    st.warning(f"No se pudo eliminar el archivo de música temporal: {e}")
            
            if voice_over:
                try:
                    os.remove(temp_voice)
                except Exception as e:
                    st.warning(f"No se pudo eliminar el archivo de voz temporal: {e}")
            
            # Limpiar los contenedores de progreso
            progress_container.empty()
            status_container.empty()
            
            # Mostrar el video generado
            st.success("¡Video generado con éxito!")
            st.video(output_path)
            
            # Proporcionar enlace de descarga
            with open(output_path, "rb") as f:
                st.download_button(
                    "Descargar Video",
                    f,
                    file_name=os.path.basename(output_path),
                    mime="video/mp4"
                )
        except Exception as e:
            # Limpiar los contenedores de progreso en caso de error
            progress_container.empty()
            status_container.empty()
            st.error(f"Error al generar el video: {str(e)}")

    if st.button("Procesar batch ahora"):
        import os, uuid
        from pathlib import Path
        from datetime import datetime
        from utils.audio_services import generate_edge_tts_audio
        
        if not st.session_state.batch_projects:
            st.warning("No hay proyectos para procesar. Por favor, añade al menos un proyecto.")
            return
            
        st.info("Procesando proyectos... Esto puede tardar unos minutos.")
        
        # Definir variables de configuración con valores por defecto
        # Configuración de voz
        voz_seleccionada = "es-ES-AlvaroNeural"  # Voz por defecto
        velocidad = 0  # Velocidad por defecto
        tono = 0  # Tono por defecto
            
        # Configuración de IA
        proveedor = "OpenAI"  # Proveedor por defecto
        modelo = "gpt-3.5-turbo"  # Modelo por defecto
        system_prompt = "Eres un guionista experto en videos de YouTube. Escribe guiones atractivos, estructurados y con gancho para la audiencia hispanohablante."
        user_prompt = "Crea un guion para un video titulado: '{titulo}'.\nContexto adicional: '{contexto}'.\nIncluye introducción, desarrollo y conclusión."
        prompt_img_obj = {
            "system_prompt": "Eres un experto en generación de prompts para imágenes.\nTu tarea es crear prompts detallados y descriptivos para generar imágenes que representen el contenido del texto.\nEl estilo debe ser realista.\nIncluye detalles sobre personajes, ambiente, iluminación y composición.",
            "user_prompt": "Texto a representar: {scene_text}\nTítulo del video: {titulo}\nGenera un prompt detallado para crear una imagen que represente este contenido."
        }
            
        # Configuración de video
        use_auto_duration = True  # Por defecto usar cálculo automático de duración
        transition_type = "dissolve"  # Transición por defecto
        transition_duration = 1.0  # Duración de transición por defecto
        duration_per_image = 10.0  # Duración por imagen por defecto
        fade_in_duration = 1.0  # Fade in por defecto
        fade_out_duration = 1.0  # Fade out por defecto
        effects_sequence = []  # Sin efectos por defecto
        overlay_sequence = []  # Sin overlays por defecto
        
        # Crear contenedores para la barra de progreso y mensajes
        progress_container = st.empty()
        status_container = st.empty()
        progress_bar = progress_container.progress(0)
        
        def update_progress(progress: float, message: str):
            progress_bar.progress(progress)
            status_container.text(message)
        
        # Crear carpeta principal de proyectos si no existe
        projects_dir = Path("projects")
        projects_dir.mkdir(exist_ok=True)
        update_progress(0.05, "📁 Creando estructura de carpetas...")
        
        resultados = []
        total_projects = len(st.session_state.batch_projects)
        
        for i, p in enumerate(st.session_state.batch_projects):
            current_progress = (i / total_projects) * 0.9  # 90% del progreso para los proyectos
            update_progress(current_progress, f"🔄 Procesando proyecto {i+1}/{total_projects}: {p['titulo']}")
            
            # Crear nombre seguro para la carpeta del proyecto
            slug = p["titulo"].lower().replace(" ", "_").replace("/", "_")[:30]
            project_id = str(uuid.uuid4())[:8]
            project_folder = projects_dir / f"{slug}__{project_id}"
            
            # Crear estructura de carpetas para el proyecto
            project_folder.mkdir(exist_ok=True)
            
            # Crear subcarpetas
            for subfolder in ["images", "audio", "video", "temp"]:
                subfolder_path = project_folder / subfolder
                subfolder_path.mkdir(exist_ok=True)
            
            # Archivo de metadatos del proyecto
            project_info = {
                "id": project_id,
                "titulo": p["titulo"],
                "contexto": p["contexto"],
                "fecha_creacion": datetime.now().isoformat(),
                "configuracion_voz": {
                    "voz": voz_seleccionada,
                    "velocidad": velocidad,
                    "tono": tono
                }
            }
            
            # Guardar información del proyecto
            info_path = project_folder / "project_info.json"
            with open(info_path, "w", encoding='utf-8') as f:
                import json
                json.dump(project_info, f, indent=4, ensure_ascii=False)
            
            # Generar guion según proveedor/modelo
            prompt_final = user_prompt.format(titulo=p["titulo"], contexto=p["contexto"])
            
            # Actualizar progreso para cada paso del proyecto
            update_progress(current_progress + 0.1, f"📝 Generando guion para: {p['titulo']}")
            guion = ""
            if proveedor == "OpenAI":
                from utils.ai_services import generate_openai_script
                guion = generate_openai_script(system_prompt, prompt_final, model=modelo)
            elif proveedor == "Gemini":
                from utils.ai_services import generate_gemini_script
                guion = generate_gemini_script(system_prompt, prompt_final, model=modelo)
            elif proveedor == "Ollama":
                from utils.ai_services import generate_ollama_script
                guion = generate_ollama_script(system_prompt, prompt_final, model=modelo)
            else:
                from utils.ai_services import generate_openai_script
                guion = generate_openai_script(system_prompt, prompt_final, model="gpt-3.5-turbo")
            
            # Guardar guion
            guion_path = project_folder / "script.txt"
            with open(guion_path, "w", encoding='utf-8') as f:
                f.write(guion)
            
            # Verificar que el guion se generó correctamente antes de continuar
            if guion and not guion.startswith("[ERROR]"):
                # Generar audio para el guion
                try:
                    # Generar el audio para el guion
                    update_progress(current_progress + 0.15, f"🔊 Generando audio para: {p['titulo']}")
                    audio_path = generate_edge_tts_audio(
                        text=guion,
                        voice=voz_seleccionada,
                        rate=f"{velocidad:+d}%",
                        pitch=f"{tono:+d}Hz",
                        output_dir=str(project_folder / "audio")
                    )
                    st.success(f"🔊 Audio generado correctamente en: {audio_path}")
                    
                    # Obtener la duración del audio generado
                    audio_clip = AudioFileClip(audio_path)
                    audio_duration = audio_clip.duration
                    audio_clip.close()
                    
                    st.info(f"Duración del audio: {audio_duration:.2f} segundos")
                    
                    # Realizar transcripción del audio
                    try:
                        from utils.transcription_services import TranscriptionService
                        
                        update_progress(current_progress + 0.2, f"🎯 Iniciando transcripción para: {p['titulo']}")
                        
                        # Inicializar servicio de transcripción
                        transcription_service = TranscriptionService(
                            model_size="small",  # Modelo más ligero para CPU
                            device="cpu",
                            compute_type="int8"  # Optimizado para CPU
                        )
                        
                        # Realizar transcripción
                        segments, metadata = transcription_service.transcribe_audio(
                            audio_path,
                            language="es",
                            beam_size=3,  # Reducido para CPU
                            progress_callback=lambda prog, msg: update_progress(
                                current_progress + 0.2 + (prog * 0.1),
                                f"🎯 Transcripción - {msg}"
                            )
                        )
                        
                        # Guardar transcripción
                        transcription_path = project_folder / "transcription.json"
                        transcription_service.save_transcription(
                            segments,
                            metadata,
                            transcription_path,
                            format="json"
                        )
                        
                        # Actualizar información del proyecto
                        project_info["transcription"] = {
                            "path": str(transcription_path),
                            "metadata": metadata
                        }
                        with open(info_path, "w", encoding='utf-8') as f:
                            json.dump(project_info, f, indent=4, ensure_ascii=False)
                        
                        st.success(f"📝 Transcripción completada y guardada en: {transcription_path}")
                        
                        # Generar escenas y prompts usando la duración óptima
                        try:
                            from utils.scene_generator import SceneGenerator
                            
                            update_progress(current_progress + 0.3, f"🎬 Generando escenas para: {p['titulo']}")
                            
                            # Crear una instancia del generador de escenas
                            scene_generator = SceneGenerator()
                            
                            # Calcular la duración óptima por imagen basada en el audio
                            trans_type = "dissolve" if transition_type != "none" else "none"
                            
                            # Usar la duración del slider si está activada esa opción
                            use_slider_duration = not use_auto_duration
                            
                            if use_slider_duration:
                                # Usar la duración configurada en el slider
                                scene_generator.set_duration_per_image(duration_per_image)
                                st.info(f"Usando duración por imagen configurada: {duration_per_image:.2f} segundos")
                                actual_duration_per_image = duration_per_image
                            else:
                                # Calcular duración óptima automáticamente
                                estimated_num_images = scene_generator.estimate_num_images(
                                    audio_duration, 
                                    min_images=5, 
                                    max_duration_per_image=25.0
                                )
                                
                                optimal_duration = scene_generator.calculate_optimal_duration(
                                    audio_duration,
                                    estimated_num_images,
                                    transition_duration,
                                    trans_type
                                )
                                
                                actual_duration_per_image = scene_generator.duration_per_image
                                
                                st.info(f"""
                                Cálculo automático de duración:
                                - Audio: {audio_duration:.2f} segundos
                                - Imágenes estimadas: ~{estimated_num_images}
                                - Duración óptima por imagen: {actual_duration_per_image:.2f} segundos
                                """)
                            
                            # Cargar transcripción
                            transcription = scene_generator.load_transcription(str(transcription_path))
                            
                            # Segmentar transcripción (usando la duración ya ajustada)
                            scene_segments = scene_generator.segment_transcription(transcription)
                            
                            # Verificar si tenemos suficientes segmentos para cubrir todo el audio
                            # y ajustar si es necesario
                            original_segment_count = len(scene_segments)
                            target_segment_count = scene_generator.ensure_full_audio_coverage(
                                audio_duration,
                                original_segment_count,
                                transition_duration,
                                trans_type
                            )
                            
                            # Si necesitamos más segmentos de los que se generaron automáticamente
                            if target_segment_count > original_segment_count:
                                st.warning(f"""
                                ⚠️ Se necesitan más imágenes para cubrir todo el audio:
                                - Segmentos actuales: {original_segment_count}
                                - Segmentos necesarios: {target_segment_count}
                                - Duración del audio: {audio_duration:.2f} segundos
                                
                                Generando {target_segment_count - original_segment_count} segmentos adicionales...
                                """)
                                
                                # Volver a segmentar la transcripción con una duración más corta por imagen
                                # para obtener más segmentos
                                adjusted_duration = audio_duration / target_segment_count
                                scene_generator.set_duration_per_image(adjusted_duration)
                                scene_segments = scene_generator.segment_transcription(transcription)
                                
                                st.success(f"Se han generado {len(scene_segments)} segmentos para cubrir completamente el audio")
                            
                            st.info(f"Generando {len(scene_segments)} escenas basadas en el audio")
                            
                            # Generar prompts para las escenas
                            prompts = scene_generator.generate_image_prompts(
                                scene_segments,
                                project_info=project_info,
                                prompt_obj=prompt_img_obj,
                                style="realista",
                                progress_callback=lambda prog, msg: update_progress(
                                    current_progress + 0.3 + (prog * 0.1),
                                    f"🎨 {msg}"
                                )
                            )
                            
                            # Guardar escenas y prompts
                            scenes_path = project_folder / "scenes.json"
                            scene_generator.save_scenes(
                                prompts,
                                str(scenes_path),
                                project_info
                            )
                            
                            # Actualizar información del proyecto
                            project_info["scenes"] = {
                                "path": str(scenes_path),
                                "total_scenes": len(prompts),
                                "total_duration": sum(p['duration'] for p in prompts),
                                "duration_per_image": actual_duration_per_image
                            }
                            with open(info_path, "w", encoding='utf-8') as f:
                                json.dump(project_info, f, indent=4, ensure_ascii=False)
                            
                            st.success(f"🎬 Escenas generadas y guardadas en: {scenes_path}")

                            # Generar imágenes con Replicate para cada prompt
                            try:
                                from utils.ai_services import generate_image_with_replicate
                                images_dir = project_folder / "images"
                                images_dir.mkdir(exist_ok=True)
                                
                                # Definir parámetros de formato de imagen con valores por defecto
                                output_format = "webp"  # Formato por defecto
                                aspect_ratio = "1:1"  # Aspecto por defecto
                                output_quality = 80  # Calidad por defecto
                                megapixels = "1"  # Megapíxeles por defecto
                                
                                update_progress(current_progress + 0.4, f"🖼️ Generando imágenes para: {p['titulo']}")
                                
                                for idx, prompt_data in enumerate(prompts):
                                    img_path = images_dir / f"scene_{idx+1}.{output_format}"
                                    try:
                                        st.info(f"🖼️ Generando imagen {idx+1}/{len(prompts)} con Replicate...")
                                        generate_image_with_replicate(
                                            prompt=prompt_data['prompt'],
                                            aspect_ratio=aspect_ratio,
                                            output_format=output_format,
                                            output_quality=output_quality,
                                            megapixels=megapixels,
                                            num_outputs=1,
                                            output_path=str(img_path)
                                        )
                                        st.success(f"Imagen guardada: {img_path}")
                                    except Exception as e:
                                        st.error(f"Error generando imagen {idx+1}: {e}")
                            except Exception as e:
                                st.error(f"❌ Error generando imágenes: {e}")
                        except Exception as e:
                            st.error(f"❌ Error generando escenas: {e}")
                    except Exception as e:
                        st.error(f"❌ Error en transcripción: {e}")
                except Exception as e:
                    st.error(f"❌ Error generando audio: {e}")
            else:
                st.error(f"❌ Error generando guion para {p['titulo']}: {guion}")
            
            # Actualizar progreso final del proyecto
            update_progress(current_progress + 0.2, f"✅ Proyecto completado: {p['titulo']}")
            
            # A partir de aquí, continuar con la creación del video
            st.info(f"⚙️ DEBUG: Iniciando generación de video para: {p['titulo']}")
            
            # Opciones de subtítulos
            st.header("5. Configuración de Subtítulos")
            st.info("Personaliza la apariencia de los subtítulos del video.")

            subtitle_col1, subtitle_col2 = st.columns(2)
            with subtitle_col1:
                use_subtitles = st.checkbox("Añadir subtítulos al video", value=True)
                subtitle_font = st.selectbox(
                    "Fuente de subtítulos",
                    options=["Arial", "Verdana", "DejaVuSans", "Impact", "Times New Roman"],
                    index=0
                )
                subtitle_size = st.slider(
                    "Tamaño de fuente",
                    min_value=20,
                    max_value=80,
                    value=54,
                    step=2
                )
                subtitle_position = st.selectbox(
                    "Posición de subtítulos",
                    options=["bottom", "center", "top"],
                    format_func=lambda x: "Abajo" if x == "bottom" else "Centro" if x == "center" else "Arriba",
                    index=0
                )

            with subtitle_col2:
                subtitle_color = st.color_picker(
                    "Color del texto",
                    value="#FFFFFF"  # Blanco por defecto
                )
                subtitle_stroke_color = st.color_picker(
                    "Color del borde",
                    value="#000000"  # Negro por defecto
                )
                subtitle_stroke_width = st.slider(
                    "Grosor del borde",
                    min_value=0,
                    max_value=10,
                    value=1,
                    step=1
                )
                use_subtitle_background = st.checkbox("Usar fondo para subtítulos", value=False)
                if use_subtitle_background:
                    subtitle_bg_opacity = st.slider(
                        "Opacidad del fondo",
                        min_value=0.1,
                        max_value=1.0,
                        value=0.5,
                        step=0.1
                    )

            try:
                # Verificar que tenemos todos los datos necesarios para crear el video
                if audio_path and os.path.exists(audio_path) and images_dir:
                    st.info(f"✅ DEBUG: Condiciones válidas - audio_path: {audio_path}, images_dir: {images_dir}")
                    update_progress(current_progress + 0.7, f"🎬 Generando video final para: {p['titulo']}")
                    
                    # Asegurar que output_format está definido
                    output_format = "webp"  # Formato por defecto
                    
                    # Crear lista de rutas de imágenes generadas
                    st.info(f"🔍 DEBUG: Buscando imágenes en: {images_dir} con formato: {output_format}")
                    image_files = sorted(list(images_dir.glob(f"scene_*.{output_format}")))
                    st.info(f"🔍 DEBUG: Encontradas {len(image_files)} imágenes")
                    
                    if not image_files:
                        st.error(f"❌ No se encontraron imágenes para el proyecto {p['titulo']}")
                    else:
                        # Cargar el archivo de audio
                        audio_clip = AudioFileClip(audio_path)
                        audio_duration = audio_clip.duration
                        
                        # Crear instancia de VideoServices
                        video_service = VideoServices()
                        
                        # Crear directorio de video si no existe
                        video_dir = project_folder / "video"
                        video_dir.mkdir(exist_ok=True)
                        
                        # Ruta para el video final
                        video_output_path = str(video_dir / f"{slug}_video.mp4")
                        
                        try:
                            st.info(f"🎬 Generando video con {len(image_files)} imágenes y audio de {audio_duration:.2f} segundos...")
                            
                            # Definir duración por imagen
                            actual_duration_per_image = None
                            # Usar una duración por defecto o calculada
                            if 'scene_generator' in vars() and scene_generator:
                                actual_duration_per_image = scene_generator.duration_per_image
                            else:
                                # Calcular directamente con transiciones
                                if transition_type != "none" and transition_duration > 0 and len(image_files) > 1:
                                    # Fórmula mejorada con margen de seguridad
                                    transitions_total = (len(image_files) - 1) * transition_duration
                                    actual_duration_per_image = (audio_duration + transitions_total) * 1.01 / len(image_files)
                                else:
                                    # Añadir 1% de margen de seguridad
                                    actual_duration_per_image = (audio_duration * 1.01) / len(image_files)
                            
                            # Verificar si la duración calculada es suficiente para cubrir todo el audio
                            if transition_type != "none" and transition_duration > 0 and len(image_files) > 1:
                                expected_video_duration = (actual_duration_per_image * len(image_files)) - ((len(image_files) - 1) * transition_duration)
                            else:
                                expected_video_duration = actual_duration_per_image * len(image_files)
                            
                            # Si la duración es insuficiente, ajustar con margen adicional
                            if expected_video_duration < audio_duration:
                                adjustment = (audio_duration * 1.01) / expected_video_duration
                                actual_duration_per_image *= adjustment
                                st.warning(f"""
                                ⚠️ Ajuste de duración necesario para cubrir todo el audio:
                                - Duración esperada original: {expected_video_duration:.2f}s
                                - Audio: {audio_duration:.2f}s
                                - Factor de ajuste: {adjustment:.3f}
                                - Nueva duración por imagen: {actual_duration_per_image:.2f}s
                                """)
                                
                                # Recalcular la duración esperada
                                if transition_type != "none" and transition_duration > 0 and len(image_files) > 1:
                                    expected_video_duration = (actual_duration_per_image * len(image_files)) - ((len(image_files) - 1) * transition_duration)
                                else:
                                    expected_video_duration = actual_duration_per_image * len(image_files)
                                
                                st.info(f"Nueva duración esperada: {expected_video_duration:.2f}s (audio: {audio_duration:.2f}s)")
                            
                            # Generar el video usando la duración calculada
                            output_path = video_service.create_video_from_images(
                                images=[str(img) for img in image_files],
                                duration_per_image=actual_duration_per_image,
                                transition_duration=transition_duration,
                                transition_type=transition_type,
                                background_music=None,  # Ya tenemos el audio principal
                                voice_over=audio_clip,
                                effects_sequence=effects_sequence,
                                overlay_sequence=overlay_sequence,
                                fade_in_duration=fade_in_duration,
                                fade_out_duration=fade_out_duration,
                                progress_callback=lambda prog, msg: update_progress(
                                    current_progress + 0.7 + (prog * 0.2),
                                    f"🎬 {msg}"
                                )
                            )
                            
                            # Mover o copiar el video generado a la ubicación final
                            import shutil
                            shutil.copy(output_path, video_output_path)
                            
                            # Calcular duración del video
                            video_duration = 0
                            if transition_type != "none" and transition_duration > 0 and len(image_files) > 1:
                                video_duration = (len(image_files) * actual_duration_per_image) - ((len(image_files) - 1) * transition_duration)
                            else:
                                video_duration = len(image_files) * actual_duration_per_image
                            
                            # Actualizar el project_info con la información del video
                            project_info["video"] = {
                                "path": video_output_path,
                                "duration": video_duration,
                                "settings": {
                                    "duration_per_image": actual_duration_per_image,
                                    "transition_type": transition_type,
                                    "transition_duration": transition_duration
                                }
                            }
                            
                            # Guardar la información actualizada del proyecto
                            with open(info_path, "w", encoding='utf-8') as f:
                                json.dump(project_info, f, indent=4, ensure_ascii=False)
                                
                            st.success(f"✅ Video generado exitosamente: {video_output_path}")
                            
                            # Opcional: Añadir subtítulos al video
                            try:
                                if use_subtitles and transcription_path and os.path.exists(str(transcription_path)):
                                    # Crear video con subtítulos
                                    subtitled_output = str(video_dir / f"{slug}_subtitled.mp4")
                                    
                                    # Cargar transcripción
                                    with open(transcription_path, 'r', encoding='utf-8') as f:
                                        transcription_data = json.load(f)
                                    
                                    # Preparar segmentos para subtítulos
                                    subtitle_segments = []
                                    for segment in transcription_data.get('segments', []):
                                        subtitle_segments.append({
                                            'text': segment.get('text', ''),
                                            'start': segment.get('start', 0),
                                            'end': segment.get('end', 0)
                                        })
                                    
                                    # Añadir subtítulos
                                    if subtitle_segments:
                                        st.info(f"🎬 Añadiendo subtítulos al video...")
                                        
                                        # Usar las opciones de subtítulos configuradas por el usuario
                                        if use_subtitle_background:
                                            # Versión con fondo
                                            video_service.add_hardcoded_subtitles_with_bg(
                                                video_path=video_output_path,
                                                segments=subtitle_segments,
                                                output_path=subtitled_output,
                                                font=subtitle_font,
                                                font_size=subtitle_size,
                                                color=subtitle_color,
                                                stroke_color=subtitle_stroke_color,
                                                stroke_width=subtitle_stroke_width,
                                                position=subtitle_position,
                                                bg_opacity=subtitle_bg_opacity
                                            )
                                        else:
                                            # Versión sin fondo
                                            video_service.add_hardcoded_subtitles(
                                                video_path=video_output_path,
                                                segments=subtitle_segments,
                                                output_path=subtitled_output,
                                                font=subtitle_font,
                                                font_size=subtitle_size,
                                                color=subtitle_color,
                                                stroke_color=subtitle_stroke_color,
                                                stroke_width=subtitle_stroke_width,
                                                position=subtitle_position
                                            )
                                        
                                        # Actualizar información del proyecto con los ajustes de subtítulos
                                        project_info["video"]["subtitled_path"] = subtitled_output
                                        project_info["video"]["subtitle_settings"] = {
                                            "font": subtitle_font,
                                            "size": subtitle_size,
                                            "color": subtitle_color,
                                            "stroke_color": subtitle_stroke_color,
                                            "stroke_width": subtitle_stroke_width,
                                            "position": subtitle_position,
                                            "with_background": use_subtitle_background
                                        }
                                        if use_subtitle_background:
                                            project_info["video"]["subtitle_settings"]["bg_opacity"] = subtitle_bg_opacity
                                            
                                        with open(info_path, "w", encoding='utf-8') as f:
                                            json.dump(project_info, f, indent=4, ensure_ascii=False)
                                            
                                        st.success(f"✅ Video con subtítulos generado: {subtitled_output}")
                            except Exception as e:
                                st.error(f"❌ Error al añadir subtítulos: {e}")
                        except Exception as e:
                            st.error(f"❌ Error al generar el video para {p['titulo']}: {e}")
                if not image_files:
                        st.error(f"❌ No se pudieron recuperar los archivos necesarios")
                        continue
                else:
                    st.warning(f"⚠️ DEBUG: Condiciones no cumplidas - audio_path definido: {bool(audio_path)}, images_dir definido: {bool(images_dir)}, audio_path existe: {os.path.exists(audio_path) if audio_path else False}")
                    # Intentar recuperar las rutas con información existente
                    if project_folder:
                        # Forzar la búsqueda de imágenes en la carpeta images
                        images_dir = project_folder / "images"
                        st.info(f"🔍 DEBUG: Intentando recuperar imágenes de: {images_dir}")
                        
                        # Verificar si hay algún archivo de audio
                        audio_dir = project_folder / "audio"
                        audio_files = list(audio_dir.glob("*.mp3"))
                        if audio_files:
                            audio_path = str(audio_files[0])
                            st.info(f"🔍 DEBUG: Usando audio recuperado: {audio_path}")
                            
                            # Verificar output_format
                            output_format = "webp"  # Formato por defecto
                            
                            # Buscar imágenes
                            image_files = sorted(list(images_dir.glob(f"scene_*.{output_format}")))
                            st.info(f"🔍 DEBUG: Recuperadas {len(image_files)} imágenes")
                            
                            if image_files and os.path.exists(audio_path):
                                update_progress(current_progress + 0.7, f"🎬 Generando video final para: {p['titulo']} (recuperado)")
                                st.success("🔄 Recuperación exitosa - continuando con la generación de video")
                            else:
                                st.error(f"❌ No se pudieron recuperar los archivos necesarios")
                                continue
                        else:
                            st.error(f"❌ No se encontraron archivos de audio para recuperar")
                            continue
                    else:
                        st.error(f"❌ No se puede generar el video para {p['titulo']} - Faltan datos necesarios")
                        continue
            except Exception as e:
                st.error(f"❌ Error general en la generación de video para {p['titulo']}: {e}")
            
            # Añadir el proyecto al listado de resultados
            resultados.append({
                "titulo": p["titulo"],
                "contexto": p["contexto"],
                "guion": guion if 'guion' in vars() and guion is not None else "",
                "audio": audio_path if 'audio_path' in vars() and audio_path is not None else None,
                "carpeta": str(project_folder),
                "project_info": project_info
            })
        
        # Progreso final
        update_progress(1.0, "🎉 ¡Procesamiento por lotes completado!")
        st.success("Todos los proyectos han sido procesados exitosamente.")