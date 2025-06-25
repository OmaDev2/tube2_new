import streamlit as st
import json
from pathlib import Path
import os
from datetime import datetime

def show_history():
    st.title("📋 Historial de Proyectos")
    
    # Obtener directorio de proyectos
    config_dir = Path.home() / ".videogenai"
    config_file = config_dir / "config.json"
    
    if not config_file.exists():
        st.warning("No se encontró la configuración. Por favor, configura la aplicación primero.")
        return
    
    # Leer configuración
    with open(config_file, "r") as f:
        config = json.load(f)
    
    projects_dir = Path(config["projects_dir"])
    
    if not projects_dir.exists():
        st.warning("No se encontró el directorio de proyectos.")
        return
    
    # Obtener lista de proyectos
    projects = []
    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir():
            project_file = project_dir / "project.json"
            if project_file.exists():
                with open(project_file, "r") as f:
                    project_data = json.load(f)
                    projects.append(project_data)
    
    if not projects:
        st.info("No hay proyectos en el historial.")
        return
    
    # Ordenar proyectos por fecha
    projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Mostrar lista de proyectos
    for project in projects:
        with st.expander(f"📽️ {project.get('name', 'Proyecto sin nombre')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Fecha de creación:** {project.get('created_at', 'Desconocida')}")
                st.write(f"**Duración:** {project.get('duration', 'Desconocida')} segundos")
                st.write(f"**Número de imágenes:** {len(project.get('images', []))}")
            
            with col2:
                st.write(f"**Resolución:** {project.get('resolution', 'Desconocida')}")
                st.write(f"**Formato:** {project.get('format', 'Desconocido')}")
                st.write(f"**Efectos aplicados:** {', '.join(project.get('effects', []))}")
            
            # Mostrar vista previa del video si existe
            video_path = project.get('output_path')
            if video_path and os.path.exists(video_path):
                st.video(video_path)
            
            # Botones de acción
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Reabrir", key=f"reopen_{project.get('id')}"):
                    st.session_state.current_project = project
                    st.experimental_rerun()
            
            with col2:
                if st.button("📤 Exportar", key=f"export_{project.get('id')}"):
                    export_project(project)
            
            with col3:
                if st.button("🗑️ Eliminar", key=f"delete_{project.get('id')}"):
                    delete_project(project)
                    st.experimental_rerun()

def export_project(project):
    """Exporta un proyecto a un archivo ZIP"""
    import shutil
    from datetime import datetime
    
    export_dir = Path.home() / "Downloads" / "VideoGenAI_Exports"
    export_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_name = f"{project.get('name', 'proyecto')}_{timestamp}"
    export_path = export_dir / f"{export_name}.zip"
    
    # Crear archivo ZIP
    shutil.make_archive(
        str(export_dir / export_name),
        'zip',
        project.get('project_dir')
    )
    
    st.success(f"Proyecto exportado a: {export_path}")

def delete_project(project):
    """Elimina un proyecto"""
    import shutil
    
    project_dir = Path(project.get('project_dir'))
    if project_dir.exists():
        shutil.rmtree(project_dir)
        st.success("Proyecto eliminado correctamente.")
    else:
        st.error("No se pudo encontrar el directorio del proyecto.") 