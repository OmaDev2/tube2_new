# pages/settings_page.py
import streamlit as st
import os
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, List
import requests

# Importaciones locales
from utils.config import load_config, save_config, save_config_with_api_keys

# Importar las nuevas clases de validación y backup
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from tmp_rovodev_settings_enhanced import (
        ConfigValidator, ConfigBackupManager, ConfigStatusDashboard,
        render_video_configuration_tab, render_backup_restore_section
    )
except ImportError:
    # Fallback si no se puede importar
    class ConfigValidator:
        @staticmethod
        def validate_api_key(service: str, api_key: str):
            """Valida una API key específica"""
            if not api_key or api_key.strip() == "":
                return False, "API key vacía"
            
            try:
                if service == "openai":
                    return ConfigValidator._validate_openai_key(api_key)
                elif service == "gemini":
                    return ConfigValidator._validate_gemini_key(api_key)
                elif service == "replicate":
                    return ConfigValidator._validate_replicate_key(api_key)
                elif service == "fish_audio":
                    return ConfigValidator._validate_fish_audio_key(api_key)
                else:
                    return True, "Servicio no soportado para validación"
            except Exception as e:
                return False, f"Error validando: {str(e)}"
        
        @staticmethod
        def _validate_openai_key(api_key: str):
            """Valida API key de OpenAI"""
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                # Hacer una llamada simple para verificar
                response = client.models.list()
                return True, "✅ API key válida"
            except Exception as e:
                return False, f"❌ API key inválida: {str(e)}"
        
        @staticmethod
        def _validate_gemini_key(api_key: str):
            """Valida API key de Gemini"""
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                # Intentar listar modelos
                models = list(genai.list_models())
                return True, "✅ API key válida"
            except Exception as e:
                return False, f"❌ API key inválida: {str(e)}"
        
        @staticmethod
        def _validate_replicate_key(api_key: str):
            """Valida API key de Replicate"""
            try:
                headers = {"Authorization": f"Token {api_key}"}
                response = requests.get("https://api.replicate.com/v1/account", headers=headers, timeout=10)
                if response.status_code == 200:
                    return True, "✅ API key válida"
                else:
                    return False, f"❌ API key inválida: {response.status_code}"
            except Exception as e:
                return False, f"❌ Error validando: {str(e)}"
        
        @staticmethod
        def _validate_fish_audio_key(api_key: str):
            """Valida API key de Fish Audio"""
            try:
                from fish_audio_sdk import Session
                session = Session(api_key)
                return True, "✅ API key configurada"
            except Exception as e:
                return False, f"❌ Error validando: {str(e)}"
        
        @staticmethod
        def validate_directory(path: str):
            """Valida que un directorio existe o puede ser creado"""
            try:
                path_obj = Path(path)
                if path_obj.exists():
                    if path_obj.is_dir():
                        return True, "✅ Directorio existe"
                    else:
                        return False, "❌ La ruta existe pero no es un directorio"
                else:
                    # Intentar crear el directorio
                    path_obj.mkdir(parents=True, exist_ok=True)
                    return True, "✅ Directorio creado"
            except Exception as e:
                return False, f"❌ Error con directorio: {str(e)}"
        
        @staticmethod
        def validate_ollama_connection(base_url: str):
            """Valida conexión con Ollama"""
            try:
                response = requests.get(f"{base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return True, f"✅ Conectado - {len(models)} modelos disponibles"
                else:
                    return False, f"❌ Error de conexión: {response.status_code}"
            except Exception as e:
                return False, f"❌ No se puede conectar: {str(e)}"
    
    class ConfigStatusDashboard:
        @staticmethod
        def render_status_dashboard(config):
            """Renderiza el dashboard de estado"""
            st.subheader("📊 Estado de Configuraciones")
            
            # Crear métricas de estado
            col1, col2, col3, col4 = st.columns(4)
            
            # Estado de APIs
            api_status = ConfigStatusDashboard._check_api_status(config)
            with col1:
                api_count = len([k for k, v in api_status.items() if v["valid"]])
                total_apis = len(api_status)
                st.metric(
                    "🔑 APIs Configuradas",
                    f"{api_count}/{total_apis}",
                    f"{(api_count/total_apis)*100:.0f}%" if total_apis > 0 else "0%"
                )
            
            # Estado de directorios
            dir_status = ConfigStatusDashboard._check_directories_status(config)
            with col2:
                dir_count = len([k for k, v in dir_status.items() if v["valid"]])
                total_dirs = len(dir_status)
                st.metric(
                    "📁 Directorios",
                    f"{dir_count}/{total_dirs}",
                    f"{(dir_count/total_dirs)*100:.0f}%" if total_dirs > 0 else "0%"
                )
            
            # Estado de servicios
            service_status = ConfigStatusDashboard._check_services_status(config)
            with col3:
                service_count = len([k for k, v in service_status.items() if v["available"]])
                total_services = len(service_status)
                st.metric(
                    "🛠️ Servicios",
                    f"{service_count}/{total_services}",
                    f"{(service_count/total_services)*100:.0f}%" if total_services > 0 else "0%"
                )
            
            # Configuración completa
            with col4:
                total_valid = api_count + dir_count + service_count
                total_items = total_apis + total_dirs + total_services
                overall_percentage = (total_valid / total_items * 100) if total_items > 0 else 0
                st.metric(
                    "✅ Configuración General",
                    f"{overall_percentage:.0f}%",
                    "Completa" if overall_percentage >= 80 else "Incompleta"
                )
            
            # Detalles expandibles
            with st.expander("🔍 Ver Detalles de Estado"):
                ConfigStatusDashboard._render_detailed_status(api_status, dir_status, service_status)
        
        @staticmethod
        def _check_api_status(config):
            """Verifica el estado de las APIs"""
            ai_config = config.get("ai", {})
            tts_config = config.get("tts", {})
            
            apis = {
                "OpenAI": {
                    "key": ai_config.get("openai_api_key", ""),
                    "valid": False,
                    "message": ""
                },
                "Gemini": {
                    "key": ai_config.get("gemini_api_key", ""),
                    "valid": False,
                    "message": ""
                },
                "Replicate": {
                    "key": ai_config.get("replicate_api_key", ""),
                    "valid": False,
                    "message": ""
                },
                "Fish Audio": {
                    "key": tts_config.get("fish_audio", {}).get("api_key", ""),
                    "valid": False,
                    "message": ""
                }
            }
            
            # Verificar cada API (sin hacer llamadas reales para no consumir cuota)
            for name, info in apis.items():
                if info["key"] and info["key"].strip():
                    apis[name]["valid"] = True
                    apis[name]["message"] = "✅ Configurada"
                else:
                    apis[name]["message"] = "❌ No configurada"
            
            return apis
        
        @staticmethod
        def _check_directories_status(config):
            """Verifica el estado de los directorios"""
            directories = {
                "Output": config.get("output_dir", ""),
                "Projects": config.get("projects_dir", ""),
                "Temp": config.get("temp_dir", ""),
                "Background Music": config.get("background_music_dir", "")
            }
            
            # Agregar directorios de video si existen
            video_paths = config.get("video_generation", {}).get("paths", {})
            for key, path in video_paths.items():
                if path:
                    directories[key.replace("_", " ").title()] = path
            
            status = {}
            for name, path in directories.items():
                if path:
                    valid, message = ConfigValidator.validate_directory(path)
                    status[name] = {
                        "path": path,
                        "valid": valid,
                        "message": message
                    }
                else:
                    status[name] = {
                        "path": "",
                        "valid": False,
                        "message": "❌ No configurado"
                    }
            
            return status
        
        @staticmethod
        def _check_services_status(config):
            """Verifica el estado de los servicios"""
            services = {}
            
            # Ollama
            ollama_url = config.get("ai", {}).get("ollama_base_url", "")
            if ollama_url:
                valid, message = ConfigValidator.validate_ollama_connection(ollama_url)
                services["Ollama"] = {
                    "available": valid,
                    "message": message,
                    "url": ollama_url
                }
            
            # Fish Audio SDK
            try:
                import fish_audio_sdk
                services["Fish Audio SDK"] = {
                    "available": True,
                    "message": "✅ SDK disponible"
                }
            except ImportError:
                services["Fish Audio SDK"] = {
                    "available": False,
                    "message": "❌ SDK no instalado"
                }
            
            # Replicate
            try:
                import replicate
                services["Replicate SDK"] = {
                    "available": True,
                    "message": "✅ SDK disponible"
                }
            except ImportError:
                services["Replicate SDK"] = {
                    "available": False,
                    "message": "❌ SDK no instalado"
                }
            
            return services
        
        @staticmethod
        def _render_detailed_status(api_status, dir_status, service_status):
            """Renderiza los detalles de estado"""
            
            # APIs
            st.write("**🔑 Estado de APIs:**")
            for name, info in api_status.items():
                icon = "✅" if info["valid"] else "❌"
                st.write(f"{icon} **{name}**: {info['message']}")
            
            st.divider()
            
            # Directorios
            st.write("**📁 Estado de Directorios:**")
            for name, info in dir_status.items():
                icon = "✅" if info["valid"] else "❌"
                st.write(f"{icon} **{name}**: `{info['path']}` - {info['message']}")
            
            st.divider()
            
            # Servicios
            st.write("**🛠️ Estado de Servicios:**")
            for name, info in service_status.items():
                icon = "✅" if info["available"] else "❌"
                st.write(f"{icon} **{name}**: {info['message']}")
    
    class ConfigBackupManager:
        """Clase para manejar backups de configuración"""
        
        def __init__(self):
            self.backup_dir = Path("config_backups")
            self.backup_dir.mkdir(exist_ok=True)
        
        def create_backup(self, config, name: str = None) -> str:
            """Crea un backup de la configuración"""
            if not name:
                name = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_file = self.backup_dir / f"{name}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False, default=str)
            
            return str(backup_file)
        
        def list_backups(self):
            """Lista todos los backups disponibles"""
            backups = []
            for backup_file in self.backup_dir.glob("*.json"):
                try:
                    stat = backup_file.stat()
                    backups.append({
                        "name": backup_file.stem,
                        "file": str(backup_file),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime)
                    })
                except Exception:
                    continue
            
            return sorted(backups, key=lambda x: x["modified"], reverse=True)
        
        def restore_backup(self, backup_file: str):
            """Restaura un backup"""
            with open(backup_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        def delete_backup(self, backup_file: str) -> bool:
            """Elimina un backup"""
            try:
                Path(backup_file).unlink()
                return True
            except Exception:
                return False
    
    def render_video_configuration_tab(config):
        """Renderiza la pestaña completa de configuración de video"""
        st.header("🎥 Configuración de Generación de Video")
        
        # Inicializar configuración de video si no existe
        if "video_generation" not in config:
            config["video_generation"] = {
                "quality": {
                    "resolution": "1920x1080",
                    "fps": 24,
                    "bitrate": "5000k",
                    "audio_bitrate": "192k"
                },
                "paths": {
                    "projects_dir": "projects",
                    "assets_dir": "overlays",
                    "output_dir": "output",
                    "background_music_dir": "background_music"
                },
                "subtitles": {
                    "enable": True,
                    "font": "Arial",
                    "font_size": 24,
                    "font_color": "#FFFFFF",
                    "stroke_color": "#000000",
                    "stroke_width": 1.5,
                    "position": "bottom",
                    "max_words": 7
                },
                "transitions": {
                    "default_type": "dissolve",
                    "default_duration": 1.0
                },
                "audio": {
                    "default_music_volume": 0.08,
                    "normalize_audio": True
                }
            }
        
        video_config = config["video_generation"]
        
        # Configuración de Calidad
        st.subheader("🎯 Calidad de Video")
        quality_config = video_config.get("quality", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Resolución
            resolution_options = [
                "1920x1080", "1280x720", "3840x2160", "2560x1440", "1366x768"
            ]
            current_resolution = quality_config.get("resolution", "1920x1080")
            if current_resolution not in resolution_options:
                resolution_options.append(current_resolution)
            
            quality_config["resolution"] = st.selectbox(
                "Resolución",
                resolution_options,
                index=resolution_options.index(current_resolution),
                help="Resolución del video de salida"
            )
            
            # FPS
            quality_config["fps"] = st.selectbox(
                "FPS (Frames por Segundo)",
                [24, 25, 30, 60],
                index=[24, 25, 30, 60].index(quality_config.get("fps", 24)),
                help="Frames por segundo del video"
            )
        
        with col2:
            # Bitrate de video
            quality_config["bitrate"] = st.text_input(
                "Bitrate de Video",
                value=quality_config.get("bitrate", "5000k"),
                help="Bitrate del video (ej: 5000k, 8000k)"
            )
            
            # Bitrate de audio
            quality_config["audio_bitrate"] = st.text_input(
                "Bitrate de Audio",
                value=quality_config.get("audio_bitrate", "192k"),
                help="Bitrate del audio (ej: 128k, 192k, 320k)"
            )
        
        video_config["quality"] = quality_config
        
        st.divider()
        
        # Configuración de Subtítulos
        st.subheader("📝 Configuración de Subtítulos")
        subtitle_config = video_config.get("subtitles", {})
        
        # Habilitar subtítulos
        subtitle_config["enable"] = st.checkbox(
            "Habilitar Subtítulos",
            value=subtitle_config.get("enable", True),
            help="Activar o desactivar la generación de subtítulos"
        )
        
        if subtitle_config["enable"]:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Fuente
                subtitle_config["font"] = st.text_input(
                    "Fuente",
                    value=subtitle_config.get("font", "Arial"),
                    help="Nombre de la fuente para subtítulos"
                )
                
                # Tamaño de fuente
                subtitle_config["font_size"] = st.slider(
                    "Tamaño de Fuente",
                    min_value=12,
                    max_value=72,
                    value=subtitle_config.get("font_size", 24),
                    help="Tamaño de la fuente en píxeles"
                )
            
            with col2:
                # Color de fuente
                subtitle_config["font_color"] = st.color_picker(
                    "Color de Fuente",
                    value=subtitle_config.get("font_color", "#FFFFFF"),
                    help="Color del texto de los subtítulos"
                )
                
                # Color del borde
                subtitle_config["stroke_color"] = st.color_picker(
                    "Color del Borde",
                    value=subtitle_config.get("stroke_color", "#000000"),
                    help="Color del borde del texto"
                )
            
            with col3:
                # Ancho del borde
                subtitle_config["stroke_width"] = st.slider(
                    "Ancho del Borde",
                    min_value=0.0,
                    max_value=5.0,
                    value=float(subtitle_config.get("stroke_width", 1.5)),
                    step=0.1,
                    help="Ancho del borde en píxeles"
                )
                
                # Posición
                subtitle_config["position"] = st.selectbox(
                    "Posición",
                    ["bottom", "top", "center"],
                    index=["bottom", "top", "center"].index(subtitle_config.get("position", "bottom")),
                    help="Posición de los subtítulos en el video"
                )
            
            # Máximo de palabras por línea
            subtitle_config["max_words"] = st.slider(
                "Máximo de Palabras por Línea",
                min_value=3,
                max_value=15,
                value=subtitle_config.get("max_words", 7),
                help="Número máximo de palabras por línea de subtítulo"
            )
        
        video_config["subtitles"] = subtitle_config
        
        st.divider()
        
        # Configuración de Transiciones
        st.subheader("🔄 Configuración de Transiciones")
        transition_config = video_config.get("transitions", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Tipo de transición por defecto
            transition_types = [
                "dissolve", "fade", "slide_left", "slide_right", 
                "slide_up", "slide_down", "zoom_in", "zoom_out"
            ]
            current_transition = transition_config.get("default_type", "dissolve")
            if current_transition not in transition_types:
                transition_types.append(current_transition)
            
            transition_config["default_type"] = st.selectbox(
                "Tipo de Transición por Defecto",
                transition_types,
                index=transition_types.index(current_transition),
                help="Tipo de transición que se usará por defecto entre escenas"
            )
        
        with col2:
            # Duración de transición
            transition_config["default_duration"] = st.slider(
                "Duración de Transición (segundos)",
                min_value=0.1,
                max_value=3.0,
                value=float(transition_config.get("default_duration", 1.0)),
                step=0.1,
                help="Duración por defecto de las transiciones"
            )
        
        video_config["transitions"] = transition_config
        
        st.divider()
        
        # Configuración de Audio
        st.subheader("🎵 Configuración de Audio")
        audio_config = video_config.get("audio", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Volumen de música de fondo
            audio_config["default_music_volume"] = st.slider(
                "Volumen de Música de Fondo",
                min_value=0.0,
                max_value=1.0,
                value=float(audio_config.get("default_music_volume", 0.08)),
                step=0.01,
                help="Volumen por defecto de la música de fondo (0.0 = silencio, 1.0 = máximo)"
            )
        
        with col2:
            # Normalizar audio
            audio_config["normalize_audio"] = st.checkbox(
                "Normalizar Audio",
                value=audio_config.get("normalize_audio", True),
                help="Normalizar el volumen del audio para mantener consistencia"
            )
        
        video_config["audio"] = audio_config
        
        st.divider()
        
        # Configuración de Rutas
        st.subheader("📁 Rutas de Archivos")
        paths_config = video_config.get("paths", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            paths_config["projects_dir"] = st.text_input(
                "Directorio de Proyectos",
                value=paths_config.get("projects_dir", "projects"),
                help="Directorio donde se guardan los proyectos"
            )
            
            paths_config["output_dir"] = st.text_input(
                "Directorio de Salida",
                value=paths_config.get("output_dir", "output"),
                help="Directorio donde se guardan los videos generados"
            )
        
        with col2:
            paths_config["assets_dir"] = st.text_input(
                "Directorio de Assets",
                value=paths_config.get("assets_dir", "overlays"),
                help="Directorio con overlays y elementos gráficos"
            )
            
            paths_config["background_music_dir"] = st.text_input(
                "Directorio de Música",
                value=paths_config.get("background_music_dir", "background_music"),
                help="Directorio con archivos de música de fondo"
            )
        
        video_config["paths"] = paths_config
        
        # Validar directorios
        st.subheader("✅ Validación de Directorios")
        for name, path in paths_config.items():
            valid, message = ConfigValidator.validate_directory(path)
            if valid:
                st.success(f"📁 {name}: {message}")
            else:
                st.error(f"📁 {name}: {message}")
        
        config["video_generation"] = video_config
        return config
    
    def render_backup_restore_section(config):
        """Renderiza la sección de backup y restore"""
        st.subheader("💾 Backup y Restauración")
        
        # Crear directorio de backups si no existe
        backup_dir = Path("config_backups")
        backup_dir.mkdir(exist_ok=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📤 Crear Backup**")
            
            backup_name = st.text_input(
                "Nombre del Backup (opcional)",
                placeholder="backup_personalizado",
                help="Si no especificas nombre, se usará la fecha y hora actual"
            )
            
            if st.button("💾 Crear Backup", type="primary"):
                try:
                    # Crear nombre del backup
                    if not backup_name:
                        backup_name = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    backup_file = backup_dir / f"{backup_name}.json"
                    
                    # Guardar configuración
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False, default=str)
                    
                    st.success(f"✅ Backup creado: {backup_file}")
                except Exception as e:
                    st.error(f"❌ Error creando backup: {e}")
        
        with col2:
            st.write("**📥 Restaurar Backup**")
            
            # Listar backups disponibles
            backup_files = list(backup_dir.glob("*.json"))
            
            if backup_files:
                # Ordenar por fecha de modificación
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                backup_options = []
                for backup_file in backup_files:
                    modified_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    size_mb = backup_file.stat().st_size / 1024 / 1024
                    backup_options.append(f"{backup_file.stem} ({modified_time.strftime('%Y-%m-%d %H:%M')} - {size_mb:.1f}MB)")
                
                selected_backup_idx = st.selectbox(
                    "Seleccionar Backup",
                    range(len(backup_options)),
                    format_func=lambda x: backup_options[x],
                    help="Selecciona un backup para restaurar"
                )
                
                col2_1, col2_2 = st.columns(2)
                
                with col2_1:
                    if st.button("📥 Restaurar", type="secondary"):
                        try:
                            selected_backup = backup_files[selected_backup_idx]
                            with open(selected_backup, 'r', encoding='utf-8') as f:
                                restored_config = json.load(f)
                            
                            # Guardar en session state para aplicar
                            st.session_state["restored_config"] = restored_config
                            st.success("✅ Backup restaurado. Guarda la configuración para aplicar cambios.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error restaurando backup: {e}")
                
                with col2_2:
                    if st.button("🗑️ Eliminar", type="secondary"):
                        try:
                            selected_backup = backup_files[selected_backup_idx]
                            selected_backup.unlink()
                            st.success("✅ Backup eliminado")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
            else:
                st.info("No hay backups disponibles")
        
        # Mostrar lista de backups
        if backup_files:
            st.write("**📋 Backups Disponibles:**")
            for backup_file in backup_files[:5]:  # Mostrar solo los 5 más recientes
                modified_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                size_mb = backup_file.stat().st_size / 1024 / 1024
                st.write(f"• {backup_file.stem} - {modified_time.strftime('%Y-%m-%d %H:%M')} ({size_mb:.1f} MB)")
        
        # Aplicar configuración restaurada si existe
        if "restored_config" in st.session_state:
            config = st.session_state["restored_config"]
            del st.session_state["restored_config"]
        
        return config



def show_settings_page():
    """Renderiza la página de configuración completa y centralizada."""
    st.title("⚙️ Configuración Central del Proyecto")
    st.markdown("Aquí puedes gestionar todos los ajustes de la aplicación. Los cambios se guardan en `config.yaml`.")

    # Cargar configuración con cache mejorado
    if "config_cache_time" not in st.session_state:
        st.session_state.config_cache_time = datetime.now()
    
    # Recargar config si han pasado más de 30 segundos o si se fuerza
    if "force_config_reload" in st.session_state or \
       (datetime.now() - st.session_state.config_cache_time).seconds > 30:
        load_config.clear()  # Limpiar cache de Streamlit
        st.session_state.config_cache_time = datetime.now()
        if "force_config_reload" in st.session_state:
            del st.session_state.force_config_reload

    config = load_config()

    # Dashboard de estado al inicio
    ConfigStatusDashboard.render_status_dashboard(config)
    
    st.divider()

    # Crear pestañas expandidas
    tab_dashboard, tab_general, tab_ai, tab_tts, tab_transcription, tab_video, tab_fish_audio_monitoring, tab_backup = st.tabs([
        "📊 Dashboard",
        "⚙️ General", 
        "🤖 IA", 
        "🎤 Síntesis de Voz (TTS)",
        "🎙️ Transcripción",
        "🎥 Video",
        "🐟 Monitoreo Fish Audio",
        "💾 Backup/Restore"
    ])

    # --- Pestaña Dashboard ---
    with tab_dashboard:
        st.header("📊 Panel de Control")
        
        # Configuración inteligente
        st.subheader("🧠 Configuración Inteligente")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔧 Auto-detectar Configuración Óptima", type="primary"):
                with st.spinner("Detectando configuración óptima..."):
                    config = auto_detect_optimal_config(config)
                    st.success("✅ Configuración optimizada automáticamente")
                    st.session_state.force_config_reload = True
                    st.rerun()
        
        with col2:
            if st.button("🔄 Recargar Configuración", type="secondary"):
                st.session_state.force_config_reload = True
                st.rerun()
        
        # Métricas rápidas
        st.subheader("📈 Métricas Rápidas")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Contar APIs configuradas
            ai_config = config.get("ai", {})
            apis_configured = sum([
                1 for key in ["openai_api_key", "gemini_api_key", "replicate_api_key"] 
                if ai_config.get(key, "").strip()
            ])
            st.metric("🔑 APIs", f"{apis_configured}/3")
        
        with col2:
            # Verificar directorios
            dirs = [config.get("output_dir"), config.get("projects_dir"), 
                   config.get("temp_dir"), config.get("background_music_dir")]
            dirs_valid = sum([1 for d in dirs if d and Path(d).exists()])
            st.metric("📁 Directorios", f"{dirs_valid}/{len(dirs)}")
        
        with col3:
            # Estado TTS
            tts_providers = 0
            if config.get("tts", {}).get("edge", {}).get("default_voice"):
                tts_providers += 1
            if config.get("tts", {}).get("fish_audio", {}).get("api_key", "").strip():
                tts_providers += 1
            st.metric("🎤 TTS", f"{tts_providers}/2")
        
        with col4:
            # Configuración de video
            video_config = config.get("video_generation", {})
            video_complete = 1 if video_config else 0
            st.metric("🎥 Video", f"{video_complete}/1")
        
        # Acciones rápidas
        st.subheader("⚡ Acciones Rápidas")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🧪 Probar APIs", type="secondary"):
                test_all_apis(config)
        
        with col2:
            if st.button("📁 Crear Directorios", type="secondary"):
                create_all_directories(config)
        
        with col3:
            if st.button("💾 Backup Rápido", type="secondary"):
                backup_manager = ConfigBackupManager()
                backup_file = backup_manager.create_backup(config)
                st.success(f"✅ Backup creado: {backup_file}")
        
        # Logs recientes
        st.subheader("📋 Configuración Actual")
        with st.expander("Ver configuración completa (JSON)"):
            st.json(config)

    # --- Pestaña General ---
    with tab_general:
        st.header("Configuración General")
        
        # Configuración de directorios
        st.subheader("📁 Directorios")
        col1, col2 = st.columns(2)
        
        with col1:
            config["output_dir"] = st.text_input(
                "Directorio de Salida",
                value=config.get("output_dir", "output"),
                help="Directorio donde se guardarán los videos generados"
            )
            
            config["projects_dir"] = st.text_input(
                "Directorio de Proyectos",
                value=config.get("projects_dir", "projects"),
                help="Directorio donde se guardarán los proyectos"
            )
        
        with col2:
            config["temp_dir"] = st.text_input(
                "Directorio Temporal",
                value=config.get("temp_dir", "temp"),
                help="Directorio para archivos temporales"
            )
            
            config["background_music_dir"] = st.text_input(
                "Directorio de Música",
                value=config.get("background_music_dir", "background_music"),
                help="Directorio con música de fondo"
            )

    # --- Pestaña de IA ---
    with tab_ai:
        st.header("Configuración de Servicios de IA")
        
        # Configuración de OpenAI
        st.subheader("🔑 OpenAI")
        ai_config = config.get("ai", {})
        
        col_key, col_validate = st.columns([3, 1])
        
        with col_key:
            ai_config["openai_api_key"] = st.text_input(
                "OpenAI API Key",
                value=ai_config.get("openai_api_key", ""),
                type="password",
                help="API key de OpenAI. Obtén una en https://platform.openai.com"
            )
        
        with col_validate:
            st.write("")  # Espaciado
            if st.button("🔍", key="validate_openai", help="Validar API Key"):
                if ai_config["openai_api_key"]:
                    with st.spinner("Validando..."):
                        valid, message = ConfigValidator.validate_api_key("openai", ai_config["openai_api_key"])
                        if valid:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.warning("Ingresa una API key primero")
        
        # Configuración de Gemini
        st.subheader("🔑 Google Gemini")
        col_key, col_validate = st.columns([3, 1])
        
        with col_key:
            ai_config["gemini_api_key"] = st.text_input(
                "Gemini API Key",
                value=ai_config.get("gemini_api_key", ""),
                type="password",
                help="API key de Google Gemini. Obtén una en https://makersuite.google.com"
            )
        
        with col_validate:
            st.write("")  # Espaciado
            if st.button("🔍", key="validate_gemini", help="Validar API Key"):
                if ai_config["gemini_api_key"]:
                    with st.spinner("Validando..."):
                        valid, message = ConfigValidator.validate_api_key("gemini", ai_config["gemini_api_key"])
                        if valid:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.warning("Ingresa una API key primero")
        
        # Configuración de Replicate
        st.subheader("🔑 Replicate")
        col_key, col_validate = st.columns([3, 1])
        
        with col_key:
            ai_config["replicate_api_key"] = st.text_input(
                "Replicate API Key",
                value=ai_config.get("replicate_api_key", ""),
                type="password",
                help="API key de Replicate. Obtén una en https://replicate.com"
            )
        
        with col_validate:
            st.write("")  # Espaciado
            if st.button("🔍", key="validate_replicate", help="Validar API Key"):
                if ai_config["replicate_api_key"]:
                    with st.spinner("Validando..."):
                        valid, message = ConfigValidator.validate_api_key("replicate", ai_config["replicate_api_key"])
                        if valid:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.warning("Ingresa una API key primero")
        
        # Configuración de Ollama
        st.subheader("🔑 Ollama")
        col_key, col_validate = st.columns([3, 1])
        
        with col_key:
            ai_config["ollama_base_url"] = st.text_input(
                "Ollama Base URL",
                value=ai_config.get("ollama_base_url", "http://localhost:11434"),
                help="URL base de Ollama (por defecto: http://localhost:11434)"
            )
        
        with col_validate:
            st.write("")  # Espaciado
            if st.button("🔍", key="validate_ollama", help="Probar Conexión"):
                if ai_config["ollama_base_url"]:
                    with st.spinner("Probando conexión..."):
                        valid, message = ConfigValidator.validate_ollama_connection(ai_config["ollama_base_url"])
                        if valid:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.warning("Ingresa una URL primero")
        
        # Modelos por defecto
        st.subheader("🤖 Modelos por Defecto")
        default_models = ai_config.get("default_models", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            default_models["openai"] = st.text_input(
                "Modelo OpenAI",
                value=default_models.get("openai", "gpt-4o-mini"),
                help="Modelo de OpenAI por defecto"
            )
            
            default_models["gemini"] = st.text_input(
                "Modelo Gemini",
                value=default_models.get("gemini", "models/gemini-1.5-flash-latest"),
                help="Modelo de Gemini por defecto"
            )
        
        with col2:
            default_models["ollama"] = st.text_input(
                "Modelo Ollama",
                value=default_models.get("ollama", "llama3"),
                help="Modelo de Ollama por defecto"
            )
            
            default_models["image_generation"] = st.text_input(
                "Modelo de Generación de Imágenes",
                value=default_models.get("image_generation", "black-forest-labs/flux-schnell"),
                help="Modelo para generación de imágenes"
            )
        
        ai_config["default_models"] = default_models
        config["ai"] = ai_config

    # --- Pestaña de TTS ---
    with tab_tts:
        st.header("Configuración de Síntesis de Voz (TTS)")
        
        # Inicializar configuración TTS si no existe
        if "tts" not in config:
            config["tts"] = {
                "default_provider": "edge",
                "edge": {
                    "default_voice": "es-ES-AlvaroNeural",
                    "default_rate": "+0%",
                    "default_pitch": "+0Hz"
                },
                "fish_audio": {
                    "api_key": "TU_CLAVE_FISH_AUDIO_AQUI",
                    "default_model": "speech-1.6",
                    "default_format": "mp3",
                    "default_mp3_bitrate": 128,
                    "default_normalize": True,
                    "default_latency": "normal",
                    "reference_id": None
                }
            }
        
        tts_config = config["tts"]
        
        # Proveedor por defecto
        st.subheader("🔧 Configuración General")
        tts_config["default_provider"] = st.selectbox(
            "Proveedor TTS por Defecto",
            ["edge", "fish"],
            index=0 if tts_config.get("default_provider", "edge") == "edge" else 1,
            format_func=lambda x: "Edge TTS" if x == "edge" else "Fish Audio",
            help="Proveedor de síntesis de voz que se usará por defecto"
        )
        
        st.divider()
        
        # Configuración de Edge TTS
        st.subheader("🔊 Edge TTS (Gratuito)")
        edge_config = tts_config.get("edge", {})
        col1, col2, col3 = st.columns(3)
        
        with col1:
            edge_config["default_voice"] = st.text_input(
                "Voz por Defecto",
                value=edge_config.get("default_voice", "es-ES-AlvaroNeural"),
                help="Voz de Edge TTS por defecto"
            )
        
        with col2:
            edge_config["default_rate"] = st.text_input(
                "Velocidad por Defecto",
                value=edge_config.get("default_rate", "+0%"),
                help="Formato: +X% o -X%"
            )
        
        with col3:
            edge_config["default_pitch"] = st.text_input(
                "Tono por Defecto",
                value=edge_config.get("default_pitch", "+0Hz"),
                help="Formato: +XHz o -XHz"
            )
        
        tts_config["edge"] = edge_config
        
        st.divider()
        
        # Configuración de Fish Audio
        st.subheader("🐟 Fish Audio (Premium)")
        st.info("Fish Audio ofrece calidad premium de síntesis de voz. Requiere una API key válida.")
        
        fish_config = tts_config.get("fish_audio", {})
        
        # API Key
        fish_config["api_key"] = st.text_input(
            "Fish Audio API Key",
            value=fish_config.get("api_key", ""),
            type="password",
            help="API key de Fish Audio. Obtén una en https://fish.audio"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Modelo por defecto
            fish_models = [
                ("speech-1.5", "Fish Audio Speech 1.5"),
                ("speech-1.6", "Fish Audio Speech 1.6 (Recomendado)"),
                ("s1", "Fish Audio S1")
            ]
            default_model = fish_config.get("default_model", "speech-1.6")
            model_index = [m[0] for m in fish_models].index(default_model) if default_model in [m[0] for m in fish_models] else 1
            fish_config["default_model"] = st.selectbox(
                "Modelo por Defecto",
                [m[0] for m in fish_models],
                index=model_index,
                format_func=lambda x: dict(fish_models)[x]
            )
            
            # Formato por defecto
            fish_config["default_format"] = st.selectbox(
                "Formato por Defecto",
                ["mp3", "wav", "pcm"],
                index=0 if fish_config.get("default_format", "mp3") == "mp3" else (1 if fish_config.get("default_format") == "wav" else 2)
            )
            
            # Bitrate por defecto
            fish_config["default_mp3_bitrate"] = st.selectbox(
                "Bitrate MP3 por Defecto",
                [64, 128, 192],
                index=1 if fish_config.get("default_mp3_bitrate", 128) == 128 else (0 if fish_config.get("default_mp3_bitrate") == 64 else 2)
            )
        
        with col2:
            # Latencia por defecto
            fish_config["default_latency"] = st.selectbox(
                "Latencia por Defecto",
                ["normal", "balanced"],
                index=0 if fish_config.get("default_latency", "normal") == "normal" else 1,
                help="Normal: Mayor estabilidad. Balanced: Menor latencia (300ms)"
            )
            
            # Normalizar por defecto
            fish_config["default_normalize"] = st.checkbox(
                "Normalizar Texto por Defecto",
                value=fish_config.get("default_normalize", True),
                help="Mejora la estabilidad para números y texto en inglés/chino"
            )
            
            # Reference ID (opcional)
            fish_config["reference_id"] = st.text_input(
                "Reference ID (Opcional)",
                value=fish_config.get("reference_id", ""),
                help="ID del modelo de referencia personalizado (opcional)"
            )
        
        tts_config["fish_audio"] = fish_config
        config["tts"] = tts_config

    # --- Pestaña de Transcripción ---
    with tab_transcription:
        st.header("🎙️ Configuración de Transcripción")
        
        # Inicializar configuración de transcripción si no existe
        if "transcription" not in config:
            config["transcription"] = {
                "service_type": "local",
                "local": {
                    "model_size": "medium",
                    "device": "cpu",
                    "compute_type": "int8",
                    "default_language": "es",
                    "beam_size": 5
                },
                "replicate": {
                    "default_language": "es",
                    "task": "transcribe",
                    "timestamp": "chunk",
                    "batch_size": 24,
                    "diarise_audio": False,
                    "hf_token": None
                }
            }
        
        transcription_config = config["transcription"]
        
        # Tipo de servicio
        st.subheader("🔧 Configuración General")
        transcription_config["service_type"] = st.selectbox(
            "Servicio de Transcripción",
            ["local", "replicate"],
            index=0 if transcription_config.get("service_type", "local") == "local" else 1,
            format_func=lambda x: "Whisper Local" if x == "local" else "Replicate (Incredibly Fast Whisper)",
            help="Whisper Local: Gratuito, requiere descarga de modelo. Replicate: Más rápido, requiere API key."
        )
        
        st.divider()
        
        # Configuración de Whisper Local
        st.subheader("🔊 Whisper Local (Gratuito)")
        st.info("Whisper local funciona sin conexión a internet pero requiere descargar el modelo.")
        
        local_config = transcription_config.get("local", {})
        col1, col2 = st.columns(2)
        
        with col1:
            # Tamaño del modelo
            model_sizes = [
                ("tiny", "Tiny (39MB) - Más rápido, menos preciso"),
                ("base", "Base (74MB) - Equilibrio velocidad/precisión"),
                ("small", "Small (244MB) - Bueno para la mayoría de casos"),
                ("medium", "Medium (769MB) - Recomendado"),
                ("large-v2", "Large V2 (1550MB) - Muy preciso, lento"),
                ("large-v3", "Large V3 (1550MB) - Más preciso, más lento")
            ]
            default_model = local_config.get("model_size", "medium")
            model_index = [m[0] for m in model_sizes].index(default_model) if default_model in [m[0] for m in model_sizes] else 3
            local_config["model_size"] = st.selectbox(
                "Tamaño del Modelo",
                [m[0] for m in model_sizes],
                index=model_index,
                format_func=lambda x: dict(model_sizes)[x],
                help="Modelos más grandes son más precisos pero más lentos"
            )
            
            # Dispositivo
            local_config["device"] = st.selectbox(
                "Dispositivo",
                ["cpu", "cuda"],
                index=0 if local_config.get("device", "cpu") == "cpu" else 1,
                help="CPU: Más lento pero funciona en cualquier máquina. CUDA: Más rápido si tienes GPU NVIDIA"
            )
        
        with col2:
            # Tipo de cómputo
            compute_types = [
                ("int8", "Int8 - Más rápido, menos preciso"),
                ("float16", "Float16 - Equilibrio velocidad/precisión"),
                ("int8_float16", "Int8 Float16 - Optimizado"),
                ("float32", "Float32 - Más preciso, más lento")
            ]
            default_compute = local_config.get("compute_type", "int8")
            compute_index = [c[0] for c in compute_types].index(default_compute) if default_compute in [c[0] for c in compute_types] else 0
            local_config["compute_type"] = st.selectbox(
                "Tipo de Cómputo",
                [c[0] for c in compute_types],
                index=compute_index,
                format_func=lambda x: dict(compute_types)[x]
            )
            
            # Beam size
            local_config["beam_size"] = st.slider(
                "Beam Size",
                min_value=1,
                max_value=10,
                value=local_config.get("beam_size", 5),
                help="Valores más altos mejoran la precisión pero son más lentos"
            )
        
        # Idioma por defecto
        default_lang = local_config.get("default_language", "es")
        lang_options = ["es", "en", "fr", "pt", "it"]
        lang_names = {"es": "Español", "en": "Inglés", "fr": "Francés", "pt": "Portugués", "it": "Italiano"}
        lang_index = lang_options.index(default_lang) if default_lang in lang_options else 0
        
        local_config["default_language"] = st.selectbox(
            "Idioma por Defecto (Local)",
            lang_options,
            index=lang_index,
            format_func=lambda x: lang_names[x],
            help="Idioma por defecto para transcripción local"
        )
        
        transcription_config["local"] = local_config
        
        st.divider()
        
        # Configuración de Replicate
        st.subheader("🚀 Replicate (Incredibly Fast Whisper)")
        st.info("Replicate ofrece transcripción mucho más rápida y precisa. Requiere API key de Replicate.")
        
        replicate_config = transcription_config.get("replicate", {})
        
        # Verificar si Replicate está disponible
        try:
            import replicate
            replicate_available = True
        except ImportError:
            replicate_available = False
            st.error("❌ Replicate no está disponible. Instala 'replicate' para usar este servicio.")
        
        if replicate_available:
            col1, col2 = st.columns(2)
            
            with col1:
                # Idioma por defecto
                replicate_languages = {
                    "es": "Español",
                    "en": "Inglés", 
                    "fr": "Francés",
                    "pt": "Portugués",
                    "pt-BR": "Portugués Brasileño",
                    "it": "Italiano"
                }
                default_replicate_lang = replicate_config.get("default_language", "es")
                lang_index = list(replicate_languages.keys()).index(default_replicate_lang) if default_replicate_lang in replicate_languages else 0
                replicate_config["default_language"] = st.selectbox(
                    "Idioma por Defecto (Replicate)",
                    list(replicate_languages.keys()),
                    index=lang_index,
                    format_func=lambda x: replicate_languages[x],
                    help="Idioma por defecto para transcripción con Replicate"
                )
                
                # Tarea
                replicate_config["task"] = st.selectbox(
                    "Tarea",
                    ["transcribe", "translate"],
                    index=0 if replicate_config.get("task", "transcribe") == "transcribe" else 1,
                    format_func=lambda x: "Transcribir" if x == "transcribe" else "Traducir",
                    help="Transcribir: Mantener idioma original. Traducir: Convertir a inglés"
                )
            
            with col2:
                # Timestamp
                replicate_config["timestamp"] = st.selectbox(
                    "Tipo de Timestamp",
                    ["chunk", "word"],
                    index=0 if replicate_config.get("timestamp", "chunk") == "chunk" else 1,
                    format_func=lambda x: "Por Chunk" if x == "chunk" else "Por Palabra",
                    help="Chunk: Timestamps por segmentos. Word: Timestamps por palabra (más preciso)"
                )
                
                # Batch size
                replicate_config["batch_size"] = st.slider(
                    "Batch Size",
                    min_value=8,
                    max_value=64,
                    value=replicate_config.get("batch_size", 24),
                    help="Tamaño del batch. Reducir si hay problemas de memoria"
                )
            
            # Diarización de audio
            replicate_config["diarise_audio"] = st.checkbox(
                "Diarización de Audio",
                value=replicate_config.get("diarise_audio", False),
                help="Identificar diferentes hablantes en el audio (requiere Hugging Face token)"
            )
            
            # Hugging Face token (solo si diarización está habilitada)
            if replicate_config["diarise_audio"]:
                replicate_config["hf_token"] = st.text_input(
                    "Hugging Face Token",
                    value=replicate_config.get("hf_token", ""),
                    type="password",
                    help="Token de Hugging Face para diarización. Obtén uno en https://huggingface.co/settings/tokens"
                )
            
            # Información de costos
            st.info("""
            **Costos estimados de Replicate:**
            - Aproximadamente $0.01-0.05 por minuto de audio
            - Más rápido que Whisper local
            - Mejor precisión en múltiples idiomas
            """)
        
        transcription_config["replicate"] = replicate_config
        config["transcription"] = transcription_config

    # --- Pestaña de Video ---
    with tab_video:
        config = render_video_configuration_tab(config)

    # --- Pestaña de Monitoreo Fish Audio ---
    with tab_fish_audio_monitoring:
        st.header("🐟 Monitoreo de Créditos Fish Audio")
        
        try:
            from utils.audio_services import get_fish_audio_tracker, FISH_AUDIO_AVAILABLE
            
            if not FISH_AUDIO_AVAILABLE:
                st.error("❌ Fish Audio SDK no está disponible. Instala 'fish-audio-sdk' para usar el monitoreo.")
                st.stop()
            
            tracker = get_fish_audio_tracker()
            usage_summary = tracker.get_usage_summary()
            
            # Información general
            st.subheader("📊 Resumen de Uso")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "💰 Costo Total",
                    f"${usage_summary['total']['cost_usd']:.2f}",
                    f"${usage_summary['total']['cost_usd'] - usage_summary['yesterday']['cost_usd']:.2f}"
                )
            
            with col2:
                st.metric(
                    "📈 Bytes Procesados",
                    f"{usage_summary['total']['bytes_processed']:,}",
                    f"{usage_summary['total']['bytes_processed'] - usage_summary['yesterday']['bytes_processed']:,}"
                )
            
            with col3:
                st.metric(
                    "🎯 Presupuesto Restante",
                    f"${usage_summary['total']['budget_remaining']:.2f}",
                    f"de ${usage_summary['budget_limit']:.2f}"
                )
            
            with col4:
                percentage_used = (usage_summary['total']['cost_usd'] / usage_summary['budget_limit']) * 100
                st.metric(
                    "📊 Porcentaje Usado",
                    f"{percentage_used:.1f}%"
                )
            
            # Barra de progreso del presupuesto
            st.progress(min(percentage_used / 100, 1.0))
            
            # Uso de hoy vs ayer
            st.subheader("📅 Uso Diario")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "📅 Hoy",
                    f"${usage_summary['today']['cost_usd']:.2f}",
                    f"{usage_summary['today']['requests']} requests"
                )
            
            with col2:
                st.metric(
                    "📅 Ayer",
                    f"${usage_summary['yesterday']['cost_usd']:.2f}",
                    f"{usage_summary['yesterday']['requests']} requests"
                )
            
            # Estimaciones
            st.subheader("🔮 Estimaciones")
            
            # Calcular estimaciones
            estimation = tracker.estimate_remaining_usage()
            
            if estimation['can_process']:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "📝 Caracteres Restantes",
                        f"{estimation['estimated_characters']:,}"
                    )
                
                with col2:
                    st.metric(
                        "📖 Palabras Restantes",
                        f"{estimation['estimated_words']:,}"
                    )
                
                with col3:
                    st.metric(
                        "⏱️ Minutos de Audio",
                        f"{estimation['estimated_minutes']}"
                    )
            else:
                st.warning("⚠️ No hay presupuesto restante para procesar más texto.")
            
            # Configuración de alertas
            st.subheader("⚙️ Configuración de Alertas")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Límite de presupuesto
                new_budget_limit = st.number_input(
                    "Límite de Presupuesto ($)",
                    min_value=1.0,
                    max_value=1000.0,
                    value=float(usage_summary['budget_limit']),
                    step=1.0,
                    help="Límite de presupuesto mensual en dólares"
                )
                
                if st.button("💾 Guardar Límite"):
                    tracker.set_budget_limit(new_budget_limit)
                    st.success("✅ Límite de presupuesto actualizado")
                    st.rerun()
            
            with col2:
                # Estimador de texto
                st.subheader("🧮 Estimador de Texto")
                
                sample_text = st.text_area(
                    "Ingresa texto para estimar costo:",
                    placeholder="Escribe aquí el texto que quieres procesar...",
                    height=100
                )
                
                if sample_text:
                    text_estimation = tracker.estimate_remaining_usage(len(sample_text))
                    
                    if text_estimation.get('can_process_text', False):
                        st.success(f"✅ Costo estimado: ${text_estimation['text_cost']:.4f}")
                    else:
                        st.error(f"❌ Costo estimado: ${text_estimation['text_cost']:.4f} - Excede el presupuesto")
            
            # Acciones
            st.subheader("🛠️ Acciones")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Actualizar Datos", type="secondary"):
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Reiniciar Estadísticas", type="secondary"):
                    if st.checkbox("Confirmar reinicio de estadísticas"):
                        tracker.reset_usage()
                        st.success("✅ Estadísticas reiniciadas")
                        st.rerun()
            
            # Información adicional
            st.subheader("ℹ️ Información")
            
            st.info(f"""
            **Precio**: ${usage_summary['cost_per_million_bytes']:.2f} por millón de bytes UTF-8
            
            **Cálculo**: 1 millón de bytes ≈ 500,000 caracteres ≈ 83,000 palabras ≈ 5-6 horas de audio
            
            **Recomendación**: Monitorea tu uso regularmente para optimizar costos.
            """)
            
        except ImportError as e:
            st.error(f"❌ Error importando módulos de Fish Audio: {e}")
        except Exception as e:
            st.error(f"❌ Error cargando datos de monitoreo: {e}")
            st.exception(e)

    # --- Pestaña de Backup/Restore ---
    with tab_backup:
        config = render_backup_restore_section(config)

    # --- Botón de Guardado Mejorado --- 
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Guardar Configuración", type="primary", use_container_width=True):
            with st.spinner("Guardando configuración..."):
                # Crear backup automático antes de guardar
                backup_manager = ConfigBackupManager()
                backup_file = backup_manager.create_backup(config, "auto_backup_before_save")
                
                if save_config(config):
                    st.success(f"✅ Configuración guardada. Backup automático: {backup_file}")
                    st.session_state.force_config_reload = True
                    st.rerun()
                else:
                    st.error("❌ Error guardando configuración")
    
    with col2:
        if st.button("🔐 Guardar con API Keys", type="secondary", use_container_width=True):
            with st.spinner("Guardando configuración y API keys..."):
                backup_manager = ConfigBackupManager()
                backup_file = backup_manager.create_backup(config, "auto_backup_with_keys")
                
                if save_config_with_api_keys(config):
                    st.success(f"✅ Configuración y API keys guardadas. Backup: {backup_file}")
                    st.session_state.force_config_reload = True
                    st.rerun()
                else:
                    st.error("❌ Error guardando configuración")
    
    with col3:
        if st.button("🧪 Validar Todo", type="secondary", use_container_width=True):
            validate_entire_configuration(config)

# --- Funciones Auxiliares ---

def auto_detect_optimal_config(config: Dict[Any, Any]) -> Dict[Any, Any]:
    """Detecta automáticamente la configuración óptima"""
    
    # Detectar capacidades del sistema
    import psutil
    import platform
    
    # Configuración de transcripción basada en recursos
    memory_gb = psutil.virtual_memory().total / (1024**3)
    cpu_count = psutil.cpu_count()
    
    if "transcription" not in config:
        config["transcription"] = {}
    
    if "local" not in config["transcription"]:
        config["transcription"]["local"] = {}
    
    # Seleccionar modelo de Whisper basado en memoria
    if memory_gb >= 16:
        config["transcription"]["local"]["model_size"] = "large-v3"
        config["transcription"]["local"]["compute_type"] = "float16"
    elif memory_gb >= 8:
        config["transcription"]["local"]["model_size"] = "medium"
        config["transcription"]["local"]["compute_type"] = "int8_float16"
    else:
        config["transcription"]["local"]["model_size"] = "small"
        config["transcription"]["local"]["compute_type"] = "int8"
    
    # Detectar GPU NVIDIA
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            config["transcription"]["local"]["device"] = "cuda"
            st.info("🎯 GPU NVIDIA detectada - Configurando para usar CUDA")
        else:
            config["transcription"]["local"]["device"] = "cpu"
    except ImportError:
        config["transcription"]["local"]["device"] = "cpu"
    
    # Configuración de video basada en resolución común
    if "video_generation" not in config:
        config["video_generation"] = {}
    
    if "quality" not in config["video_generation"]:
        config["video_generation"]["quality"] = {}
    
    # Configuración conservadora para compatibilidad
    config["video_generation"]["quality"]["resolution"] = "1920x1080"
    config["video_generation"]["quality"]["fps"] = 24
    config["video_generation"]["quality"]["bitrate"] = "5000k"
    
    st.success(f"🎯 Configuración optimizada para: {memory_gb:.1f}GB RAM, {cpu_count} CPUs")
    
    return config

def test_all_apis(config: Dict[Any, Any]):
    """Prueba todas las APIs configuradas"""
    st.subheader("🧪 Probando APIs...")
    
    ai_config = config.get("ai", {})
    tts_config = config.get("tts", {})
    
    apis_to_test = [
        ("OpenAI", "openai", ai_config.get("openai_api_key", "")),
        ("Gemini", "gemini", ai_config.get("gemini_api_key", "")),
        ("Replicate", "replicate", ai_config.get("replicate_api_key", "")),
        ("Fish Audio", "fish_audio", tts_config.get("fish_audio", {}).get("api_key", ""))
    ]
    
    results = []
    
    for name, service, api_key in apis_to_test:
        if api_key and api_key.strip():
            with st.spinner(f"Probando {name}..."):
                valid, message = ConfigValidator.validate_api_key(service, api_key)
                results.append((name, valid, message))
        else:
            results.append((name, False, "❌ API key no configurada"))
    
    # Mostrar resultados
    for name, valid, message in results:
        if valid:
            st.success(f"✅ {name}: {message}")
        else:
            st.error(f"❌ {name}: {message}")

def create_all_directories(config: Dict[Any, Any]):
    """Crea todos los directorios necesarios"""
    st.subheader("📁 Creando directorios...")
    
    directories = [
        ("Output", config.get("output_dir", "output")),
        ("Projects", config.get("projects_dir", "projects")),
        ("Temp", config.get("temp_dir", "temp")),
        ("Background Music", config.get("background_music_dir", "background_music"))
    ]
    
    # Agregar directorios de video si existen
    video_paths = config.get("video_generation", {}).get("paths", {})
    for key, path in video_paths.items():
        if path:
            directories.append((key.title(), path))
    
    success_count = 0
    
    for name, path in directories:
        if path:
            valid, message = ConfigValidator.validate_directory(path)
            if valid:
                st.success(f"✅ {name}: {message}")
                success_count += 1
            else:
                st.error(f"❌ {name}: {message}")
        else:
            st.warning(f"⚠️ {name}: Ruta no configurada")
    
    st.info(f"📊 {success_count}/{len(directories)} directorios creados/verificados")

def validate_entire_configuration(config: Dict[Any, Any]):
    """Valida toda la configuración"""
    st.subheader("🔍 Validando configuración completa...")
    
    validation_results = {
        "apis": 0,
        "directories": 0,
        "services": 0,
        "total_checks": 0
    }
    
    # Validar APIs
    st.write("**🔑 Validando APIs...**")
    test_all_apis(config)
    
    # Validar directorios
    st.write("**📁 Validando directorios...**")
    create_all_directories(config)
    
    # Validar servicios
    st.write("**🛠️ Validando servicios...**")
    
    # Ollama
    ollama_url = config.get("ai", {}).get("ollama_base_url", "")
    if ollama_url:
        valid, message = ConfigValidator.validate_ollama_connection(ollama_url)
        if valid:
            st.success(f"✅ Ollama: {message}")
        else:
            st.error(f"❌ Ollama: {message}")
    
    st.success("🎉 Validación completa finalizada")

# Para poder llamar a esta página desde app.py
if __name__ == "__main__":
    show_settings_page()
