# utils/content_optimizer.py
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ContentOptimizer:
    """
    Genera contenido optimizado para YouTube y redes sociales usando IA.
    """
    
    def __init__(self, ai_service=None, default_provider='gemini', default_model='models/gemini-2.5-flash-lite-preview-06-17'):
        self.ai_service = ai_service
        self.default_provider = default_provider
        self.default_model = default_model
        self.prompts = self._load_optimization_prompts()
    
    def _load_optimization_prompts(self) -> Dict:
        """Carga las plantillas de prompts para optimización."""
        return {
            "youtube_optimizer": {
                "system": """Eres un experto de clase mundial en SEO y marketing de contenidos para YouTube. Tu única tarea es generar metadatos de vídeo optimizados, limpios y listos para ser copiados y pegados.\n\n**REGLAS ESTRICTAS:**\n1. **NO uses formato Markdown.** No uses asteriscos, guiones, ni ningún otro tipo de formato.\n2. **NO incluyas justificaciones, explicaciones o texto introductorio.** Tu respuesta debe empezar directamente con "TITULO_1:".\n3. **Sigue el formato de salida EXACTO** que se especifica a continuación.""",
                "user": """Basado en el siguiente vídeo:\n- Título Original: "{original_title}"\n- Contexto General: "{context}"\n\nGenera los siguientes metadatos:\n- 5 títulos alternativos.\n- 1 descripción optimizada (entre 150-300 palabras).\n- 25 tags SEO relevantes (separados por comas).\n\n**FORMATO DE SALIDA EXACTO (usa estas claves literales):**\nTITULO_1: [Tu primer título aquí]\nTITULO_2: [Tu segundo título aquí]\nTITULO_3: [Tu tercer título aquí]\nTITULO_4: [Tu cuarto título aquí]\nTITULO_5: [Tu quinto título aquí]\nDESCRIPCION: [Tu descripción completa aquí, incluyendo un hook, el contenido principal, un llamado a la acción y 10-15 hashtags al final en una nueva línea.]\nTAGS: [Tus 25 tags aquí, separados por comas]\n"""
            },
            "thumbnails": {
                "system": "Eres un diseñador de miniaturas de YouTube. Creas conceptos de texto impactantes.",
                "user": """\nPara el video: "{title}"\nTema: "{context}"\n\nGenera 5 conceptos de texto para miniaturas que sean:\n- Cortos (máximo 4 palabras)\n- Impactantes y emocionales\n- Fáciles de leer en miniatura\n- Variados en enfoque\n\nFormato:\n- Concepto 1\n- Concepto 2\n- Concepto 3\n- Concepto 4\n- Concepto 5\n"""
            },
            "social_posts": {
                "system": "Eres un community manager experto. Creas publicaciones virales para redes sociales.",
                "user": """\nPara promocionar el video: "{title}"\nSobre: "{context}"\n\nGenera 2 publicaciones diferentes:\n\n1. PREGUNTA INTERACTIVA: Una pregunta con 4 opciones de respuesta que genere debate\n2. DATO CURIOSO: Un fact interesante que enganche y haga querer ver el video\n\nCada publicación debe ser concisa, atractiva y incluir call-to-action.\n"""
            },
            "chapters": {
                "system": "Eres un editor de video experto en estructurar contenido educativo para YouTube.",
                "user": """\nBasándote en este guión de video:\n"{script_content}"\n\nY este título: "{title}"\n\nGenera capítulos para YouTube con timestamps, considerando:\n- Duración aproximada del video: {duration} segundos\n- Introducción siempre en 00:00\n- Conclusión al final\n- Capítulos lógicos y descriptivos\n- Entre 8-15 capítulos total\n\nFormato:\n00:00 Introducción\nXX:XX Nombre del capítulo\n...\nXX:XX Conclusión\n"""
            }
        }
    
    def generate_optimized_content(self, project_info: Dict, config: Dict) -> Dict:
        """
        Genera todo el contenido optimizado para un proyecto.
        """
        try:
            title = project_info.get('titulo', 'Video sin título')
            context = project_info.get('contexto', '')
            script_path = project_info.get('script_path')
            duration = project_info.get('audio_duration', 60)
            
            script_content = ""
            if script_path and Path(script_path).exists():
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()[:2000]
            
            logger.info(f"Generando contenido optimizado para: {title}")
            
            llm_provider = config.get('optimization_provider', self.default_provider)
            llm_model = config.get('optimization_model', self.default_model)
            
            logger.info(f"🤖 Generando contenido optimizado usando {llm_provider.upper()}/{llm_model}")
            
            # --- Llamada unificada a la IA ---
            core_content = self._generate_youtube_metadata(title, context, llm_provider, llm_model)
            
            optimized_content = {
                'original_title': title,
                'context': context,
                'generated_at': datetime.now().isoformat(),
                'llm_used': f"{llm_provider}/{llm_model}",
                **core_content,  # Fusionar títulos, descripción y tags
                'thumbnails': self._generate_thumbnails(title, context, llm_provider, llm_model),
                'social_posts': self._generate_social_posts(title, context, llm_provider, llm_model),
                'chapters': self._generate_chapters(title, script_content, duration, llm_provider, llm_model) if script_content else None
            }
            
            if config.get('generate_series_tags') or config.get('use_same_style'):
                optimized_content = self.enhance_for_batch_series(optimized_content, config)
            
            return optimized_content
            
        except Exception as e:
            logger.error(f"Error generando contenido optimizado: {e}", exc_info=True)
            return None

    def _generate_youtube_metadata(self, title: str, context: str, provider: str, model: str) -> Dict:
        """
        Genera títulos, descripción y tags en una sola llamada a la IA.
        """
        try:
            prompt = self.prompts['youtube_optimizer']['user'].format(
                original_title=title,
                context=context
            )
            
            response = self.ai_service.generate_content(
                provider=provider or self.default_provider,
                model=model or self.default_model,
                system_prompt=self.prompts['youtube_optimizer']['system'],
                user_prompt=prompt
            )
            
            # Parsear la respuesta unificada
            content = {
                "titles": [],
                "description": "",
                "tags": []
            }
            
            current_description = []
            in_description = False

            for line in response.split('\n'):
                line = line.strip()
                if not line:
                    continue

                if line.startswith("TITULO_"):
                    in_description = False
                    content["titles"].append(line.split(":", 1)[1].strip())
                elif line.startswith("DESCRIPCION:"):
                    in_description = True
                    current_description.append(line.split(":", 1)[1].strip())
                elif line.startswith("TAGS:"):
                    in_description = False
                    tags_str = line.split(":", 1)[1].strip()
                    content["tags"] = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                elif in_description:
                    current_description.append(line)
            
            content["description"] = "\n".join(current_description)
            return content

        except Exception as e:
            logger.error(f"Error generando metadatos de YouTube: {e}", exc_info=True)
            return {"titles": [], "description": "", "tags": []}

    def _generate_thumbnails(self, title: str, context: str, provider: str = None, model: str = None) -> List[str]:
        """Genera conceptos de miniaturas"""
        try:
            prompt = self.prompts['thumbnails']['user'].format(
                title=title,
                context=context
            )
            response = self.ai_service.generate_content(
                provider=provider or self.default_provider,
                model=model or self.default_model,
                system_prompt=self.prompts['thumbnails']['system'],
                user_prompt=prompt
            )
            return [line.strip('- ').strip() for line in response.split('\n') if line.strip()]
        except Exception as e:
            logger.error(f"Error generando miniaturas: {e}")
            return []

    def _generate_social_posts(self, title: str, context: str, provider: str = None, model: str = None) -> Dict:
        """Genera publicaciones para redes sociales"""
        try:
            prompt = self.prompts['social_posts']['user'].format(
                title=title,
                context=context
            )
            response = self.ai_service.generate_content(
                provider=provider or self.default_provider,
                model=model or self.default_model,
                system_prompt=self.prompts['social_posts']['system'],
                user_prompt=prompt
            )
            return {'raw_response': response}
        except Exception as e:
            logger.error(f"Error generando publicaciones sociales: {e}")
            return {}

    def _generate_chapters(self, title: str, script_content: str, duration: float, provider: str = None, model: str = None) -> List[Dict]:
        """Genera capítulos con timestamps"""
        try:
            prompt = self.prompts['chapters']['user'].format(
                title=title,
                script_content=script_content,
                duration=int(duration)
            )
            response = self.ai_service.generate_content(
                provider=provider or self.default_provider,
                model=model or self.default_model,
                system_prompt=self.prompts['chapters']['system'],
                user_prompt=prompt
            )
            chapters = []
            for line in response.split('\n'):
                if ':' in line and len(line.strip()) > 5:
                    parts = line.strip().split(' ', 1)
                    if len(parts) == 2:
                        chapters.append({'timestamp': parts[0], 'title': parts[1]})
            return chapters
        except Exception as e:
            logger.error(f"Error generando capítulos: {e}")
            return []

    def save_optimized_content(self, content: Dict, output_dir: Path) -> tuple:
        """Guarda el contenido optimizado en archivos TXT y JSON."""
        try:
            output_dir = Path(output_dir)
            txt_path = output_dir / "content_optimization.txt"
            json_path = output_dir / "youtube_metadata.json"
            
            txt_content = self._format_txt_content(content)
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(txt_content)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Contenido optimizado guardado en: {txt_path} y {json_path}")
            return txt_path, json_path
        except Exception as e:
            logger.error(f"Error guardando contenido optimizado: {e}")
            return None, None

    def _format_txt_content(self, content: Dict) -> str:
        """Formatea el contenido para el archivo TXT, ahora más limpio."""
        
        # Títulos
        titles_str = ""
        for i, title in enumerate(content.get('titles', []), 1):
            titles_str += f"TITULO_{i}: {title}\n"

        # Descripción
        description_str = content.get('description', 'N/A')

        # Tags
        tags_str = ', '.join(content.get('tags', []))

        # Miniaturas
        thumbnails_str = ""
        for i, thumb in enumerate(content.get('thumbnails', []), 1):
            thumbnails_str += f"CONCEPTO_{i}: {thumb}\n"

        # Publicaciones Sociales
        social_str = content.get('social_posts', {}).get('raw_response', 'N/A')

        # Capítulos
        chapters_str = ""
        if content.get('chapters'):
            for chapter in content['chapters']:
                chapters_str += f"{chapter['timestamp']} {chapter['title']}\n"

        txt = f"""\n--- METADATOS PARA YOUTUBE ---\n\n{titles_str}\nDESCRIPCION:\n{description_str}\n\nTAGS:\n{tags_str}\n\n--- IDEAS ADICIONALES ---\n\nCONCEPTOS DE MINIATURA:\n{thumbnails_str}\nPOSTS PARA REDES SOCIALES:\n{social_str}\n"""
        if chapters_str:
            txt += f"""\nCAPÍTULOS:\n{chapters_str}\n"""
        return txt.strip()

    def enhance_for_batch_series(self, content: Dict, config: Dict) -> Dict:
        """Mejora el contenido para series/batch con tags adicionales."""
        try:
            if config.get('generate_series_tags', False):
                series_tags = [
                    "serie documental", "historia religiosa", "santos católicos",
                    "biografía histórica", "documentales educativos"
                ]
                existing_tags = content.get('tags', [])
                for tag in series_tags:
                    if tag not in existing_tags:
                        existing_tags.append(tag)
                content['tags'] = existing_tags
            
            if config.get('use_same_style', False):
                content['batch_notes'] = "Contenido optimizado para mantener consistencia en serie de videos"
            
            return content
        except Exception as e:
            logger.error(f"Error mejorando contenido para batch: {e}")
            return content 