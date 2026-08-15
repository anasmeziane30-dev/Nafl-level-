import os
import asyncio
import random
import aiosqlite
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# إعداد سيرفر فلاسك البسيط لإبقاء بوت Render مستيقظاً (Web Service)
app = Flask('')

@app.route('/')
def home():
    return "Discord Level Bot is running!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعدادات بوت الديسكورد
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# تتبع أوقات الأعضاء في الرومات الصوتية
voice_timers = {}

# --- [ اسم القناة المخصصة لإرسال إشعارات اللفل ] ---
LEVEL_CHANNEL_NAME = "level-log" # يمكنك تغيير هذا الاسم إلى اسم القناة التي تفضلها في سيرفرك

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
    print(f'Logged in as {bot.user.name}!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!rank | Level System"))

# دالة مساعدة لإرسال رسالة اللفل بالنص المطلوب في القناة المخصصة
async def send_level_up_text(guild, member, level, type_name):
    target_channel = discord.utils.get(guild.text_channels, name=LEVEL_CHANNEL_NAME)
    
    # إذا لم يجد القناة المخصصة، سيقوم بالنشر في أول روم نصي متاح كاحتياط
    if not target_channel and guild.text_channels:
        target_channel = guild.system_channel or guild.text_channels[0]
        
    if target_channel:
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        content = f"🥳 Congratulations {member.mention}, you have reached level number **{level}**! ({type_name})\n🖼️ {avatar_url}"
        await target_channel.send(content)

# نظام الشات (XP لكل رسالة)
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

# نظام الصوت (XP عند الجلوس في الرومات الصوتية)
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    user_id = str(member.id)

    # دخل روم صوتي
    if before.channel is None and after.channel is not None:
        voice_timers[user_id] = asyncio.get_event_loop().time()
    
    # خرج من الروم الصوتي
    elif before.channel is not None and after.channel is None:
        if user_id in voice_timers:
            del voice_timers[user_id]

# مهمة خلفية لحساب نقاط الصوت كل دقيقة
async def voice_xp_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(60) # كل دقيقة
        current_time = asyncio.get_event_loop().time()
        
        for user_id, join_time in list(voice_timers.items()):
            if current_time - join_time >= 60:
                for guild in bot.guilds:
                    member = guild.get_member(int(user_id))
                    if member and member.voice and member.voice.channel:
                        guild_id = str(guild.id)
                        xp_to_add = 10 # 10 XP لكل دقيقة صوتية

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

# أمر لعرض اللفل (!rank)
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

    avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    await ctx.send(f"📊 **User Level:** {ctx.author.name}\n🌟 **Level:** {current_level}\n✨ **XP:** {current_xp} / {needed_xp}\n🖼️ {avatar_url}")

# تشغيل سيرفر الويب والبوت معاً
if __name__ == '__main__':
    keep_alive()
    bot.loop.create_task(voice_xp_loop())
    bot.run(os.environ.get('TOKEN'))

