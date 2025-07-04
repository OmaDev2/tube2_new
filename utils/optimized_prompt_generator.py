# utils/optimized_prompt_generator.py
"""
Generador de prompts optimizado para coherencia visual
Prompts compactos, consistentes y efectivos
"""

import logging
from typing import Dict, List, Any, Optional
import re

logger = logging.getLogger(__name__)

class OptimizedPromptGenerator:
    """Generador de prompts optimizado para coherencia visual"""
    
    def __init__(self):
        # Descripción base fija del personaje principal
        self.character_base = {
            "san_cristobal": {
                "description": "San Cristóbal: Tall, powerful man in his 30s, dark brown hair, weathered face with kind dark eyes, simple brown woolen tunic, leather belt, worn leather sandals. Consistent appearance across all scenes.",
                "period": "3rd century Roman Empire",
                "location": "Eastern Mediterranean region"
            },
            "santa_teresa": {
                "description": "Santa Teresa: Middle-aged woman, serene expression, dark hair with white veil, simple brown Carmelite habit, wooden cross, gentle hands. Consistent appearance across all scenes.",
                "period": "16th century Spain",
                "location": "Castile, Spain"
            },
            "leonardo": {
                "description": "Leonardo da Vinci: Renaissance man in his 40s, long dark hair, intense eyes, simple dark tunic, artist's hands. Consistent appearance across all scenes.",
                "period": "Italian Renaissance, late 15th century",
                "location": "Florence and Milan, Italy"
            },
            "napoleon": {
                "description": "Napoleon Bonaparte: Medium height man, dark hair, piercing eyes, military uniform or simple coat, confident posture. Consistent appearance across all scenes.",
                "period": "Early 19th century, Napoleonic era",
                "location": "France and European battlefields"
            }
        }
        
        # Estilos visuales base
        self.visual_styles = {
            "photorealistic": "Photorealistic, cinematic lighting, natural colors, detailed textures",
            "historical_accurate": "Historically accurate, period-appropriate clothing and architecture",
            "cinematic": "Cinematic composition, dramatic lighting, film-like quality",
            "documentary": "Documentary style, natural lighting, authentic atmosphere"
        }
        
        # Especificaciones técnicas base
        self.technical_specs = {
            "standard": "Medium shot, natural lighting, sharp focus, 4K quality",
            "wide": "Wide shot, environmental context, natural lighting, detailed background",
            "close": "Close-up shot, emotional focus, soft lighting, shallow depth of field"
        }
    
    def detect_character_from_context(self, title: str, context: str) -> str:
        """Detecta el personaje principal basado en título y contexto"""
        
        title_lower = title.lower()
        context_lower = context.lower()
        
        # Detectar personajes conocidos
        if any(name in title_lower or name in context_lower for name in ['cristóbal', 'cristobal', 'christopher']):
            return "san_cristobal"
        elif any(name in title_lower or name in context_lower for name in ['teresa', 'ávila', 'avila']):
            return "santa_teresa"
        elif any(name in title_lower or name in context_lower for name in ['leonardo', 'da vinci', 'vinci']):
            return "leonardo"
        elif any(name in title_lower or name in context_lower for name in ['napoleón', 'napoleon', 'bonaparte']):
            return "napoleon"
        else:
            # Personaje genérico
            return "generic"
    
    def create_generic_character(self, title: str, context: str) -> Dict[str, str]:
        """Crea descripción de personaje genérico basado en contexto"""
        
        # Extraer información del contexto
        period = self._extract_historical_period(context)
        location = self._extract_location(context)
        
        # Crear descripción genérica
        character_name = self._extract_main_character_name(title, context)
        
        return {
            "description": f"{character_name}: Historical figure, period-appropriate clothing and appearance, authentic to {period}. Consistent appearance across all scenes.",
            "period": period,
            "location": location
        }
    
    def _extract_historical_period(self, context: str) -> str:
        """Extrae el período histórico del contexto"""
        
        # Patrones de períodos históricos
        period_patterns = {
            r'\b(siglo\s+(?:I{1,3}|IV|V{1,3}|IX|X{1,3}|XI{1,3}|XV{1,3}|XVI{1,3}|XVII{1,3}|XVIII|XIX|XX))\b': lambda m: m.group(1),
            r'\b(\d{3,4})\s*[-–]\s*(\d{3,4})\b': lambda m: f"{m.group(1)}-{m.group(2)}",
            r'\b(\d{3,4})\s*d\.?\s*C\.?\b': lambda m: f"{m.group(1)} AD",
            r'\brenacimiento\b': lambda m: "Renaissance period",
            r'\bmedieval\b': lambda m: "Medieval period",
            r'\bimperio\s+romano\b': lambda m: "Roman Empire",
            r'\bedad\s+media\b': lambda m: "Middle Ages"
        }
        
        context_lower = context.lower()
        
        for pattern, extractor in period_patterns.items():
            match = re.search(pattern, context_lower)
            if match:
                return extractor(match)
        
        return "Historical period"
    
    def _extract_location(self, context: str) -> str:
        """Extrae la ubicación del contexto"""
        
        # Patrones de ubicaciones
        location_patterns = {
            r'\b(españa|spain|castilla|ávila|toledo|madrid)\b': "Spain",
            r'\b(italia|italy|florencia|florence|milán|milan|roma|rome)\b': "Italy", 
            r'\b(francia|france|parís|paris)\b': "France",
            r'\b(imperio\s+romano|roman\s+empire)\b': "Roman Empire",
            r'\b(mediterráneo|mediterranean)\b': "Mediterranean region",
            r'\b(asia\s+menor|anatolia)\b': "Asia Minor",
            r'\b(egipto|egypt)\b': "Egypt",
            r'\b(grecia|greece)\b': "Greece"
        }
        
        context_lower = context.lower()
        
        for pattern, location in location_patterns.items():
            if re.search(pattern, context_lower):
                return location
        
        return "Historical location"
    
    def _extract_main_character_name(self, title: str, context: str) -> str:
        """Extrae el nombre del personaje principal"""
        
        # Buscar nombres propios en el título
        title_words = title.split()
        for word in title_words:
            if word[0].isupper() and len(word) > 2:
                return word
        
        # Buscar en el contexto
        context_words = context.split()[:20]  # Primeras 20 palabras
        for word in context_words:
            if word[0].isupper() and len(word) > 2 and word not in ['El', 'La', 'Los', 'Las', 'De', 'Del']:
                return word
        
        return "Historical figure"
    
    def determine_scene_focus(self, scene_text: str) -> str:
        """Determina el enfoque visual de la escena"""
        
        text_lower = scene_text.lower()
        
        # Patrones para determinar enfoque
        if any(word in text_lower for word in ['ciudad', 'lugar', 'paisaje', 'arquitectura', 'edificio']):
            return "Environmental focus, wide shot showing architecture and setting"
        elif any(word in text_lower for word in ['multitud', 'gente', 'personas', 'grupo', 'comunidad']):
            return "Group scene, multiple people interacting"
        elif any(word in text_lower for word in ['cara', 'ojos', 'expresión', 'mirada', 'sonrisa']):
            return "Character focus, emotional expression"
        elif any(word in text_lower for word in ['acción', 'movimiento', 'corrió', 'saltó', 'luchó']):
            return "Action scene, dynamic movement"
        else:
            return "Balanced composition, character in environment"
    
    def generate_optimized_prompt(self, scene_text: str, scene_index: int, 
                                 title: str, context: str) -> str:
        """Genera un prompt optimizado y compacto"""
        
        # Detectar o crear personaje
        character_key = self.detect_character_from_context(title, context)
        
        if character_key in self.character_base:
            character_info = self.character_base[character_key]
        else:
            character_info = self.create_generic_character(title, context)
        
        # Determinar enfoque de la escena
        scene_focus = self.determine_scene_focus(scene_text)
        
        # Determinar tipo de toma
        shot_type = self._determine_shot_type(scene_text)
        
        # Crear prompt optimizado
        optimized_prompt = f"""
{character_info['description']}

Scene: {scene_text}

Setting: {character_info['period']}, {character_info['location']}

Focus: {scene_focus}

Style: Photorealistic, cinematic lighting, historically accurate, natural colors, detailed textures

Technical: {shot_type}, natural lighting, sharp focus, 4K quality

Avoid: Modern elements, anachronisms, inconsistent character appearance
        """.strip()
        
        logger.info(f"Generated optimized prompt for scene {scene_index}: {len(optimized_prompt)} characters")
        
        return optimized_prompt
    
    def _determine_shot_type(self, scene_text: str) -> str:
        """Determina el tipo de toma basado en el contenido"""
        
        text_lower = scene_text.lower()
        
        if any(word in text_lower for word in ['ciudad', 'lugar', 'paisaje', 'arquitectura', 'multitud']):
            return "Wide shot"
        elif any(word in text_lower for word in ['cara', 'ojos', 'expresión', 'mirada', 'emoción']):
            return "Close-up shot"
        else:
            return "Medium shot"
    
    def create_optimized_prompt_config(self, title: str, context: str) -> Dict[str, Any]:
        """Crea configuración optimizada de prompts para un proyecto"""
        
        character_key = self.detect_character_from_context(title, context)
        
        if character_key in self.character_base:
            character_info = self.character_base[character_key]
        else:
            character_info = self.create_generic_character(title, context)
        
        return {
            "nombre": "Prompts Optimizados para Coherencia Visual",
            "system_prompt": f"""Generate concise, visually consistent prompts for historical scenes.

CHARACTER BASE: {character_info['description']}
PERIOD: {character_info['period']}
LOCATION: {character_info['location']}

RULES:
- Keep character appearance EXACTLY consistent across all scenes
- Focus on scene-specific elements only
- Use historically accurate details
- Maintain photorealistic style
- Avoid modern elements completely

Generate prompts under 300 words focusing on scene specifics while maintaining character consistency.""",
            
            "user_prompt": """Create a concise, historically accurate prompt for:

SCENE: {scene_text}

Include:
1. Consistent character appearance (as defined in base)
2. Scene-specific action/setting
3. Historical period accuracy
4. Appropriate camera angle
5. Natural lighting

Keep under 300 words. Focus on visual consistency and scene specifics.""",
            
            "variables": ["scene_text"],
            "style": "optimized_coherent",
            "max_length": 300
        }

# Función principal para integrar con el sistema existente
def create_optimized_prompts_for_scenes(scenes: List[Dict], title: str, context: str) -> List[str]:
    """Crea prompts optimizados para una lista de escenas"""
    
    generator = OptimizedPromptGenerator()
    optimized_prompts = []
    
    logger.info(f"🎨 Generando prompts optimizados para {len(scenes)} escenas")
    
    for i, scene in enumerate(scenes):
        scene_text = scene.get('text', '')
        
        optimized_prompt = generator.generate_optimized_prompt(
            scene_text=scene_text,
            scene_index=i,
            title=title,
            context=context
        )
        
        optimized_prompts.append(optimized_prompt)
    
    # Estadísticas
    avg_length = sum(len(p) for p in optimized_prompts) / len(optimized_prompts)
    logger.info(f"✅ Prompts optimizados generados:")
    logger.info(f"  • Promedio de longitud: {avg_length:.0f} caracteres")
    logger.info(f"  • Reducción estimada: ~75% vs prompts anteriores")
    
    return optimized_prompts