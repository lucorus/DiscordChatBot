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

c.execute('''CREATE TABLE IF NOT EXISTS assortment
 (title TEXT PRIMARY KEY, upgrade INTEGER, price INTEGER)''')


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


# товары, увеличивающие кол-во баллов за сообщение (первое число (индекс 0) - сколько баллов добавляет,
# а второе (индекс 1) - сколько стоит)
assortment = {
    'garage': (1, 10),
    'house': (10, 100),
}


# пользователь может купить предмет, увеличивающий кол-во баллов за сообщение (себе или другому человеку)
@bot.command(name='buy')
async def buy(ctx, user: discord.Member, title: str):
    if title not in assortment:
        await ctx.send('Товара с таким названием нет')
    else:
        if not user:
            user = ctx.author
        # берём данные покупающего пользователя
        c.execute("SELECT * FROM users WHERE user_id=?", (ctx.author.id,))
        buyer = c.fetchone()
        # если у покупающего баллов больше, чем нужно (или ровно столько), то он может купить
        if buyer[1] >= 10:

            c.execute('SELECT * FROM assortment WHERE title=?', (title, ))
            print(c.fetchone())
            # забираем баллы у купившего
            c.execute("UPDATE users SET points=? WHERE user_id=?", (buyer[1] - assortment[title][1], ctx.author.id))

            # изменяем кол-во баллов за сообщение пользователю
            c.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
            user_data = c.fetchone()
            c.execute("UPDATE users SET payment=? WHERE user_id=?", (user_data[3] + assortment[title][0], user.id))
            await ctx.send(f'{ user.name } теперь получает больше баллов за сообщение!')
        else:
            await ctx.send('У вас нет нужного количества баллов')


@bot.command(name='info')
async def info(ctx):
    await ctx.reply('Этот бот даёт баллы за сообщение (1 раз в минуту), вы можете увеличить количество баллов,'
                    ' получаемых за сообщение с помощью команды !buy @user "предмет, который вы хотите купить"'
                    ' (узнать ассортимент предметов можно с помощью команды !assortment). '
                    ' Чтобы узнать количество баллов используй команду !points @user.'
                    ' Чтобы узнать количество баллов, получаемых за сообщение используй команду !payment @user.')


@bot.command(name='add_item')
async def add_item(ctx, title: str, upgrade: int, price: int):
    if ctx.author.id == 854253015862607872:
        c.execute("INSERT INTO assortment VALUES (?, ?, ?)", (title, upgrade, price))
        await ctx.send(f'Товар с названием { title } был добавлен, его цена = { price }, '
                       f'он добавляет к получаемым баллам за сообщение { upgrade } баллов ')
    else:
        await ctx.send('У вас недостаточно прав для этого действия')


@bot.command(name='assortment')
async def see_assortment(ctx):
    c.execute("SELECT * FROM assortment")
    if c.fetchone() == None:
        await ctx.send('Товаров нет')
    else:
        assort = 'Список товаров: \n'
        for item in c.fetchall():
            assort += f'{ item[0] } имеет цену { item[2] } и добавляет { item[1] } баллов за сообщение \n'
        await ctx.send(assort)


@bot.command(name='delete_item')
async def delete_item(ctx, title):
    if ctx.author.id == 854253015862607872:
        c.execute("DELETE FROM assortment WHERE title=?", (title, ))
        await ctx.send('Товар успешно удалён')
    else:
        await ctx.send('У вас недостаточно прав для этого действия')


# изменяет количество баллов у пользователя (может как увеличить, так и уменьшить)
@bot.command(name='add_points')
async def add_points(ctx, number: str, user: discord.Member):
    if ctx.author.id == 854253015862607872:
        if number[0] == '-':
            num = int(number[1:len(number)]) * -1
        else:
            num = int(number)
        c.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
        user_data = c.fetchone()
        c.execute("UPDATE users SET points=? WHERE user_id=?", ((user_data[1] + num), user.id))
        await ctx.send('Действие успешно выполнено!')
    else:
        await ctx.send('У вас недостаточно прав для этого действия')


bot.run(config.token)
