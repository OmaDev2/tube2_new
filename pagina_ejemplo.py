#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ejemplo de cómo integrar controles de subtítulos en Streamlit
"""

import os
import json
import logging
import streamlit as st
from pathlib import Path
from utils.video_services import VideoServices

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def show_subtitle_options():
    """Muestra las opciones de personalización de subtítulos"""
    
    st.title("🎬 Generador de Videos con Subtítulos Personalizables")
    
    st.header("Configuración de Subtítulos")
    st.info("Personaliza la apariencia de los subtítulos del video.")

    # Usar disposición en columnas para mejor organización
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
        
        subtitle_bg_opacity = 0.5  # Valor por defecto
        if use_subtitle_background:
            subtitle_bg_opacity = st.slider(
                "Opacidad del fondo",
                min_value=0.1,
                max_value=1.0,
                value=0.5,
                step=0.1
            )
    
    # Botón para generar vista previa
    if st.button("Generar vista previa de subtítulos"):
        # Aquí normalmente se llamaría a la función para generar una vista previa
        # En este ejemplo sólo mostramos los valores seleccionados
        st.success("Configuración de subtítulos guardada")
        
        # Mostrar configuración elegida
        st.subheader("Configuración Actual")
        config = {
            "Aplicar subtítulos": use_subtitles,
            "Fuente": subtitle_font,
            "Tamaño": f"{subtitle_size}px",
            "Color del texto": subtitle_color,
            "Color del borde": subtitle_stroke_color,
            "Grosor del borde": f"{subtitle_stroke_width}px",
            "Posición": subtitle_position,
            "Usar fondo": use_subtitle_background
        }
        
        if use_subtitle_background:
            config["Opacidad del fondo"] = f"{subtitle_bg_opacity:.1f}"
        
        # Mostrar como tabla
        st.json(config)

        # Indicaciones para integración
        st.info("""
        Para añadir subtítulos al video, esta configuración debe integrarse con las funciones:
        - video_service.add_hardcoded_subtitles() - Para subtítulos sin fondo
        - video_service.add_hardcoded_subtitles_with_bg() - Para subtítulos con fondo
        """)

if __name__ == "__main__":
    show_subtitle_options() 