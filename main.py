import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import random
import string
import io
import asyncio
<<<<<<< HEAD

=======
>>>>>>> 5dff67b77daf687b4aa0ce6c074c96bae178f3f2
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
        self.purchases = {}  # {purchase_id: {"user_id": str, "items": list, "item_id": str, "quantity": int, "timestamp": str}}
        self.load_data()

    def load_data(self):
        try:
            with open('shop_data.json', 'r') as f:
                data = json.load(f)
                self.stock = data.get('stock', {})
                self.user_credits = data.get('user_credits', {})
                self.keys = data.get('keys', {})
                self.purchases = data.get('purchases', {})
        except FileNotFoundError:
            self.save_data()

    def save_data(self):
        with open('shop_data.json', 'w') as f:
            json.dump({
                'stock': self.stock,
                'user_credits': self.user_credits,
                'keys': self.keys,
                'purchases': self.purchases
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
        await bot.tree.sync(guild=None)  # Force global sync
        print("Successfully synced commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")
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
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return

    generated_keys = []
    for _ in range(amount):
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        shop.keys[key] = credits
        generated_keys.append(key)

    shop.save_data()

    await interaction.response.send_message("✅ Keys generated! Check your DMs.", ephemeral=True)

    if amount == 1:
        keys_text = "\n".join([f"🔑 **{key}** - 💰 {credits} credits" for key in generated_keys])
        embed = create_embed("Keys Generated", f"Generated {amount} key:\n{keys_text}")
        await interaction.user.send(embed=embed)
    else:
        keys_text = "\n".join([f"{key} - {credits} credits" for key in generated_keys])
        buffer = io.StringIO(keys_text)
        file = discord.File(fp=buffer, filename=f"generated_keys_{amount}.txt")
        embed = create_embed("Keys Generated", f"✅ Generated {amount} keys!\nCheck the attached file.")
        await interaction.user.send(embed=embed, file=file)

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

        if item_id in shop.stock:
            shop.stock[item_id]["stock"].extend(stock_items)
            total_stock = len(shop.stock[item_id]["stock"])
            embed = create_embed(
                "✅ Stock Updated",
                f"**Item Details:**\n🏷️ Name: `{name}`\n🔑 ID: `{item_id}`\n💰 Price: `{shop.stock[item_id]['price']} credits`\n📦 Added Items: `{len(stock_items)}`\n📊 Total Stock: `{total_stock}`"
            )
        else:
            shop.stock[item_id] = {"name": name, "price": price, "stock": stock_items}
            embed = create_embed(
                "✅ New Item Added",
                f"**Item Details:**\n🏷️ Name: `{name}`\n🔑 ID: `{item_id}`\n💰 Price: `{price} credits`\n📦 Initial Stock: `{len(stock_items)}`"
            )

        shop.save_data()
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error processing file: {str(e)}")

@bot.tree.command(name="redeem", description="Redeem a key for credits 🎁")
async def redeem(interaction: discord.Interaction, key: str):
    user_id = str(interaction.user.id)

    if key not in shop.keys:
        await interaction.response.send_message("❌ Invalid or already used key!")
        return

    credits = shop.keys[key]
    shop.user_credits[user_id] = shop.user_credits.get(user_id, 0) + credits
    del shop.keys[key]
    shop.save_data()

    embed = create_embed("Key Redeemed", f"✅ Successfully redeemed **{credits}** credits!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="replace", description="Replace items in a ticket [Admin Only, Ticket Channel Only]")
@app_commands.describe(quantity="Number of replacement items (optional, defaults to original purchase quantity)")
async def replace(interaction: discord.Interaction, quantity: int = None):
    # Check if user is an owner
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return

    # Check if command is run in a ticket channel
    if not interaction.channel.name.startswith(("support-", "replacement-", "purchase-")):
        await interaction.response.send_message("❌ This command can only be used in a ticket channel!", ephemeral=True)
        return

    # Check if it's a replacement ticket
    if not interaction.channel.name.startswith("replacement-"):
        await interaction.response.send_message("❌ This command can only be used in replacement tickets!", ephemeral=True)
        return

    # Get purchase_id from the ticket embed
    async for message in interaction.channel.history(limit=10):  # Look at recent messages
        if message.embeds and "Purchase ID: " in message.embeds[0].description:
            purchase_id_line = next((line for line in message.embeds[0].description.split('\n') if "Purchase ID: " in line), None)
            if purchase_id_line:
                purchase_id = purchase_id_line.split('`')[1]  # Extract between backticks
                break
    else:
        await interaction.response.send_message("❌ Could not find Purchase ID in this ticket!", ephemeral=True)
        return

    # Validate purchase_id
    if purchase_id not in shop.purchases:
        await interaction.response.send_message("❌ Invalid Purchase ID found in ticket!", ephemeral=True)
        return

    purchase = shop.purchases[purchase_id]
    item_id = purchase["item_id"]

    # Determine quantity (use original if not specified)
    replacement_quantity = quantity if quantity is not None else purchase["quantity"]
    if replacement_quantity < 1:
        await interaction.response.send_message("❌ Quantity must be at least 1!", ephemeral=True)
        return

    if item_id not in shop.stock or len(shop.stock[item_id]["stock"]) < replacement_quantity:
        await interaction.response.send_message("❌ Not enough stock available for replacement!", ephemeral=True)
        return

    # Get user ID from channel topic
    topic = interaction.channel.topic
    if not topic or "User ID: " not in topic:
        await interaction.response.send_message("❌ Could not identify user from ticket topic!", ephemeral=True)
        return
    try:
        user_id_str = topic.split("User ID: ")[1].split()[0]
        user_id = int(user_id_str)
        user = await bot.fetch_user(user_id)
    except (IndexError, ValueError, discord.errors.NotFound):
        await interaction.response.send_message("❌ Invalid or unfindable user ID in ticket topic!", ephemeral=True)
        return

    # Process replacement
    replacement_items = shop.stock[item_id]["stock"][:replacement_quantity]
    shop.stock[item_id]["stock"] = shop.stock[item_id]["stock"][replacement_quantity:]
    shop.save_data()

    # Send replacement items via DM
    if replacement_quantity == 1:
        item_parts = replacement_items[0].split(':')
        if len(item_parts) == 2:
            email, password = item_parts
            dm_embed = create_embed(
                "Replacement Received",
                f"🔄 Replacement for Purchase ID: `{purchase_id}`\n🏷️ Item: {shop.stock[item_id]['name']}\n\n📧 Email: ```{email}```\n🔑 Password: ```{password}```\n📝 Combo: ```{email}:{password}```"
            )
        else:
            dm_embed = create_embed(
                "Replacement Received",
                f"🔄 Replacement for Purchase ID: `{purchase_id}`\n🏷️ Item: {shop.stock[item_id]['name']}\n```{replacement_items[0]}```"
            )
        await user.send(embed=dm_embed)
    else:
        buffer = io.StringIO('\n'.join(replacement_items))
        file = discord.File(fp=buffer, filename=f"{shop.stock[item_id]['name']}_replacement_{purchase_id}.txt")
        dm_embed = create_embed(
            "Replacement Received",
            f"🔄 Replacement for Purchase ID: `{purchase_id}`\n🏷️ Item: {shop.stock[item_id]['name']}\n📏 Quantity: {replacement_quantity}\nCheck the attached file for your replacement items!"
        )
        await user.send(embed=dm_embed, file=file)

    # Notify in ticket channel and close it
    embed = create_embed(
        "Replacement Processed",
        f"✅ Sent {replacement_quantity}x {shop.stock[item_id]['name']} as replacement for Purchase ID: `{purchase_id}` to {user.mention}'s DMs.\nTicket will close in 5 seconds..."
    )
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(5)
    await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketSelect())

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General Support", value="support", description="Get help with general issues", emoji="❓"),
            discord.SelectOption(label="Item Replacement", value="replacement", description="Request replacement for invalid items", emoji="🔄"),
            discord.SelectOption(label="Purchase Issue", value="purchase", description="Report issues with purchases", emoji="🛒")
        ]
        super().__init__(placeholder="Select ticket type", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        class TicketModal(discord.ui.Modal):
            def __init__(self, ticket_type):
                super().__init__(title=f"Create {ticket_type.capitalize()} Ticket")
                self.ticket_type = ticket_type
                self.issue = discord.ui.TextInput(
                    label="Describe your issue",
                    style=discord.TextStyle.paragraph,
                    placeholder="Please provide details about your issue",
                    required=True
                )
                self.add_item(self.issue)
                if ticket_type == "replacement":
                    self.purchase_id = discord.ui.TextInput(
                        label="Purchase ID",
                        placeholder="Enter your Purchase ID (e.g., ABC123XY)",
                        required=True,
                        min_length=8,
                        max_length=8
                    )
                    self.add_item(self.purchase_id)
                elif ticket_type == "purchase":
                    self.item_id = discord.ui.TextInput(
                        label="Item ID (if applicable)",
                        required=False,
                        placeholder="Enter the item ID related to your issue"
                    )
                    self.add_item(self.item_id)

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    guild_id = int(os.getenv('GUILD_ID'))
                    guild = interaction.client.get_guild(guild_id)
                    if not guild:
                        await interaction.response.send_message("❌ Error: Server not found!", ephemeral=True)
                        return
                except (ValueError, TypeError):
                    await interaction.response.send_message("❌ Error: Invalid server configuration!", ephemeral=True)
                    return

<<<<<<< HEAD
                categories = {"support": "Support Tickets", "replacement": "Replacement Tickets", "purchase": "Purchase Tickets"}
=======
                # Create categories if they don't exist
                categories = {
                    "support": "Support Tickets",
                    "replacement": "Replacement Tickets",
                    "purchase": "Purchase Tickets"
                }

>>>>>>> 5dff67b77daf687b4aa0ce6c074c96bae178f3f2
                category_name = categories[self.ticket_type]
                category = discord.utils.get(guild.categories, name=category_name)
                if not category:
                    category = await guild.create_category(category_name)

                ticket_id = random.randint(1000, 9999)
                channel_name = f"{self.ticket_type}-{interaction.user.name}-{ticket_id}"
                channel = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    topic=f"{self.ticket_type.capitalize()} ticket for {interaction.user.name} | User ID: {interaction.user.id}"
                )

                await channel.set_permissions(guild.default_role, read_messages=False)
                await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
                for owner_id in OWNER_IDS:
                    try:
                        owner = await interaction.client.fetch_user(owner_id)
                        await channel.set_permissions(owner, read_messages=True, send_messages=True)
                    except Exception as e:
                        print(f"Failed to set permissions for owner {owner_id}: {e}")

                type_emoji = {"support": "❓", "replacement": "🔄", "purchase": "🛒"}
                additional_info = ""
                if self.ticket_type == "replacement":
                    purchase_id = self.purchase_id.value
                    if purchase_id in shop.purchases:
                        purchase = shop.purchases[purchase_id]
                        item = shop.stock.get(purchase["item_id"], {"name": "Unknown Item"})
                        additional_info = (
                            f"\n📦 Purchase ID: `{purchase_id}`\n"
                            f"🏷️ Item: {item['name']}\n"
                            f"📏 Quantity: {purchase['quantity']}\n"
                            f"⏰ Purchased: {purchase['timestamp']}\n"
                            f"📋 Items: ```{', '.join(purchase['items'])}```"
                        )
                    else:
                        additional_info = f"\n📦 Purchase ID: `{purchase_id}` (Not found)"
                elif self.ticket_type == "purchase" and hasattr(self, 'item_id'):
                    additional_info = f"\n🔑 Item ID: {self.item_id.value}" if self.item_id.value else ""

                embed = create_embed(
                    f"{type_emoji[self.ticket_type]} New {self.ticket_type.capitalize()} Ticket",
                    f"🎫 Ticket ID: **#{ticket_id}**\n👤 User: {interaction.user.mention}\n📝 Issue: {self.issue.value}{additional_info}\n\nPlease wait for a staff member to assist you."
                )
                view = CloseTicketView()
                await channel.send(embed=embed, view=view)

                await interaction.response.send_message(
                    f"✅ Ticket created! Please check {channel.mention}\nYour ticket ID: **#{ticket_id}**",
                    ephemeral=True
                )

        modal = TicketModal(self.values[0])
        await interaction.response.send_modal(modal)

@bot.tree.command(name="ticket", description="Open a support ticket 🎫")
async def ticket(interaction: discord.Interaction):
    view = TicketView()
    await interaction.response.send_message("Please select the type of ticket you'd like to create:", view=view, ephemeral=True)

<<<<<<< HEAD
=======

class QuantityModal(discord.ui.Modal):
    def __init__(self, item_id):
        super().__init__(title="Purchase Quantity")
        self.item_id = item_id
        self.quantity = discord.ui.TextInput(
            label="Quantity",
            placeholder="Enter the quantity you want to purchase",
            style=discord.TextStyle.short,
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.quantity)

    async def callback(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity.value)
            await self.process_purchase(interaction, quantity)
        except ValueError:
            await interaction.response.send_message("❌ Invalid quantity!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)


    async def process_purchase(self, interaction: discord.Interaction, quantity: int):
        user_id = str(interaction.user.id)

        if self.item_id not in shop.stock:
            await interaction.response.send_message("❌ Invalid item ID!", ephemeral=True)
            return

        item = shop.stock[self.item_id]
        total_cost = item['price'] * quantity

        if len(item['stock']) < quantity:
            await interaction.response.send_message("❌ Not enough stock available!", ephemeral=True)
            return

        if shop.user_credits.get(user_id, 0) < total_cost:
            await interaction.response.send_message("❌ Insufficient credits!", ephemeral=True)
            return

        # Generate purchase ID
        purchase_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # Process purchase
        purchased_items = item['stock'][:quantity]
        item['stock'] = item['stock'][quantity:]
        shop.user_credits[user_id] -= total_cost
        shop.save_data()

        # Create purchases directory if it doesn't exist
        if not os.path.exists('purchases'):
            os.makedirs('purchases')

        # Save purchase to file
        with open(f'purchases/{purchase_id}.txt', 'w') as f:
            f.write('\n'.join(purchased_items))

        # Send items via DM
        user = interaction.user

        if quantity == 1:
            item_parts = purchased_items[0].split(':')
            if len(item_parts) == 2:
                email, password = item_parts
                dm_embed = create_embed(
                    "Purchase Successful",
                    f"🎉 You purchased {item['name']}\n"
                    f"📦 Purchase ID: `{purchase_id}`\n\n"
                    f"📧 Email: ```{email}```\n"
                    f"🔑 Password: ```{password}```\n\n"
                    f"📝 Combo: ```{email}:{password}```"
                )
            else:
                dm_embed = create_embed(
                    "Purchase Successful",
                    f"🎉 You purchased {item['name']}\n"
                    f"📦 Purchase ID: `{purchase_id}`\n"
                    f"```{purchased_items[0]}```"
                )
        else:
            # Create txt file for multiple items
            buffer = io.StringIO('\n'.join(purchased_items))
            file = discord.File(fp=buffer, filename=f"{item['name']}_purchase.txt")
            dm_embed = create_embed(
                "Purchase Successful",
                f"🎉 You purchased {quantity}x {item['name']}\nCheck the attached file for your items!"
            )
            await user.send(embed=dm_embed, file=file)

        if quantity == 1:
            await user.send(embed=dm_embed)

        # Confirmation in channel
        embed = create_embed(
            "Purchase Successful",
            f"✅ Successfully purchased {quantity}x {item['name']}\n"
            f"📦 Purchase ID: `{purchase_id}`\n"
            f"Check your DMs for the items!\n\n"
            "⚠️ If there's any issue with your purchase, use `/ticket` to report it."
        )
        purchase_file = discord.File(f'purchases/{purchase_id}.txt', filename=f'{purchase_id}.txt')
        await interaction.response.send_message(embed=embed, file=purchase_file)


>>>>>>> 5dff67b77daf687b4aa0ce6c074c96bae178f3f2
class PurchaseView(discord.ui.View):
    def __init__(self, items, quantity):
        super().__init__()
        self.add_item(PurchaseSelect(items, quantity))

class CloseTicketView(discord.ui.View):
    def __init__(self):
<<<<<<< HEAD
        super().__init__(timeout=None)  # Persistent view

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary, emoji="✋")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🎫 Ticket claimed by {interaction.user.mention}")
=======
        super().__init__()

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary, emoji="✋")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🎫 Ticket claimed by {interaction.user.mention}", ephemeral=False)
>>>>>>> 5dff67b77daf687b4aa0ce6c074c96bae178f3f2
        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
<<<<<<< HEAD
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
=======
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...", ephemeral=False)
>>>>>>> 5dff67b77daf687b4aa0ce6c074c96bae178f3f2
        await asyncio.sleep(5)
        await interaction.channel.delete()

class PurchaseSelect(discord.ui.Select):
    def __init__(self, items, quantity):
        self.quantity = quantity
        options = [
            discord.SelectOption(
                label=f"{item['name']}",
                value=item_id,
                description=f"Price: {item['price']} credits | Stock: {len(item['stock'])}"
            )
            for item_id, item in items.items() if len(item['stock']) > 0
        ]
        super().__init__(placeholder="Select an item to purchase", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        user_id = str(interaction.user.id)

        if item_id not in shop.stock:
            await interaction.response.send_message("❌ Invalid item ID!", ephemeral=True)
            return

        item = shop.stock[item_id]
        total_cost = item['price'] * self.quantity

        if len(item['stock']) < self.quantity:
            await interaction.response.send_message("❌ Not enough stock available!", ephemeral=True)
            return

        if shop.user_credits.get(user_id, 0) < total_cost:
            await interaction.response.send_message("❌ Insufficient credits!", ephemeral=True)
            return

        # Generate purchase ID
        purchase_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # Process purchase
        purchased_items = item['stock'][:self.quantity]
        item['stock'] = item['stock'][self.quantity:]
        shop.user_credits[user_id] -= total_cost

        # Record purchase
        from datetime import datetime
        shop.purchases[purchase_id] = {
            "user_id": user_id,
            "items": purchased_items,
            "item_id": item_id,
            "quantity": self.quantity,
            "timestamp": datetime.now().isoformat()
        }
        shop.save_data()

        # Create purchases directory if it doesn't exist
        if not os.path.exists('purchases'):
            os.makedirs('purchases')

        # Save purchase to file (for internal tracking, not sent to server)
        with open(f'purchases/{purchase_id}.txt', 'w') as f:
            f.write('\n'.join(purchased_items))

        # Send items via DM
        user = interaction.user
        if self.quantity == 1:
            item_parts = purchased_items[0].split(':')
            if len(item_parts) == 2:
                email, password = item_parts
                dm_embed = create_embed(
                    "Purchase Successful",
                    f"🎉 You purchased {item['name']}\n📦 Purchase ID: `{purchase_id}`\n\n📧 Email: ```{email}```\n🔑 Password: ```{password}```\n📝 Combo: ```{email}:{password}```"
                )
            else:
                dm_embed = create_embed(
                    "Purchase Successful",
                    f"🎉 You purchased {item['name']}\n📦 Purchase ID: `{purchase_id}`\n```{purchased_items[0]}```"
                )
            await user.send(embed=dm_embed)
        else:
            buffer = io.StringIO('\n'.join(purchased_items))
            file = discord.File(fp=buffer, filename=f"{item['name']}_purchase_{purchase_id}.txt")
            dm_embed = create_embed(
                "Purchase Successful",
                f"🎉 You purchased {self.quantity}x {item['name']}\n📦 Purchase ID: `{purchase_id}`\nCheck the attached file for your items!"
            )
            await user.send(embed=dm_embed, file=file)

        # Confirmation in channel (no file or credentials)
        embed = create_embed(
            "Purchase Successful",
            f"✅ Successfully purchased {self.quantity}x {item['name']}\n📦 Purchase ID: `{purchase_id}`\nCheck your DMs for the items!\n\n⚠️ If there's any issue with your purchase, use `/ticket` to report it."
        )
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show available commands 📚")
async def help(interaction: discord.Interaction):
    embed = create_embed("Available Commands 📚", "Here are all the available commands:")
    commands = {
        "balance": "Check your credit balance 💰",
        "stock": "Check available items in shop 🏪",
        "purchase": "Purchase items from shop 🛒",
        "redeem": "Redeem a key for credits 🎁",
        "ticket": "Open a support ticket 🎫",
        "help": "Show this help message 📚"
    }
    if is_owner(interaction.user.id):
        commands.update({
            "generatekey": "Generate redeem keys 🔑",
            "addstock": "Add items to shop inventory 🏪",
            "replace": "Replace items in a ticket [Ticket Channel Only] 🔄"
        })
    for cmd, desc in commands.items():
        embed.add_field(name=f"/{cmd}", value=desc, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="help", description="Show available commands 📚")
async def help(interaction: discord.Interaction):
    embed = create_embed(
        "Available Commands 📚",
        "Here are all the available commands:"
    )

    commands = {
        "balance": "Check your credit balance 💰",
        "stock": "Check available items in shop 🏪",
        "purchase": "Purchase items from shop 🛒",
        "redeem": "Redeem a key for credits 🎁",
        "ticket": "Open a support ticket 🎫",
        "help": "Show this help message 📚"
    }

    # Add owner-only commands if user is an owner
    if is_owner(interaction.user.id):
        commands.update({
            "generatekey": "Generate redeem keys 🔑",
            "addstock": "Add items to shop inventory 🏪",
            "replace": "Process replacement requests 🔄"
        })

    for cmd, desc in commands.items():
        embed.add_field(name=f"/{cmd}", value=desc, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="purchase", description="Purchase items from shop 🛒")
@app_commands.describe(quantity="Number of items to purchase")
async def purchase(interaction: discord.Interaction, quantity: int = 1):
    if not shop.stock:
        await interaction.response.send_message("❌ No items available in the shop!")
        return

    if quantity < 1:
        await interaction.response.send_message("❌ Quantity must be at least 1!", ephemeral=True)
        return

    view = PurchaseView(shop.stock, quantity)
    await interaction.response.send_message("Select an item to purchase:", view=view)

<<<<<<< HEAD
bot.run(TOKEN)
=======




bot.run(TOKEN)
>>>>>>> 5dff67b77daf687b4aa0ce6c074c96bae178f3f2
