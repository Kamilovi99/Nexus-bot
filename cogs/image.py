import discord
import os
import requests
from discord.ext import commands

class Image(commands.Cog, name="🎨 Memes"):
    """Comandos de generación de memes."""
    def __init__(self, bot):
        self.bot = bot
        self.meme_templates = {
            "drake": "181913649", "novio": "112126428", "simply": "61579",
            "doge": "8072285", "botones": "87743020", "gru": "105458615",
            "cerebro": "93895088", "bob": "102156234", "panik": "188390779",
            "pajaro": "100777631", "sorpresa": "247375501", "batman": "438680",
            "futurama": "61520", "matrix": "100947", "pikachu": "155067746",
            "spiderman": "47921009", "capitan": "28034788"
        }

    @commands.command()
    async def meme(self, ctx, plantilla: str, *, texto: str):
        """Crea un meme con una plantilla. Uso: @meme <plantilla> <texto1>;<texto2>"""
        username = os.getenv("IMGFLIP_USER")
        password = os.getenv("IMGFLIP_PASS")

        if not username or not password:
            return await ctx.send("❌ Las credenciales de Imgflip (IMGFLIP_USER, IMGFLIP_PASS) no están configuradas en .env.")

        plantilla_id = self.meme_templates.get(plantilla.lower())
        if not plantilla_id:
            return await ctx.send(f"❌ Plantilla no válida. Usa `@meme_list` para ver las opciones.")

        partes = texto.split(";", 1)
        text0 = partes[0].strip()
        text1 = partes[1].strip() if len(partes) > 1 else ""

        url = "https://api.imgflip.com/caption_image"
        data = {
            "username": username, "password": password,
            "template_id": plantilla_id, "text0": text0, "text1": text1
        }
        try:
            resp = requests.post(url, data=data).json()
            if resp.get("success"):
                await ctx.send(resp["data"]["url"])
            else:
                await ctx.send(f"❌ Error de la API de Imgflip: {resp.get('error_message','desconocido')}")
        except requests.RequestException as e:
            await ctx.send(f"❌ No pude conectarme a la API de Imgflip. Error: {e}")

    @commands.command()
    async def meme_list(self, ctx):
        """Muestra la lista de plantillas de memes disponibles."""
        lista_texto = "\n".join([f"🔹 **{nombre}**" for nombre in self.meme_templates.keys()])
        embed = discord.Embed(
            title="🧩 Plantillas de Memes Disponibles",
            description=lista_texto,
            color=discord.Color.blue()
        )
        embed.set_footer(text='Uso: @meme <plantilla> Texto arriba ; Texto abajo')
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Image(bot))