import requests, discord, datetime, os, json
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix="$", intents=intents)

# File to store posted links
LINKS_FILE = 'posted_links.json'

# Load poasted links from file
def load_posted_links():
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, 'r') as file:
            try:
                return set(json.load(file))
            except json.JSONDecodeError:
                return set()
    else:
        return set()
    
# Save posted links to file
def save_posted_links(posted_links):
    with open(LINKS_FILE, 'w') as file:
        json.dump(list(posted_links), file)

# Set to store previous links
posted_links = load_posted_links()

@bot.event
async def on_ready():
    print(f'{bot.user} is ready to serve.')
    scheduled_scraping.start()

@bot.command()
async def scrape(ctx=None):
    print("Scraping...")
    try:
        channel = bot.get_channel(1006323059231313973)

        res = requests.get("https://www.warhammer-community.com/en-gb/")
        res.raise_for_status()

        soup = BeautifulSoup(res.text, 'html.parser')
        article_links = soup.select('article > div > a')

        numOpen = min(7, len(article_links))
        if numOpen == 0:
            await channel.send("No articles found.")
        else:
            for i in range(numOpen):
                urlToOpen = "https://www.warhammer-community.com" + article_links[i].get('href')
                if urlToOpen not in posted_links:
                    await channel.send(urlToOpen)
                    posted_links.add(urlToOpen)
                    save_posted_links(posted_links)
                else:
                    print(f"Duplicate link: {urlToOpen}")
                
    except requests.exceptions.RequestException as e:
        await channel.send(f"Error occurred while scraping: {e}")

@tasks.loop(minutes=1)
async def scheduled_scraping():
    now = datetime.datetime.now()
    if now.minute == 0 and now.hour in [7, 12, 19, 22, 23]:
        await scrape(None)

bot.run('TOKEN')
