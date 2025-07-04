# Corrección para scene_generator.py - Segmentación con límite de duración

def create_dynamic_scenes_with_duration_limit(self, transcription_segments: List[Dict], max_scene_duration: float = 12.0) -> List[Dict]:
    """
    Crea escenas dinámicas respetando el límite máximo de duración.
    
    LÓGICA:
    1. Usa timestamps REALES del audio (no estimaciones)
    2. Respeta límite máximo de duración (12-15s)
    3. Subdivide escenas largas en momentos visuales
    4. Mantiene coherencia semántica
    """
    
    if not transcription_segments:
        return []
    
    logger.info(f"🎬 Creando escenas dinámicas con límite: {max_scene_duration}s")
    
    # PASO 1: Agrupar segmentos por coherencia semántica
    semantic_groups = self._group_segments_semantically(transcription_segments)
    
    # PASO 2: Procesar cada grupo respetando límite de duración
    final_scenes = []
    
    for group_idx, group in enumerate(semantic_groups):
        group_duration = group['end'] - group['start']
        group_text = group['text']
        
        logger.info(f"Grupo {group_idx+1}: {group_duration:.1f}s - {group_text[:60]}...")
        
        if group_duration <= max_scene_duration:
            # Grupo corto: usar como una sola escena
            final_scenes.append({
                "index": len(final_scenes),
                "text": group_text,
                "start": group['start'],
                "end": group['end'],
                "duration": group_duration,
                "type": "single_moment"
            })
            logger.info(f"  → Escena única ({group_duration:.1f}s)")
        
        else:
            # Grupo largo: subdividir en momentos visuales
            logger.info(f"  → Subdividiendo grupo largo ({group_duration:.1f}s)")
            visual_moments = self._subdivide_group_into_moments(group, max_scene_duration)
            
            for moment_idx, moment in enumerate(visual_moments):
                final_scenes.append({
                    "index": len(final_scenes),
                    "text": moment['text'],
                    "start": moment['start'],
                    "end": moment['end'],
                    "duration": moment['duration'],
                    "type": "visual_moment",
                    "moment_of": group_idx + 1
                })
                logger.info(f"    • Momento {moment_idx+1}: {moment['duration']:.1f}s")
    
    logger.info(f"✅ Resultado: {len(final_scenes)} escenas dinámicas")
    return final_scenes

def _group_segments_semantically(self, transcription_segments: List[Dict]) -> List[Dict]:
    """
    Agrupa segmentos de transcripción por coherencia semántica.
    Respeta pausas naturales y cambios de tema.
    """
    
    if not transcription_segments:
        return []
    
    groups = []
    current_group_segments = []
    current_group_start = transcription_segments[0]['start']
    
    for i, segment in enumerate(transcription_segments):
        current_group_segments.append(segment)
        
        # Determinar si cerrar el grupo actual
        should_close_group = False
        close_reason = ""
        
        # Es el último segmento
        if i == len(transcription_segments) - 1:
            should_close_group = True
            close_reason = "último segmento"
        
        # Hay una pausa larga después de este segmento
        elif i < len(transcription_segments) - 1:
            next_segment = transcription_segments[i + 1]
            pause_duration = next_segment['start'] - segment['end']
            
            if pause_duration > 1.0:  # Pausa de más de 1 segundo
                should_close_group = True
                close_reason = f"pausa larga ({pause_duration:.1f}s)"
        
        # Cambio semántico detectado
        if not should_close_group and i < len(transcription_segments) - 1:
            next_segment = transcription_segments[i + 1]
            if self._is_semantic_break(segment['text'], next_segment['text']):
                should_close_group = True
                close_reason = "cambio semántico"
        
        if should_close_group:
            # Crear grupo semántico
            group_text = " ".join(seg['text'].strip() for seg in current_group_segments)
            group_end = segment['end']
            group_duration = group_end - current_group_start
            
            groups.append({
                'text': group_text,
                'start': current_group_start,
                'end': group_end,
                'duration': group_duration,
                'segments': current_group_segments.copy()
            })
            
            logger.debug(f"Grupo cerrado: {group_duration:.1f}s ({close_reason})")
            
            # Iniciar nuevo grupo
            current_group_segments = []
            if i < len(transcription_segments) - 1:
                current_group_start = transcription_segments[i + 1]['start']
    
    return groups

def _is_semantic_break(self, current_text: str, next_text: str) -> bool:
    """
    Detecta si hay un cambio semántico significativo entre dos segmentos.
    """
    
    current_lower = current_text.lower().strip()
    next_lower = next_text.lower().strip()
    
    # Indicadores de cambio semántico
    semantic_breaks = [
        # Cambios temporales
        "después", "luego", "más tarde", "posteriormente", "años después",
        "tiempo después", "al día siguiente", "en otra ocasión",
        
        # Cambios de tema/escenario
        "por otro lado", "mientras tanto", "sin embargo", "no obstante",
        "en otro lugar", "en otra ciudad", "lejos de allí",
        
        # Nuevas secciones narrativas
        "ahora", "veamos", "imaginemos", "consideremos",
        "la historia continúa", "pero la historia",
        
        # Transiciones biográficas
        "su vida", "su biografía", "su historia", "su obra",
        "sus escritos", "sus enseñanzas"
    ]
    
    # Verificar si el siguiente segmento empieza con indicador de cambio
    for indicator in semantic_breaks:
        if next_lower.startswith(indicator) or f" {indicator}" in next_lower[:50]:
            return True
    
    return False

def _subdivide_group_into_moments(self, group: Dict, max_duration: float) -> List[Dict]:
    """
    Subdivide un grupo semántico largo en momentos visuales más cortos.
    """
    
    group_duration = group['duration']
    group_segments = group['segments']
    
    # Calcular número óptimo de momentos
    num_moments = max(2, int(group_duration / max_duration) + 1)
    target_moment_duration = group_duration / num_moments
    
    logger.info(f"    Subdividiendo en {num_moments} momentos de ~{target_moment_duration:.1f}s")
    
    moments = []
    current_moment_segments = []
    current_moment_start = group['start']
    current_moment_duration = 0.0
    
    for i, segment in enumerate(group_segments):
        current_moment_segments.append(segment)
        current_moment_duration = segment['end'] - current_moment_start
        
        # Determinar si cerrar el momento actual
        should_close_moment = False
        
        # Es el último segmento del grupo
        if i == len(group_segments) - 1:
            should_close_moment = True
        
        # El momento ha alcanzado la duración objetivo
        elif current_moment_duration >= target_moment_duration:
            # Buscar un punto de corte natural
            if self._is_good_cut_point(segment['text']):
                should_close_moment = True
        
        # El momento se haría demasiado largo
        elif current_moment_duration >= max_duration * 0.9:
            should_close_moment = True
        
        if should_close_moment:
            # Crear momento visual
            moment_text = " ".join(seg['text'].strip() for seg in current_moment_segments)
            moment_end = segment['end']
            actual_duration = moment_end - current_moment_start
            
            moments.append({
                'text': moment_text,
                'start': current_moment_start,
                'end': moment_end,
                'duration': actual_duration
            })
            
            # Iniciar nuevo momento
            current_moment_segments = []
            if i < len(group_segments) - 1:
                current_moment_start = segment['end']
                current_moment_duration = 0.0
    
    return moments

def _is_good_cut_point(self, text: str) -> bool:
    """
    Determina si un texto es un buen punto para cortar un momento visual.
    """
    
    text_lower = text.lower().strip()
    
    # Buenos puntos de corte
    good_cuts = [
        # Finales de oración
        ".", "!", "?",
        
        # Pausas naturales
        ",", ";", ":",
        
        # Conectores que permiten corte
        "y", "pero", "sin embargo", "además", "también",
        "mientras", "cuando", "donde", "como"
    ]
    
    # Verificar si el texto termina con un buen punto de corte
    for cut_point in good_cuts:
        if text_lower.endswith(cut_point):
            return True
    
    return False

# FUNCIÓN PRINCIPAL MEJORADA
def generate_scenes_with_duration_limit(self, script_content: str, transcription_segments: List[Dict], 
                                      mode: str, project_info: Dict, image_prompt_config: Dict, 
                                      ai_service: AIServices, max_scene_duration: float = 12.0) -> List[Dict]:
    """
    Genera escenas respetando el límite máximo de duración para mantener dinamismo.
    """
    
    logger.info(f"🎬 Generando escenas con límite de duración: {max_scene_duration}s")
    
    if mode == "Por Párrafos (Híbrido)":
        # Usar nueva lógica con límite de duración
        dynamic_scenes = self.create_dynamic_scenes_with_duration_limit(
            transcription_segments, max_scene_duration
        )
        
        # Generar prompts para las escenas dinámicas
        scenes_with_prompts = self.generate_prompts_for_scenes(
            dynamic_scenes, project_info, image_prompt_config, ai_service
        )
        
        logger.info(f"✅ Generadas {len(scenes_with_prompts)} escenas dinámicas")
        return scenes_with_prompts
    
    else:
        # Usar métodos anteriores para otros modos
        return self._generate_scenes_legacy(script_content, transcription_segments, mode)