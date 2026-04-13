import requests
import discord
import datetime
import os
import json
import time
import logging
from dotenv import load_dotenv
load_dotenv()
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

# ========================= CONFIG =========================
LINKS_FILE = 'posted_links.json'
CHANNEL_ID = 1315911622967164960  # Your target channel
SCRAPE_URL = "https://www.warhammer-community.com/en-gb/"

# Set up logging so you can see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Discord setup
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

# Load previously posted links (persistent set)
def load_posted_links():
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, 'r') as f:
                data = json.load(f)
                return set(data)
        except (json.JSONDecodeError, IOError):
            logger.warning("Could not load posted links file, starting a fresh file.")
            return set()
    return set()

def save_posted_links(posted_links):
    try:
        with open(LINKS_FILE, 'w') as f:
            json.dump(list(posted_links), f, indent=2)
    except IOError as e:
        logger.error(f"Failed to save posted links: {e}")

posted_links = load_posted_links()

# Better headers to look more like a real browser (helps avoid blocks)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

@bot.event
async def on_ready():
    logger.info(f'{bot.user} is online and ready!')
    scheduled_scraping.start()

@bot.command(name="scrape")
async def manual_scrape(ctx=None):
    """Manual scrape command: $scrape"""
    logger.info("Manual scrape triggered")
    await scrape_and_post()

async def scrape_and_post():
    """Core scraping logic - called by both manual command and scheduled task"""
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        logger.error("Could not find the target channel!")
        return

    try:
        res = requests.get(SCRAPE_URL, headers=HEADERS, timeout=15)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, 'html.parser')
        # This selector may need updating if the site changes — check it occasionally
        article_links = soup.select('article > div > a')

        if not article_links:
            await channel.send("No new articles found on Warhammer Community at this time.")
            return

        num_to_post = min(7, len(article_links))
        new_posts = 0

        for i in range(num_to_post):
            href = article_links[i].get('href')
            if not href:
                continue

            full_url = "https://www.warhammer-community.com" + href if not href.startswith("http") else href

            if full_url not in posted_links:
                await channel.send(full_url)
                posted_links.add(full_url)
                new_posts += 1
                save_posted_links(posted_links)
                logger.info(f"Posted new link: {full_url}")
                time.sleep(1.5)  # Be polite — small delay between posts
            else:
                logger.debug(f"Skipped duplicate: {full_url}")

        if new_posts == 0:
            logger.info("No new articles this run.")

    except requests.exceptions.RequestException as e:
        error_msg = f"Network error while scraping: {e}"
        logger.error(error_msg)
        if channel:
            await channel.send(error_msg)
    except Exception as e:
        logger.exception("Unexpected error during scrape")
        if channel:
            await channel.send(f"Unexpected error: {str(e)[:200]}")

@tasks.loop(minutes=60)  # Check every hour (cheaper + sufficient)
async def scheduled_scraping():
    now = datetime.datetime.now(datetime.UTC)
    # Run at 7, 12, 19, 22, 23 UTC (adjust if you want different timezone)
    if now.hour in [7, 12, 19, 22, 23] and now.minute < 5:  # Small window to avoid missing exact minute
        logger.info(f"Scheduled scrape starting at {now}")
        await scrape_and_post()

# ========================= RUN BOT =========================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set!")
        raise ValueError("Please set your Discord bot token as an environment variable.")
    bot.run(token)
