import discord, os, asyncio
print(f"Usando discord.py versión: {discord.__version__}")
from dotenv import load_dotenv
from discord.ext import commands

async def main():
    load_dotenv()
    token = os.getenv("dt")

    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    intents.reactions = True

    bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

    @bot.event
    async def on_ready():
        print(f'Bot conectado como {bot.user} (ID: {bot.user.id})')
        print('------')

    # Cargar todos los cogs de la carpeta /cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"Cog cargado: {filename}")
            except Exception as e:
                print(f"Error al cargar el cog {filename}: {e}")

    print(f"Token loaded: {token}")
    await bot.start(token)

try:
    if __name__ == "__main__":
        asyncio.run(main())
        
except KeyboardInterrupt:
    print("\n🛑 Bot detenido manualmente desde VS Code.")
