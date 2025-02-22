
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import random
import string

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_IDS = list(map(int, os.getenv('OWNER_IDS', '').split(',')))

# Initialize bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Data structures
class Shop:
    def __init__(self):
        self.stock = {}  # {item_id: {"name": str, "price": float, "stock": list}}
        self.user_credits = {}  # {user_id: credits}
        self.keys = {}  # {key: credits}
        self.load_data()

    def load_data(self):
        try:
            with open('shop_data.json', 'r') as f:
                data = json.load(f)
                self.stock = data.get('stock', {})
                self.user_credits = data.get('user_credits', {})
                self.keys = data.get('keys', {})
        except FileNotFoundError:
            self.save_data()

    def save_data(self):
        with open('shop_data.json', 'w') as f:
            json.dump({
                'stock': self.stock,
                'user_credits': self.user_credits,
                'keys': self.keys
            }, f, indent=4)

shop = Shop()

# Utility functions
def is_owner(user_id):
    return user_id in OWNER_IDS

def create_embed(title, description, color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="🛍️ Discord Shop System")
    return embed

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    print(f"{bot.user} is ready! 🚀")

@bot.tree.command(name="balance", description="Check your credit balance 💰")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    credits = shop.user_credits.get(user_id, 0)
    embed = create_embed("Balance", f"💳 Your current balance: **{credits}** credits")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stock", description="Check available items in shop 🏪")
async def stock(interaction: discord.Interaction):
    if not shop.stock:
        embed = create_embed("Shop Stock", "❌ No items available in the shop!")
        await interaction.response.send_message(embed=embed)
        return

    embed = create_embed("Shop Stock", "🏪 Available items:")
    for item_id, item in shop.stock.items():
        embed.add_field(
            name=f"ID: {item_id} - {item['name']}",
            value=f"💰 Price: {item['price']} credits\n📦 Stock: {len(item['stock'])} items",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="generatekey", description="Generate redeem keys [Admin Only] 🔑")
async def generatekey(interaction: discord.Interaction, amount: int, credits: int):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ You don't have permission to use this command!")
        return

    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    shop.keys[key] = credits
    shop.save_data()

    embed = create_embed(
        "Key Generated",
        f"🔑 Key: **{key}**\n💰 Credits: **{credits}**"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addstock", description="Add items to shop [Admin Only] 🏪")
@app_commands.describe(
    item_id="The unique ID for the item",
    name="The name of the item",
    price="The price in credits",
    file="The .txt file containing the stock items"
)
async def addstock(interaction: discord.Interaction, item_id: str, name: str, price: float, file: discord.Attachment):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ You don't have permission to use this command!")
        return

    if not file.filename.endswith('.txt'):
        await interaction.response.send_message("❌ Please provide a .txt file!")
        return

    try:
        content = await file.read()
        stock_items = content.decode('utf-8').splitlines()
        
        shop.stock[item_id] = {
            "name": name,
            "price": price,
            "stock": stock_items
        }
        shop.save_data()

        embed = create_embed(
            "Stock Added",
            f"✅ Added {len(stock_items)} items to {name}"
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error processing file: {str(e)}")

@bot.tree.command(name="purchase", description="Purchase items from shop 🛒")
async def purchase(interaction: discord.Interaction, item_id: str, quantity: int = 1):
    user_id = str(interaction.user.id)
    
    if item_id not in shop.stock:
        await interaction.response.send_message("❌ Invalid item ID!")
        return

    item = shop.stock[item_id]
    total_cost = item['price'] * quantity

    if len(item['stock']) < quantity:
        await interaction.response.send_message("❌ Not enough stock available!")
        return

    if shop.user_credits.get(user_id, 0) < total_cost:
        await interaction.response.send_message("❌ Insufficient credits!")
        return

    # Process purchase
    purchased_items = item['stock'][:quantity]
    item['stock'] = item['stock'][quantity:]
    shop.user_credits[user_id] -= total_cost
    shop.save_data()

    # Send items via DM
    user = interaction.user
    items_text = '\n'.join(purchased_items)
    dm_embed = create_embed(
        "Purchase Successful",
        f"🎉 You purchased {quantity}x {item['name']}\n```{items_text}```"
    )
    await user.send(embed=dm_embed)

    # Confirmation in channel
    embed = create_embed(
        "Purchase Successful",
        f"✅ Successfully purchased {quantity}x {item['name']}\nCheck your DMs for the items!"
    )
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
