import discord
import os
import logging
from dotenv import load_dotenv
from discord.ext import commands, tasks
import json
import random
import time

intents = discord.Intents.all()

load_dotenv()

last_message_time = 0
AUTO_MESSAGE_CHANNEL_ID = 1469698021603414211
argent = ARGENT_USERS = {}
GEMS_USERS = {}
cooldowns = {}
cooldowns_level = {
    "message": {},
    "command": {},
    "reaction": {}
}
work_cooldowns = {}
daily_cooldowns = {}
cooldown = 60
daily_cooldown = 86400
daily_gain = 1000
level_channel_id = 1469742344436846887
ROLE_XP_BOOSTS = {
    1469754360002121728: 1.08,
    1470094772092932220: 1.10,
    1470091386845135071: 1.20,
    1469755033061949581: 1.30,
    1469755162716278975: 1.50,
    1469755295852003358: 1.60,
    1470094922534096948: 1.80,
    1470091514079219948: 2.0,
    1469755411363270699: 2.20,
    1469755527327125684: 2.40,
    1469755612224032828: 2.60,
    1470095046492557546: 2.90,
    1470091725145116896: 3.20,
    1492294406391468192: 4.0
    }
LEVEL_ROLES = {
   5: 1469754360002121728,
   10: 1469755033061949581,
   20: 1469755162716278975,
   35: 1469755295852003358,
   60: 1469755411363270699,
   95: 1469755527327125684,
   145: 1469755612224032828
}

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    log.info(f"Bot en ligne : {bot.user}")
    try:
        synced = await bot.tree.sync()
        log.info(f"{len(synced)} commandes synchronisées")
    except Exception as e:
        log.error(f"Erreur sync : {e}")
    voice_xp_loop.start()
    auto_message.start()

@tasks.loop(minutes=5)
async def voice_xp_loop():
    data = load_level()
    gain_par_cycle = 20

    for guild in bot.guilds:
        for channel in guild.voice_channels:
            for member in channel.members:
                if member.bot:
                    continue
                if member.voice.self_deaf or member.voice.deaf:
                    continue

                user_id = str(member.id)
                data.setdefault(user_id, {
                    "xp": 0, "level": 0, "messages": 0,
                    "commands": 0, "reactions": 0, "voice_time": 0
                })

                await add_xp(member, gain_par_cycle, data)
                log.info(f"[VOCAL XP] +{gain_par_cycle} XP → {member.display_name} ({guild.name})")

@voice_xp_loop.before_loop
async def before_voice_xp():
    await bot.wait_until_ready()

def format_number(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}k"
    else:
        return str(n)

def format_money(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}k"
    else:
        return str(n)
    
def format_gems(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}k"
    else:
        return str(n)

def load_data():
    if not os.path.exists("profile.json"):
        return {}
    try:
        with open("profile.json", "r") as f:
            return json.load(f)
    except:
        return {}
    
def save_data(data):
    with open("profile.json", "w") as f:
        json.dump(data, f, indent=4) 

## Message Auto

@tasks.loop(hours=2)
async def auto_message():
    channel = bot.get_channel(AUTO_MESSAGE_CHANNEL_ID)
    if not channel:
        log.warning("[AUTO MSG] Salon Introuvable")
        return
    
    if time.time() - last_message_time < 600:
        log.info("[AUTO MSG] Message ignoré, aucun envoie fait")
        return
    
    await channel.send("<@&1501230963139543162> réveillez vous !")
    log.info("[AUTO MSG] Message envoyé !")

@auto_message.auto.message()
async def before_auto_message():
    await bot.wait_until_ready()

## LEVELING

def load_level():
    try:
        with open("level.json", "r") as f:
            return json.load(f)
    except:
        return {}
        
def save_level(data):
    with open("level.json", "w") as f:
        json.dump(data, f, indent=4)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s » %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)

log = logging.getLogger("bot")

@bot.event
async def on_voice_state_update(member, before, after):
    data = load_level()
    user_id = str(member.id)

    data.setdefault(user_id, {
        "xp": 0,
        "level": 0,
        "messages": 0,
        "commands": 0,
        "reactions": 0,
        "voice_time": 0
    })

    if before.channel is None and after.channel is not None:
        data[user_id]["voice_join"] = time.time()
        log.info(f"[VOCAL] {member.display_name} a rejoint #{after.channel.name}")

    elif before.channel is not None and after.channel is None:
        join_time = data[user_id].get("voice_join")
        log.info(f"[VOCAL] {member.display_name} quitte le salon #{before.channel.name}")

    if join_time:
        duration =time.time() - join_time
        data[user_id]["voice_time"] += int(duration)
        data[user_id]["voice_join"] = None

    save_level(data)

async def update_level_roles(member, level):
    guild = member.guild

    for lvl, role_id in LEVEL_ROLES.items():
        role = guild.get_role(role_id)

        if not role:
            continue

        if level >= lvl and role not in member.roles:
            if role < guild.me.top_role:
                await member.add_roles(role)

    for lvl, role_id in sorted(LEVEL_ROLES.items()):
        role = guild.get_role(role_id)

        if not role:
            continue

    if level < lvl and role in member.roles:
        if role < guild.me.top_role:
            await member.remove_roles(role)

def get_xp_multiplier(member):
    multiplier = 1.0

    for role in member.roles:
        if role.id in ROLE_XP_BOOSTS:
            multiplier = max(multiplier, ROLE_XP_BOOSTS[role.id])

    return multiplier 

def is_on_cooldown(user_id, cooldown_time, action_type):
    now = time.time()

    if user_id not in cooldowns_level[action_type]:
        cooldowns_level[action_type][user_id] = 0

    if now - cooldowns_level[action_type][user_id] < cooldown_time:
        return True
    
    cooldowns_level[action_type][user_id] = now
    return False

def xp_needed(level):
    return int(100 * 1.3 ** level)

async def add_xp(user, gain, data):

    user_id = str(user.id)

    if not hasattr(user, "roles"):
        return

    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 0, "messages": 0, "commands": 0, "reactions": 0}

    multiplier = get_xp_multiplier(user)
    final_gain = int(gain * multiplier)

    data[user_id]["xp"] += final_gain

    xp = data[user_id]["xp"]
    level = data[user_id]["level"]

    while data[user_id]["xp"] >= xp_needed(data[user_id]["level"]):
        data[user_id]["xp"] -= xp_needed(data[user_id]["level"])
        data[user_id]["level"] += 1
        log.info(f"[LEVEL UP] {user} → niveau {data[user_id]['level']}")

        await update_level_roles(user, data[user_id]["level"])

        channel = bot.get_channel(level_channel_id)
        if channel:
            await channel.send(f"{user.mention} est passé niveau {data[user_id]['level']} !")

    save_level(data)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    global last_message_time
    last_message_time = time.time()
    
    data = load_level()
    user_id = str(message.author.id)

    data.setdefault(user_id, {
        "xp": 0,
        "level": 0,
        "messages": 0,
        "commands": 0,
        "reactions": 0,
        "voice_time": 0
    })

    data[user_id]["messages"] += 1

    log.debug(f"[MESSAGE] {message.author} dans #{message.channel}")
 
    gain = random.randint(10, 30)

    if not is_on_cooldown(user_id, 60, "message"):
        await add_xp(message.author, gain, data)

    await bot.process_commands(message)

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command):
    if interaction.user.bot:
        return
    
    data = load_level()
    user_id = str(interaction.user.id)

    if user_id not in data:
        data[user_id] = {
        "xp": 0,
        "level": 0,
        "messages": 0,
        "commands": 0,
        "reactions": 0,
        "voice_time": 0
    }
    else:
        data[user_id].setdefault("xp", 0)
        data[user_id].setdefault("level", 0)
        data[user_id].setdefault("messages", 0)
        data[user_id].setdefault("commands", 0)
        data[user_id].setdefault("reactions", 0)
        data[user_id].setdefault("voice_time", 0)

    data[user_id]["commands"] += 1

    if is_on_cooldown(user_id, 120, "command"):
        return
    
    save_level(data)
    
    gain = random.randint(5, 15)
    await add_xp(interaction.user, gain, data)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    data = load_level()

    user_id = str(user.id)
    data[user_id]["reactions"] +=1

    data.setdefault(user_id, {
        "xp": 0,
        "level": 0,
        "messages": 0,
        "commands": 0,
        "reactions": 0,
        "voice_time": 0
    })

    if is_on_cooldown(user_id, 300, "reaction"):
        return
    
    gain = random.randint(2, 10)
    await add_xp(user, gain, data)

    save_level(data)

@bot.tree.command(name="leaderboard", description="Affiche le classment du serveur")
@discord.app_commands.describe(categorie="Choisis l'option de classement")
@discord.app_commands.choices(categorie=[
    discord.app_commands.Choice(name="Niveau", value="level"),
    discord.app_commands.Choice(name="Messages", value="messages"),
    discord.app_commands.Choice(name="Commandes", value="commands"),
    discord.app_commands.Choice(name="Réactions", value="reactions"),
    discord.app_commands.Choice(name="Temps vocal", value="voice_time"),
])
async def leaderboard(interaction: discord.Interaction, categorie: discord.app_commands.Choice[str] = None):
    await interaction.response.defer()

    data = load_level()
    categorie_value = categorie.value if categorie else "level"
    categorie_name = categorie.name if categorie else "Niveau"

    guild_member_ids = {str(m.id) for m in interaction.guild.members if not m.bot}

    filtered = {uid: d for uid, d in data.items() if uid in guild_member_ids}

    if categorie_value == "level":
        sorted_data = sorted(
        filtered.items(),
        key=lambda x: (
            x[1].get("level", 0),
            sum(xp_needed(lvl) for lvl in range(x[1].get("level", 0))) + x[1].get("xp", 0)
        ),
        reverse=True
    )
    else:
        sorted_data = sorted(filtered.items(), key=lambda x: x[1].get(categorie_value, 0), reverse=True)

    top = sorted_data[:10]

    medals = {1: "<:1_:1500970757847781396>", 2: "<:2_:1500970802735222907>", 3: "<:3_:1500970826537894028>"}

    description = "" 
    for i, (user_id, user_data) in enumerate(top, start=1):
        member = interaction.guild.get_member(int(user_id))
        name = member.display_name if member else f"Utilisateur Inconnu"
        prefix = medals.get(i, f"`#{i}`")

        if categorie_value == "level":
            level = user_data.get("level", 0)
            xp_current = user_data.get("xp", 0)
            xp_total = sum(xp_needed(lvl) for lvl in range(level)) + xp_current
            value = f"Niveau **{level}** (`{format_number(xp_total)} xp`)"

        elif categorie_value == "voice_time":
            seconds = user_data.get("voice_time", 0)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            value = f"`{hours}h {minutes}m`"

        else:
            raw = user_data.get(categorie_value, 0)
            value = f"`{format_number(raw)}`"

        description += f"{prefix} **{name}**  {value}\n"

    if not description:
        description = "Aucune donnée enregistrée."

    embed = discord.Embed(title=f"Classement ({categorie_name})", description=description, color=0x750000)

    embed.set_footer(text=f"Top 10 sur {interaction.guild.name}")

    await interaction.followup.send(embed=embed)
        
@bot.tree.command(name="give_xp", description="Donne de l'xp a un membre")
@discord.app_commands.describe(
    user="Membre",
    montant="Quantité d'Xp"
)
async def give_xp(interaction: discord.Interaction, user: discord.Member, montant: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("**Tu n'es pas admin.**", ephemeral=True)
        return
    if user.bot:
        await interaction.response.send_message("**Impossible de donner de l'xp à un bot.**", ephemeral=True)
        return
    if montant <= 0:
        await interaction.response.send_message("**Le montant doit être supérieur à zéro.**", ephemeral=True)
        return

    data = load_level()
    user_id = str(user.id)

    data.setdefault(user_id, {
        "xp": 0, "level": 0, "messages": 0,
        "commands": 0, "reactions": 0, "voice_time": 0
    })

    await add_xp(user, montant, data)

    embed = discord.Embed(description=f"**{montant} XP** ont été donnés à {user.mention} !", color=0x750000)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="del_xp", description="Retire de l'xp")
@discord.app_commands.describe(
    user="Membre",
    montant="Quantité d'Xp"
)
async def del_xp(interaction: discord.Interaction, user: discord.Member, montant: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("**Tu n'es pas admin.**", ephemeral=True)
        return
    if user.bot:
        await interaction.response.send_message("**Impossible de retirer de l'xp à un bot.**", ephemeral=True)
        return
    if montant <= 0:
        await interaction.response.send_message("**Le montant doit être supérieur à zéro.**", ephemeral=True)
        return

    data = load_level()
    user_id = str(user.id)

    data.setdefault(user_id, {
        "xp": 0, "level": 0, "messages": 0,
        "commands": 0, "reactions": 0, "voice_time": 0
    })

    user_xp_total = data[user_id]["xp"] + sum(
        xp_needed(lvl) for lvl in range(data[user_id]["level"])
    )

    montant_reel = min(montant, user_xp_total)
    new_total = user_xp_total - montant_reel

    data[user_id]["xp"] = 0
    data[user_id]["level"] = 0

    while new_total >= xp_needed(data[user_id]["level"]):
        new_total -= xp_needed(data[user_id]["level"])
        data[user_id]["level"] += 1

    data[user_id]["xp"] = new_total

    await update_level_roles(user, data[user_id]["level"])
    save_level(data)                                       

    embed = discord.Embed(description=f"**{montant_reel} XP** ont été retirés à {user.mention} !", color=0x750000)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="boost", description="affiche les boost actuel")
async def boost(interaction: discord.Interaction):
    if not ROLE_XP_BOOSTS:
        await interaction.response.send_message("Aucun boost configuré", ephemeral=True)
        return
    
    embed = discord.Embed(title="Voici les boost de niveau de rôle", description="", color=0x750000)
    
    for role_id, multiplier in ROLE_XP_BOOSTS.items():
        role = interaction.guild.get_role(role_id)

        mention = f"<@&{role_id}>"

        if role:
            embed.add_field(name="", value=f"* {mention}\n> x{multiplier}", inline=False)
        else:
            embed.add_field(name=f"Rôle inconnu ({role_id})", value=f"x{multiplier}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rewards", description="affiche les roles de niveaux")
async def rewards(interaction: discord.Interaction):
    if not LEVEL_ROLES:
        await interaction.response.send_message("Aucun role niveau configuré", ephemeral=True)
        return
    
    embed = discord.Embed(title="Voici les roles de niveau", description="", color=0x750000)
    
    for level, role_id in LEVEL_ROLES.items():
        role = interaction.guild.get_role(role_id)

        if role:
            embed.add_field(name="", value=f"* {role.mention}\n> {level}", inline=False)
        else:
            embed.add_field(name=f"Rôle inconnu ({role.mention})", value=f"{level}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rank", description="affiche ton rank")
async def rank(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user

    if user.bot:
        await interaction.response.send_message("**Cet utilisateur ne peut pas avoir de niveau**", ephemeral=True)
        return

    data = load_level()
    user_id = str(user.id)

    data.setdefault(user_id, {
            "xp": 0,
            "level": 0,
            "messages": 0,
            "commands": 0,
            "reactions": 0,
            "voice_time": 0
        })

    user_data = data[user_id]

    voice_hours = user_data.get("voice_time", 0) / 3600

    level = user_data.get("level", 0)
    xp = user_data.get("xp", 0)

    next_xp = xp_needed(level)

    progress = min(10, int((xp / next_xp) * 10)) if next_xp > 0 else 0
    bar = "█" * progress + "░" * (10 - progress)

    embed = discord.Embed(title="", description=f"**Voici le profil de {user.mention}**", color=0x750000)
    embed.add_field(name="Niveau : ", value=f"`{level}`")
    embed.add_field(name="Xp : ", value=f"`{xp}`")
    embed.add_field(name="Messages : ", value=f"`{format_number(user_data.get('messages', 0))}`",inline=True)
    embed.add_field(name="Commandes : ", value=f"`{format_number(user_data.get('commands', 0))}`",inline=True)
    embed.add_field(name="Réactions : ", value=f"`{format_number(user_data.get('reactions', 0))}`",inline=True)
    embed.add_field(name="Temps Vocal", value=f"`{voice_hours:.2f}h`", inline=True)
    embed.add_field(name="Prochain niveaux : ", value=f"`{bar}` {xp}/{next_xp}", inline=False)
    await interaction.response.send_message(embed=embed)

    save_level(data)

@bot.tree.command(name="reset_rank", description="reset le niveau d'un membre")
@discord.app_commands.describe(
    user="Utilisateur",
    action="level, xp ou tout"
)
@discord.app_commands.choices(action=[

    discord.app_commands.Choice(name="Niveau", value="level"),
    discord.app_commands.Choice(name="Xp", value="xp"),
    discord.app_commands.Choice(name="Tout", value="all")
])

async def reset_rank(interaction: discord.Interaction, user: discord.Member, action: discord.app_commands.Choice[str]):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Tu n'as pas les permissions pour effectuer cet commande", ephemeral=True)
        return
    
    data = load_level()
    user_id = str(user.id)

    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 0}

    already_reset = (data[user_id]["xp"] == 0 and data[user_id]["level"] == 0)
    if already_reset:
        await interaction.response.send_message(f"**{user.mention} a deja été reset !**", ephemeral=True)
        return

    if action.value == "level":
        data[user_id]["level"] = 0

    elif action.value == "xp":
        data[user_id]["xp"] = 0

    elif action.value == "all":
        data[user_id]["level"] = 0
        data[user_id]["xp"] = 0

    save_level(data)

    await interaction.response.send_message(f"**{action.name} a été reset pour {user.mention} !**", ephemeral=True)


## ECONOMY

@bot.tree.command(name="balance", description="Voir sont argent")
async def balance(interaction: discord.Interaction, user: discord.Member = None):     
    user = user or interaction.user   
    if user.bot:
        await interaction.response.send_message("**Cet utilisateur ne peut pas avoir d'argent**", ephemeral=True)
        return
    data = load_data()
    user_data =data.get(str(user.id), {"argent": 0, "gemmes": 0})

    user_data.setdefault("argent", 0)
    user_data.setdefault("gemmes", 0)

    argent = user_data["argent"]
    gemmes = user_data["gemmes"]
    embed = discord.Embed(title='', description=f'**Voici le profile de {user.mention}**',color=0x750000)
    embed.add_field(name="<:cash:1493950444001693818> Argent",value=f"{format_money(argent)}")
    embed.add_field(name="Gemmes",value=f"{format_gems(gemmes)}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bal", description="Voir sont argent")
async def bal(interaction: discord.Interaction, user: discord.Member = None):     
    user = user or interaction.user   
    if user.bot:
        await interaction.response.send_message("**Cet utilisateur ne peut pas avoir d'argent**", ephemeral=True)
        return
    data = load_data()
    user_data =data.get(str(user.id), {"argent": 0, "gemmes": 0})

    user_data.setdefault("argent", 0)
    user_data.setdefault("gemmes", 0)

    argent = user_data["argent"]
    gemmes = user_data["gemmes"]
    embed = discord.Embed(title='', description=f'**Voici le profile de {user.mention}**',color=0x750000)
    embed.add_field(name="<:cash:1493950444001693818> Argent",value=f"{format_money(argent)}")
    embed.add_field(name="Gemmes",value=f"{format_gems(gemmes)}")
    await interaction.response.send_message(embed=embed)

## Commandes utilisateurs
@bot.tree.command(name="work", description="travail pour gagner de l'argent")
async def work(interaction: discord.Interaction):
    user = interaction.user
    current_time = time.time()
    gain = random.randint(0, 1000)
    if user.id in work_cooldowns:
        if current_time - work_cooldowns[user.id] < cooldown:
            await interaction.response.send_message("**Tu dois attendre avant de refaire la commande !**", ephemeral=True)
            return
    work_cooldowns[user.id] = current_time
    data = load_data()
    user_data =data.get(str(user.id), {"argent": 0, "gemmes": 0})
    user_data["argent"] += gain
    data[str(user.id)] = user_data
    await interaction.response.send_message(f"**Vous avez travaillez et obtenu {gain} <:cash:1493950444001693818> !**")
    save_data(data)

@bot.tree.command(name="daily", description="Récupére ta récompense journalière")
async def daily(interaction: discord.Interaction):
    user = interaction.user
    data = load_data()
    current_time = time.time()
    if user.id in daily_cooldowns:
        if current_time - daily_cooldowns[user.id] < daily_cooldown:
            await interaction.response.send_message("**Tu dois attendre avant de refaire la commande !**", ephemeral=True)
            return
    daily_cooldowns[user.id] = current_time
    user_data = data.get(str(user.id), {"argent": 0, "gemmes": 0 })

    user_data.setdefault("argent", 0)
    user_data.setdefault("gemmes", 0)

    user_data["argent"] += daily_gain
    data[str(user.id)] = user_data
    await interaction.response.send_message(f"**Vous avez obtenu {format_money(daily_gain)} d'argent <:cash:1493950444001693818>**")
    save_data(data)

## Commandes Admin

bot.run(os.getenv('DISCORD_TOKEN'))
