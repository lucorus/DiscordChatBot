import random
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
    if not user:
        user = ctx.author
    # берём данные покупающего пользователя
    c.execute("SELECT * FROM users WHERE user_id=?", (ctx.author.id,))
    buyer = c.fetchone()
    # берём данные товара
    c.execute('SELECT * FROM assortment WHERE title=?', (title,))
    item = c.fetchone()

    # если такой товар существует, то забираем его стоимость и увеличиваем кол-во баллов за сообщение
    if item != None:
        # если у покупающего баллов больше, чем нужно (или ровно столько), то он может купить
        if buyer[1] >= 10:

            # забираем баллы у купившего
            c.execute("UPDATE users SET points=? WHERE user_id=?", (buyer[1] - item[2], ctx.author.id))

            # изменяем кол-во баллов за сообщение пользователю
            c.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
            user_data = c.fetchone()

            c.execute("UPDATE users SET payment=? WHERE user_id=?", (user_data[3] + item[1], user.id))
            await ctx.send(f'{user.name} теперь получает больше баллов за сообщение!')
        else:
            await ctx.send('У вас нет нужного количества баллов')
    else:
        await ctx.send('Товар не найден')


@bot.command(name='info')
async def info(ctx):
    await ctx.reply('Этот бот даёт баллы за сообщение (1 раз в минуту), вы можете увеличить количество баллов,'
                    ' получаемых за сообщение с помощью команды !buy @user "предмет, который вы хотите купить"'
                    ' (узнать ассортимент предметов можно с помощью команды !assortment). \n'
                    ' Чтобы узнать количество баллов используй команду !points @user. \n'
                    ' Чтобы узнать количество баллов, получаемых за сообщение используй команду !payment @user. \n'
                    ' Чтобы попытать удачу в казино нужно использовать команду !casino и написать ставку. \n')


@bot.command(name='add_item')
async def add_item(ctx, title: str, upgrade: int, price: int):
    if ctx.author.id == 854253015862607872:
        c.execute("INSERT INTO assortment VALUES (?, ?, ?)", (title, upgrade, price))
        await ctx.send(f'Товар с названием { title } был добавлен, его цена = { price }, '
                       f'он добавляет к получаемым баллам за сообщение { upgrade } баллов ')
    else:
        await ctx.send('У вас недостаточно прав для этого действия')


# отображает список товаров (почему-то первый товар не отображается)
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


# максимальное количество одинаковых цифр в числе
def max_count_figure(number):
    number = str(number)
    max_count = 1
    for i in range(0, 10):
        count_number = number.count(str(i))
        if count_number > max_count:
            max_count = count_number
    return max_count


# создаёт случайное трёхзначное число, если 2 цифры одинаковые - выигрыш 1.5Х, если 3 одинаковые, то выигрыш = 3Х
@bot.command(name='casino')
async def casino(ctx, bet):
    try:
        # если ставка не является числом, то будет исключение
        bet = int(bet)
        # если ставка = 0, то будет исключение
        t = 10
        t = t / bet
        # если ставка отрицательная, то делаем её положительной
        if bet < 0:
            bet = bet * -1

        c.execute('SELECT * FROM users WHERE user_id=?', (ctx.author.id,))
        user_data = c.fetchone()

        # проверяем количество баллов пользователя
        if user_data[1] >= bet:
            number = random.randint(100, 999)
            # считаем количество одинаковых цифр
            count_figure = max_count_figure(number)

            if count_figure == 1:
                c.execute("UPDATE users SET points=? WHERE user_id=?", (user_data[1] - bet, ctx.author.id))
                if bet >= 1000:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов ))))')
                else:
                    await ctx.reply(f'Выпало число {number} \nВы проиграли {bet} баллов')

            elif count_figure == 2:
                c.execute("UPDATE users SET points=? WHERE user_id=?",
                          (user_data[1] + ((bet * 1.5) // 1), ctx.author.id))
                await ctx.reply(f'Выпало число {number} \nВы выиграли {int((bet * 1.5) // 1)} баллов!')

            elif count_figure == 3:
                c.execute("UPDATE users SET points=? WHERE user_id=?", (user_data[1] + (bet * 3), ctx.author.id))
                await ctx.reply(f'Выпало число {number} \nВы выиграли {bet * 3} баллов!')

        else:
            await ctx.reply('У вас не хватает баллов для этой ставки')
    except:
        await ctx.reply('Вы ввели некорректную ставку')


bot.run(config.token)
