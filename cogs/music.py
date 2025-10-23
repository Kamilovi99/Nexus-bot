import discord
import asyncio
import functools
import yt_dlp
from discord.ext import commands
from typing import List, Dict

# --- Opciones y configuración --- #
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}
YTDL_OPTS = {
    "format": "bestaudio/best", "noplaylist": True, "quiet": True,
    "default_search": "ytsearch", "source_address": "0.0.0.0",
}

# --- Clase de fuente de audio --- #
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title", "(sin título)")
        self.url = data.get("webpage_url", "")

    @classmethod
    async def from_query(cls, ytdl, query: str, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, functools.partial(ytdl.extract_info, f"ytsearch1:{query}", download=False)
        )
        if not data or "entries" not in data or not data["entries"]:
            raise RuntimeError(f"No encontré resultados para '{query}'")
        entry = data["entries"][0]
        return cls(discord.FFmpegPCMAudio(entry["url"], **FFMPEG_OPTIONS), data=entry)

# --- Cog de Música --- #
class Music(commands.Cog, name="🎵 Música"):
    def __init__(self, bot):
        self.bot = bot
        self.music_queue: Dict[int, List[Dict]] = {}
        self.now_playing: Dict[int, Dict] = {}
        self._ytdl = yt_dlp.YoutubeDL(YTDL_OPTS)

    def _ensure_queue(self, guild_id: int):
        if guild_id not in self.music_queue:
            self.music_queue[guild_id] = []

    async def _play_next(self, ctx):
        guild_id = ctx.guild.id
        if not self.music_queue.get(guild_id):
            self.now_playing.pop(guild_id, None)
            # Opcional: Desconectar después de un tiempo de inactividad
            # await asyncio.sleep(60)
            # if ctx.voice_client and not ctx.voice_client.is_playing():
            #     await ctx.voice_client.disconnect()
            return

        song_data = self.music_queue[guild_id].pop(0)
        self.now_playing[guild_id] = song_data

        try:
            player = await YTDLSource.from_query(self._ytdl, song_data['webpage_url'], loop=self.bot.loop)
            
            ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self._play_next(ctx), self.bot.loop).result())

            embed = discord.Embed(title=f"▶️ Reproduciendo ahora", description=f"[{player.title}]({player.url})", color=discord.Color.green())
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error al reproducir: `{e}`")
            await self._play_next(ctx)

    @commands.command(name="join", aliases=["unir"])
    async def join(self, ctx):
        """Hace que el bot se una a tu canal de voz."""
        if not ctx.author.voice:
            return await ctx.send("❌ No estás en un canal de voz.")
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"👋 Me he unido a **{channel.name}**.")

    @commands.command(name="leave", aliases=["salir"])
    async def leave(self, ctx):
        """Hace que el bot abandone el canal de voz."""
        if not ctx.voice_client:
            return await ctx.send("ℹ️ No estoy en un canal de voz.")
        guild_id = ctx.guild.id
        self.music_queue.pop(guild_id, None)
        self.now_playing.pop(guild_id, None)
        await ctx.voice_client.disconnect()
        await ctx.send("👋 ¡Adiós!")

    @commands.command(name="play", aliases=["p", "sonar"])
    async def play(self, ctx, *, query: str):
        """Busca una canción y la añade a la cola."""
        if not ctx.author.voice:
            return await ctx.send("❌ Debes estar en un canal de voz.")
        if not ctx.voice_client:
            await ctx.invoke(self.bot.get_command('join'))

        await ctx.send(f"🔎 Buscando y añadiendo: `{query}`...")
        try:
            data = await self.bot.loop.run_in_executor(
                None, functools.partial(self._ytdl.extract_info, f"ytsearch1:{query}", download=False)
            )
            if not data or "entries" not in data or not data["entries"]:
                return await ctx.send("❌ No encontré resultados.")
            
            song = data['entries'][0]
            self._ensure_queue(ctx.guild.id)
            self.music_queue[ctx.guild.id].append(song)
            await ctx.send(f"✅ Añadido a la cola: **{song['title']}**")
            
            if not ctx.voice_client.is_playing():
                await self._play_next(ctx)
                
        except Exception as e:
            await ctx.send(f"❌ Ocurrió un error: {e}")

    @commands.command(name="pause", aliases=["pausar"])
    async def pause(self, ctx):
        """Pausa la reproducción actual."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Pausado.")
        else:
            await ctx.send("ℹ️ No hay nada reproduciéndose.")

    @commands.command(name="resume", aliases=["reanudar"])
    async def resume(self, ctx):
        """Reanuda la reproducción."""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ Reanudado.")
        else:
            await ctx.send("ℹ️ No hay nada pausado.")

    @commands.command(name="skip", aliases=["saltar"])
    async def skip(self, ctx):
        """Salta la canción actual."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭️ Canción saltada.")
        else:
            await ctx.send("ℹ️ No hay nada que saltar.")

    @commands.command(name="queue", aliases=["q", "cola"])
    async def queue(self, ctx):
        """Muestra la cola de reproducción."""
        guild_id = ctx.guild.id
        embed = discord.Embed(title="🎵 Cola de reproducción", color=discord.Color.purple())
        
        current = self.now_playing.get(guild_id)
        if current:
            embed.add_field(name="Ahora suena", value=f"[{current['title']}]({current['webpage_url']})", inline=False)
        
        q = self.music_queue.get(guild_id, [])
        if not q:
            if not current:
                embed.description = "La cola está vacía."
        else:
            next_up = "".join(f"{i}. [{s['title']}]({s['webpage_url']})\n" for i, s in enumerate(q[:10], 1))
            embed.add_field(name="A continuación", value=next_up, inline=False)
            if len(q) > 10:
                embed.set_footer(text=f"Y {len(q) - 10} más...")
                
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))