# utils/content_optimizer.py
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ContentOptimizer:
    """
    Genera contenido optimizado para YouTube y redes sociales usando IA
    """
    
    def __init__(self, ai_service=None, default_provider='gemini', default_model='models/gemini-2.5-flash-lite-preview-06-17'):
        self.ai_service = ai_service
        self.default_provider = default_provider
        self.default_model = default_model
        self.prompts = self._load_optimization_prompts()
    
    def _load_optimization_prompts(self) -> Dict:
        """Carga las plantillas de prompts para optimización"""
        return {
            "titles": {
                "system": "Eres un experto en marketing de YouTube y SEO. Generas títulos virales y atractivos.",
                "user": """
Basándote en este título: "{original_title}"
Y este contexto: "{context}"

Genera 5 títulos alternativos para YouTube que sean:
- Atractivos y clickeable
- Optimizados para SEO
- Variados en estilo (misterio, educativo, emocional)
- Entre 40-60 caracteres

Formato de respuesta:
- Título 1
- Título 2  
- Título 3
- Título 4
- Título 5
"""
            },
            "description": {
                "system": "Eres un especialista en copywriting para YouTube. Creas descripciones que maximizan engagement y SEO.",
                "user": """
Para un video sobre: "{title}"
Con este contexto: "{context}"

Genera una descripción de YouTube que incluya:
1. Hook inicial atractivo (2-3 líneas)
2. Descripción del contenido (3-4 párrafos)
3. Call to action para suscribirse
4. 10-15 hashtags relevantes al final

La descripción debe ser entre 150-300 palabras, optimizada para SEO y engagement.
"""
            },
            "tags": {
                "system": "Eres un experto en SEO de YouTube. Generas tags relevantes y de alto ranking.",
                "user": """
Para un video titulado: "{title}"
Sobre el tema: "{context}"

Genera 20-25 tags SEO optimizados que incluyan:
- Palabras clave principales
- Variaciones y sinónimos
- Tags de nicho específico
- Tags populares del tema

Separa cada tag con coma. Ordena por relevancia (más importantes primero).
"""
            },
            "thumbnails": {
                "system": "Eres un diseñador de miniaturas de YouTube. Creas conceptos de texto impactantes.",
                "user": """
Para el video: "{title}"
Tema: "{context}"

Genera 5 conceptos de texto para miniaturas que sean:
- Cortos (máximo 4 palabras)
- Impactantes y emocionales
- Fáciles de leer en miniatura
- Variados en enfoque

Formato:
- Concepto 1
- Concepto 2
- Concepto 3
- Concepto 4
- Concepto 5
"""
            },
            "social_posts": {
                "system": "Eres un community manager experto. Creas publicaciones virales para redes sociales.",
                "user": """
Para promocionar el video: "{title}"
Sobre: "{context}"

Genera 2 publicaciones diferentes:

1. PREGUNTA INTERACTIVA: Una pregunta con 4 opciones de respuesta que genere debate
2. DATO CURIOSO: Un fact interesante que enganche y haga querer ver el video

Cada publicación debe ser concisa, atractiva y incluir call-to-action.
"""
            },
            "chapters": {
                "system": "Eres un editor de video experto en estructurar contenido educativo para YouTube.",
                "user": """
Basándote en este guión de video:
"{script_content}"

Y este título: "{title}"

Genera capítulos para YouTube con timestamps, considerando:
- Duración aproximada del video: {duration} segundos
- Introducción siempre en 00:00
- Conclusión al final
- Capítulos lógicos y descriptivos
- Entre 8-15 capítulos total

Formato:
00:00 Introducción
XX:XX Nombre del capítulo
...
XX:XX Conclusión
"""
            }
        }
    
    def generate_optimized_content(self, project_info: Dict, config: Dict) -> Dict:
        """
        Genera todo el contenido optimizado para un proyecto
        """
        try:
            title = project_info.get('titulo', 'Video sin título')
            context = project_info.get('contexto', '')
            script_path = project_info.get('script_path')
            duration = project_info.get('audio_duration', 60)
            
            # Leer el script si existe
            script_content = ""
            if script_path and Path(script_path).exists():
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()[:2000]  # Primeros 2000 caracteres
            
            logger.info(f"Generando contenido optimizado para: {title}")
            
            # Obtener configuración de LLM desde config o usar defaults
            llm_provider = config.get('optimization_provider', self.default_provider)
            llm_model = config.get('optimization_model', self.default_model)
            
            logger.info(f"🤖 Generando contenido optimizado usando {llm_provider.upper()}/{llm_model}")
            
            # Generar cada sección
            optimized_content = {
                'original_title': title,
                'context': context,
                'generated_at': datetime.now().isoformat(),
                'llm_used': f"{llm_provider}/{llm_model}",
                'titles': self._generate_titles(title, context, llm_provider, llm_model),
                'description': self._generate_description(title, context, llm_provider, llm_model),
                'tags': self._generate_tags(title, context, llm_provider, llm_model),
                'thumbnails': self._generate_thumbnails(title, context, llm_provider, llm_model),
                'social_posts': self._generate_social_posts(title, context, llm_provider, llm_model),
                'chapters': self._generate_chapters(title, script_content, duration, llm_provider, llm_model) if script_content else None
            }
            
            # Mejorar para batch/series si está configurado
            if config.get('generate_series_tags') or config.get('use_same_style'):
                optimized_content = self.enhance_for_batch_series(optimized_content, config)
            
            return optimized_content
            
        except Exception as e:
            logger.error(f"Error generando contenido optimizado: {e}")
            return None
    
    def _generate_titles(self, title: str, context: str, provider: str = None, model: str = None) -> List[str]:
        """Genera títulos alternativos"""
        try:
            prompt = self.prompts['titles']['user'].format(
                original_title=title,
                context=context
            )
            
            response = self.ai_service.generate_content(
                provider=provider or self.default_provider,
                model=model or self.default_model,
                system_prompt=self.prompts['titles']['system'],
                user_prompt=prompt
            )
            
            # Parsear respuesta en lista
            titles = [line.strip('- ').strip() for line in response.split('\n') if line.strip().startswith('-')]
            return titles[:5]  # Máximo 5 títulos
            
        except Exception as e:
            logger.error(f"Error generando títulos: {e}")
            return []
    
    def _generate_description(self, title: str, context: str, provider: str = None, model: str = None) -> str:
        """Genera descripción optimizada"""
        try:
            prompt = self.prompts['description']['user'].format(
                title=title,
                context=context
            )
            
            return self.ai_service.generate_content(
                provider=provider or self.default_provider,
                model=model or self.default_model,
                system_prompt=self.prompts['description']['system'],
                user_prompt=prompt
            )
            
        except Exception as e:
            logger.error(f"Error generando descripción: {e}")
            return ""
    
    def _generate_tags(self, title: str, context: str, provider: str = None, model: str = None) -> List[str]:
        """Genera tags SEO"""
        try:
            prompt = self.prompts['tags']['user'].format(
                title=title,
                context=context
            )
            
            response = self.ai_service.generate_content(
                provider=provider or self.default_provider,
                model=model or self.default_model,
                system_prompt=self.prompts['tags']['system'],
                user_prompt=prompt
            )
            
            # Parsear tags separados por coma
            tags = [tag.strip() for tag in response.split(',') if tag.strip()]
            return tags[:25]  # Máximo 25 tags
            
        except Exception as e:
            logger.error(f"Error generando tags: {e}")
            return []
    
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
            
            thumbnails = [line.strip('- ').strip() for line in response.split('\n') if line.strip().startswith('-')]
            return thumbnails[:5]
            
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
            
            # Parsear respuesta (esto se puede mejorar)
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
            
            # Parsear timestamps (formato: XX:XX Título)
            chapters = []
            for line in response.split('\n'):
                if ':' in line and len(line.strip()) > 5:
                    parts = line.strip().split(' ', 1)
                    if len(parts) == 2:
                        timestamp, chapter_title = parts
                        chapters.append({
                            'timestamp': timestamp,
                            'title': chapter_title
                        })
            
            return chapters
            
        except Exception as e:
            logger.error(f"Error generando capítulos: {e}")
            return []
    
    def save_optimized_content(self, content: Dict, output_dir: Path) -> tuple:
        """
        Guarda el contenido optimizado en archivos TXT y JSON
        """
        try:
            output_dir = Path(output_dir)
            
            # Archivo TXT legible
            txt_path = output_dir / "content_optimization.txt"
            json_path = output_dir / "youtube_metadata.json"
            
            # Generar contenido TXT
            txt_content = self._format_txt_content(content)
            
            # Guardar archivos
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
        """Formatea el contenido para el archivo TXT"""
        txt = f"""
=== CONTENIDO OPTIMIZADO PARA YOUTUBE ===
Generado: {content.get('generated_at', 'N/A')}
Título Original: {content.get('original_title', 'N/A')}

TÍTULOS ALTERNATIVOS:
"""
        
        for i, title in enumerate(content.get('titles', []), 1):
            txt += f"- {title}\n"
        
        txt += f"\nDESCRIPCIÓN:\n{content.get('description', 'N/A')}\n\n"
        
        txt += "TAGS:\n"
        tags = content.get('tags', [])
        txt += ', '.join(tags) + "\n\n"
        
        txt += "MINIATURAS:\n"
        for thumbnail in content.get('thumbnails', []):
            txt += f"- {thumbnail}\n"
        
        txt += f"\nPUBLICACIONES:\n{content.get('social_posts', {}).get('raw_response', 'N/A')}\n\n"
        
        if content.get('chapters'):
            txt += "----- CAPÍTULOS YOUTUBE -----\n"
            for chapter in content['chapters']:
                txt += f"{chapter['timestamp']} {chapter['title']}\n"
        
        return txt
    
    def enhance_for_batch_series(self, content: Dict, config: Dict) -> Dict:
        """
        Mejora el contenido para series/batch con tags adicionales y estilo consistente
        """
        try:
            # Añadir tags de serie si está habilitado
            if config.get('generate_series_tags', False):
                series_tags = [
                    "serie documental",
                    "historia religiosa",
                    "santos católicos",
                    "biografía histórica",
                    "documentales educativos"
                ]
                
                existing_tags = content.get('tags', [])
                # Añadir tags de serie sin duplicar
                for tag in series_tags:
                    if tag not in existing_tags:
                        existing_tags.append(tag)
                
                content['tags'] = existing_tags
            
            # Añadir nota sobre consistencia de estilo
            if config.get('use_same_style', False):
                content['batch_notes'] = "Contenido optimizado para mantener consistencia en serie de videos"
            
            return content
            
        except Exception as e:
            logger.error(f"Error mejorando contenido para batch: {e}")
            return content 