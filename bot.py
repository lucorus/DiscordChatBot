import discord
from discord.ext import commands
import asyncio
import sqlite3
from datetime import datetime
import config

intents = discord.Intents.all()

bot = commands.Bot('!', intents=intents)
points = {}

# Подключение к базе данных
conn = sqlite3.connect('mydatabase.db')
c = conn.cursor()

# Создание таблицы
c.execute('''CREATE TABLE IF NOT EXISTS users
 (user_id INTEGER PRIMARY KEY, points INTEGER, last_message_time INTEGER, payment INTEGER)''')


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Получение данных пользователя из базы данных
    c.execute("SELECT * FROM users WHERE user_id=?", (message.author.id,))
    user_data = c.fetchone()

    if user_data is None:
        # Если пользователь не найден, добавляем его в базу данных
        c.execute("INSERT INTO users VALUES (?, ?, ?, 1)", (message.author.id, 0, int(datetime.utcnow().timestamp())))
    else:
        # Если пользователь найден, проверяем время последнего сообщения
        last_message_time = user_data[2]
        current_time = int(datetime.utcnow().timestamp())
        time_difference = current_time - last_message_time

        # Если прошло больше минуты, добавляем баллы и обновляем время последнего сообщения
        if time_difference > 60:
            c.execute("UPDATE users SET points=?, last_message_time=? WHERE user_id=?", (user_data[1] + user_data[3], current_time, message.author.id))

    conn.commit()
    await bot.process_commands(message)


# Обновление баллов пользователей раз в минуту
@bot.event
async def on_ready():
    while True:
        await asyncio.sleep(60)


# Получаем количество баллов пользователя
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


# Получаем количество получаемых баллов за сообщение пользователя
@bot.command(name='payment')
async def get_user_payment(ctx, user: discord.Member=None):
    if not user:
        user = ctx.author
    c.execute("SELECT payment FROM users WHERE user_id=?", (user.id,))
    result = c.fetchone()
    if result:
        await ctx.send(f"Количество баллов за сообщение у {user.mention}: {result[0]}")
    else:
        await ctx.send(f"Количество баллов за сообщение у {user.mention}: 0")


# пользователь может купить предмет, увеличивающий кол-во баллов за сообщение (себе или другому человеку)
@bot.command(name='buy')
async def buy(ctx, user: discord.Member=None):
    if not user:
        user = ctx.author
    # берём данные покупающего пользователя
    c.execute("SELECT * FROM users WHERE user_id=?", (ctx.author.id,))
    buyer = c.fetchone()
    # если у покупающего баллов больше, чем нужно (или ровно столько), то он может купить
    if buyer[1] >= 10:

        # забираем баллы у купившего
        c.execute("UPDATE users SET points=? WHERE user_id=?",(buyer[1] - 10, ctx.author.id))

        # изменяем кол-во баллов за сообщение пользователю
        c.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
        user_data = c.fetchone()
        c.execute("UPDATE users SET payment=? WHERE user_id=?", (user_data[3] + 1, user.id))
        await ctx.send(f'{ user.name } теперь получает больше баллов за сообщение!')
    else:
        await ctx.send('У вас нет нужного количества баллов')


bot.run(config.token)
