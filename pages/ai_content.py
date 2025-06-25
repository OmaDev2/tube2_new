import streamlit as st
from utils.ai_services import AIServices, list_gemini_models, list_openai_models, list_ollama_models
from utils.ai_services import generate_gemini_script, generate_openai_script, generate_ollama_script

def show_ai_content_page():
    st.title("Generador de Contenido con IA")
    
    # Inicializar el servicio de IA
    ai_service = AIServices()
    
    # Selección del proveedor de IA
    provider = st.selectbox(
        "Selecciona el proveedor de IA",
        ["gemini", "openai", "ollama"],
        index=0
    )
    
    # Mostrar modelos disponibles según el proveedor seleccionado
    if provider == "gemini":
        models = list_gemini_models()
    elif provider == "openai":
        models = list_openai_models()
    else:  # ollama
        models = list_ollama_models()
    
    # Filtrar modelos que no son errores
    available_models = [(name, methods) for name, methods in models if not name.startswith("[ERROR]")]
    
    if not available_models:
        st.error("No hay modelos disponibles para el proveedor seleccionado.")
        return
    
    # Selección del modelo
    model_names = [name for name, _ in available_models]
    selected_model = st.selectbox(
        "Selecciona el modelo",
        model_names,
        index=0
    )
    
    # Inputs para el prompt
    system_prompt = st.text_area(
        "Prompt del sistema (opcional)",
        "Eres un asistente útil que genera contenido creativo y atractivo."
    )
    
    user_prompt = st.text_area(
        "Tu prompt",
        "Genera un guión para un video corto sobre..."
    )
    
    # Botón para generar contenido
    if st.button("Generar Contenido"):
        with st.spinner("Generando contenido..."):
            if provider == "gemini":
                response = generate_gemini_script(system_prompt, user_prompt, model=selected_model)
            elif provider == "openai":
                response = generate_openai_script(system_prompt, user_prompt, model=selected_model)
            else:  # ollama
                response = generate_ollama_script(system_prompt, user_prompt, model=selected_model)
            
            # Mostrar la respuesta
            if response.startswith("[ERROR]"):
                st.error(response)
            else:
                st.success("¡Contenido generado con éxito!")
                st.text_area("Respuesta", response, height=200)
                
                # Opción para copiar el contenido
                if st.button("Copiar al Portapapeles"):
                    st.code(response)
                    st.success("¡Contenido copiado!") 