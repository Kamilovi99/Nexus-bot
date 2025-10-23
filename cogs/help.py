import discord
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help(self, ctx):
        embed = discord.Embed(
            title="Ayuda del Bot",
            description="Aquí tienes una lista de todos los comandos disponibles, organizados por categoría.",
            color=discord.Color.blue()
        )
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        # Iterar sobre los cogs y añadir sus comandos al embed
        for cog_name, cog in self.bot.cogs.items():
            # Ignorar el cog de ayuda para no auto-listarse de forma rara
            if cog_name == "Help":
                continue
            
            commands_list = [f"`!{c.name}`" for c in cog.get_commands() if not c.hidden]
            if commands_list:
                embed.add_field(
                    name=f" {cog.qualified_name}",
                    value='\n'.join(commands_list),
                    inline=False
                )
        
        embed.set_footer(text=f"Usa !<comando> para ejecutar una acción.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
