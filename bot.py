import discord
from discord.ext import commands
import asyncio
import sqlite3
from datetime import datetime, timedelta

import config

intents = discord.Intents.all()

# config = {
#     'token': 'MTAzNTI0NzI0MTQwMjc4NTg0Mg.Gzm1m3.Tp7sAuu2c9rCO9YbGlqVuAOUt90xucOTTDT0Rk',
#     'prefix': '!',
# }

bot = commands.Bot('!', intents=intents)
points = {}

# Подключение к базе данных
conn = sqlite3.connect('mydatabase.db')
c = conn.cursor()

# Создание таблицы
c.execute('''CREATE TABLE IF NOT EXISTS users
 (user_id INTEGER PRIMARY KEY, points INTEGER, last_message_time INTEGER)''')


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Получение данных пользователя из базы данных
    c.execute("SELECT * FROM users WHERE user_id=?", (message.author.id,))
    user_data = c.fetchone()

    if user_data is None:
        # Если пользователь не найден, добавляем его в базу данных
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (message.author.id, 0, int(datetime.utcnow().timestamp())))
    else:
        # Если пользователь найден, проверяем время последнего сообщения
        last_message_time = user_data[2]
        current_time = int(datetime.utcnow().timestamp())
        time_difference = current_time - last_message_time

        # Если прошло больше минуты, добавляем баллы и обновляем время последнего сообщения
        if time_difference > 60:
            c.execute("UPDATE users SET points=?, last_message_time=? WHERE user_id=?", (user_data[1] + 1, current_time, message.author.id))

    conn.commit()
    await bot.process_commands(message)


# Обновление баллов пользователей раз в минуту
@bot.event
async def on_ready():
    while True:
        await asyncio.sleep(10)


@bot.command(name='points')
async def get_user_points(ctx, user: discord.Member=None):
    if not user:
        user = ctx.author
    c.execute("SELECT points FROM users WHERE user_id=?", (user.id,))
    result = c.fetchone()
    if result:
        await ctx.send(f"Количество баллов у {user.mention}: {result[0]}")
    else:
        await ctx.send(f"Количество баллов у {user.mention}: 0")


bot.run(config.token)
