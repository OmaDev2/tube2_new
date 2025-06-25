
# pages/prompts_manager_page.py
import streamlit as st
import json
from pathlib import Path
from typing import List, Dict
import os
import logging
import traceback # Para mostrar errores detallados en la UI
import sys 

# Añadir el directorio raíz del proyecto al sys.path
# Esto permite que el script encuentre la carpeta 'utils'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Ubicación ÚNICA y ROBUSTA para los archivos de prompts ---
# Ir dos niveles arriba desde utils/ o pages/ para llegar a la raíz del proyecto
# Asumiendo que prompts_manager.py está en la carpeta 'pages/'
try:
    # Path(__file__) es la ruta de este archivo .py
    # .resolve() obtiene la ruta absoluta
    # .parent es la carpeta 'pages'
    # .parent de nuevo es la carpeta raíz del proyecto
    PROJECT_ROOT_MODULE_LEVEL = Path(__file__).resolve().parent.parent
except NameError:
     # __file__ no está definido si se ejecuta de forma interactiva, usar directorio actual
     PROJECT_ROOT_MODULE_LEVEL = Path(".").resolve()

PROMPTS_DIR = PROJECT_ROOT_MODULE_LEVEL / "prompts" # Carpeta 'prompts' en la raíz

# --- Funciones de Carga/Guardado (Unificadas) ---

def get_prompts_filepath(tipo: str) -> Path:
    """Devuelve la ruta completa al archivo JSON para un tipo de prompt."""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True) # Asegura que la carpeta exista
    return PROMPTS_DIR / f"{tipo}_prompts.json"

def _create_default_prompts(tipo: str) -> List[Dict]:
    """Crea la estructura de prompts por defecto para un tipo."""
    logger.warning(f"Creando prompts por defecto para tipo '{tipo}'.")
    if tipo == "guion":
        return [{
            "nombre": "Guion Básico (Default)",
            "system_prompt": "Eres un guionista experto en videos de YouTube...",
            "user_prompt": "Crea un guion para video titulado: '{titulo}'.\nContexto: '{contexto}'.\nIncluye intro, desarrollo, conclusión.",
            "variables": ["titulo", "contexto"]
        }]
    elif tipo == "imagenes":
         return [{
            "nombre": "Imágenes Detalladas (Default)",
            "system_prompt": "Generate detailed image prompts in English...",
            "user_prompt": "Image for scene: {scene_text}. Video title: {titulo}. Context: {contexto}.",
            "variables": ["scene_text", "titulo", "contexto"]
         }]
    return []

def list_prompts(tipo: str) -> List[Dict]:
    """Carga prompts desde JSON. Crea defaults si no existe o está corrupto."""
    filepath = get_prompts_filepath(tipo)
    if not filepath.exists():
        logger.info(f"Archivo no encontrado: {filepath}. Creando con defaults.")
        defaults = _create_default_prompts(tipo)
        save_prompts(tipo, defaults) # Guardar los defaults creados
        return defaults

    try:
        with open(filepath, "r", encoding='utf-8') as f:
            prompts_data = json.load(f)
        if not isinstance(prompts_data, list):
            logger.error(f"Archivo {filepath} no contiene una lista. Recreando con defaults.")
            # Borrar archivo corrupto y recrear
            os.remove(filepath)
            return list_prompts(tipo) # Llamada recursiva segura

        # Asegurar estructura mínima de cada prompt
        for p in prompts_data:
            p.setdefault("nombre", "Prompt Sin Nombre")
            p.setdefault("system_prompt", "")
            p.setdefault("user_prompt", "")
            p.setdefault("variables", [])
        logger.info(f"Prompts tipo '{tipo}' cargados desde {filepath}")
        return prompts_data
    except json.JSONDecodeError:
        logger.error(f"Error JSON en {filepath}. Recreando con defaults.", exc_info=True)
        os.remove(filepath)
        return list_prompts(tipo)
    except Exception as e:
        logger.error(f"Error inesperado cargando {filepath}: {e}", exc_info=True)
        return []

def save_prompts(tipo: str, prompts: List[Dict]):
    """Guarda la lista de prompts en el archivo JSON correspondiente."""
    filepath = get_prompts_filepath(tipo)
    try:
        with open(filepath, "w", encoding='utf-8') as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        logger.info(f"Prompts tipo '{tipo}' guardados en {filepath}")
    except Exception as e:
        logger.error(f"Error guardando prompts en {filepath}: {e}", exc_info=True)
        st.error(f"Error al guardar prompts: {e}")

# --- Interfaz del Gestor ---

def render_prompts_manager(app_config): # Cambiado de show_prompts_manager a render_prompts_manager
    """Muestra la UI para gestionar prompts, usando las funciones unificadas."""
    
    # Determinar el tipo basado en un selector o parámetro si es necesario
    # Para este ejemplo, asumimos que se pasa o se selecciona de alguna manera.
    # Aquí, como ejemplo, se puede usar un selectbox para elegir el tipo de prompt a gestionar.
    tipo_prompt_a_gestionar = st.selectbox(
        "Selecciona el tipo de prompt a gestionar:", 
        ["guion", "imagenes"],
        key="tipo_prompt_selector"
    )
    
    default_variables = []
    if tipo_prompt_a_gestionar == "guion":
        default_variables = ["titulo", "contexto"]
    elif tipo_prompt_a_gestionar == "imagenes":
        default_variables = ["scene_text", "titulo", "contexto"]

    # Usar un estado de sesión por tipo para detectar cambios y forzar recarga si es necesario
    session_key_prompts = f"prompts_list_{tipo_prompt_a_gestionar}"
    if session_key_prompts not in st.session_state:
         st.session_state[session_key_prompts] = list_prompts(tipo_prompt_a_gestionar)

    st.header(f"Gestor de Prompts ({tipo_prompt_a_gestionar.capitalize()})")
    st.caption(f"Editando archivo: `{get_prompts_filepath(tipo_prompt_a_gestionar)}`")

    prompts_actuales = st.session_state[session_key_prompts]

    if not prompts_actuales:
        st.info("No hay prompts guardados. Añade uno nuevo a continuación.")

    # Botón para recargar desde archivo (por si se edita externamente)
    if st.button(f"Recargar Prompts de '{tipo_prompt_a_gestionar}' desde archivo", key=f"reload_{tipo_prompt_a_gestionar}"):
         st.session_state[session_key_prompts] = list_prompts(tipo_prompt_a_gestionar)
         st.rerun()

    # Mostrar prompts existentes
    indices_a_eliminar = []
    prompts_modificados = False # Flag para saber si hubo cambios

    for i, prompt in enumerate(prompts_actuales):
        # Usar nombre y índice para key más estable si el nombre cambia
        expander_key = f"expander_{tipo_prompt_a_gestionar}_{i}_{prompt.get('nombre','noname')}"
        with st.expander(f"📝 {prompt.get('nombre', f'Prompt {i+1}')}", expanded=False):
            key_base = f"prompt_{tipo_prompt_a_gestionar}_{i}"

            # --- Edición ---
            # Guardar los valores editados temporalmente
            nombre_edit = st.text_input("Nombre", value=prompt.get('nombre', ''), key=f"{key_base}_name")
            system_edit = st.text_area("System Prompt", value=prompt.get('system_prompt', ''), height=100, key=f"{key_base}_system")
            user_edit = st.text_area("User Prompt (Plantilla)", value=prompt.get('user_prompt', ''), height=150, key=f"{key_base}_user")
            variables_actuales = prompt.get('variables', default_variables)
            variables_str_edit = st.text_input(f"Variables ({', '.join(['{'+v+'}' for v in default_variables])})", value=", ".join(variables_actuales), key=f"{key_base}_vars")

            # --- Botones ---
            col1, col2 = st.columns(2)
            # Botón Guardar Cambios (actualiza el prompt en la lista temporal)
            if col1.button("💾 Actualizar Este Prompt", key=f"{key_base}_update"):
                nuevas_vars = [v.strip() for v in variables_str_edit.split(",") if v.strip()]
                # Actualizar directamente en la lista en session_state
                st.session_state[session_key_prompts][i] = {
                    "nombre": nombre_edit, "system_prompt": system_edit,
                    "user_prompt": user_edit, "variables": nuevas_vars
                }
                st.success(f"Prompt '{nombre_edit}' listo para guardar.")
                prompts_modificados = True
                st.rerun() # Rerun para mostrar el cambio visualmente

            # Botón Eliminar (marca para eliminar)
            if col2.button("🗑️ Eliminar Este Prompt", key=f"{key_base}_delete", type="secondary"):
                 indices_a_eliminar.append(i)
                 prompts_modificados = True
                 st.warning(f"'{prompt.get('nombre')}' marcado para eliminar. Pulsa 'Guardar Todos los Cambios'.")
                 # Forzar rerun para actualizar UI y quitar el expander eliminado visualmente
                 st.rerun()

    # --- Acciones Globales (Añadir, Guardar Todo) ---
    st.divider()

    # Añadir Nuevo Prompt
    with st.expander("➕ Añadir Nuevo Prompt"):
        with st.form(f"new_prompt_{tipo_prompt_a_gestionar}_form", clear_on_submit=True):
            st.subheader("Nuevo Prompt")
            nuevo_nombre = st.text_input("Nombre del Nuevo Prompt*")
            nuevo_system = st.text_area("System Prompt*", height=100)
            nuevo_user = st.text_area("User Prompt (Plantilla)*", height=150)
            nuevo_vars_str = st.text_input("Variables (separadas por coma)", value=", ".join(default_variables))
            st.caption(f"Variables sugeridas: {', '.join(['{'+v+'}' for v in default_variables])}")
            submitted_new = st.form_submit_button("Añadir a la lista (temporalmente)")
            if submitted_new:
                if nuevo_nombre and nuevo_system and nuevo_user:
                    nuevas_vars_list = [v.strip() for v in nuevo_vars_str.split(",") if v.strip()]
                    # Añadir a la lista en session_state
                    st.session_state[session_key_prompts].append({
                        "nombre": nuevo_nombre, "system_prompt": nuevo_system,
                        "user_prompt": nuevo_user, "variables": nuevas_vars_list
                    })
                    st.success(f"'{nuevo_nombre}' añadido a la lista. Pulsa 'Guardar Todos los Cambios' para confirmar.")
                    prompts_modificados = True
                    st.rerun()
                else: st.error("Nombre, System y User prompt son requeridos.")

    # Botón para Guardar TODOS los cambios (incluidas eliminaciones)
    st.divider()
    if st.button(f"💾 Guardar Todos los Cambios de Prompts '{tipo_prompt_a_gestionar}' en Archivo", type="primary", disabled=not prompts_modificados):
         # Eliminar los marcados ANTES de guardar
         if indices_a_eliminar:
             # Iterar en reversa para no afectar índices restantes
             for index in sorted(indices_a_eliminar, reverse=True):
                  # Asegurarse que el índice todavía es válido (por si hubo reruns)
                  if 0 <= index < len(st.session_state[session_key_prompts]):
                       del st.session_state[session_key_prompts][index]
             logger.info(f"Eliminados {len(indices_a_eliminar)} prompts tipo '{tipo_prompt_a_gestionar}'.")

         # Guardar la lista completa que está en session_state
         save_prompts(tipo_prompt_a_gestionar, st.session_state[session_key_prompts])
         st.success(f"Todos los cambios para prompts '{tipo_prompt_a_gestionar}' han sido guardados.")
         # Ya no necesitamos marcar como modificado
         # Considera si quieres un rerun aquí para limpiar estado visual de botones etc.
         st.rerun()

    elif prompts_modificados:
         st.warning("Tienes cambios sin guardar en la lista de prompts.")

