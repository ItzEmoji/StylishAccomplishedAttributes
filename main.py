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

    # Send confirmation in server
    await interaction.response.send_message("✅ Keys generated! Check your DMs.", ephemeral=True)

    # Send keys via DM
    if amount == 1:
        keys_text = "\n".join([f"🔑 **{key}** - 💰 {credits} credits" for key in generated_keys])
        embed = create_embed(
            "Keys Generated",
            f"Generated {amount} key:\n{keys_text}"
        )
        await interaction.user.send(embed=embed)
    else:
        # Create txt file for multiple keys
        keys_text = "\n".join([f"{key} - {credits} credits" for key in generated_keys])
        buffer = io.StringIO(keys_text)
        file = discord.File(fp=buffer, filename=f"generated_keys_{amount}.txt")
        embed = create_embed(
            "Keys Generated",
            f"✅ Generated {amount} keys!\nCheck the attached file."
        )
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
            # Append to existing stock
            shop.stock[item_id]["stock"].extend(stock_items)
            total_stock = len(shop.stock[item_id]["stock"])
            embed = create_embed(
                "✅ Stock Updated",
                f"**Item Details:**\n" + 
                f"🏷️ Name: `{name}`\n" +
                f"🔑 ID: `{item_id}`\n" +
                f"💰 Price: `{shop.stock[item_id]['price']} credits`\n" +
                f"📦 Added Items: `{len(stock_items)}`\n" +
                f"📊 Total Stock: `{total_stock}`"
            )
        else:
            # Create new item
            shop.stock[item_id] = {
                "name": name,
                "price": price,
                "stock": stock_items
            }
            embed = create_embed(
                "✅ New Item Added",
                f"**Item Details:**\n" + 
                f"🏷️ Name: `{name}`\n" +
                f"🔑 ID: `{item_id}`\n" +
                f"💰 Price: `{price} credits`\n" +
                f"📦 Initial Stock: `{len(stock_items)}`"
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

    embed = create_embed(
        "Key Redeemed",
        f"✅ Successfully redeemed **{credits}** credits!"
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="replace", description="Request a replacement for invalid item [Admin Only] 🔄")
@app_commands.describe(
    user="The user who needs a replacement",
    item_name="The name of the invalid item"
)
async def replace(interaction: discord.Interaction, user: discord.Member, item_name: str):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ You don't have permission to use this command!")
        return

    # Notify admins via DM
    for owner_id in OWNER_IDS:
        try:
            owner = await bot.fetch_user(owner_id)
            embed = create_embed(
                "⚠️ Invalid Item Report",
                f"User: {user.mention}\nItem: {item_name}\nReported by: {interaction.user.mention}"
            )
            await owner.send(embed=embed)
        except Exception as e:
            print(f"Failed to DM owner {owner_id}: {e}")

    embed = create_embed(
        "Replacement Initiated",
        f"✅ Replacement request for {user.mention} has been sent to the admins."
    )
    await interaction.response.send_message(embed=embed)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketSelect())

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="General Support",
                value="support",
                description="Get help with general issues",
                emoji="❓"
            ),
            discord.SelectOption(
                label="Item Replacement",
                value="replacement",
                description="Request replacement for invalid items",
                emoji="🔄"
            ),
            discord.SelectOption(
                label="Purchase Issue",
                value="purchase",
                description="Report issues with purchases",
                emoji="🛒"
            )
        ]
        super().__init__(
            placeholder="Select ticket type",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # Create modal for additional information
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
                if ticket_type == "purchase":
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

                # Create categories if they don't exist
                categories = {
                    "support": "Support Tickets",
                    "replacement": "Replacement Tickets",
                    "purchase": "Purchase Tickets"
                }

                category_name = categories[self.ticket_type]
                category = discord.utils.get(guild.categories, name=category_name)
                if not category:
                    category = await guild.create_category(category_name)

                ticket_id = random.randint(1000, 9999)
                channel_name = f"{self.ticket_type}-{interaction.user.name}-{ticket_id}"
                channel = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    topic=f"{self.ticket_type.capitalize()} ticket for {interaction.user.name}"
                )

                # Set permissions
                await channel.set_permissions(guild.default_role, read_messages=False)
                await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
                for owner_id in OWNER_IDS:
                    try:
                        owner = await interaction.client.fetch_user(owner_id)
                        await channel.set_permissions(owner, read_messages=True, send_messages=True)
                    except Exception as e:
                        print(f"Failed to set permissions for owner {owner_id}: {e}")

                # Create ticket message
                type_emoji = {
                    "support": "❓",
                    "replacement": "🔄",
                    "purchase": "🛒"
                }

                item_id_value = getattr(self, 'item_id', None)
                item_id_text = f"\n🔑 Item ID: {item_id_value.value}" if item_id_value else ""

                embed = create_embed(
                    f"{type_emoji[self.ticket_type]} New {self.ticket_type.capitalize()} Ticket",
                    f"🎫 Ticket ID: **#{ticket_id}**\n"
                    f"👤 User: {interaction.user.mention}\n"
                    f"📝 Issue: {self.issue.value}{item_id_text}\n\n"
                    "Please wait for a staff member to assist you."
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


class PurchaseView(discord.ui.View):
    def __init__(self, items, quantity):
        super().__init__()
        self.add_item(PurchaseSelect(items, quantity))

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary, emoji="✋")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🎫 Ticket claimed by {interaction.user.mention}", ephemeral=False)
        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...", ephemeral=False)
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
            for item_id, item in items.items()
            if len(item['stock']) > 0
        ]
        super().__init__(
            placeholder="Select an item to purchase",
            min_values=1,
            max_values=1,
            options=options
        )

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

        # Process purchase
        purchased_items = item['stock'][:self.quantity]
        item['stock'] = item['stock'][self.quantity:]
        shop.user_credits[user_id] -= total_cost
        shop.save_data()

        # Send items via DM
        user = interaction.user

        if self.quantity == 1:
            item_parts = purchased_items[0].split(':')
            if len(item_parts) == 2:
                email, password = item_parts
                dm_embed = create_embed(
                    "Purchase Successful",
                    f"🎉 You purchased {item['name']}\n\n"
                    f"📧 Email: ```{email}```\n"
                    f"🔑 Password: ```{password}```\n\n"
                    f"📝 Combo: ```{email}:{password}```"
                )
                await user.send(embed=dm_embed)
            else:
                dm_embed = create_embed(
                    "Purchase Successful",
                    f"🎉 You purchased {item['name']}\n```{purchased_items[0]}```"
                )
                await user.send(embed=dm_embed)
        else:
            buffer = io.StringIO('\n'.join(purchased_items))
            file = discord.File(fp=buffer, filename=f"{item['name']}_purchase.txt")
            dm_embed = create_embed(
                "Purchase Successful",
                f"🎉 You purchased {self.quantity}x {item['name']}\nCheck the attached file for your items!"
            )
            await user.send(embed=dm_embed, file=file)

        # Confirmation in channel
        embed = create_embed(
            "Purchase Successful",
            f"✅ Successfully purchased {self.quantity}x {item['name']}\nCheck your DMs for the items!\n\n"
            "⚠️ If there's any issue with your purchase, use `/ticket` to report it."
        )
        await interaction.response.send_message(embed=embed)


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





bot.run(TOKEN)
