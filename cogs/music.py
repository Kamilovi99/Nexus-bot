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
        self.loop_song: Dict[int, bool] = {}
        self.loop_queue: Dict[int, bool] = {}
        self.played_history: Dict[int, List[dict]] = {}

    def ensure_queue(self, guild_id: int):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        if guild_id not in self.played_history:
            self.played_history[guild_id] = []

    async def _play_next_for_guild(self, guild_id: int):
        queue = self.queues.get(guild_id, [])
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        vc = discord.utils.get(self.bot.voice_clients, guild=guild)

        if not vc:
            return

        if self.loop_song.get(guild_id) and guild_id in self.now_playing:
            song = self.now_playing[guild_id]
        else:
            if not queue:
                if self.loop_queue.get(guild_id) and self.played_history[guild_id]:
                    queue.extend(self.played_history[guild_id])
                    self.played_history[guild_id].clear()
                else:
                    self.now_playing.pop(guild_id, None)
                    return
            song = queue.pop(0)

        self.now_playing[guild_id] = song
        self.played_history[guild_id].append(song)

        stream_url = song.get("stream_url")
        if not stream_url:
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

            embed = discord.Embed(
                title="🎶 Reproduciendo ahora",
                description=f"[{song.get('title')}]({song.get('webpage_url')})",
                color=discord.Color.green()
            )
            requester_id = song.get("requested_by")
            requester = guild.get_member(requester_id)
            if requester:
                embed.set_footer(text=f"Solicitado por {requester.display_name}")

            text_channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
            if text_channels:
                await text_channels[0].send(embed=embed)

        except Exception as e:
            print(f"[music] Excepción al reproducir: {e}")
            await asyncio.sleep(0)
            await self._play_next_for_guild(guild_id)
            
    # ------------- Comandos ------------- #
    # --- Hacer de que el bot se una y salga del canal de voz --- #
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

    # --- Saltar a la siguiente canción --- #
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

    # ⏭️ --- Saltar a la siguiente canción --- #
    @commands.command(name="skip", aliases=["saltar"])
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭️ Saltada.")
        else:
            await ctx.send("ℹ️ No hay nada que saltar.")

    # 🔂 --- Hacer de que la reproducción se repita en bucle --- #
    @commands.command(name="loop", aliases=["bucle"])
    async def loop_cmd(self, ctx):
        gid = ctx.guild.id
        state = self.loop_song.get(gid, False)
        self.loop_song[gid] = not state
        msg = "🔂 Bucle de **canción actual** activado." if not state else "🚫 Bucle de canción desactivado."
        await ctx.send(msg)

    # 🔂 --- Hacer de que la lista se repita en bucle --- #
    @commands.command(name="loopqueue", aliases=["buclecola"])
    async def loop_queue_cmd(self, ctx):
        gid = ctx.guild.id
        state = self.loop_queue.get(gid, False)
        self.loop_queue[gid] = not state
        msg = "🔁 Bucle de **cola completa** activado." if not state else "🚫 Bucle de cola desactivado."
        await ctx.send(msg)

    # 🔄️ --- Reiniciar la canción actual --- #
    @commands.command(name="replay", aliases=["reiniciar"])
    async def restart(self, ctx):
        gid = ctx.guild.id
        song = self.now_playing.get(gid)
        if not song:
            return await ctx.send("❌ No hay canción actual.")
        self.queues[gid].insert(0, song)
        ctx.voice_client.stop()
        await ctx.send(f"🔁 Reiniciando: **{song['title']}**")
        
    # ⏮️ --- Volver a la anterior canción --- #
    @commands.command(name="previous", aliases=["anterior"])
    async def previous_cmd(self, ctx):
        gid = ctx.guild.id
        history = self.played_history.get(gid, [])
        if len(history) < 2:
            return await ctx.send("⚠️ No hay una canción anterior para reproducir.")
        prev_song = history[-2]
        history.pop()
        self.queues[gid].insert(0, prev_song.copy())
        ctx.voice_client.stop()
        await ctx.send(f"⏮️ Reproduciendo la canción anterior: **{prev_song['title']}**")

    # --- ⏸️ Pausar canción actual --- #
    @commands.command(name="pause", aliases=["pausar"])
    async def pause_cmd(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            return await ctx.send("⚠️ No hay ninguna canción reproduciéndose.")
        vc.pause()
        await ctx.send("⏸️ Reproducción pausada.")

    # --- ▶️ Reanudar canción pausada --- #
    @commands.command(name="resume", aliases=["reanudar"])
    async def resume_cmd(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_paused():
            return await ctx.send("⚠️ No hay ninguna canción pausada.")
        vc.resume()
        await ctx.send("▶️ Reproducción reanudada.")

    # --- Ver la lista de reproducción --- #
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

    # ⏹️ --- Detener todo la reproducción --- #
    @commands.command(name="stop", aliases=["detener"])
    async def stop_cmd(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("⚠️ No estoy conectado a ningún canal de voz.")
        if vc.is_playing():
            vc.stop()

        gid = ctx.guild.id
        self.queues[gid] = []
        self.played_history[gid] = []
        self.now_playing.pop(gid, None)
        self.loop_song[gid] = False
        self.loop_queue[gid] = False

        await ctx.send("⏹️ Se detuvo la reproducción y se limpió la cola por completo.")

async def setup(bot):
    await bot.add_cog(Music(bot))
