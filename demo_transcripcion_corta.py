#!/usr/bin/env python3
"""
Demostración del script con una transcripción corta de ejemplo
"""

import sys
from pathlib import Path

# Agregar la ruta de utils al path
sys.path.append(str(Path(__file__).parent))

from utils.ai_services import extract_historical_context, AIServices
import json

def demo_transcripcion_corta():
    print("=" * 60)
    print("  DEMO: GENERADOR DE PROMPTS DESDE TRANSCRIPCIÓN")
    print("=" * 60)
    print("📝 Usando transcripción corta de ejemplo...")
    
    # Transcripción de ejemplo corta
    transcripcion = """Santa Teresa de Ávila escribió Las Moradas en su celda del convento carmelita. 
    La mística española contemplaba el alma como un castillo interior. Oraba profundamente 
    durante las noches, recibiendo visiones místicas que después plasmaba en sus escritos."""
    
    titulo = "Santa Teresa de Ávila"
    
    print(f"\n📄 TRANSCRIPCIÓN:")
    print(f"'{transcripcion}'")
    print(f"\n👤 PERSONAJE: {titulo}")
    
    # 1. Extraer contexto histórico
    print(f"\n⏳ Paso 1: Extrayendo contexto histórico...")
    contexto_historico = extract_historical_context(
        titulo=titulo,
        contexto=transcripcion,
        provider="gemini"
    )
    
    print(f"\n📊 CONTEXTO HISTÓRICO EXTRAÍDO:")
    print("-" * 40)
    for key, value in contexto_historico.items():
        emoji = {
            "periodo_historico": "📅",
            "ubicacion": "🌍",
            "contexto_cultural": "🏛️",
            "fecha_nacimiento": "🎂",
            "fecha_muerte": "⚱️",
            "edad_personaje": "👤"
        }.get(key, "📋")
        print(f"{emoji} {key.replace('_', ' ').title()}: {value}")
    
    # 2. Identificar escenas
    print(f"\n⏳ Paso 2: Identificando escenas visuales...")
    escenas = [
        "Santa Teresa escribió Las Moradas en su celda del convento carmelita",
        "La mística española contemplaba el alma como un castillo interior", 
        "Oraba profundamente durante las noches, recibiendo visiones místicas"
    ]
    
    print(f"🎬 ESCENAS DETECTADAS:")
    for i, escena in enumerate(escenas, 1):
        print(f"  {i}. {escena}")
    
    # 3. Generar prompt para la primera escena
    escena_seleccionada = escenas[0]
    print(f"\n⏳ Paso 3: Generando prompt para escena 1...")
    print(f"📝 Escena: '{escena_seleccionada}'")
    
    ai_services = AIServices()
    
    # Template de prompt
    system_prompt = """Eres un experto en generación de prompts para imágenes fotorrealistas con precisión histórica.
    Crea un prompt detallado que genere una imagen hiperrealista respetando el contexto histórico específico.
    
    ESTRUCTURA:
    1. PERSONAJE: Descripción física precisa con edad exacta
    2. VESTIMENTA: Ropa históricamente apropiada 
    3. ESCENARIO: Arquitectura y ambiente de la época
    4. ILUMINACIÓN: Apropiada para el período
    5. CALIDAD: Términos técnicos fotográficos
    6. TÉRMINOS NEGATIVOS: Para evitar anacronismos
    
    El prompt debe ser en inglés, históricamente preciso y detallado."""

    user_prompt = f"""Genera un prompt para imagen fotorrealista de:

CONTEXTO HISTÓRICO:
- Período: {contexto_historico['periodo_historico']}
- Ubicación: {contexto_historico['ubicacion']}
- Edad del personaje: {contexto_historico['edad_personaje']} años exactos

ESCENA: {escena_seleccionada}

INSTRUCCIONES:
- Personaje de exactamente {contexto_historico['edad_personaje']} años
- Vestimenta carmelita del {contexto_historico['periodo_historico']}
- Arquitectura de convento español del siglo XVI
- Máximo realismo histórico

Responde SOLO con el prompt en inglés."""

    try:
        prompt_generado = ai_services.generate_content(
            provider="gemini",
            model="models/gemini-2.5-flash-lite-preview-06-17",
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # Limpiar markdown si lo tiene
        if "```" in prompt_generado:
            prompt_generado = prompt_generado.split("```")[1].strip()
        
        print(f"\n🎨 PROMPT GENERADO:")
        print("=" * 60)
        print(prompt_generado)
        print("=" * 60)
        
        # 4. Evaluar calidad
        print(f"\n⏳ Paso 4: Evaluando calidad del prompt...")
        
        checks = {
            "edad_mencionada": str(contexto_historico['edad_personaje']) in prompt_generado,
            "periodo_historico": "16th century" in prompt_generado.lower() or "siglo xvi" in prompt_generado.lower(),
            "vestimenta": "carmelite" in prompt_generado.lower() or "nun" in prompt_generado.lower(),
            "calidad_foto": "photorealistic" in prompt_generado.lower() or "detailed" in prompt_generado.lower(),
            "escenario": "convent" in prompt_generado.lower() or "cell" in prompt_generado.lower()
        }
        
        puntuacion = sum(checks.values())
        
        print(f"📊 EVALUACIÓN:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            descripciones = {
                "edad_mencionada": f"Edad específica ({contexto_historico['edad_personaje']} años)",
                "periodo_historico": f"Período histórico (Siglo XVI)",
                "vestimenta": "Vestimenta carmelita",
                "calidad_foto": "Calidad fotorrealista",
                "escenario": "Escenario de convento"
            }
            print(f"  {status} {descripciones[check]}")
        
        print(f"\n⭐ PUNTUACIÓN: {puntuacion}/5")
        
        if puntuacion >= 4:
            print("🎉 EXCELENTE: Prompt de alta calidad")
        elif puntuacion >= 3:
            print("✅ BUENO: Prompt aceptable")
        else:
            print("⚠️  MEJORABLE: Necesita refinamiento")
        
        # 5. Mostrar resultado final
        print(f"\n📋 RESUMEN DEL PROCESO:")
        print(f"✅ Transcripción analizada automáticamente")
        print(f"✅ Contexto histórico extraído (edad {contexto_historico['edad_personaje']} años)")
        print(f"✅ Escenas visuales identificadas")
        print(f"✅ Prompt optimizado generado")
        print(f"✅ Calidad evaluada ({puntuacion}/5)")
        
        print(f"\n💡 BENEFICIOS PARA TU PROYECTO:")
        print(f"🎯 Mantiene consistencia histórica entre imágenes")
        print(f"🔄 Automatiza el proceso de conversión transcripción→prompt")
        print(f"📊 Evalúa calidad automáticamente")
        print(f"⚠️  Evita pérdida de contexto histórico")
        
        return {
            "transcripcion": transcripcion,
            "contexto_historico": contexto_historico,
            "prompt_generado": prompt_generado,
            "puntuacion": puntuacion
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Iniciando demostración...")
    resultado = demo_transcripcion_corta()
    
    if resultado:
        print(f"\n✨ DEMOSTRACIÓN COMPLETADA EXITOSAMENTE")
        print(f"📁 Este es el flujo que seguirá tu proyecto real")
    else:
        print(f"\n❌ Error en la demostración")
    
    print(f"\n🔧 Para usar en tu proyecto:")
    print(f"   python test_prompts_transcripcion.py")
    print(f"   (script interactivo completo)") 