import streamlit as st

def show_effects_ui():
    """
    Muestra la interfaz de usuario para definir una secuencia de efectos
    """
    st.header("🎬 Secuencia de Efectos")
    
    # Lista de efectos disponibles
    efectos_disponibles = {
        "kenburns": "Ken Burns",
        "zoom_in": "Zoom In",
        "zoom_out": "Zoom Out",
        "pan_left": "Paneo Izquierda",
        "pan_right": "Paneo Derecha",
        "fade_in": "Fade In",
        "fade_out": "Fade Out",
        "mirror_x": "Espejo Horizontal",
        "mirror_y": "Espejo Vertical"
    }
    
    # Parámetros por defecto para cada efecto
    parametros_por_defecto = {
        "kenburns": {
            "duration": 1.0,
            "zoom_start": 1.0,
            "zoom_end": 1.5,
            "pan_start": (0.0, 0.0),
            "pan_end": (0.2, 0.2)
        },
        "zoom_in": {"duration": 1.0, "zoom_factor": 1.5},
        "zoom_out": {"duration": 1.0, "zoom_factor": 1.5},
        "pan_left": {"duration": 1.0, "distance": 0.5},
        "pan_right": {"duration": 1.0, "distance": 0.5},
        "fade_in": {"duration": 1.0},
        "fade_out": {"duration": 1.0},
        "mirror_x": {},
        "mirror_y": {}
    }
    
    # Seleccionar efectos para la secuencia
    st.subheader("Selecciona los efectos para tu secuencia")
    efectos_seleccionados = st.multiselect(
        "Efectos (se aplicarán en orden)",
        list(efectos_disponibles.keys()),
        format_func=lambda x: efectos_disponibles[x],
        default=["zoom_in", "zoom_out"],  # Efectos seleccionados por defecto
        key="efectos_secuencia"
    )
    
    # Configurar parámetros para cada efecto seleccionado
    efectos_configurados = []
    
    for efecto in efectos_seleccionados:
        st.subheader(f"Configuración para {efectos_disponibles[efecto]}")
        params = {}
        
        # Configurar duración si el efecto la requiere
        if efecto in ["kenburns", "zoom_in", "zoom_out", "pan_left", "pan_right", "fade_in", "fade_out"]:
            params["duration"] = st.slider(
                "Duración (segundos)",
                min_value=0.1,
                max_value=3.0,
                value=parametros_por_defecto[efecto]["duration"],
                step=0.1,
                key=f"duracion_{efecto}"
            )
        
        # Configurar parámetros específicos para Ken Burns
        if efecto == "kenburns":
            col1, col2 = st.columns(2)
            with col1:
                params["zoom_start"] = st.slider(
                    "Zoom Inicial",
                    min_value=1.0,
                    max_value=2.0,
                    value=float(parametros_por_defecto[efecto]["zoom_start"]),
                    step=0.1,
                    key=f"zoom_start_{efecto}"
                )
                pan_start_x = st.slider(
                    "Paneo Inicial X",
                    min_value=-0.5,
                    max_value=0.5,
                    value=float(parametros_por_defecto[efecto]["pan_start"][0]),
                    step=0.1,
                    key=f"pan_start_x_{efecto}"
                )
                pan_start_y = st.slider(
                    "Paneo Inicial Y",
                    min_value=-0.5,
                    max_value=0.5,
                    value=float(parametros_por_defecto[efecto]["pan_start"][1]),
                    step=0.1,
                    key=f"pan_start_y_{efecto}"
                )
            with col2:
                params["zoom_end"] = st.slider(
                    "Zoom Final",
                    min_value=1.0,
                    max_value=2.0,
                    value=float(parametros_por_defecto[efecto]["zoom_end"]),
                    step=0.1,
                    key=f"zoom_end_{efecto}"
                )
                pan_end_x = st.slider(
                    "Paneo Final X",
                    min_value=-0.5,
                    max_value=0.5,
                    value=float(parametros_por_defecto[efecto]["pan_end"][0]),
                    step=0.1,
                    key=f"pan_end_x_{efecto}"
                )
                pan_end_y = st.slider(
                    "Paneo Final Y",
                    min_value=-0.5,
                    max_value=0.5,
                    value=float(parametros_por_defecto[efecto]["pan_end"][1]),
                    step=0.1,
                    key=f"pan_end_y_{efecto}"
                )
            # Crear las tuplas de paneo
            params["pan_start"] = (pan_start_x, pan_start_y)
            params["pan_end"] = (pan_end_x, pan_end_y)
        
        # Configurar factor de zoom para efectos de zoom
        elif efecto in ["zoom_in", "zoom_out"]:
            params["zoom_factor"] = st.slider(
                "Factor de Zoom",
                min_value=1.1,
                max_value=3.0,
                value=parametros_por_defecto[efecto]["zoom_factor"],
                step=0.1,
                key=f"zoom_{efecto}"
            )
        
        # Configurar distancia para efectos de paneo
        elif efecto in ["pan_left", "pan_right"]:
            params["distance"] = st.slider(
                "Distancia de Paneo",
                min_value=0.1,
                max_value=1.0,
                value=parametros_por_defecto[efecto]["distance"],
                step=0.1,
                key=f"distancia_{efecto}"
            )
        
        efectos_configurados.append((efecto, params))
    
    return efectos_configurados 