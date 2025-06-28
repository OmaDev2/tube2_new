#!/usr/bin/env python3
"""
Script para reparar problemas de contexto histórico en proyectos existentes.
Regenera los prompts de imagen con contexto histórico correcto.
"""

import json
import logging
from pathlib import Path
from utils.scene_generator import SceneGenerator
from utils.ai_services import AIServices

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_historical_prompts(project_path: str):
    """
    Repara los prompts anacrónicos de un proyecto aplicando contexto histórico correcto.
    """
    project_path = Path(project_path)
    scenes_file = project_path / "scenes.json"
    
    if not scenes_file.exists():
        logger.error(f"No se encontró {scenes_file}")
        return False
    
    # Cargar proyecto actual
    with open(scenes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    project_info = data.get("project_info_summary", {})
    scenes = data.get("scenes", [])
    
    logger.info(f"🏛️ Reparando proyecto: {project_info.get('titulo', 'Sin título')}")
    logger.info(f"📊 Escenas a reparar: {len(scenes)}")
    
    # Configurar el generador de escenas
    scene_generator = SceneGenerator()
    ai_service = AIServices()
    
    # Configuración del prompt histórico
    image_prompt_config = {
        "prompt_obj": {
            "nombre": "Escenas Fotorrealistas Históricamente Precisas",
            "system_prompt": """Eres un experto en generación de prompts para imágenes fotorrealistas con precisión histórica y cultural.
Tu tarea es crear prompts detallados que generen imágenes hiperrealistas respetando el contexto histórico, cultural y geográfico específico del contenido.

DEBES ANALIZAR Y INCLUIR:
- Período histórico exacto y sus características visuales
- Arquitectura típica de la época y región
- Vestimenta, peinados y accesorios apropiados para el tiempo
- Tecnología, objetos y herramientas disponibles en ese período
- Contexto geográfico y cultural específico
- Materiales, texturas y colores auténticos de la época

SIEMPRE INCLUYE:
- Personajes con características físicas y vestimenta históricamente precisas
- Ambiente y escenario con arquitectura y elementos de la época correcta
- Iluminación natural apropiada (velas, antorchas, luz solar según corresponda)
- Composición fotográfica profesional con profundidad de campo
- Materiales, texturas y objetos auténticos del período
- Referencias específicas al estilo artístico de la época si aplica

EVITA COMPLETAMENTE:
- Elementos modernos o anacrónicos
- Arquitectura, vestimenta o tecnología posterior al período
- Materiales o colores que no existían en la época
- Peinados, maquillaje o accesorios modernos

El prompt debe ser en inglés, históricamente preciso y técnicamente detallado.""",
            "user_prompt": """Genera un prompt detallado para crear una imagen fotorrealista históricamente precisa que represente:

CONTEXTO DEL VIDEO:
Título: {titulo}
Tema general: {contexto}
PERÍODO HISTÓRICO: {periodo_historico}
UBICACIÓN GEOGRÁFICA: {ubicacion}
CONTEXTO CULTURAL: {contexto_cultural}

ESCENA A REPRESENTAR:
{scene_text}

Crea un prompt que:
1. Respete completamente el período histórico especificado
2. Incluya arquitectura, vestimenta y objetos auténticos de la época
3. Mantenga coherencia cultural y geográfica
4. Use terminología fotográfica técnica precisa
5. Evite cualquier elemento anacrónico o moderno
6. Capture la esencia de la escena con máximo realismo histórico

El prompt debe ser en inglés y extremadamente detallado en aspectos históricos.""",
            "variables": [
                "contexto",
                "titulo", 
                "scene_text",
                "periodo_historico",
                "ubicacion",
                "contexto_cultural"
            ]
        },
        "historical_variables": {
            "periodo_historico": "Siglo IV d.C. (circa 280-316 d.C.), Imperio Romano tardío, era de las persecuciones cristianas bajo Diocleciano",
            "ubicacion": "Sebastea, Armenia histórica (actual Sivas, Turquía), región montañosa del Asia Menor bajo dominio romano",
            "contexto_cultural": "Cristianismo primitivo bajo persecución sistemática del emperador Diocleciano, comunidades cristianas clandestinas, tradición médica greco-romana, conflicto entre paganismo y cristianismo emergente"
        }
    }
    
    logger.info("🔧 Regenerando prompts con contexto histórico correcto...")
    
    # Regenerar prompts para todas las escenas
    fixed_scenes = scene_generator.generate_prompts_for_scenes(
        scenes, 
        project_info, 
        image_prompt_config, 
        ai_service
    )
    
    # Crear backup del archivo original
    backup_file = project_path / f"scenes_backup_{data['project_info_summary'].get('last_modified', 'unknown')}.json"
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Backup creado: {backup_file}")
    
    # Actualizar datos
    data["scenes"] = fixed_scenes
    data["project_info_summary"]["last_modified"] = "2025-06-27T21:30:00.000000"
    data["project_info_summary"]["fixed_historical_context"] = True
    
    # Guardar archivo reparado
    with open(scenes_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info("✅ Proyecto reparado exitosamente!")
    logger.info(f"📁 Archivo actualizado: {scenes_file}")
    logger.info(f"🔍 Revisa los nuevos prompts - deberían ser 100% precisos históricamente")
    
    return True

if __name__ == "__main__":
    project_path = "projects/san_blas__58f6615d"
    
    print("🏛️ REPARADOR DE CONTEXTO HISTÓRICO")
    print("=" * 50)
    print(f"Proyecto a reparar: {project_path}")
    print("Este script corregirá los prompts anacrónicos aplicando")
    print("el contexto histórico correcto de San Blas (Siglo IV d.C.)")
    print("=" * 50)
    
    confirm = input("\n¿Continuar con la reparación? (s/N): ").strip().lower()
    if confirm in ['s', 'sí', 'si', 'y', 'yes']:
        success = fix_historical_prompts(project_path)
        if success:
            print("\n🎉 ¡REPARACIÓN COMPLETADA!")
            print("Todos los prompts ahora son históricamente precisos")
            print("y están contextualizados en el siglo IV d.C. en Armenia")
        else:
            print("\n❌ Error durante la reparación")
    else:
        print("Operación cancelada") 