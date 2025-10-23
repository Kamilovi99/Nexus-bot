import discord
import os
import requests
import feedparser
import google.generativeai as genai
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from discord.ext import commands, tasks

class Tools(commands.Cog, name="🤖 IA (Gratis) y Herramientas"):
    """Herramientas de IA de Google, noticias, GitHub y RSS."""
    def __init__(self, bot):
        self.bot = bot
        self.genai_model = None
        if os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.genai_model = genai.GenerativeModel('models/gemini-pro-latest')
        
        self.feeds_file = "feeds.json"
        self.check_rss_feeds.start()

    def cog_unload(self):
        self.check_rss_feeds.cancel()

    # --- RSS Helper Functions ---
    def _load_feeds(self):
        try:
            with open(self.feeds_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_feeds(self, feeds_data):
        with open(self.feeds_file, 'w') as f:
            json.dump(feeds_data, f, indent=4)

    async def _discover_feed(self, url: str):
        """Intenta descubrir la URL de un feed RSS desde una URL base."""
        print(f"[DEBUG RSS] Intentando descubrir feed para: {url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
            }
            response = await self.bot.loop.run_in_executor(None, lambda: requests.get(url, timeout=10, headers=headers))
            response.raise_for_status()
            print(f"[DEBUG RSS] Status code para {url}: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            print(f"[DEBUG RSS] Links encontrados en head para {url}: {soup.find_all('link', rel='alternate')}")

            link_tag = soup.find("link", {"rel": "alternate", "type": "application/rss+xml"})
            if link_tag and link_tag.get('href'):
                discovered_url = urljoin(url, link_tag['href'])
                print(f"[DEBUG RSS] Encontrado link RSS en HTML: {discovered_url}")
                return discovered_url
            
            link_tag = soup.find("link", {"rel": "alternate", "type": "application/atom+xml"})
            if link_tag and link_tag.get('href'):
                discovered_url = urljoin(url, link_tag['href'])
                print(f"[DEBUG RSS] Encontrado link Atom en HTML: {discovered_url}")
                return discovered_url

            print(f"[DEBUG RSS] No se encontró link RSS/Atom en HTML para {url}. Intentando rutas comunes.")
            common_paths = ['/feed', '/rss', '/feed.xml', '/rss.xml']
            for path in common_paths:
                guess_url = urljoin(url, path)
                print(f"[DEBUG RSS] Intentando ruta común: {guess_url}")
                try:
                    head_res = await self.bot.loop.run_in_executor(None, lambda: requests.head(guess_url, timeout=5))
                    print(f"[DEBUG RSS] Status code para ruta común {guess_url}: {head_res.status_code}")
                    if head_res.status_code == 200:
                        parsed = feedparser.parse(guess_url)
                        print(f"[DEBUG RSS] Bozo status para {guess_url}: {parsed.bozo}")
                        if not parsed.bozo:
                            return guess_url
                except requests.RequestException:
                    print(f"[DEBUG RSS] Error al acceder a ruta común {guess_url}")
                    continue
            
            print(f"[DEBUG RSS] No se encontró feed para {url} después de todos los intentos.")
            return None
        except requests.RequestException as e:
            print(f"[DEBUG RSS] Error de RequestException para {url}: {e}")
            return None

    # --- Background Task for RSS ---
    @tasks.loop(minutes=15)
    async def check_rss_feeds(self):
        feeds_data = self._load_feeds()
        if not feeds_data:
            return

        for guild_id, feeds in feeds_data.items():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue

            for i, feed_info in enumerate(feeds):
                url = feed_info['url']
                last_guid = feed_info.get('last_guid')
                channel_id = feed_info['channel_id']
                channel = guild.get_channel(channel_id)
                if not channel:
                    continue

                try:
                    parsed_feed = feedparser.parse(url)
                    if not parsed_feed.entries:
                        continue

                    latest_entry = parsed_feed.entries[0]
                    latest_guid = latest_entry.get("id") or latest_entry.get("link")

                    if latest_guid != last_guid:
                        feeds_data[guild_id][i]['last_guid'] = latest_guid
                        embed = discord.Embed(title=f"Nueva entrada en {parsed_feed.feed.title}", description=latest_entry.title, url=latest_entry.link, color=discord.Color.orange())
                        if 'summary' in latest_entry:
                            summary = BeautifulSoup(latest_entry.summary, 'html.parser').get_text()
                            embed.add_field(name="Resumen", value=summary[:1020] + "...", inline=False)
                        await channel.send(embed=embed)
                except Exception as e:
                    print(f"Error procesando el feed {url}: {e}")
        self._save_feeds(feeds_data)

    @check_rss_feeds.before_loop
    async def before_check_rss_feeds(self):
        await self.bot.wait_until_ready()

    # --- RSS Commands ---
    @commands.group(name="rss", invoke_without_command=True)
    async def rss(self, ctx):
        await ctx.send("Comando inválido. Usa `@rss agregar <url> <#canal>`, `@rss listar` o `@rss quitar <url>`.")

    @rss.command(name="agregar")
    async def rss_agregar(self, ctx, url: str, canal: discord.TextChannel):
        await ctx.typing()
        
        feed_url = await self._discover_feed(url)
        
        if not feed_url:
            parsed_check = feedparser.parse(url)
            if not parsed_check.bozo:
                feed_url = url
            else:
                return await ctx.send("❌ No pude encontrar un feed RSS válido en esa URL. Intenta encontrar la URL específica del feed manualmente.")

        parsed_feed = feedparser.parse(feed_url)
        if parsed_feed.bozo:
            return await ctx.send(f"❌ La URL encontrada (`{feed_url}`) no parece ser un feed RSS válido.")

        feeds_data = self._load_feeds()
        guild_id = str(ctx.guild.id)
        if guild_id not in feeds_data:
            feeds_data[guild_id] = []

        if any(f['url'] == feed_url for f in feeds_data[guild_id]):
            return await ctx.send(f"❌ Este feed (`{feed_url}`) ya está siendo vigilado.")

        latest_guid = parsed_feed.entries[0].get("id") or parsed_feed.entries[0].get("link") if parsed_feed.entries else None

        feeds_data[guild_id].append({'url': feed_url, 'channel_id': canal.id, 'last_guid': latest_guid})
        self._save_feeds(feeds_data)
        
        await ctx.send(f"✅ Feed añadido (`{feed_url}`). Las nuevas publicaciones de **{parsed_feed.feed.title}** se anunciarán en {canal.mention}.")

        if parsed_feed.entries:
            try:
                latest_entry = parsed_feed.entries[0]
                embed = discord.Embed(title=f"¡Feed Añadido! Última entrada:", description=latest_entry.title, url=latest_entry.link, color=discord.Color.green())
                embed.set_footer(text=f"Feed: {parsed_feed.feed.title}")
                await canal.send(embed=embed)
            except Exception as e:
                await ctx.send(f"⚠️ No pude publicar la entrada de confirmación en {canal.mention}. Error: {e}")

    @rss.command(name="listar")
    async def rss_listar(self, ctx):
        feeds_data = self._load_feeds()
        guild_id = str(ctx.guild.id)
        if guild_id not in feeds_data or not feeds_data[guild_id]:
            return await ctx.send("ℹ️ No se está vigilando ningún feed RSS en este servidor.")
        embed = discord.Embed(title="Feeds RSS Vigilados", color=discord.Color.blue())
        for feed_info in feeds_data[guild_id]:
            channel = ctx.guild.get_channel(feed_info['channel_id'])
            embed.add_field(name=feed_info['url'], value=f"Publicando en: {channel.mention if channel else 'Canal no encontrado'}", inline=False)
        await ctx.send(embed=embed)

    @rss.command(name="quitar")
    async def rss_quitar(self, ctx, url: str):
        feeds_data = self._load_feeds()
        guild_id = str(ctx.guild.id)
        if guild_id not in feeds_data:
            return await ctx.send("❌ No se está vigilando ese feed.")
        feed_a_quitar = None
        for feed in feeds_data[guild_id]:
            if feed['url'] == url:
                feed_a_quitar = feed
                break
        if feed_a_quitar:
            feeds_data[guild_id].remove(feed_a_quitar)
            self._save_feeds(feeds_data)
            await ctx.send(f"✅ Feed `{url}` eliminado.")
        else:
            await ctx.send("❌ No se encontró ese feed en la lista.")

    @rss.command(name="forzar")
    async def rss_forzar(self, ctx):
        await ctx.send("⚙️ Forzando la revisión de todos los feeds RSS...")
        await self.check_rss_feeds()
        await ctx.send("✅ Revisión completada.")

    # --- Other Commands ---
    @commands.command(name="pregunta", aliases=["ask"])
    async def pregunta(self, ctx, *, pregunta: str):
        if not self.genai_model:
            return await ctx.send("❌ La API Key de Gemini no está configurada en el archivo .env (GEMINI_API_KEY).")
        await ctx.typing()
        try:
            response = self.genai_model.generate_content(pregunta)
            respuesta_texto = response.text
            if len(respuesta_texto) <= 2000:
                await ctx.send(respuesta_texto)
            else:
                partes = [respuesta_texto[i:i+1990] for i in range(0, len(respuesta_texto), 1990)]
                for parte in partes:
                    await ctx.send(parte)
        except Exception as e:
            await ctx.send(f"❌ Ocurrió un error con la API de Gemini: {e}")

    @commands.command(name="noticias")
    async def noticias(self, ctx, pais: str = "co"):
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            return await ctx.send("❌ La API Key de NewsAPI no está configurada en el archivo .env (NEWS_API_KEY).")
        url = f"https://newsapi.org/v2/everything?q={pais}&sortBy=publishedAt&language=es&apiKey={api_key}"
        try:
            response = requests.get(url)
            data = response.json()
            if data["status"] != "ok":
                return await ctx.send("❌ No se pudieron obtener las noticias.")
            embed = discord.Embed(title=f"📰 Últimas Noticias de '{pais.upper()}'", color=discord.Color.blue())
            for article in data["articles"][:5]:
                embed.add_field(name=article['title'], value=f"{article['description'] or 'Sin descripción'}\n[Leer más]({article['url']})", inline=False)
            await ctx.send(embed=embed)
        except requests.RequestException as e:
            await ctx.send(f"❌ Error al conectar con NewsAPI: {e}")

    @commands.command(name="github")
    async def github(self, ctx, repo: str):
        url = f"https://api.github.com/repos/{repo}"
        try:
            response = requests.get(url)
            if response.status_code != 200:
                return await ctx.send(f"❌ No se encontró el repositorio o la API de GitHub falló (código: {response.status_code}).")
            data = response.json()
            embed = discord.Embed(title=f"📦 {data['full_name']}", url=data['html_url'], color=discord.Color.dark_grey())
            embed.set_thumbnail(url=data['owner']['avatar_url'])
            embed.description = data['description']
            embed.add_field(name="⭐ Estrellas", value=data['stargazers_count'])
            embed.add_field(name="🍴 Forks", value=data['forks_count'])
            embed.add_field(name="👀 Watchers", value=data['subscribers_count'])
            embed.add_field(name="📜 Licencia", value=data.get('license', {}).get('name', 'No especificada'))
            embed.add_field(name=" idioma", value=data['language'])
            await ctx.send(embed=embed)
        except requests.RequestException as e:
            await ctx.send(f"❌ Error al conectar con GitHub API: {e}")

async def setup(bot):
    await bot.add_cog(Tools(bot))