# tts_test.py - ejecuta desde REPL dentro del bot, o integra como comando temporal
async def test_play(vc):
    # vc = ctx.voice_client (pasalo desde tu contexto)
    if not vc:
        print("No voice_client.")
        return
    # crea un mp3 muy simple: usa ffmpeg para generar tono (o usa un mp3 existente)
    # Si tienes un mp3 local 'sample.mp3', úsalo. Si no, generar con ffmpeg:
    import subprocess, os
    sample = "test_tone.mp3"
    if not os.path.exists(sample):
        cmd = ["ffmpeg", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-q:a", "9", "-y", sample]
        subprocess.run(cmd, check=True)
    source = discord.FFmpegPCMAudio(sample)
    vc.play(source)
    while vc.is_playing():
        await asyncio.sleep(0.2)
    print("Reproducción finalizada.")
