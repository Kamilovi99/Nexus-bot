from deep_translator import GoogleTranslator
import asyncio
import random
import functools
from typing import List, Dict
import discord

LANG_MAP = {
    "en": "en", "english": "en", "ingles": "en",
    "es": "es", "spanish": "es", "español": "es",
    "fr": "fr", "french": "fr", "francés": "fr",
    "de": "de", "german": "de", "alemán": "de",
    "it": "it", "italian": "it", "italiano": "it",
    "ja": "ja", "japanese": "ja", "japones": "ja",
    "pt": "pt", "portuguese": "pt", "portugués": "pt",
    "ko": "ko", "korean": "ko", "coreano": "ko",
    "ar": "ar", "arabic": "ar", "arabe": "ar",
    "hu": "hu", "hungrian": "hu", "hungaro": "hu",
    "ne": "ne", "nepali": "ne", "nepalí": "ne",
    "bg": "bg", "bulgarian": "bg", "búlgaro": "bg",
    # puedes añadir más...
}


def obtener_codigo(idioma: str) -> str:
    """Devuelve el código de idioma (2 letras) a partir del nombre."""
    key = idioma.strip().lower()
    return LANG_MAP.get(key, key)  # si no está en el mapa, se asume código válido

def traducir_texto(texto: str, idioma_destino: str) -> str:
    """Traduce un texto al idioma de destino usando deep-translator."""
    codigo = obtener_codigo(idioma_destino)
    traduccion = GoogleTranslator(source='auto', target=codigo).translate(texto)
    return traduccion

preguntas = {
    "¿Cuál es el planeta más grande del sistema solar?": "jupiter",
    "¿Cuántos continentes hay en el mundo?": "7",
    "¿Quién pintó la Mona Lisa?": "leonardo da vinci",
    "¿Cuántos huesos tiene el cuerpo humano adulto?": "206",
    "¿En qué año llegó el hombre a la Luna?": "1969",
    "¿Cuál es el río más largo del mundo?": "amazonas",
    "¿Cuántos lados tiene un hexágono?": "6",
    "¿Quién escribió 'Don Quijote de la Mancha'?": "miguel de cervantes",
    "¿Cuál es el océano más grande del mundo?": "pacifico",
    "¿Cuántos colores tiene el arcoíris?": "7",
    "¿Cuál es el metal más abundante en la corteza terrestre?": "aluminio",
    "¿Qué gas usan las plantas en la fotosíntesis?": "dioxido de carbono",
    "¿Quién fue el primer presidente de los Estados Unidos?": "george washington",
    "¿Cuál es el país más grande del mundo por territorio?": "rusia",
    "¿Qué científico formuló la teoría de la relatividad?": "albert einstein",
    "¿Cuántos corazones tiene un pulpo?": "3",
    "¿Cuál es el animal terrestre más rápido del mundo?": "guepardo",
    "¿Qué vitamina se obtiene del sol?": "vitamina d",
    "¿En qué país se encuentra la Torre Eiffel?": "francia",
    "¿Cuántos jugadores hay en un equipo de fútbol?": "11",
    "¿Cómo se llama la capital de Japón?": "tokio",
    "¿Quién descubrió América?": "cristobal colon",
    "¿Cuál es el símbolo químico del oro?": "au",
    "¿Qué órgano bombea la sangre en el cuerpo humano?": "corazon",
    "¿En qué año terminó la Segunda Guerra Mundial?": "1945",
    "¿Cuál es el país con mayor población del mundo?": "china",
    "¿Cuántos anillos olímpicos hay en la bandera de los Juegos Olímpicos?": "5",
    "¿Cuál es la moneda oficial del Reino Unido?": "libra esterlina",
    "¿Cuál es el hueso más largo del cuerpo humano?": "femur",
    "¿En qué año comenzó la Primera Guerra Mundial?": "1914",
    "¿Cuál es el único mamífero capaz de volar?": "murcielago",
    "¿Qué gas es el más abundante en la atmósfera terrestre?": "nitrogeno",
    "¿Cómo se llama el proceso por el cual el agua pasa de estado líquido a gaseoso?": "evaporacion",
    "¿Qué instrumento se usa para medir los terremotos?": "sismografo",
    "¿Qué planeta es conocido como el planeta rojo?": "marte",
    "¿Qué famoso físico dijo 'Dios no juega a los dados con el universo'?": "albert einstein",
    "¿Cómo se llama el himno nacional de Francia?": "la marsellesa",
    "¿Qué animal es el símbolo de la paz?": "paloma",
    "¿Cuál es el país más pequeño del mundo?": "vaticano",
    "¿Cuál es el idioma más hablado en el mundo?": "ingles",
    "¿Quién escribió 'Cien años de soledad'?": "gabriel garcia marquez",
    "¿Cuál es el símbolo químico del oxígeno?": "o",
    "¿Qué día se celebra el Día de la Independencia de México?": "16 de septiembre"
}

def obtener_preguntas():
    pregunta, respuesta = random.choice(list(preguntas.items()))
    return pregunta, respuesta