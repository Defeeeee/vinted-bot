import datetime
import os
import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
from discord import app_commands

from vinted import fetch_vinted_items

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Load the bot token from environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Initialize the bot with intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent if needed

class MyBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="!", intents=intents)
        # Removed redundant self.tree initialization

    async def setup_hook(self):
        guild = discord.Object(id=868582958729150504)
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

bot = MyBot(intents=intents)

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logging.info('------')

@bot.tree.command(name='sync', description='Owner only')
async def sync(Interaction: discord.Interaction):
    if Interaction.user.id == 333215596944818177:
        await bot.tree.sync()
        await Interaction.response.send_message('Command tree synced.')
    else:
        await Interaction.response.send_message('You must be the owner to use this command!')

@bot.tree.command(description="añade el monitoreo del link deseado")
@app_commands.describe(link="Link to monitor")
async def add(Interaction: discord.Interaction, link: str):
    if not link.startswith("https://www.vinted.es/"):
        await Interaction.response.send_message("El link no es de Vinted")
        return

    # defer the response to give time for processing
    await Interaction.response.defer(thinking=True)
    # Fetch items from the provided link
    items = await fetch_vinted_items(link)  # Await the coroutine

    if not items:
        await Interaction.followup.send("No se encontraron artículos en el enlace proporcionado.")
        return

    # Process and send the items to the user
    for item in items:
        embed = discord.Embed(
            color=discord.Color.blue()
        )
        embed.set_image(url=item['thumbnail'])
        embed.set_footer(text=item['price'])
        embed.set_author(name=item['description'],url=item['url'])
        # spanish tz
        embed.timestamp = datetime.datetime.now()
        await Interaction.followup.send(embed=embed)

    await Interaction.followup.send("Los artículos han sido enviados a tu DM.")
# Run the bot
try:
    bot.run(TOKEN)
except Exception as e:
    logging.error('Error when running the bot', exc_info=True)

