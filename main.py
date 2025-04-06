import datetime
import os
import discord
from discord.ext import commands, tasks
import logging

from dotenv import load_dotenv
from discord import app_commands
import csv
import time

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

# Define the path for the trackers CSV file
TRACKERS_FILE = "trackers.csv"

class MyBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="!", intents=intents)
        self.trackers = []  # List to store active trackers
        
    async def setup_hook(self):
        guild = discord.Object(id=868582958729150504)
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        # Load existing trackers from CSV
        self.load_trackers()
        # Start the check_trackers task
        self.check_trackers.start()

    def load_trackers(self):
        """Load trackers from the CSV file"""
        if not os.path.exists(TRACKERS_FILE):
            # Create the file with headers if it doesn't exist
            with open(TRACKERS_FILE, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['link', 'channel_id', 'last_check_time', 'last_item_ids'])
            return
            
        with open(TRACKERS_FILE, 'r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Convert last_item_ids from string to list
                if row['last_item_ids']:
                    last_item_ids = row['last_item_ids'].split('|')
                else:
                    last_item_ids = []
                    
                self.trackers.append({
                    'link': row['link'],
                    'channel_id': int(row['channel_id']),
                    'last_check_time': float(row['last_check_time']),
                    'last_item_ids': last_item_ids
                })
            logging.info(f"Loaded {len(self.trackers)} trackers from {TRACKERS_FILE}")
    
    def save_trackers(self):
        """Save trackers to the CSV file"""
        with open(TRACKERS_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['link', 'channel_id', 'last_check_time', 'last_item_ids'])
            
            for tracker in self.trackers:
                # Convert list of last_item_ids to pipe-separated string
                last_item_ids_str = '|'.join(tracker['last_item_ids'])
                
                writer.writerow([
                    tracker['link'],
                    tracker['channel_id'],
                    tracker['last_check_time'],
                    last_item_ids_str
                ])
            logging.info(f"Saved {len(self.trackers)} trackers to {TRACKERS_FILE}")

    @tasks.loop(seconds=30)
    async def check_trackers(self):
        """Check all trackers for new items every 30 seconds"""
        logging.info("Checking trackers for updates...")
        
        for tracker in self.trackers:
            try:
                channel = self.get_channel(tracker['channel_id'])
                if not channel:
                    logging.warning(f"Channel {tracker['channel_id']} not found for tracker {tracker['link']}")
                    continue
                    
                # Fetch items from the tracked link
                items = await fetch_vinted_items(tracker['link'])
                items = items[:5]  # Only check the first 5 items
                
                if not items:
                    logging.warning(f"No items found for link: {tracker['link']}")
                    continue
                    
                # Update the last check time
                current_time = time.time()
                
                # Get item IDs from URLs to compare
                new_items = []
                current_item_ids = []
                
                for item in items:
                    # Extract item ID from URL
                    item_id = item['url'].split('/')[-1].split('?')[0]
                    current_item_ids.append(item_id)
                    
                    # If this is a new item (not in last_item_ids)
                    if item_id not in tracker['last_item_ids']:
                        new_items.append(item)
                
                # Send new items to the channel
                for item in new_items:
                    embed = discord.Embed(color=discord.Color.blue())
                    embed.set_image(url=item['thumbnail'])
                    embed.set_footer(text=item['price'])
                    embed.set_author(name=item['description'], url=item['url'])
                    embed.timestamp = datetime.datetime.now()
                    await channel.send(embed=embed)
                    logging.info(f"Sent new item to channel {tracker['channel_id']}")
                
                # Update the tracker with new information
                tracker['last_check_time'] = current_time
                tracker['last_item_ids'] = current_item_ids
                
            except Exception as e:
                logging.error(f"Error checking tracker {tracker['link']}: {e}", exc_info=True)
        
        # Save updated trackers to CSV
        self.save_trackers()

    @check_trackers.before_loop
    async def before_check_trackers(self):
        """Wait until the bot is ready before starting the tracker loop"""
        await self.wait_until_ready()

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
    """Add a new tracker for the specified Vinted link in the current channel"""
    if not link.startswith("https://www.vinted.es/"):
        await Interaction.response.send_message("El link no es de Vinted")
        return

    if "order" in link:
        link = link.replace("order=relevance", "order_by=newest_first")
        link = link.replace("order=price_low_to_high", "order_by=newest_first")
        link = link.replace("order=price_high_to_low", "order_by=newest_first")
    else:
        link += "&order_by=newest_first"
    
    channel_id = Interaction.channel_id
    
    # Check if tracker for this link and channel already exists
    for tracker in bot.trackers:
        if tracker['link'] == link and tracker['channel_id'] == channel_id:
            await Interaction.response.send_message("Ya existe un tracker para este link en este canal.")
            return

    await Interaction.response.defer(thinking=True)

    # Fetch items from the link
    items = await fetch_vinted_items(link)
    item_ids = []
    for item in items:
        item_id = item['url'].split('/')[-1].split('?')[0]
        item_ids.append(item_id)

    # Create a new tracker
    new_tracker = {
        'link': link,
        'channel_id': channel_id,
        'last_check_time': time.time(),
        'last_item_ids': item_ids
    }
    
    # Add to trackers list
    bot.trackers.append(new_tracker)
    
    # Save updated trackers to CSV
    bot.save_trackers()
    
    await Interaction.followup.send("Tracker creado con éxito. El bot monitoreará nuevos artículos en este canal cada 30 segundos.")

@bot.tree.command(description="Elimina un tracker existente en este canal")
@app_commands.describe(link="Link del tracker a eliminar")
async def remove(Interaction: discord.Interaction, link: str = None):
    """Remove a tracker from the current channel"""
    channel_id = Interaction.channel_id
    
    # If link is provided, remove that specific tracker
    if link:
        removed = False
        for i, tracker in enumerate(bot.trackers):
            if tracker['link'] == link and tracker['channel_id'] == channel_id:
                bot.trackers.pop(i)
                removed = True
                break
                
        if removed:
            bot.save_trackers()
            await Interaction.response.send_message(f"Tracker para `{link}` eliminado.")
        else:
            await Interaction.response.send_message(f"No se encontró un tracker para `{link}` en este canal.")
        return
        
    # If no link is provided, show list of trackers in this channel
    channel_trackers = [t for t in bot.trackers if t['channel_id'] == channel_id]
    
    if not channel_trackers:
        await Interaction.response.send_message("No hay trackers activos en este canal.")
        return
        
    tracker_list = "\n".join([f"{i+1}. `{t['link']}`" for i, t in enumerate(channel_trackers)])
    await Interaction.response.send_message(f"Trackers activos en este canal:\n{tracker_list}\n\nUsa `/remove [link]` para eliminar un tracker específico.")

@bot.tree.command(description="Muestra los trackers activos en este canal")
async def list(Interaction: discord.Interaction):
    """List all active trackers in the current channel"""
    channel_id = Interaction.channel_id
    
    # Find trackers for this channel
    channel_trackers = [t for t in bot.trackers if t['channel_id'] == channel_id]
    
    if not channel_trackers:
        await Interaction.response.send_message("No hay trackers activos en este canal.")
        return
        
    tracker_list = "\n".join([f"{i+1}. `{t['link']}`" for i, t in enumerate(channel_trackers)])
    await Interaction.response.send_message(f"Trackers activos en este canal:\n{tracker_list}")

# muestra todos los trackers del servidor
@bot.tree.command(description="Muestra todos los trackers activos en el servidor")
async def list_all(Interaction: discord.Interaction):
    """List all active trackers in the server"""
    # Find trackers for this server
    server_trackers = [t for t in bot.trackers if t['channel_id'] != 0]

    if not server_trackers:
        await Interaction.response.send_message("No hay trackers activos en el servidor.")
        return

    # Create a list with tracker info including channel mentions
    formatted_trackers = []
    for i, tracker in enumerate(server_trackers):
        channel = bot.get_channel(tracker['channel_id'])
        # Use channel mention format <#channel_id> to create clickable links
        channel_mention = f"<#{tracker['channel_id']}>" if channel else f"Canal desconocido (ID: {tracker['channel_id']})"
        formatted_trackers.append(f"{i+1}. `{tracker['link']}` en {channel_mention}")

    tracker_list = "\n".join(formatted_trackers)
    await Interaction.response.send_message(f"Trackers activos en el servidor:\n{tracker_list}")

# Run the bot
try:
    bot.run(TOKEN)
except Exception as e:
    logging.error('Error when running the bot', exc_info=True)

