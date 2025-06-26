import streamlit as st
from pathlib import Path
import yaml
import sys

# Añadir el directorio raíz del proyecto al sys.path
# Esto permite que el script encuentre la carpeta 'utils'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.config import load_config

def render_settings(app_config):
    """Renderiza la página de configuración"""
    st.title("⚙️ Configuración del Proyecto")
    st.markdown("Ver y editar configuración actual")
    
    tab1, tab2 = st.tabs(["Configuración actual", "Configuración por defecto"])
    
    # --- Pestaña 1: Configuración Actual ---
    with tab1:
        try:
            voidrules_path = Path(__file__).parent.parent / ".voidrules"
            if voidrules_path.exists():
                with open(voidrules_path, "r") as f:
                    void_conf = yaml.safe_load(f)
                st.code(yaml.dump(void_conf, allow_unicode=True, default_flow_style=False), language="yaml")
            else:
                st.warning("Archivo .voidrules no encontrado")
        except Exception as e:
            st.error(f"No se pudo cargar .voidrules: {e}")
    
    # --- Pestaña 2: Configuración por defecto ---
    with tab2:
        st.markdown("### 📁 Configuración cargada del proyecto")
        try:
            if app_config:
                st.code(yaml.dump(app_config, allow_unicode=True, default_flow_style=False), language="yaml")
            else:
                st.info("Ninguna configuración cargada")
        except Exception:
            st.info("No hay configuración para mostrar")
    
    st.markdown("---")
    
    # --- Editar archivo .voidrules ---
    if st.checkbox("🛠️ Editar configuración manualmente"):
        try:
            with open(".voidrules", "r") as f:
                void_data = f.read()
            edited_config = st.text_area("Editar .voidrules", void_data, height=300)
            
            if st.button("Guardar Configuración"):
                with open(".voidrules", "w") as f:
                    f.write(edited_config)
                st.success("Configuración guardada exitosamente")
                st.rerun()
                
        except Exception as e:
            st.error(f"No se pudo cargar el archivo: {e}")

    if st.checkbox("📊 Ver información del proyecto"):
        if "loaded_project" in st.session_state:
            st.json(st.session_state.loaded_project)
        else:
            st.warning("No hay proyecto cargado")

def render_settings_page(app_config):
    st.title("⚙️ Configuración del Sistema")
    st.markdown("Gestiona la configuración global de la aplicación y revisa el estado de los servicios.")
    st.divider()
    
    # Tabs para organizar mejor
    tab1, tab2, tab3, tab4 = st.tabs(["🤖 Servicios IA", "🎵 Audio", "🎬 Video", "📁 Rutas"])
    
    with tab1:
        st.header("Servicios de Inteligencia Artificial")
        
        # Mostrar información de proveedores disponibles
        from utils.ai_services import get_available_providers_info
        providers_info = get_available_providers_info()
        
        st.subheader("🔍 Estado de Proveedores de IA")
        
        for provider_name, info in providers_info.items():
            provider_display_name = {
                'openai': '🟢 OpenAI',
                'gemini': '🔵 Google Gemini', 
                'ollama': '🟠 Ollama (Local)'
            }.get(provider_name, provider_name.title())
            
            with st.expander(f"{provider_display_name} - {info['status']}", expanded=info['configured']):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    if info['configured']:
                        st.success(f"✅ {provider_display_name} está configurado y listo para usar")
                    else:
                        st.error(f"❌ {provider_display_name} no está configurado")
                        
                        if provider_name == 'openai':
                            st.info("💡 Configura `OPENAI_API_KEY` en variables de entorno o config.yaml")
                        elif provider_name == 'gemini':
                            st.info("💡 Configura `GEMINI_API_KEY` en variables de entorno o config.yaml")

                        elif provider_name == 'ollama':
                            st.info("💡 Configura `OLLAMA_BASE_URL` en variables de entorno o config.yaml")
                
                with col2:
                    if info['configured']:
                        st.metric("Estado", "🟢 Activo")
                    else:
                        st.metric("Estado", "🔴 Inactivo")
                
                st.write("**Modelos disponibles:**")
                for model in info['models']:
                    if info['configured']:
                        st.write(f"✅ `{model}`")
                    else:
                        st.write(f"⚪ `{model}` (requiere configuración)")
        
        st.divider()
        
        # Configuración de LLM por defecto para optimización
        st.subheader("🎯 Configuración por Defecto para Optimización YouTube")
        st.markdown("Configura qué LLM usar por defecto cuando generes contenido optimizado.")
        
        # Filtrar solo proveedores configurados
        available_providers = [name for name, info in providers_info.items() if info['configured']]
        
        if available_providers:
            col1, col2 = st.columns(2)
            with col1:
                default_provider = st.selectbox(
                    "Proveedor por Defecto",
                    available_providers,
                    index=0,
                    format_func=lambda x: {
                        'openai': 'OpenAI',
                        'gemini': 'Google Gemini',
                        'ollama': 'Ollama (Local)'
                    }.get(x, x.title()),
                    help="Este proveedor se usará por defecto en la optimización YouTube"
                )
            
            with col2:
                if default_provider in providers_info:
                    available_models = providers_info[default_provider]['models']
                    default_model = st.selectbox(
                        "Modelo por Defecto",
                        available_models,
                        help=f"Modelo de {default_provider.title()} a usar por defecto"
                    )
            
            st.info(f"💡 **Configuración actual:** {default_provider.upper()}/{default_model}")
            st.caption("Esta configuración se puede cambiar individualmente en cada generación de video.")
        else:
            st.warning("⚠️ No hay proveedores de IA configurados. Configura al menos uno (OpenAI, Gemini o Ollama) para usar la optimización YouTube.")
    
    # ... existing code for other tabs ...