# 🎭 Plan Revisado: Sistema de Coherencia Visual de Personajes

## 📊 **Estado Actual Detectado:**

### ✅ **Fortalezas del Sistema Existente:**
- ✅ Sistema de variables históricas implementado
- ✅ Plantilla "Escenas Fotorrealistas Históricamente Precisas" sofisticada
- ✅ Detección automática de contexto histórico funcional
- ✅ Flujo robusto con fallbacks y logging detallado
- ✅ Variables flexibles en templates

### ⚠️ **Limitaciones Críticas:**
- ❌ No existe coherencia de personajes entre escenas
- ❌ Variables históricas son genéricas, no específicas por escena/edad
- ❌ Falta detección automática de etapa de vida del personaje
- ❌ Sin dossier centralizado del personaje principal

---

## 🚀 **PLAN REVISADO Y OPTIMIZADO**

### **🎯 FASE 1: Crear el Dossier de Personaje (MEJORADO)**

#### **Paso 1.1: Nueva Plantilla de Dossier**
**UBICACIÓN**: `prompts/imagenes_prompts.json`
**ACCIÓN**: Añadir nueva plantilla optimizada para el sistema existente

```json
{
  "nombre": "Dossier de Personaje Principal",
  "system_prompt": "Eres un director de casting y caracterización experto...",
  "user_prompt": "Crea un dossier detallado del personaje principal para: {titulo}...",
  "variables": ["titulo", "contexto"],
  "output_format": "structured_character_profile"
}
```

#### **Paso 1.2: Función de Generación de Dossier**
**UBICACIÓN**: `utils/scene_generator.py`
**FUNCIÓN**: `_generate_character_dossier()`

**INTEGRACIÓN INTELIGENTE**:
- ✅ **Reutilizar** sistema existente de `ai_service.generate_content()`
- ✅ **Aprovechar** variables históricas ya disponibles
- ✅ **Mantener** compatibilidad con logging actual
- ✅ **Usar** mismo patrón de fallbacks

---

### **🎯 FASE 2: Detección Inteligente de Edad (OPTIMIZADO)**

#### **Paso 2.1: Modificar Plantilla Histórica Existente**
**NO crear nueva plantilla**, sino **EXTENDER** la existente:

```json
{
  "nombre": "Escenas Fotorrealistas Históricamente Precisas",
  "variables": [
    "contexto", "titulo", "scene_text",
    "periodo_historico", "ubicacion", "contexto_cultural",
    "character_description"  // ← NUEVA VARIABLE
  ]
}
```

#### **Paso 2.2: Función de Detección de Edad Mejorada**
**FUNCIÓN**: `_detect_character_stage_for_scene()`

**LÓGICA AVANZADA**:
```python
def _detect_character_stage_for_scene(self, scene_text: str, titulo: str) -> str:
    """
    Detecta la etapa de vida del personaje principal en una escena específica.
    
    PALABRAS CLAVE EXTENDIDAS:
    - Infancia: "niño", "bebé", "pequeño", "hijo", "nacimiento"
    - Juventud: "joven", "estudiante", "adolescente", "muchacho"
    - Adultez: "hombre", "mujer", "adulto", "ordenación", "trabajo"
    - Vejez: "anciano", "viejo", "maduro", "sabio", "muerte"
    
    CONTEXTO ESPECÍFICO POR SANTO/BIOGRAFÍA:
    - San Blas: "médico" → Adultez, "obispo" → Madurez
    - Napoleón: "general" → Adultez, "emperador" → Madurez
    """
```

#### **Paso 2.3: Función de Extracción Inteligente**
**FUNCIÓN**: `_extract_character_description_for_stage()`

---

### **🎯 FASE 3: Integración Optimizada (COMPATIBLE)**

#### **Paso 3.1: Modificación Mínima de `generate_prompts_for_scenes()`**

**CAMBIOS ESTRATÉGICOS**:
1. **ANTES del bucle**: Una sola llamada para generar dossier
2. **DENTRO del bucle**: 
   - Detectar edad del personaje
   - Extraer descripción específica
   - **INTEGRAR** con variables históricas existentes
3. **MANTENER** toda la lógica de fallbacks actual

**PSEUDOCÓDIGO**:
```python
def generate_prompts_for_scenes(self, scenes, project_info, image_prompt_config, ai_service):
    # 🆕 NUEVO: Generar dossier una sola vez
    character_dossier = self._generate_character_dossier(project_info, ai_service)
    
    for i, scene in enumerate(scenes):
        # 🆕 NUEVO: Detectar edad y extraer descripción
        character_stage = self._detect_character_stage_for_scene(scene['text'], project_info['titulo'])
        character_description = self._extract_character_description_for_stage(character_dossier, character_stage)
        
        # ✅ EXISTENTE: Preparar variables (EXTENDIDO)
        template_variables = {
            'scene_text': scene['text'],
            'titulo': project_info.get("titulo", ""),
            'contexto': project_info.get("contexto", ""),
            'character_description': character_description  # ← NUEVA
        }
        
        # ✅ EXISTENTE: Añadir variables históricas
        historical_variables = image_prompt_config.get('historical_variables', {})
        template_variables.update(historical_variables)
        
        # ✅ EXISTENTE: Resto del flujo sin cambios
        # ... (generar prompt con ai_service)
```

---

## 🎯 **VENTAJAS DEL PLAN REVISADO**

### **🔧 Compatibilidad Total**
- ✅ **No rompe** el sistema actual
- ✅ **Reutiliza** infraestructura existente
- ✅ **Mantiene** todos los fallbacks
- ✅ **Preserva** logging detallado

### **🚀 Implementación Incremental**
- ✅ **Fase por fase** sin interrumpir funcionamiento
- ✅ **Testing independiente** de cada componente
- ✅ **Rollback sencillo** si hay problemas

### **📈 Escalabilidad**
- ✅ **Compatible** con múltiples personajes futuros
- ✅ **Extensible** a otros tipos de coherencia
- ✅ **Integrable** con otros estilos de prompt

### **🎭 Coherencia Mejorada**
- ✅ **Descripción única** del personaje por proyecto
- ✅ **Adaptación automática** por edad/escena
- ✅ **Consistencia visual** a lo largo del video
- ✅ **Precisión histórica** mantenida

---

## 📋 **RESUMEN DE CAMBIOS MÍNIMOS**

### **Archivos a Modificar:**
1. `prompts/imagenes_prompts.json` → Añadir plantilla dossier + extender histórica
2. `utils/scene_generator.py` → 3 funciones nuevas + modificar una existente

### **Funciones Nuevas:**
1. `_generate_character_dossier()` 
2. `_detect_character_stage_for_scene()`
3. `_extract_character_description_for_stage()`

### **Funciones Modificadas:**
1. `generate_prompts_for_scenes()` → Añadir lógica de dossier

---

## 🎯 **PRÓXIMO PASO RECOMENDADO**

**IMPLEMENTAR FASE 1 COMO PRUEBA DE CONCEPTO:**
- Crear plantilla de dossier
- Implementar `_generate_character_dossier()`
- Testear con un proyecto existente (ej: San Blas)
- Verificar calidad del dossier generado

**¿Proceder con Fase 1?** 🚀 