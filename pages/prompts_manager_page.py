# pages/prompts_manager_page.py
import streamlit as st
import json
from pathlib import Path
from typing import List, Dict, Tuple
import os
import logging
import traceback
import sys
import re
from datetime import datetime

# Añadir el directorio raíz del proyecto al sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

# --- Configuración de Rutas ---
try:
    PROJECT_ROOT_MODULE_LEVEL = Path(__file__).resolve().parent.parent
except NameError:
    PROJECT_ROOT_MODULE_LEVEL = Path(".").resolve()

PROMPTS_DIR = PROJECT_ROOT_MODULE_LEVEL / "prompts"
BACKUPS_DIR = PROJECT_ROOT_MODULE_LEVEL / "backups" / "prompts"

# --- Configuración de Estilos por Defecto ---
DEFAULT_IMAGE_STYLES = {
    "cinematic": "cinematic, high detail, professional photography",
    "artistic": "artistic, painterly, detailed illustration, concept art",
    "photorealistic": "photorealistic, ultra-detailed, 8k resolution, studio lighting", 
    "minimalist": "minimalist, clean composition, simple, elegant",
    "vintage": "vintage style, retro aesthetic, film grain, warm tones"
}

# --- Funciones de Validación ---

def validate_prompt_variables(user_prompt: str, declared_variables: List[str]) -> Tuple[bool, List[str], List[str]]:
    """
    Valida que las variables en el prompt coincidan con las declaradas.
    
    Returns:
        Tuple[bool, List[str], List[str]]: (is_valid, variables_found, issues)
    """
    # Manejo seguro de entradas vacías o None
    if not user_prompt or not isinstance(user_prompt, str):
        return True, [], []  # Sin prompt, sin variables requeridas
    
    if not declared_variables or not isinstance(declared_variables, list):
        declared_variables = []
    
    try:
        # Buscar todas las variables en formato {variable}
        variables_found = re.findall(r'\{([^}]+)\}', user_prompt)
        variables_found = list(set(variables_found))  # Eliminar duplicados
        
        # Filtrar variables vacías o solo espacios
        variables_found = [var.strip() for var in variables_found if var.strip()]
        
        # Limpiar variables declaradas
        declared_clean = [var.strip() for var in declared_variables if var.strip()]
        
        # Verificar que todas las variables declaradas estén en el prompt
        missing_variables = [var for var in declared_clean if var not in variables_found]
        
        # Verificar que no hay variables no declaradas
        undeclared_variables = [var for var in variables_found if var not in declared_clean]
        
        is_valid = len(missing_variables) == 0 and len(undeclared_variables) == 0
        
        return is_valid, variables_found, missing_variables + undeclared_variables
        
    except Exception as e:
        logger.error(f"Error en validación de variables: {e}")
        return False, [], [f"Error de validación: {str(e)}"]

def debug_variables(user_prompt: str, declared_variables: List[str]):
    """Función de debug para entender el problema de variables."""
    st.write("🔍 **Debug Info:**")
    st.write(f"User prompt: `{repr(user_prompt)}`")
    st.write(f"Declared variables: `{declared_variables}`")
    
    # Mostrar qué encuentra el regex
    if user_prompt:
        found_raw = re.findall(r'\{([^}]+)\}', user_prompt)
        st.write(f"Variables found by regex: `{found_raw}`")
        
        cleaned = [var.strip() for var in found_raw if var.strip()]
        st.write(f"Variables after cleaning: `{cleaned}`")
    
    declared_clean = [var.strip() for var in declared_variables if var.strip()]
    st.write(f"Declared after cleaning: `{declared_clean}`")

def render_validation_feedback(user_prompt: str, declared_variables: List[str]):
    """Renderiza feedback visual sobre la validación de variables."""
    
    is_valid, variables_found, issues = validate_prompt_variables(user_prompt, declared_variables)
    
    if is_valid:
        st.success("✅ Todas las variables están correctamente declaradas y utilizadas")
        if variables_found:
            st.info(f"Variables encontradas: {', '.join(['{'+v+'}' for v in variables_found])}")
    else:
        st.error("❌ Problemas con las variables:")
        
        # Separar problemas por tipo para mejor claridad
        declared_clean = [var.strip() for var in declared_variables if var.strip()]
        
        # Variables usadas pero no declaradas
        undeclared = [var for var in variables_found if var not in declared_clean]
        if undeclared:
            st.error("**Variables usadas en el prompt pero no declaradas:**")
            for var in undeclared:
                st.error(f"• `{{{var}}}` se usa en el prompt pero no está declarada")
        
        # Variables declaradas pero no usadas  
        unused = [var for var in declared_clean if var not in variables_found]
        if unused:
            st.warning("**Variables declaradas pero no usadas en el prompt:**")
            for var in unused:
                st.warning(f"• `{{{var}}}` está declarada pero no se usa en el prompt")
        
        # Ayuda contextual
        if variables_found:
            st.info(f"💡 Variables encontradas en el prompt: {', '.join(['{'+v+'}' for v in variables_found])}")
        if declared_clean:
            st.info(f"📝 Variables declaradas: {', '.join(['{'+v+'}' for v in declared_clean])}")
        
        # Debug info simple (sin expander anidado)
        if st.session_state.get("debug_mode", False):
            st.caption(f"🔍 Debug: Found={variables_found}, Declared={declared_clean}")

# --- Funciones de Backup ---

def create_backup(tipo: str, prompts: List[Dict]) -> bool:
    """
    Crea un backup automático de los prompts antes de guardar.
    
    Returns:
        bool: True si el backup fue exitoso
    """
    try:
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{tipo}_prompts_{timestamp}.json"
        backup_path = BACKUPS_DIR / backup_filename
        
        with open(backup_path, "w", encoding='utf-8') as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Backup creado: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Error creando backup: {e}")
        return False

def cleanup_old_backups(tipo: str, keep_last: int = 5):
    """Limpia backups antiguos manteniendo solo los últimos N."""
    try:
        if not BACKUPS_DIR.exists():
            return
            
        pattern = f"{tipo}_prompts_*.json"
        backup_files = list(BACKUPS_DIR.glob(pattern))
        
        if len(backup_files) > keep_last:
            # Ordenar por fecha de modificación (más reciente primero)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Eliminar los archivos más antiguos
            for old_backup in backup_files[keep_last:]:
                old_backup.unlink()
                logger.info(f"Backup antiguo eliminado: {old_backup}")
                
    except Exception as e:
        logger.error(f"Error limpiando backups antiguos: {e}")

# --- Funciones de Carga/Guardado Mejoradas ---

def get_prompts_filepath(tipo: str) -> Path:
    """Devuelve la ruta completa al archivo JSON para un tipo de prompt."""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROMPTS_DIR / f"{tipo}_prompts.json"

def _create_default_prompts(tipo: str) -> List[Dict]:
    """Crea la estructura de prompts por defecto para un tipo."""
    logger.warning(f"Creando prompts por defecto para tipo '{tipo}'.")
    if tipo == "guion":
        return [{
            "nombre": "Guion Básico (Default)",
            "system_prompt": "Eres un guionista experto en videos de YouTube. Escribe guiones atractivos, estructurados y con gancho para la audiencia hispanohablante.",
            "user_prompt": "Crea un guion para un video titulado: '{titulo}'.\nContexto adicional: '{contexto}'.\nIncluye introducción, desarrollo y conclusión.",
            "variables": ["titulo", "contexto"]
        }]
    elif tipo == "imagenes":
        return [{
            "nombre": "Escenas Fotorrealistas Históricamente Precisas",
            "system_prompt": "Eres un experto en generación de prompts para imágenes fotorrealistas históricamente precisas.\nTu tarea es crear prompts detallados y descriptivos para generar imágenes hiperrealistas que representen fielmente períodos históricos específicos.\nDebes mantener la coherencia visual con el tema general del video mientras te enfocas en cada escena específica.\n\nIncluye siempre detalles sobre:\n- Personajes con características físicas apropiadas para la época y región\n- Vestimenta, peinados y accesorios históricamente auténticos\n- Arquitectura, objetos y herramientas de la época exacta\n- Ambiente y escenario con precisión geográfica e histórica\n- Iluminación natural y técnicas fotográficas realistas\n- Composición que respete las convenciones visuales del período\n- Evitar completamente elementos anacrónicos o modernos\n- Coherencia del personaje principal a través de todas las escenas\n\nEl prompt debe ser en inglés, históricamente preciso y técnicamente detallado para lograr máximo realismo histórico.",
            "user_prompt": "Genera un prompt detallado para crear una imagen fotorrealista históricamente precisa que represente:\n\nCONTEXTO DEL VIDEO:\nTítulo: {titulo}\nTema general: {contexto}\nPERÍODO HISTÓRICO: {periodo_historico}\nUBICACIÓN GEOGRÁFICA: {ubicacion}\nCONTEXTO CULTURAL: {contexto_cultural}\n\nESCENA A REPRESENTAR:\n{scene_text}\n\nDESCRIPCIÓN DEL PERSONAJE PRINCIPAL (para coherencia visual):\n{character_description}\n\nCrea un prompt que:\n1. Respete completamente el período histórico especificado\n2. Incluya arquitectura, vestimenta y objetos auténticos de la época\n3. Mantenga coherencia cultural y geográfica\n4. Use la descripción del personaje para mantener consistencia visual entre escenas\n5. Use terminología fotográfica técnica precisa\n6. Evite cualquier elemento anacrónico o moderno\n7. Capture la esencia de la escena con máximo realismo histórico\n\nEl prompt debe ser en inglés y extremadamente detallado en aspectos históricos y de caracterización.",
            "variables": ["contexto", "titulo", "scene_text", "periodo_historico", "ubicacion", "contexto_cultural", "character_description"]
        }]
    return []

def get_style_options() -> Dict[str, str]:
    """Retorna las opciones de estilo disponibles para prompts de imágenes."""
    return DEFAULT_IMAGE_STYLES

@st.cache_data(ttl=3600) # Cachear prompts por 1 hora
def list_prompts(tipo: str) -> List[Dict]:
    """Carga prompts desde JSON. Crea defaults si no existe o está corrupto."""
    filepath = get_prompts_filepath(tipo)
    if not filepath.exists():
        logger.info(f"Archivo no encontrado: {filepath}. Creando con defaults.")
        defaults = _create_default_prompts(tipo)
        save_prompts(tipo, defaults)
        return defaults

    try:
        with open(filepath, "r", encoding='utf-8') as f:
            prompts_data = json.load(f)
        if not isinstance(prompts_data, list):
            logger.error(f"Archivo {filepath} no contiene una lista. Recreando con defaults.")
            os.remove(filepath)
            return list_prompts(tipo)

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

def save_prompts(tipo: str, prompts: List[Dict]) -> bool:
    """
    Guarda la lista de prompts en el archivo JSON correspondiente.
    Incluye backup automático y limpieza de backups antiguos.
    
    Returns:
        bool: True si el guardado fue exitoso
    """
    filepath = get_prompts_filepath(tipo)
    
    try:
        # Crear backup de la versión anterior si existe
        if filepath.exists():
            current_prompts = list_prompts(tipo)
            backup_success = create_backup(tipo, current_prompts)
            if backup_success:
                cleanup_old_backups(tipo)
        
        # Guardar nueva versión
        with open(filepath, "w", encoding='utf-8') as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Prompts tipo '{tipo}' guardados en {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error guardando prompts en {filepath}: {e}", exc_info=True)
        st.error(f"Error al guardar prompts: {e}")
        return False

# --- Funciones de UI Auxiliares ---

def render_prompt_editor(prompt: Dict, key_base: str, default_variables: List[str]) -> Dict:
    """Renderiza el editor de un prompt individual con validación."""
    
    # Campos de edición
    nombre_edit = st.text_input("Nombre", value=prompt.get('nombre', ''), key=f"{key_base}_name")
    system_edit = st.text_area("System Prompt", value=prompt.get('system_prompt', ''), height=100, key=f"{key_base}_system")
    user_edit = st.text_area("User Prompt (Plantilla)", value=prompt.get('user_prompt', ''), height=150, key=f"{key_base}_user")
    
    variables_actuales = prompt.get('variables', default_variables)
    variables_str_edit = st.text_input(
        f"Variables ({', '.join(['{'+v+'}' for v in default_variables])})", 
        value=", ".join(variables_actuales), 
        key=f"{key_base}_vars"
    )
    
    # Validación en tiempo real con manejo seguro
    if user_edit.strip():  # Solo validar si hay contenido en el prompt
        try:
            nuevas_vars = [v.strip() for v in variables_str_edit.split(",") if v.strip()] if variables_str_edit else []
            render_validation_feedback(user_edit, nuevas_vars)
        except Exception as e:
            st.error(f"Error en validación: {e}")
    
    return {
        "nombre": nombre_edit,
        "system_prompt": system_edit,
        "user_prompt": user_edit,
        "variables": [v.strip() for v in variables_str_edit.split(",") if v.strip()]
    }

def render_prompt_status(prompt: Dict, is_modified: bool = False):
    """Renderiza el estado visual de un prompt."""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if is_modified:
            st.warning("⚠️ Modificado - Pendiente de guardar")
        else:
            st.success("✅ Guardado")
    
    with col2:
        vars_count = len(prompt.get('variables', []))
        st.info(f"📝 {vars_count} variables")
    
    with col3:
        char_count = len(prompt.get('user_prompt', ''))
        st.info(f"📊 {char_count} caracteres")

# --- Función Principal ---

def render_prompts_manager(app_config):
    """Renderiza la interfaz completa del gestor de prompts con todas las mejoras."""
    
    st.title("📋 Gestor de Prompts Mejorado")
    st.markdown("Gestiona tus plantillas de prompts con validación automática y backup.")
    
    # Selector de tipo de prompt
    tipo_prompt_a_gestionar = st.selectbox(
        "Selecciona el tipo de prompt a gestionar:",
        ["guion", "imagenes"],
        key="tipo_prompt_selector"
    )
    
    # Variables por defecto según el tipo
    default_variables = []
    if tipo_prompt_a_gestionar == "guion":
        default_variables = ["titulo", "contexto"]
    elif tipo_prompt_a_gestionar == "imagenes":
        default_variables = ["scene_text", "titulo", "contexto", "style"]
        
        # Mostrar selector de estilos para imágenes
        with st.expander("🎨 Estilos Predefinidos para Imágenes", expanded=False):
            st.markdown("**Estilos disponibles para usar en la variable `{style}`:**")
            style_options = get_style_options()
            
            # Mostrar estilos en cards organizadas
            style_icons = {
                "cinematic": "🎬",
                "artistic": "🎨", 
                "photorealistic": "📸",
                "minimalist": "✨",
                "vintage": "📼"
            }
            
            for name, description in style_options.items():
                icon = style_icons.get(name, "🎯")
                
                # Card con estilo mejorado
                st.markdown(f"""
                <div style="
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 12px;
                    margin: 8px 0;
                ">
                    <div style="display: flex; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 1.2em; margin-right: 8px;">{icon}</span>
                        <strong style="color: #2c3e50; font-size: 1.1em;">{name.title()}</strong>
                    </div>
                    <div style="
                        background-color: #fff;
                        border: 1px solid #e9ecef;
                        border-radius: 4px;
                        padding: 8px;
                        font-family: 'Courier New', monospace;
                        font-size: 0.9em;
                        color: #495057;
                    ">
                        {description}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.info("💡 **Tip**: Copia cualquiera de estos estilos para usar en tus prompts, o crea combinaciones personalizadas.")
    
    # Estado de sesión
    session_key_prompts = f"prompts_list_{tipo_prompt_a_gestionar}"
    session_key_modified = f"prompts_modified_{tipo_prompt_a_gestionar}"
    
    if session_key_prompts not in st.session_state:
        st.session_state[session_key_prompts] = list_prompts(tipo_prompt_a_gestionar)
        st.session_state[session_key_modified] = False
    
    # Header con información
    st.subheader(f"Prompts de {tipo_prompt_a_gestionar.capitalize()}")
    
    # Alerta especial para prompts de imágenes con variables faltantes
    if tipo_prompt_a_gestionar == "imagenes":
        prompts_check = list_prompts("imagenes")
        needs_repair = any(
            not prompt.get('variables', []) and re.findall(r'\{(\w+)\}', prompt.get('user_prompt', ''))
            for prompt in prompts_check
        )
        if needs_repair:
            st.warning("⚠️ **Detectamos prompts con variables faltantes.** Haz clic en **🔧 Reparar** para solucionarlo automáticamente.", icon="⚠️")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.caption(f"📁 Archivo: `{get_prompts_filepath(tipo_prompt_a_gestionar)}`")
    with col2:
        if st.button("🔄 Recargar", key=f"reload_{tipo_prompt_a_gestionar}"):
            st.session_state[session_key_prompts] = list_prompts(tipo_prompt_a_gestionar)
            st.session_state[session_key_modified] = False
            st.rerun()
    with col3:
        # Botón de reparación solo para prompts de imágenes
        if tipo_prompt_a_gestionar == "imagenes":
            if st.button("🔧 Reparar", key=f"repair_{tipo_prompt_a_gestionar}", help="Repara variables faltantes automáticamente"):
                with st.spinner("Reparando variables..."):
                    if repair_image_prompts_variables():
                        st.success("✅ Variables reparadas correctamente")
                        st.session_state[session_key_prompts] = list_prompts(tipo_prompt_a_gestionar)
                        st.session_state[session_key_modified] = False
                        st.balloons()
                        st.rerun()
                    else:
                        st.info("ℹ️ No se encontraron variables que reparar")
    with col4:
        # Toggle de debug opcional
        debug_mode = st.checkbox("🐛 Debug", value=st.session_state.get("debug_mode", False), key="debug_toggle")
        st.session_state["debug_mode"] = debug_mode
    
    prompts_actuales = st.session_state[session_key_prompts]
    
    if not prompts_actuales:
        st.info("📝 No hay prompts guardados. Añade uno nuevo a continuación.")
    
    # Mostrar prompts existentes
    indices_a_eliminar = []
    
    for i, prompt in enumerate(prompts_actuales):
        with st.expander(f"📝 {prompt.get('nombre', f'Prompt {i+1}')}", expanded=False):
            key_base = f"prompt_{tipo_prompt_a_gestionar}_{i}"
            
            # Estado del prompt
            render_prompt_status(prompt, st.session_state[session_key_modified])
            
            # Editor del prompt
            prompt_editado = render_prompt_editor(prompt, key_base, default_variables)
            
            # Botones de acción
            col1, col2 = st.columns(2)
            
            if col1.button("💾 Actualizar", key=f"{key_base}_update"):
                st.session_state[session_key_prompts][i] = prompt_editado
                st.session_state[session_key_modified] = True
                st.success(f"Prompt '{prompt_editado['nombre']}' actualizado.")
                st.rerun()
            
            if col2.button("🗑️ Eliminar", key=f"{key_base}_delete", type="secondary"):
                indices_a_eliminar.append(i)
                st.session_state[session_key_modified] = True
                st.warning(f"'{prompt.get('nombre')}' marcado para eliminar.")
                st.rerun()
    
    # Sección para añadir nuevo prompt
    st.divider()
    with st.expander("➕ Añadir Nuevo Prompt", expanded=False):
        with st.form(f"new_prompt_{tipo_prompt_a_gestionar}_form", clear_on_submit=True):
            st.subheader("Crear Nuevo Prompt")
            
            nuevo_prompt = render_prompt_editor(
                {"nombre": "", "system_prompt": "", "user_prompt": "", "variables": default_variables},
                f"new_{tipo_prompt_a_gestionar}",
                default_variables
            )
            
            if st.form_submit_button("➕ Añadir Prompt"):
                if nuevo_prompt["nombre"] and nuevo_prompt["system_prompt"] and nuevo_prompt["user_prompt"]:
                    st.session_state[session_key_prompts].append(nuevo_prompt)
                    st.session_state[session_key_modified] = True
                    st.success(f"'{nuevo_prompt['nombre']}' añadido correctamente.")
                    st.rerun()
                else:
                    st.error("❌ Por favor completa todos los campos obligatorios.")
    
    # Eliminar prompts marcados
    if indices_a_eliminar:
        for index in sorted(indices_a_eliminar, reverse=True):
            if 0 <= index < len(st.session_state[session_key_prompts]):
                del st.session_state[session_key_prompts][index]
    
    # Botón para guardar todos los cambios
    st.divider()
    
    if st.session_state[session_key_modified]:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button(
                f"💾 Guardar Todos los Cambios ({len(st.session_state[session_key_prompts])} prompts)",
                type="primary",
                key=f"save_all_{tipo_prompt_a_gestionar}"
            ):
                success = save_prompts(tipo_prompt_a_gestionar, st.session_state[session_key_prompts])
                if success:
                    st.session_state[session_key_modified] = False
                    st.success("✅ Todos los cambios guardados correctamente.")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Error al guardar los cambios.")
        
        with col2:
            st.warning("⚠️ Cambios sin guardar")
    else:
        st.success("✅ Todos los cambios están guardados.")
    
    # Información de backups
    if BACKUPS_DIR.exists():
        backup_files = list(BACKUPS_DIR.glob(f"{tipo_prompt_a_gestionar}_prompts_*.json"))
        if backup_files:
            st.info(f"🔄 {len(backup_files)} backups disponibles en `{BACKUPS_DIR}`")

# --- Función de Reparación Automática ---

def repair_image_prompts_variables() -> bool:
    """
    Repara automáticamente las variables faltantes en los prompts de imágenes.
    Detecta automáticamente qué variables usa cada prompt y las asigna correctamente.
    
    Returns:
        bool: True si se realizaron reparaciones
    """
    try:
        prompts = list_prompts("imagenes")
        repairs_made = False
        
        for prompt in prompts:
            user_prompt = prompt.get('user_prompt', '')
            current_variables = prompt.get('variables', [])
            
            if user_prompt:
                # Detectar variables automáticamente del texto del prompt
                found_variables = re.findall(r'\{(\w+)\}', user_prompt)
                found_variables = list(set(found_variables))  # Eliminar duplicados
                
                # Si las variables actuales están vacías o incompletas, repararlas
                if not current_variables or set(current_variables) != set(found_variables):
                    prompt['variables'] = found_variables
                    repairs_made = True
                    logger.info(f"Reparado prompt '{prompt.get('nombre')}': variables {current_variables} -> {found_variables}")
        
        if repairs_made:
            success = save_prompts("imagenes", prompts)
            return success
        
        return False  # No se necesitaron reparaciones
        
    except Exception as e:
        logger.error(f"Error reparando prompts de imágenes: {e}")
        st.error(f"Error en la reparación: {e}")
        return False

