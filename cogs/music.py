import discord
import asyncio
import functools
import yt_dlp
from discord.ext import commands
from typing import List, Dict, Optional

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -re",
    "options": "-vn -ac 2 -ar 48000",
}
YTDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "nocheckcertificate": True,
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTS)


def _select_best_audio_format(data: dict) -> Optional[str]:
    if "formats" not in data:
        return data.get("url")
    formats = data["formats"]
    audio_formats = [f for f in formats if f.get("acodec") and f.get("acodec") != "none" and f.get("url")]
    if not audio_formats:
        return None
    def score(f):
        abr = f.get("abr") or 0
        br = f.get("tbr") or 0
        return (abr, br)
    audio_formats.sort(key=score, reverse=True)
    return audio_formats[0].get("url")


class Music(commands.Cog, name="🎵 Música"):
    def __init__(self, bot):
        self.bot = bot
        self.queues: Dict[int, List[dict]] = {}
        self.now_playing: Dict[int, dict] = {}

    def ensure_queue(self, guild_id: int):
        if guild_id not in self.queues:
            self.queues[guild_id] = []

    async def _play_next_for_guild(self, guild_id: int):
        queue = self.queues.get(guild_id, [])
        guild = self.bot.get_guild(guild_id)
        if not guild:
            print(f"[music] Guild {guild_id} no encontrada.")
            return

        vc = discord.utils.get(self.bot.voice_clients, guild=guild)

        if not queue or not vc:
            self.now_playing.pop(guild_id, None)
            return

        song = queue.pop(0)
        self.now_playing[guild_id] = song
        stream_url = song.get("stream_url")
        if not stream_url:
            print(f"[music] No se encontró stream_url para {song.get('title')}")
            await asyncio.sleep(0)
            await self._play_next_for_guild(guild_id)
            return

        try:
            if vc.is_playing():
                vc.stop()

            source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)

            def after_play(error):
                if error:
                    print(f"[music] Error en after_play: {error}")
                self.bot.loop.call_soon_threadsafe(asyncio.create_task, self._play_next_for_guild(guild_id))

            vc.play(source, after=after_play)
            print(f"[music] Reproduciendo {song.get('title')} en guild {guild_id}")

            # 👇 CAMBIO: Enviar embed cuando comienza la reproducción
            embed = discord.Embed(
                title="🎶 Reproduciendo ahora",
                description=f"[{song.get('title')}]({song.get('webpage_url')})",
                color=discord.Color.green()
            )
            requester_id = song.get("requested_by")
            requester = guild.get_member(requester_id)
            if requester:
                embed.set_footer(text=f"Solicitado por {requester.display_name}")
            else:
                embed.set_footer(text="Reproducción automática")

            # Buscar canal de texto para enviar el embed
            text_channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
            if text_channels:
                await text_channels[0].send(embed=embed)

        except Exception as e:
            print(f"[music] Excepción al reproducir: {e}")
            await asyncio.sleep(0)
            await self._play_next_for_guild(guild_id)

    # ---------- Comandos ---------- #
    @commands.command(name="join", aliases=["unir"])
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("❌ Debes estar en un canal de voz.")
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"✅ Conectado a **{channel.name}**")

    @commands.command(name="leave", aliases=["salir"])
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.queues.pop(ctx.guild.id, None)
            self.now_playing.pop(ctx.guild.id, None)
            await ctx.send("👋 Desconectado.")
        else:
            await ctx.send("ℹ️ No estoy en un canal de voz.")

    @commands.command(name="play", aliases=["p", "sonar"])
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Debes estar en un canal de voz.")

        if not ctx.voice_client:
            await ctx.invoke(self.join)

        await ctx.send(f"🔎 Buscando: `{query}` ...")
        try:
            loop = self.bot.loop
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{query}", download=False))
            if not data:
                return await ctx.send("❌ Error al buscar.")
            entry = data["entries"][0] if "entries" in data and data["entries"] else data

            stream_url = _select_best_audio_format(entry)
            if not stream_url:
                maybe = await loop.run_in_executor(None, lambda: ytdl.extract_info(entry.get("webpage_url"), download=False))
                stream_url = _select_best_audio_format(maybe) if maybe else None
            if not stream_url:
                return await ctx.send("❌ No pude resolver la URL de audio del resultado.")

            song = {
                "title": entry.get("title"),
                "webpage_url": entry.get("webpage_url"),
                "stream_url": stream_url,
                "requested_by": ctx.author.id,
            }

            self.ensure_queue(ctx.guild.id)
            self.queues[ctx.guild.id].append(song)
            await ctx.send(f"✅ Añadido a la cola: **{song['title']}**")

            vc = ctx.voice_client
            if not vc.is_playing() and not vc.is_paused():
                self.bot.loop.create_task(self._play_next_for_guild(ctx.guild.id))

        except Exception as e:
            await ctx.send(f"❌ Ocurrió un error: {e}")
            print(f"[music] Error en play: {e}")

    @commands.command(name="skip", aliases=["saltar"])
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭️ Saltada.")
        else:
            await ctx.send("ℹ️ No hay nada que saltar.")

    @commands.command(name="queue", aliases=["q", "cola"])
    async def queue_cmd(self, ctx):
        q = self.queues.get(ctx.guild.id, [])
        embed = discord.Embed(title="🎵 Cola", color=discord.Color.blurple())
        now = self.now_playing.get(ctx.guild.id)
        if now:
            embed.add_field(name="Reproduciendo ahora", value=f"[{now.get('title')}]({now.get('webpage_url')})", inline=False)
        if q:
            lista = "\n".join([f"{i+1}. {s.get('title')}" for i, s in enumerate(q[:20])])
            embed.add_field(name="Siguientes", value=lista, inline=False)
        else:
            embed.description = "La cola está vacía."
        await ctx.send(embed=embed)

    @commands.command(name="replay", aliases=["anterior", "volver"])
    async def replay(self, ctx):
        now = self.now_playing.get(ctx.guild.id)
        if not now:
            return await ctx.send("❌ No hay canción actual para repetir.")
        self.ensure_queue(ctx.guild.id)
        self.queues[ctx.guild.id].insert(0, now.copy())
        await ctx.send(f"🔁 Reproduciendo otra vez: **{now.get('title')}**")
        vc = ctx.voice_client
        if not vc.is_playing():
            self.bot.loop.create_task(self._play_next_for_guild(ctx.guild.id))


async def setup(bot):
    await bot.add_cog(Music(bot))
