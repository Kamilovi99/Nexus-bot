import discord
import random
import asyncio
import os
from discord.ext import commands
from APIS import obtener_preguntas

class Games(commands.Cog, name="🎮 Juegos y Entretenimiento"):
    """Comandos de juegos y entretenimiento."""
    def __init__(self, bot):
        self.bot = bot
        self.historias = {}

    @commands.command()
    async def trivia(self, ctx):
        """Inicia un juego de trivia."""
        pregunta, respuesta = obtener_preguntas()
        await ctx.send(f"❓ **Trivia:** {pregunta}")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", timeout=15.0, check=check)
            if msg.content.lower() == respuesta.lower():
                await ctx.send(f"✅ ¡Correcto, {ctx.author.mention}!")
            else:
                await ctx.send(f"❌ Incorrecto. La respuesta correcta era **{respuesta}**.")
        except asyncio.TimeoutError:
            await ctx.send(f"⏳ Se acabó el tiempo. La respuesta era **{respuesta}**.")

    @commands.command()
    async def jugar(self, ctx, jugador: str):
        """Juega piedra, papel o tijera contra el bot."""
        opciones = ['piedra', 'papel', 'tijera']
        jugador = jugador.lower()
        if jugador not in opciones:
            return await ctx.send("❌ Opción inválida. Elige: piedra, papel o tijera.")
        
        computadora = random.choice(opciones)
        
        if computadora == jugador:
            resultado = "¡Empate! 🤝"
        elif (jugador == "piedra" and computadora == "tijera") or \
             (jugador == "papel" and computadora == "piedra") or \
             (jugador == "tijera" and computadora == "papel"):
            resultado = f"🎉 ¡{ctx.author.mention} ganaste!"
        else:
            resultado = "😢 ¡Perdiste!"

        await ctx.send(f"La computadora eligió **{computadora}**. {resultado}")

    @commands.command()
    async def adivina(self, ctx):
        """Adivina el número que piensa el bot (1-100)."""
        numero_secreto = random.randint(1, 100)
        await ctx.send("He pensado en un número del 1 al 100. Tienes 7 intentos.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        for i in range(7):
            try:
                msg = await self.bot.wait_for("message", timeout=20.0, check=check)
                intento = int(msg.content)

                if intento < numero_secreto:
                    await ctx.send(f"🔼 Más alto. Te quedan {6-i} intentos.")
                elif intento > numero_secreto:
                    await ctx.send(f"🔽 Más bajo. Te quedan {6-i} intentos.")
                else:
                    await ctx.send(f"🎉 ¡Correcto, {ctx.author.mention}! El número era {numero_secreto}.")
                    return
            except asyncio.TimeoutError:
                await ctx.send(f"⏳ Se acabó el tiempo. El número era {numero_secreto}.")
                return
        await ctx.send(f"😢 Perdiste. El número secreto era {numero_secreto}.")

    @commands.group(name="historia", invoke_without_command=True)
    async def historia(self, ctx):
        """Crea una historia de forma colaborativa."""
        await ctx.send("Usa `@historia iniciar <frase>`, `@historia agregar <frase>` o `@historia ver`")

    @historia.command(name="iniciar")
    async def historia_iniciar(self, ctx, *, frase: str):
        """Inicia una nueva historia en este canal."""
        self.historias[ctx.channel.id] = [f"{ctx.author.display_name}: {frase}"]
        await ctx.send(f"📖 ¡Historia iniciada!\n> {frase}")

    @historia.command(name="agregar")
    async def historia_agregar(self, ctx, *, frase: str):
        """Añade una frase a la historia de este canal."""
        if ctx.channel.id not in self.historias:
            return await ctx.send("❌ No hay ninguna historia iniciada en este canal. Usa `@historia iniciar`.")
        self.historias[ctx.channel.id].append(f"{ctx.author.display_name}: {frase}")
        await ctx.send(f"✍️ Frase añadida.")

    @historia.command(name="ver")
    async def historia_ver(self, ctx):
        """Muestra la historia completa de este canal."""
        if ctx.channel.id not in self.historias:
            return await ctx.send("❌ No hay ninguna historia iniciada en este canal.")
        
        historia_completa = "\n".join(self.historias[ctx.channel.id])
        embed = discord.Embed(title=f"Historia de #{ctx.channel.name}", description=historia_completa, color=discord.Color.green())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))