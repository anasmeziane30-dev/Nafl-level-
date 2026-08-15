import os
import asyncio
import random
import aiosqlite
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# إعداد سيرفر فلاسك الآمن
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# إعدادات الصلاحيات
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

class LevelBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        self.loop.create_task(voice_xp_loop())

bot = LevelBot()
voice_timers = {}
LEVEL_CHANNEL_NAME = "level-log"

async def init_db():
    async with aiosqlite.connect('database.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS levels (
                user_id TEXT,
                guild_id TEXT,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        await db.commit()

@bot.event
async def on_ready():
    await init_db()
    print(f'Logged in as {bot.user.name} successfully!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!rank"))

async def send_level_up_text(guild, member, level, type_name):
    target_channel = discord.utils.get(guild.text_channels, name=LEVEL_CHANNEL_NAME)
    if not target_channel and guild.text_channels:
        target_channel = guild.system_channel or guild.text_channels[0]
    if target_channel:
        await target_channel.send(f"🥳 Congratulations {member.mention}, you have reached level number **{level}**! ({type_name})")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    user_id = str(message.author.id)
    guild_id = str(message.guild.id)
    xp_to_add = random.randint(15, 25)

    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?', (user_id, guild_id)) as cursor:
            row = await cursor.fetchone()

        if not row:
            await db.execute('INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)', (user_id, guild_id, xp_to_add, 0))
            await db.commit()
        else:
            xp, level = row
            new_xp = xp + xp_to_add
            needed_xp = (level + 1) * 100

            if new_xp >= needed_xp:
                level += 1
                await send_level_up_text(message.guild, message.author, level, "Chat")

            await db.execute('UPDATE levels SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?', (new_xp, level, user_id, guild_id))
            await db.commit()

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    user_id = str(member.id)
    if before.channel is None and after.channel is not None:
        voice_timers[user_id] = asyncio.get_event_loop().time()
    elif before.channel is not None and after.channel is None:
        if user_id in voice_timers:
            del voice_timers[user_id]

async def voice_xp_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(60)
        current_time = asyncio.get_event_loop().time()
        for user_id, join_time in list(voice_timers.items()):
            if current_time - join_time >= 60:
                for guild in bot.guilds:
                    member = guild.get_member(int(user_id))
                    if member and member.voice and member.voice.channel:
                        guild_id = str(guild.id)
                        xp_to_add = 10
                        async with aiosqlite.connect('database.db') as db:
                            async with db.execute('SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?', (user_id, guild_id)) as cursor:
                                row = await cursor.fetchone()
                            if not row:
                                await db.execute('INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)', (user_id, guild_id, xp_to_add, 0))
                                await db.commit()
                            else:
                                xp, level = row
                                new_xp = xp + xp_to_add
                                needed_xp = (level + 1) * 100
                                if new_xp >= needed_xp:
                                    level += 1
                                    await send_level_up_text(guild, member, level, "Voice")
                                await db.execute('UPDATE levels SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?', (new_xp, level, user_id, guild_id))
                                await db.commit()
                        voice_timers[user_id] = current_time

@bot.command(name='rank')
async def rank(ctx):
    user_id = str(ctx.author.id)
    guild_id = str(ctx.guild.id)
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?', (user_id, guild_id)) as cursor:
            row = await cursor.fetchone()
    current_xp = row[0] if row else 0
    current_level = row[1] if row else 0
    needed_xp = (current_level + 1) * 100
    await ctx.send(f"📊 **User Level:** {ctx.author.name}\n🌟 **Level:** {current_level}\n✨ **XP:** {current_xp} / {needed_xp}")

if __name__ == '__main__':
    # تشغيل فلاسك بأمان في الخلفية
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    token = os.environ.get('TOKEN')
    if token:
        bot.run(token)
    else:
        print("Error: TOKEN not found!")
