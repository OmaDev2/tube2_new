import streamlit as st
import os
from utils.video_services import VideoServices
from pages.efectos_ui import show_effects_ui
from moviepy.editor import AudioFileClip, concatenate_audioclips
from moviepy.audio.fx import all as afx
from utils.transitions import TransitionEffect
import math
from pages.overlays_ui import show_overlays_ui

def show_video_generator():
    st.title("🎥 Generador de Videos Individual")
    
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
            st.rerun()
        
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
    if st.button("Generar Video Individual"):
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
            
            # --- INICIO DE LA CORRECCIÓN POR TRANSICIONES ---
            # Asumiendo que voice_over_clip ya ha sido cargado y tiene una duración válida
            # Y que transition_duration ya está definido
            
            num_scenes = len(temp_images)

            if num_scenes > 1 and transition_duration > 0 and voice_over_clip is not None:
                # 1. Calcular el tiempo total que se perderá por la superposición de transiciones.
                total_overlap_time = (num_scenes - 1) * transition_duration
                st.info(f"Ajustando duraciones de {num_scenes} escenas para compensar {transition_duration}s de transición...")
                st.info(f"Tiempo total de superposición a compensar: {total_overlap_time:.2f}s")

                # 2. Calcular la duración objetivo que debe tener la suma de todos los clips.
                #    Debe ser la duración del audio MÁS el tiempo que se perderá.
                audio_duration = voice_over_clip.duration
                target_clips_total_duration = audio_duration + total_overlap_time
                st.info(f"Duración objetivo total de los clips (incluyendo compensación): {target_clips_total_duration:.2f}s")

                # 3. Calcular la duración total actual de las escenas (basada en duration_per_image).
                current_scenes_total_duration = num_scenes * duration_per_image
                
                if current_scenes_total_duration <= 0:
                    st.error("La duración total actual de las escenas es 0. No se puede realizar el ajuste.")
                else:
                    # 4. Calcular un factor de ajuste.
                    adjustment_factor = target_clips_total_duration / current_scenes_total_duration
                    st.info(f"Factor de ajuste de duración: {adjustment_factor:.4f}")

                    # 5. Recalcular la duración por imagen.
                    duration_per_image = duration_per_image * adjustment_factor
                    st.success(f"Nueva duración por imagen ajustada: {duration_per_image:.2f}s")

            # --- FIN DE LA CORRECCIÓN ---

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