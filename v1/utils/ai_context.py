import os
from dotenv import load_dotenv
from openai import OpenAI

# Cargar la API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Inicializar cliente moderno de OpenAI
client = OpenAI(api_key=api_key)

def evaluar_con_gpt(contexto_tecnico):
    prompt = f"""Soy un bot de trading que ha detectado la siguiente situación técnica:

{contexto_tecnico}

¿Debería abrir una posición de compra en BTC/USD ahora mismo?
Responde 'Sí' o 'No' y explica brevemente por qué."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un experto en análisis técnico de criptomonedas."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content
