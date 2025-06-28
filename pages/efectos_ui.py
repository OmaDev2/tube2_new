import streamlit as st

def show_effects_ui(key_prefix: str = ""):
    """
    Muestra la interfaz de usuario para definir una secuencia de efectos
    
    Args:
        key_prefix: Prefijo para las keys de Streamlit (para evitar conflictos en batch)
    """
    st.header("🎬 Secuencia de Efectos")
    
    # Lista de efectos disponibles - ACTUALIZADA con todos los efectos
    efectos_disponibles = {
        "kenburns": "Ken Burns",
        "zoom_in": "Zoom In",
        "zoom_out": "Zoom Out",
        "pan_left": "Paneo Izquierda",
        "pan_right": "Paneo Derecha",
        "pan_up": "Paneo Arriba",
        "pan_down": "Paneo Abajo",
        "shake": "Shake/Temblor",
        "fade_in": "Fade In",
        "fade_out": "Fade Out",
        "mirror_x": "Espejo Horizontal",
        "mirror_y": "Espejo Vertical",
        "rotate_180": "Rotar 180°",
        "shake_zoom_combo": "Shake + Zoom Combo",
        "shake_kenburns_combo": "Shake + Ken Burns Combo"
    }
    
    # Parámetros por defecto para cada efecto - ACTUALIZADOS
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
        "pan_left": {"duration": 1.0, "zoom_factor": 1.2, "distance": 0.2},
        "pan_right": {"duration": 1.0, "zoom_factor": 1.2, "distance": 0.2},
        "pan_up": {"duration": 1.0, "zoom_factor": 1.2},
        "pan_down": {"duration": 1.0, "zoom_factor": 1.2},
        "shake": {"duration": 1.0, "intensity": 5, "zoom_factor": 1.1},
        "fade_in": {"duration": 1.0},
        "fade_out": {"duration": 1.0},
        "mirror_x": {},
        "mirror_y": {},
        "rotate_180": {},
        "shake_zoom_combo": {},
        "shake_kenburns_combo": {}
    }
    
    # Seleccionar efectos para la secuencia
    st.subheader("Selecciona los efectos para tu secuencia")
    efectos_seleccionados = st.multiselect(
        "Efectos (se aplicarán en orden)",
        list(efectos_disponibles.keys()),
        format_func=lambda x: efectos_disponibles[x],
        default=["kenburns"],  # Ken Burns como efecto por defecto
        key=f"{key_prefix}efectos_secuencia"
    )
    
    # Configurar parámetros para cada efecto seleccionado
    efectos_configurados = []
    
    for efecto in efectos_seleccionados:
        st.subheader(f"Configuración para {efectos_disponibles[efecto]}")
        params = {}
        
        # Configurar duración si el efecto la requiere
        if efecto in ["kenburns", "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "shake", "fade_in", "fade_out"]:
            params["duration"] = st.slider(
                "Duración (segundos)",
                min_value=0.1,
                max_value=3.0,
                value=parametros_por_defecto[efecto]["duration"],
                step=0.1,
                key=f"{key_prefix}duracion_{efecto}"
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
                    key=f"{key_prefix}zoom_start_{efecto}"
                )
                pan_start_x = st.slider(
                    "Paneo Inicial X",
                    min_value=-0.5,
                    max_value=0.5,
                    value=float(parametros_por_defecto[efecto]["pan_start"][0]),
                    step=0.1,
                    key=f"{key_prefix}pan_start_x_{efecto}"
                )
                pan_start_y = st.slider(
                    "Paneo Inicial Y",
                    min_value=-0.5,
                    max_value=0.5,
                    value=float(parametros_por_defecto[efecto]["pan_start"][1]),
                    step=0.1,
                    key=f"{key_prefix}pan_start_y_{efecto}"
                )
            with col2:
                params["zoom_end"] = st.slider(
                    "Zoom Final",
                    min_value=1.0,
                    max_value=2.0,
                    value=float(parametros_por_defecto[efecto]["zoom_end"]),
                    step=0.1,
                    key=f"{key_prefix}zoom_end_{efecto}"
                )
                pan_end_x = st.slider(
                    "Paneo Final X",
                    min_value=-0.5,
                    max_value=0.5,
                    value=float(parametros_por_defecto[efecto]["pan_end"][0]),
                    step=0.1,
                    key=f"{key_prefix}pan_end_x_{efecto}"
                )
                pan_end_y = st.slider(
                    "Paneo Final Y",
                    min_value=-0.5,
                    max_value=0.5,
                    value=float(parametros_por_defecto[efecto]["pan_end"][1]),
                    step=0.1,
                    key=f"{key_prefix}pan_end_y_{efecto}"
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
                key=f"{key_prefix}zoom_{efecto}"
            )
        
        # Configurar parámetros para efectos de paneo con zoom
        elif efecto in ["pan_left", "pan_right"]:
            col1, col2 = st.columns(2)
            with col1:
                params["zoom_factor"] = st.slider(
                    "Factor de Zoom",
                    min_value=1.0,
                    max_value=2.0,
                    value=parametros_por_defecto[efecto]["zoom_factor"],
                    step=0.1,
                    key=f"{key_prefix}zoom_factor_{efecto}"
                )
            with col2:
                params["distance"] = st.slider(
                    "Distancia de Paneo",
                    min_value=0.1,
                    max_value=1.0,
                    value=parametros_por_defecto[efecto]["distance"],
                    step=0.1,
                    key=f"{key_prefix}distancia_{efecto}"
                )
        
        # Configurar parámetros para paneo vertical
        elif efecto in ["pan_up", "pan_down"]:
            params["zoom_factor"] = st.slider(
                "Factor de Zoom",
                min_value=1.0,
                max_value=2.0,
                value=parametros_por_defecto[efecto]["zoom_factor"],
                step=0.1,
                key=f"{key_prefix}zoom_factor_{efecto}"
            )
        
        # Configurar parámetros para shake
        elif efecto == "shake":
            col1, col2 = st.columns(2)
            with col1:
                params["intensity"] = st.slider(
                    "Intensidad del Temblor",
                    min_value=1,
                    max_value=20,
                    value=parametros_por_defecto[efecto]["intensity"],
                    step=1,
                    key=f"{key_prefix}intensity_{efecto}"
                )
            with col2:
                params["zoom_factor"] = st.slider(
                    "Factor de Zoom (para evitar bordes)",
                    min_value=1.0,
                    max_value=1.5,
                    value=parametros_por_defecto[efecto]["zoom_factor"],
                    step=0.05,
                    key=f"{key_prefix}zoom_factor_{efecto}"
                )
        
        # Configurar parámetros para shake_zoom_combo
        elif efecto == "shake_zoom_combo":
            st.subheader("🌪️🔍 Configuración Shake + Zoom Combo")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Configuración del Shake:**")
                params["shake_duration"] = st.slider("Duración del shake (segundos)", 0.5, 3.0, 2.0, 0.1)
                params["intensity"] = st.slider("Intensidad del shake", 3, 15, 8, 1)
                params["zoom_factor_shake"] = st.slider("Zoom del shake", 1.1, 1.4, 1.2, 0.05)
            with col2:
                st.write("**Configuración del Zoom:**")
                params["zoom_in_factor"] = st.slider("Factor zoom in", 1.1, 2.0, 1.4, 0.1)
                params["zoom_out_factor"] = st.slider("Factor zoom out", 1.2, 2.5, 1.6, 0.1)
            
            st.info("💡 El efecto aplica shake inicial, luego zoom in (60% del tiempo restante) y zoom out (40% del tiempo restante)")
        
        # Configurar parámetros para shake_kenburns_combo
        elif efecto == "shake_kenburns_combo":
            st.subheader("🌪️🎬 Configuración Shake + Ken Burns Combo")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Configuración del Shake:**")
                params["shake_duration"] = st.slider("Duración del shake (segundos)", 0.5, 2.5, 1.5, 0.1)
                params["intensity"] = st.slider("Intensidad del shake", 5, 20, 10, 1)
                params["zoom_factor_shake"] = st.slider("Zoom del shake", 1.05, 1.3, 1.15, 0.01)
            with col2:
                st.write("**Configuración Ken Burns:**")
                params["kenburns_zoom_start"] = st.slider("Zoom inicial Ken Burns", 0.8, 1.5, 1.0, 0.1)
                params["kenburns_zoom_end"] = st.slider("Zoom final Ken Burns", 1.1, 2.0, 1.4, 0.1)
                
            st.write("**Configuración del Paneo Ken Burns:**")
            col3, col4 = st.columns(2)
            with col3:
                pan_start_x = st.slider("Paneo inicial X", 0.0, 1.0, 0.2, 0.1)
                pan_start_y = st.slider("Paneo inicial Y", 0.0, 1.0, 0.2, 0.1)
                params["kenburns_pan_start"] = (pan_start_x, pan_start_y)
            with col4:
                pan_end_x = st.slider("Paneo final X", 0.0, 1.0, 0.7, 0.1)
                pan_end_y = st.slider("Paneo final Y", 0.0, 1.0, 0.6, 0.1)
                params["kenburns_pan_end"] = (pan_end_x, pan_end_y)
                
            st.info("💡 El efecto aplica shake inicial breve, luego un suave Ken Burns con zoom y paneo")
        
        efectos_configurados.append((efecto, params))
    
    return efectos_configurados 