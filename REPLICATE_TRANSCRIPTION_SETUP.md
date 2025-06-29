# 🚀 Configuración de Transcripción con Replicate

## Descripción

El servicio de transcripción de Replicate utiliza el modelo "Incredibly Fast Whisper" que ofrece velocidad y precisión superiores al Whisper tradicional. Este servicio es ideal para transcripciones rápidas y precisas en múltiples idiomas.

## Características

### ✅ **Velocidad Increíble**
- **10-50x más rápido** que Whisper local
- **Procesamiento en la nube** sin descarga de modelos
- **Optimizado para GPU** en servidores de Replicate

### ✅ **Precisión Superior**
- **Mejor reconocimiento** de acentos y dialectos
- **Soporte multiidioma** avanzado
- **Timestamps precisos** por chunk o palabra

### ✅ **Idiomas Soportados**
- **Español** (es)
- **Inglés** (en)
- **Francés** (fr)
- **Portugués** (pt)
- **Portugués Brasileño** (pt-BR)
- **Italiano** (it)
- **Y muchos más** (detección automática disponible)

### ✅ **Funcionalidades Avanzadas**
- **Diarización de audio** (identificación de hablantes)
- **Traducción automática** a inglés
- **Timestamps por palabra** o por chunk
- **Estimación de costos** en tiempo real

## Instalación

### 1. Verificar Dependencias

El paquete `replicate` ya está incluido en `requirements.txt`:

```txt
replicate==0.22.0
```

### 2. Obtener API Key de Replicate

1. Ve a [https://replicate.com](https://replicate.com)
2. Crea una cuenta o inicia sesión
3. Ve a tu perfil → API Tokens
4. Crea un nuevo token
5. Copia el token

### 3. Configurar API Key

#### Opción A: Variable de Entorno
```bash
export REPLICATE_API_TOKEN=tu_token_aqui
```

#### Opción B: En la Aplicación
1. Ve a **⚙️ Configuración** → **🤖 IA**
2. Configura tu **Replicate API Key**

## Configuración

### Configuración Global

1. Ve a la página **⚙️ Configuración** en la aplicación
2. Selecciona la pestaña **🎙️ Transcripción**
3. Selecciona **Replicate (Incredibly Fast Whisper)** como servicio
4. Configura los parámetros según tus necesidades

### Parámetros de Replicate

#### **Idioma por Defecto**
- **Español**: Para contenido en español
- **Inglés**: Para contenido en inglés
- **Francés**: Para contenido en francés
- **Portugués**: Para contenido en portugués
- **Portugués Brasileño**: Para contenido en portugués de Brasil
- **Italiano**: Para contenido en italiano

#### **Tarea**
- **Transcribir**: Mantiene el idioma original
- **Traducir**: Convierte todo a inglés

#### **Tipo de Timestamp**
- **Por Chunk**: Timestamps por segmentos (más rápido)
- **Por Palabra**: Timestamps por palabra (más preciso)

#### **Batch Size**
- **8-64**: Tamaño del batch de procesamiento
- **Recomendado**: 24 (equilibrio velocidad/memoria)
- **Reducir**: Si hay problemas de memoria

#### **Diarización de Audio**
- **Habilitada**: Identifica diferentes hablantes
- **Requiere**: Token de Hugging Face
- **Útil para**: Entrevistas, podcasts, reuniones

## Uso en el Código

### Función Unificada

```python
from utils.transcription_services import get_transcription_service

# Obtener servicio de Replicate
service = get_transcription_service('replicate', api_token='tu_token')

# Transcribir audio
segments, metadata = service.transcribe_audio(
    audio_path="audio.mp3",
    language="es",
    task="transcribe",
    timestamp="chunk",
    batch_size=24
)
```

### Servicio Directo

```python
from utils.transcription_services import ReplicateTranscriptionService

# Crear servicio
service = ReplicateTranscriptionService(api_token='tu_token')

# Transcribir con parámetros avanzados
segments, metadata = service.transcribe_audio(
    audio_path="audio.mp3",
    language="es",
    task="transcribe",
    timestamp="word",  # Timestamps por palabra
    batch_size=32,
    diarise_audio=True,  # Diarización
    hf_token="tu_hf_token"  # Para diarización
)
```

### Estimación de Costos

```python
# Estimar costo antes de transcribir
cost_estimate = service.estimate_cost(300.0)  # 5 minutos
print(f"Costo estimado: ${cost_estimate['estimated_cost_usd']:.4f}")
```

## Comparación: Local vs Replicate

| Característica | Whisper Local | Replicate |
|----------------|---------------|-----------|
| **Velocidad** | Lenta | ⚡ Muy rápida |
| **Costo** | Gratuito | $0.01-0.05/min |
| **Precisión** | Buena | Excelente |
| **Idiomas** | Limitados | Múltiples |
| **Offline** | ✅ Sí | ❌ No |
| **Descarga** | Requerida | No necesaria |
| **GPU** | Opcional | Incluida |
| **Diarización** | No | ✅ Sí |

## Costos y Estimaciones

### **Estructura de Costos**
- **Base**: $0.01-0.05 por minuto de audio
- **Factores**: Duración, complejidad, batch size
- **Optimización**: Usar batch size apropiado

### **Ejemplos de Costos**
- **1 minuto**: ~$0.03
- **5 minutos**: ~$0.15
- **10 minutos**: ~$0.30
- **1 hora**: ~$1.80

### **Optimización de Costos**
1. **Usar batch size apropiado** (24-32)
2. **Evitar diarización** si no es necesaria
3. **Usar timestamps por chunk** en lugar de palabra
4. **Procesar archivos grandes** en una sola llamada

## Configuración Avanzada

### **Diarización de Audio**

Para identificar diferentes hablantes:

1. **Obtener token de Hugging Face**:
   - Ve a [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - Crea un nuevo token
   - Acepta los términos de Pyannote.audio

2. **Configurar en la aplicación**:
   - Habilita "Diarización de Audio"
   - Añade tu Hugging Face Token

3. **Usar en el código**:
```python
segments, metadata = service.transcribe_audio(
    audio_path="audio.mp3",
    diarise_audio=True,
    hf_token="tu_hf_token"
)
```

### **Traducción Automática**

Para convertir audio a inglés:

```python
segments, metadata = service.transcribe_audio(
    audio_path="audio_español.mp3",
    task="translate",  # Traducir a inglés
    language="es"  # Idioma original
)
```

### **Timestamps por Palabra**

Para máxima precisión:

```python
segments, metadata = service.transcribe_audio(
    audio_path="audio.mp3",
    timestamp="word",  # Timestamps por palabra
    batch_size=16  # Reducir batch size
)
```

## Troubleshooting

### **Error: "No se encontró REPLICATE_API_TOKEN"**
**Solución**: Configura tu API key de Replicate en la aplicación o como variable de entorno

### **Error: "Replicate no está disponible"**
**Solución**: Instala el paquete replicate:
```bash
pip install replicate
```

### **Error: "Problemas de memoria"**
**Solución**: Reduce el batch_size a 8-16

### **Error: "Diarización falló"**
**Solución**: Verifica tu Hugging Face token y acepta los términos de Pyannote.audio

### **Transcripción lenta**
**Solución**: 
- Aumenta batch_size (hasta 64)
- Usa timestamps por chunk
- Deshabilita diarización si no es necesaria

### **Baja precisión**
**Solución**:
- Especifica el idioma correcto
- Usa timestamps por palabra
- Verifica la calidad del audio

## Ejemplos de Uso

### **Transcripción Básica**
```python
from utils.transcription_services import get_transcription_service

service = get_transcription_service('replicate', api_token='tu_token')

segments, metadata = service.transcribe_audio(
    audio_path="mi_audio.mp3",
    language="es"
)

print(f"Transcripción completada: {len(segments)} segmentos")
```

### **Transcripción con Diarización**
```python
segments, metadata = service.transcribe_audio(
    audio_path="entrevista.mp3",
    language="es",
    diarise_audio=True,
    hf_token="tu_hf_token"
)
```

### **Traducción a Inglés**
```python
segments, metadata = service.transcribe_audio(
    audio_path="audio_español.mp3",
    language="es",
    task="translate"
)
```

### **Timestamps por Palabra**
```python
segments, metadata = service.transcribe_audio(
    audio_path="audio.mp3",
    timestamp="word",
    batch_size=16
)
```

## Integración con el Sistema

### **En VideoProcessor**
El sistema automáticamente usa Replicate cuando está configurado:

```python
# En utils/video_processing.py
transcription_config = self.tts_config.get('transcription', {})
transcription_type = transcription_config.get('service_type', 'local')

if transcription_type == 'replicate':
    self.transcription_service = get_transcription_service('replicate', api_token=replicate_token)
```

### **En Batch Processor**
La transcripción se ejecuta automáticamente durante el procesamiento de videos.

### **Configuración Automática**
Los parámetros se cargan desde `config.yaml` y se aplican automáticamente.

## Referencias

- [Replicate Documentation](https://replicate.com/docs)
- [Incredibly Fast Whisper Model](https://replicate.com/vaibhavs10/incredibly-fast-whisper)
- [Hugging Face Pyannote.audio](https://huggingface.co/pyannote/speaker-diarization-3.1)

## Soporte

Si tienes problemas con la transcripción de Replicate:

1. Verifica tu API key de Replicate
2. Revisa los logs de error
3. Prueba con archivos de audio más pequeños
4. Contacta al soporte de Replicate si el problema persiste

---

**¡El servicio de transcripción de Replicate está completamente integrado y listo para usar! 🚀** 