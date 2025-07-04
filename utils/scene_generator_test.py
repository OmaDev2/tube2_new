# utils/scene_generator_test.py
"""
Versión de prueba del Scene Generator con lógica mejorada
Incluye manejo inteligente de transiciones y fades
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import logging
import math
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class SceneGeneratorTest:
    """Versión de prueba del generador de escenas con mejoras"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Configuración de duración y transiciones
        self.max_scene_duration = 12.0  # Máximo por imagen
        self.min_scene_duration = 4.0   # Mínimo para evitar cortes muy rápidos
        self.target_scene_duration = 8.0  # Duración ideal
        
        # Configuración de transiciones (CRÍTICO)
        self.transition_duration = 1.0  # Duración de transición entre escenas
        self.fade_in_duration = 0.5     # Fade in al inicio
        self.fade_out_duration = 0.5    # Fade out al final
        
        logger.info(f"SceneGeneratorTest inicializado:")
        logger.info(f"  • Duración máxima por escena: {self.max_scene_duration}s")
        logger.info(f"  • Duración mínima por escena: {self.min_scene_duration}s")
        logger.info(f"  • Duración de transición: {self.transition_duration}s")
        logger.info(f"  • Fade in/out: {self.fade_in_duration}s / {self.fade_out_duration}s")
    
    def test_with_santa_teresa_project(self, project_path: str) -> Dict:
        """Prueba la nueva lógica con el proyecto de Santa Teresa"""
        
        logger.info("🧪 INICIANDO PRUEBA CON PROYECTO SANTA TERESA")
        logger.info("=" * 60)
        
        # Cargar datos del proyecto
        project_data = self._load_project_data(project_path)
        if not project_data:
            return {"error": "No se pudo cargar el proyecto"}
        
        # Analizar proyecto actual
        current_analysis = self._analyze_current_project(project_data)
        
        # Generar nueva versión
        new_scenes = self._generate_improved_scenes(project_data)
        
        # Comparar resultados
        comparison = self._compare_versions(current_analysis, new_scenes)
        
        return {
            "current_analysis": current_analysis,
            "new_scenes": new_scenes,
            "comparison": comparison,
            "recommendations": self._generate_recommendations(comparison)
        }
    
    def _load_project_data(self, project_path: str) -> Dict:
        """Carga todos los datos del proyecto"""
        
        try:
            base_path = Path(project_path)
            
            # Cargar archivos del proyecto
            project_info_path = base_path / "project_info.json"
            scenes_path = base_path / "scenes.json"
            transcription_path = base_path / "transcription.json"
            
            project_data = {}
            
            if project_info_path.exists():
                with open(project_info_path, 'r', encoding='utf-8') as f:
                    project_data['project_info'] = json.load(f)
            
            if scenes_path.exists():
                with open(scenes_path, 'r', encoding='utf-8') as f:
                    project_data['current_scenes'] = json.load(f)
            
            if transcription_path.exists():
                with open(transcription_path, 'r', encoding='utf-8') as f:
                    project_data['transcription'] = json.load(f)
            
            logger.info(f"✅ Proyecto cargado desde: {base_path}")
            logger.info(f"  • Project info: {'✓' if 'project_info' in project_data else '✗'}")
            logger.info(f"  • Escenas actuales: {'✓' if 'current_scenes' in project_data else '✗'}")
            logger.info(f"  • Transcripción: {'✓' if 'transcription' in project_data else '✗'}")
            
            return project_data
            
        except Exception as e:
            logger.error(f"❌ Error cargando proyecto: {e}")
            return {}
    
    def _analyze_current_project(self, project_data: Dict) -> Dict:
        """Analiza el proyecto actual para identificar problemas"""
        
        logger.info("🔍 ANALIZANDO PROYECTO ACTUAL")
        
        current_scenes = project_data.get('current_scenes', {}).get('scenes', [])
        transcription = project_data.get('transcription', {}).get('segments', [])
        
        analysis = {
            "total_scenes": len(current_scenes),
            "total_audio_segments": len(transcription),
            "scene_durations": [],
            "problems": [],
            "sync_issues": [],
            "duration_issues": []
        }
        
        # Analizar duraciones de escenas
        for i, scene in enumerate(current_scenes):
            duration = scene.get('duration', 0)
            analysis["scene_durations"].append({
                "index": i,
                "duration": duration,
                "text_preview": scene.get('text', '')[:50] + "..."
            })
            
            # Detectar problemas de duración
            if duration > self.max_scene_duration:
                analysis["duration_issues"].append({
                    "scene": i,
                    "problem": "too_long",
                    "duration": duration,
                    "recommended": f"Dividir en {math.ceil(duration / self.target_scene_duration)} partes"
                })
            elif duration < self.min_scene_duration:
                analysis["duration_issues"].append({
                    "scene": i,
                    "problem": "too_short",
                    "duration": duration,
                    "recommended": "Combinar con escena adyacente"
                })
        
        # Analizar sincronización con audio
        for i, scene in enumerate(current_scenes):
            scene_start = scene.get('start', 0)
            scene_end = scene.get('end', 0)
            scene_text = scene.get('text', '').lower()
            
            # Buscar segmentos de audio correspondientes
            matching_audio = []
            for audio_seg in transcription:
                audio_text = audio_seg.get('text', '').lower()
                
                # Verificar overlap de palabras
                scene_words = set(scene_text.split())
                audio_words = set(audio_text.split())
                
                if scene_words and audio_words:
                    overlap = len(scene_words & audio_words) / len(scene_words)
                    if overlap > 0.3:
                        matching_audio.append({
                            "audio_start": audio_seg.get('start', 0),
                            "audio_end": audio_seg.get('end', 0),
                            "overlap": overlap
                        })
            
            if matching_audio:
                # Calcular desincronización
                audio_start = min(seg["audio_start"] for seg in matching_audio)
                audio_end = max(seg["audio_end"] for seg in matching_audio)
                
                start_diff = abs(scene_start - audio_start)
                end_diff = abs(scene_end - audio_end)
                
                if start_diff > 1.0 or end_diff > 1.0:
                    analysis["sync_issues"].append({
                        "scene": i,
                        "scene_timing": f"{scene_start:.1f}s - {scene_end:.1f}s",
                        "audio_timing": f"{audio_start:.1f}s - {audio_end:.1f}s",
                        "start_diff": start_diff,
                        "end_diff": end_diff
                    })
        
        # Resumen de problemas
        analysis["problems"] = [
            f"Escenas demasiado largas: {len([d for d in analysis['duration_issues'] if d['problem'] == 'too_long'])}",
            f"Escenas demasiado cortas: {len([d for d in analysis['duration_issues'] if d['problem'] == 'too_short'])}",
            f"Problemas de sincronización: {len(analysis['sync_issues'])}"
        ]
        
        logger.info(f"📊 ANÁLISIS COMPLETADO:")
        for problem in analysis["problems"]:
            logger.info(f"  • {problem}")
        
        return analysis
    
    def _generate_improved_scenes(self, project_data: Dict) -> List[Dict]:
        """Genera escenas mejoradas con la nueva lógica"""
        
        logger.info("🎬 GENERANDO ESCENAS MEJORADAS")
        
        transcription_segments = project_data.get('transcription', {}).get('segments', [])
        
        if not transcription_segments:
            logger.error("❌ No hay segmentos de transcripción")
            return []
        
        # PASO 1: Agrupar segmentos por coherencia semántica
        semantic_groups = self._group_segments_semantically(transcription_segments)
        
        # PASO 2: Procesar grupos con límite de duración y transiciones
        improved_scenes = self._process_groups_with_transitions(semantic_groups)
        
        logger.info(f"✅ Generadas {len(improved_scenes)} escenas mejoradas")
        return improved_scenes
    
    def _group_segments_semantically(self, transcription_segments: List[Dict]) -> List[Dict]:
        """Agrupa segmentos por coherencia semántica"""
        
        logger.info("🧠 Agrupando segmentos semánticamente...")
        
        groups = []
        current_group_segments = []
        current_group_start = transcription_segments[0]['start']
        
        for i, segment in enumerate(transcription_segments):
            current_group_segments.append(segment)
            
            # Determinar si cerrar el grupo
            should_close = False
            close_reason = ""
            
            # Último segmento
            if i == len(transcription_segments) - 1:
                should_close = True
                close_reason = "último segmento"
            
            # Pausa larga
            elif i < len(transcription_segments) - 1:
                next_segment = transcription_segments[i + 1]
                pause = next_segment['start'] - segment['end']
                
                if pause > 1.2:  # Pausa significativa
                    should_close = True
                    close_reason = f"pausa larga ({pause:.1f}s)"
            
            # Cambio semántico
            if not should_close and i < len(transcription_segments) - 1:
                next_segment = transcription_segments[i + 1]
                if self._detect_semantic_break(segment['text'], next_segment['text']):
                    should_close = True
                    close_reason = "cambio semántico"
            
            if should_close:
                group_text = " ".join(seg['text'].strip() for seg in current_group_segments)
                group_end = segment['end']
                group_duration = group_end - current_group_start
                
                groups.append({
                    'text': group_text,
                    'start': current_group_start,
                    'end': group_end,
                    'duration': group_duration,
                    'segments': current_group_segments.copy(),
                    'close_reason': close_reason
                })
                
                logger.debug(f"Grupo: {group_duration:.1f}s ({close_reason})")
                
                # Nuevo grupo
                current_group_segments = []
                if i < len(transcription_segments) - 1:
                    current_group_start = transcription_segments[i + 1]['start']
        
        logger.info(f"✅ {len(groups)} grupos semánticos creados")
        return groups
    
    def _detect_semantic_break(self, current_text: str, next_text: str) -> bool:
        """Detecta cambios semánticos entre segmentos"""
        
        next_lower = next_text.lower().strip()
        
        semantic_indicators = [
            "después", "luego", "más tarde", "posteriormente",
            "por otro lado", "mientras tanto", "sin embargo",
            "ahora", "entonces", "así", "de esta manera",
            "su vida", "su obra", "sus escritos", "su legado"
        ]
        
        for indicator in semantic_indicators:
            if next_lower.startswith(indicator) or f" {indicator}" in next_lower[:30]:
                return True
        
        return False
    
    def _process_groups_with_transitions(self, semantic_groups: List[Dict]) -> List[Dict]:
        """Procesa grupos considerando transiciones y fades"""
        
        logger.info("🎞️ Procesando grupos con transiciones...")
        
        scenes = []
        
        for group_idx, group in enumerate(semantic_groups):
            group_duration = group['duration']
            
            # Calcular duración efectiva considerando transiciones
            effective_max_duration = self._calculate_effective_max_duration(group_idx, len(semantic_groups))
            
            logger.info(f"Grupo {group_idx+1}: {group_duration:.1f}s (máx efectivo: {effective_max_duration:.1f}s)")
            
            if group_duration <= effective_max_duration:
                # Grupo corto: una sola escena
                scene = self._create_single_scene(group, group_idx, len(semantic_groups))
                scenes.append(scene)
                logger.info(f"  → Escena única: {scene['duration']:.1f}s")
            
            else:
                # Grupo largo: subdividir
                logger.info(f"  → Subdividiendo grupo largo...")
                sub_scenes = self._subdivide_group_with_transitions(group, group_idx, len(semantic_groups))
                
                for sub_idx, sub_scene in enumerate(sub_scenes):
                    scenes.append(sub_scene)
                    logger.info(f"    • Sub-escena {sub_idx+1}: {sub_scene['duration']:.1f}s")
        
        # Ajustar índices finales
        for i, scene in enumerate(scenes):
            scene['index'] = i
        
        return scenes
    
    def _calculate_effective_max_duration(self, scene_index: int, total_scenes: int) -> float:
        """
        Calcula la duración máxima efectiva considerando transiciones.
        
        LÓGICA:
        - Primera escena: sin fade-in inicial
        - Última escena: sin fade-out final  
        - Escenas intermedias: consideran overlap de transiciones
        """
        
        base_max = self.max_scene_duration
        
        # Ajustar según posición
        if scene_index == 0:
            # Primera escena: no hay transición de entrada
            effective_max = base_max
        elif scene_index == total_scenes - 1:
            # Última escena: no hay transición de salida
            effective_max = base_max
        else:
            # Escena intermedia: considerar overlap de transiciones
            # Reducir ligeramente para acomodar transiciones suaves
            effective_max = base_max - (self.transition_duration * 0.3)
        
        return max(effective_max, self.min_scene_duration)
    
    def _create_single_scene(self, group: Dict, group_index: int, total_groups: int) -> Dict:
        """Crea una escena única desde un grupo semántico"""
        
        # Calcular timing con transiciones
        scene_start, scene_end = self._calculate_scene_timing_with_transitions(
            group['start'], group['end'], group_index, total_groups
        )
        
        return {
            'index': len([]),  # Se ajustará después
            'text': group['text'],
            'start': scene_start,
            'end': scene_end,
            'duration': scene_end - scene_start,
            'type': 'single_scene',
            'group_index': group_index,
            'transition_info': self._get_transition_info(group_index, total_groups),
            'close_reason': group.get('close_reason', 'unknown')
        }
    
    def _subdivide_group_with_transitions(self, group: Dict, group_index: int, total_groups: int) -> List[Dict]:
        """Subdivide un grupo largo considerando transiciones"""
        
        group_segments = group['segments']
        group_duration = group['duration']
        
        # Calcular número óptimo de sub-escenas
        effective_max = self._calculate_effective_max_duration(group_index, total_groups)
        num_subscenes = max(2, math.ceil(group_duration / effective_max))
        
        # Distribuir segmentos entre sub-escenas
        segments_per_subscene = max(1, len(group_segments) // num_subscenes)
        
        subscenes = []
        
        for sub_idx in range(num_subscenes):
            start_seg_idx = sub_idx * segments_per_subscene
            
            if sub_idx == num_subscenes - 1:
                # Última sub-escena: incluir segmentos restantes
                end_seg_idx = len(group_segments)
            else:
                end_seg_idx = (sub_idx + 1) * segments_per_subscene
            
            sub_segments = group_segments[start_seg_idx:end_seg_idx]
            
            if sub_segments:
                sub_text = " ".join(seg['text'].strip() for seg in sub_segments)
                sub_start = sub_segments[0]['start']
                sub_end = sub_segments[-1]['end']
                
                # Ajustar timing con transiciones
                adjusted_start, adjusted_end = self._calculate_scene_timing_with_transitions(
                    sub_start, sub_end, group_index, total_groups, sub_idx, num_subscenes
                )
                
                subscenes.append({
                    'index': len([]),  # Se ajustará después
                    'text': sub_text,
                    'start': adjusted_start,
                    'end': adjusted_end,
                    'duration': adjusted_end - adjusted_start,
                    'type': 'sub_scene',
                    'group_index': group_index,
                    'sub_index': sub_idx,
                    'total_subs': num_subscenes,
                    'transition_info': self._get_transition_info(group_index, total_groups, sub_idx, num_subscenes)
                })
        
        return subscenes
    
    def _calculate_scene_timing_with_transitions(self, raw_start: float, raw_end: float, 
                                               group_index: int, total_groups: int,
                                               sub_index: int = None, total_subs: int = None) -> tuple:
        """
        Calcula el timing real de la escena considerando transiciones y fades.
        
        IMPORTANTE: Esto es crítico para evitar gaps o overlaps en el video final.
        """
        
        # Para esta versión de prueba, mantener timing original
        # En implementación final, aquí se calcularían los overlaps exactos
        adjusted_start = raw_start
        adjusted_end = raw_end
        
        # Asegurar duración mínima
        if adjusted_end - adjusted_start < self.min_scene_duration:
            adjusted_end = adjusted_start + self.min_scene_duration
        
        return adjusted_start, adjusted_end
    
    def _get_transition_info(self, group_index: int, total_groups: int, 
                           sub_index: int = None, total_subs: int = None) -> Dict:
        """Genera información de transición para la escena"""
        
        transition_info = {
            'has_fade_in': group_index == 0 and (sub_index is None or sub_index == 0),
            'has_fade_out': group_index == total_groups - 1 and (sub_index is None or sub_index == total_subs - 1),
            'transition_type': 'dissolve',  # Por defecto
            'transition_duration': self.transition_duration
        }
        
        # Determinar tipo de transición según contenido
        # (Aquí se podría hacer más sofisticado)
        
        return transition_info
    
    def _compare_versions(self, current_analysis: Dict, new_scenes: List[Dict]) -> Dict:
        """Compara la versión actual con la mejorada"""
        
        logger.info("⚖️ COMPARANDO VERSIONES")
        
        # Estadísticas de la nueva versión
        new_durations = [scene['duration'] for scene in new_scenes]
        
        comparison = {
            "scene_count": {
                "current": current_analysis["total_scenes"],
                "new": len(new_scenes),
                "change": len(new_scenes) - current_analysis["total_scenes"]
            },
            "duration_stats": {
                "current": {
                    "avg": sum(s['duration'] for s in current_analysis['scene_durations']) / len(current_analysis['scene_durations']) if current_analysis['scene_durations'] else 0,
                    "max": max(s['duration'] for s in current_analysis['scene_durations']) if current_analysis['scene_durations'] else 0,
                    "min": min(s['duration'] for s in current_analysis['scene_durations']) if current_analysis['scene_durations'] else 0
                },
                "new": {
                    "avg": sum(new_durations) / len(new_durations) if new_durations else 0,
                    "max": max(new_durations) if new_durations else 0,
                    "min": min(new_durations) if new_durations else 0
                }
            },
            "problems_solved": {
                "long_scenes": len([d for d in new_durations if d > self.max_scene_duration]),
                "short_scenes": len([d for d in new_durations if d < self.min_scene_duration]),
                "ideal_range": len([d for d in new_durations if self.min_scene_duration <= d <= self.max_scene_duration])
            }
        }
        
        # Calcular mejoras
        current_long_scenes = len([d for d in current_analysis['duration_issues'] if d['problem'] == 'too_long'])
        new_long_scenes = comparison['problems_solved']['long_scenes']
        
        comparison['improvements'] = {
            "long_scenes_reduced": current_long_scenes - new_long_scenes,
            "avg_duration_change": comparison['duration_stats']['new']['avg'] - comparison['duration_stats']['current']['avg'],
            "max_duration_reduced": comparison['duration_stats']['current']['max'] - comparison['duration_stats']['new']['max']
        }
        
        return comparison
    
    def _generate_recommendations(self, comparison: Dict) -> List[str]:
        """Genera recomendaciones basadas en la comparación"""
        
        recommendations = []
        
        improvements = comparison.get('improvements', {})
        
        if improvements.get('long_scenes_reduced', 0) > 0:
            recommendations.append(f"✅ Se redujeron {improvements['long_scenes_reduced']} escenas demasiado largas")
        
        if improvements.get('max_duration_reduced', 0) > 0:
            recommendations.append(f"✅ Duración máxima reducida en {improvements['max_duration_reduced']:.1f}s")
        
        if improvements.get('avg_duration_change', 0) < 0:
            recommendations.append(f"✅ Duración promedio mejorada: {abs(improvements['avg_duration_change']):.1f}s más corta")
        
        ideal_count = comparison.get('problems_solved', {}).get('ideal_range', 0)
        total_scenes = comparison.get('scene_count', {}).get('new', 0)
        
        if total_scenes > 0:
            ideal_percentage = (ideal_count / total_scenes) * 100
            recommendations.append(f"📊 {ideal_percentage:.1f}% de escenas en rango ideal ({self.min_scene_duration}-{self.max_scene_duration}s)")
        
        if not recommendations:
            recommendations.append("ℹ️ El proyecto ya tenía una buena estructura de escenas")
        
        return recommendations

# Función de prueba principal
def test_scene_generator_with_santa_teresa():
    """Función principal para probar el generador mejorado"""
    
    # Ruta del proyecto de Santa Teresa
    project_path = "/Users/olga/video_tube2 copia/projects/santa_teresa_de_ávila__a5409951"
    
    # Crear instancia de prueba
    tester = SceneGeneratorTest()
    
    # Ejecutar prueba
    results = tester.test_with_santa_teresa_project(project_path)
    
    return results

if __name__ == "__main__":
    # Ejecutar prueba
    test_results = test_scene_generator_with_santa_teresa()
    print(json.dumps(test_results, indent=2, ensure_ascii=False))