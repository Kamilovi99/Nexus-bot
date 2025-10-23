import discord
import random
import asyncio
import wikipediaapi
from discord.ext import commands
from APIS import traducir_texto, obtener_codigo

class Utils(commands.Cog, name="🛠️ Utilidades y Encuestas"):
    """Comandos de utilidad, herramientas y encuestas."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def add(self, ctx, left: int, right: int):
        """Suma dos números."""
        await ctx.send(left + right)

    @commands.command()
    async def roll(self, ctx, dice: str):
        """Lanza dados en formato NdN."""
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            await ctx.send('El formato debe ser NdN (ej: 2d6)!')
            return
        result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
        await ctx.send(result)

    @commands.command()
    async def repeat(self, ctx, times: int, content='repitiendo...'):
        """Repite un mensaje varias veces."""
        for i in range(times):
            await ctx.send(content)

    @commands.command()
    async def mayus(self, ctx, *, texto: str):
        """Convierte un texto a mayúsculas."""
        await ctx.send(texto.upper())

    @commands.command()
    async def minus(self, ctx, *, texto: str):
        """Convierte un texto a minúsculas."""
        await ctx.send(texto.lower())

    @commands.command()
    async def recordatorio(self, ctx, tiempo: int, *, mensaje: str):
        """Fija un recordatorio."""
        await ctx.send(f"⏳ Te recordaré '{mensaje}' en {tiempo} segundos.")
        await asyncio.sleep(tiempo)
        await ctx.send(f"⏰ {ctx.author.mention}, ¡recordatorio!: {mensaje}")

    @commands.command()
    async def ping(self, ctx):
        """Muestra la latencia del bot."""
        await ctx.send(f'🏓 Pong! Latencia: {round(self.bot.latency * 1000)}ms')

    @commands.command(name="traducir")
    async def traducir(self, ctx, idioma_destino: str, *, texto: str):
        """Traduce texto a otro idioma."""
        try:
            codigo = obtener_codigo(idioma_destino)
            resultado = traducir_texto(texto, codigo)
            embed = discord.Embed(title="🌍 Traducción", color=discord.Color.green())
            embed.add_field(name="Texto original", value=texto, inline=False)
            embed.add_field(name=f"Traducción ({codigo})", value=resultado, inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error al traducir: {e}")

    @commands.command()
    async def wiki(self, ctx, *, consulta):
        """Busca un artículo en Wikipedia."""
        user_agent = "MiBotDiscord/1.0 (juanignaciogomez@ngcarmenia.edu.co)"
        wiki_wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language="es")
        page = wiki_wiki.page(consulta)

        if page.exists():
            resumen = page.summary[:500]
            if len(page.summary) > 500:
                resumen += "..."
            await ctx.send(f"📖 **{page.title}**\n\n{resumen}\n\n🔗 {page.fullurl}")
        else:
            await ctx.send(f"❌ No encontré información sobre **{consulta}** en Wikipedia.")

    @commands.command(name="encuesta")
    async def encuesta(self, ctx, *, pregunta):
        """Crea una encuesta simple con ✅ y ❌."""
        embed = discord.Embed(title="📊 Encuesta", description=pregunta, color=discord.Color.blue())
        mensaje = await ctx.send(embed=embed)
        await mensaje.add_reaction("✅")
        await mensaje.add_reaction("❌")

    @commands.command(name="encuestaopciones")
    async def encuesta_opciones(self, ctx, pregunta: str, *opciones):
        """Crea una encuesta con hasta 10 opciones."""
        if len(opciones) > 10:
            await ctx.send("❌ Solo se permiten hasta 10 opciones.")
            return
        numeros = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        descripcion = ""
        for i, opcion in enumerate(opciones):
            descripcion += f"{numeros[i]} {opcion}\n"
        embed = discord.Embed(title=f"📊 {pregunta}", description=descripcion, color=discord.Color.green())
        mensaje = await ctx.send(embed=embed)
        for i in range(len(opciones)):
            await mensaje.add_reaction(numeros[i])

async def setup(bot):
    await bot.add_cog(Utils(bot))
