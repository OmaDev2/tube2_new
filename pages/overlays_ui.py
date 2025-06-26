import streamlit as st
from utils.overlays import OverlayManager
from typing import List, Tuple, Optional

def show_overlays_ui(key_prefix: str = "") -> List[Tuple[str, float, float, Optional[float]]]:
    """
    Muestra la interfaz de usuario para seleccionar overlays.
    
    Args:
        key_prefix: Prefijo para las keys de Streamlit (para evitar conflictos en batch)
    
    Returns:
        Lista de tuplas (nombre_overlay, opacidad, tiempo_inicio, duración)
    """
    st.header("🎨 Overlays de Video")
    
    # Inicializar el gestor de overlays
    overlay_manager = OverlayManager()
    available_overlays = overlay_manager.get_available_overlays()
    
    if not available_overlays:
        st.warning("No se encontraron overlays en la carpeta 'overlays'. Por favor, añade algunos archivos de video.")
        return []
    

    
    # Selección de overlays
    selected_overlays = st.multiselect(
        "Selecciona los overlays para aplicar secuencialmente",
        options=available_overlays,
        default=[],
        help="Los overlays se aplicarán en orden rotativo a cada clip: Clip 1 → Overlay 1, Clip 2 → Overlay 2, etc.",
        key=f"{key_prefix}overlay_selection"
    )
    
    if selected_overlays:
        st.info(f"✨ Los overlays se aplicarán secuencialmente: {' → '.join(selected_overlays)} (rotando entre clips)")
    
    # Opacidad global para todos los overlays
    opacity = st.slider(
        "Opacidad de los overlays",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.05,
        help="Controla la transparencia de todos los overlays",
        key=f"{key_prefix}overlay_opacity"
    )
    
    # Crear secuencia con la misma opacidad para todos los overlays
    # Formato: (nombre_overlay, opacidad, tiempo_inicio, duración)
    overlay_sequence = [(name, opacity, 0, None) for name in selected_overlays]
    
    return overlay_sequence 