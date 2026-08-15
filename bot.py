import os
import sqlite3
import discord
from discord.ext import commands

# إعداد الصلاحيات (Intents)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# إعداد قاعدة البيانات لحفظ الليفلات والنقاط
conn = sqlite3.connect("levels.db")
cursor = conn.cursor()
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    guild_id INTEGER,
    exp INTEGER,
    level INTEGER,
    PRIMARY KEY (user_id, guild_id)
)
"""
)
conn.commit()


@bot.event
async def on_ready():
  print(f"تم تسجيل الدخول بنجاح باسم: {bot.user}")


@bot.event
async def on_message(message):
  # تجاهل رسائل البوتات
  if message.author.bot:
    return

  user_id = message.author.id
  guild_id = message.guild.id

  cursor.execute(
      "SELECT exp, level FROM users WHERE user_id = ? AND guild_id = ?",
      (user_id, guild_id),
  )
  result = cursor.fetchone()

  if result is None:
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, guild_id, 15, 1)
    )
  else:
    exp, level = result
    exp += 15

    # معادلة حساب الليفل (كل 100 نقطة ضرب الليفل الحالي = ليفل جديد)
    if exp >= level * 100:
      level += 1
      exp = 0
      await message.channel.send(
          f"مبروك {message.author.mention}! لقد صعدت إلى المستوى **{level}** 🎉"
      )

    cursor.execute(
        "UPDATE users SET exp = ?, level = ? WHERE user_id = ? AND guild_id ="
        " ?",
        (exp, level, user_id, guild_id),
    )

  conn.commit()
  await bot.process_commands(message)


# أمر لمعرفة الليفل الحالي
@bot.command(name="level", aliases=["rank"])
async def rank(ctx, member: discord.Member = None):
  member = member or ctx.author
  cursor.execute(
      "SELECT exp, level FROM users WHERE user_id = ? AND guild_id = ?",
      (member.id, ctx.guild.id),
  )
  result = cursor.fetchone()

  if result is None:
    await ctx.send(f"العضو {member.mention} ليس لديه أي نقاط بعد!")
  else:
    exp, level = result
    embed = discord.Embed(
        title=f"معلومات رتبة {member.name}", color=discord.Color.blue()
    )
    embed.add_field(name="المستوى (Level)", value=str(level), inline=True)
    embed.add_field(
        name="النقاط (XP)", value=f"{exp} / {level * 100}", inline=True
    )
    await ctx.send(embed=embed)


# قراءة التوكن بأمان من متغيرات البيئة في Render
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
