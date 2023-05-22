from PIL import Image
from lib.image_hadler import ImageHandler
import os
import io
from dotenv import load_dotenv
import logging
import asyncio

from aiogram.utils import executor
from aiogram import Bot, Dispatcher, types
from aiogram.types import ContentType
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from telethon import TelegramClient, events
from telethon.tl.types import InputMessagesFilterPhotos
from telethon.tl.types import InputPeerChat
from telethon import types as telethon_types

from pathlib import Path

load_dotenv()

logging.basicConfig(level=logging.INFO)
API_TOKEN = os.getenv('TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

chats = {}

HELP_COMMAND = """
<b>/start</b> - <i>Инициализирует чат</i>
<b>/help</b> - <i>Выведет список команд и их описания</i>
<b>/image <u>description [count]</u></b> - <i>Предоставит изображение по описанию</i>
<b>/auth</b> - <i>Процесс авторизации пользователя для дальнейшего получения истории чата</i>
<b>/get_history</b> - <i>Получение истории чата</i>
<b>/disconnect</b> - <i>Процесс выхода из сессии бота</i>
"""

# in the future, if I wouldn't be lazy :), I will fix this strange duplicated keyboards

keyboard_phone = InlineKeyboardMarkup()
keyboard_code = InlineKeyboardMarkup()

buttons_numbers_emoji_phone = [['1️⃣', 'p1'], ['2️⃣', 'p2'], ['3️⃣', 'p3'], ['4️⃣', 'p4'], ['5️⃣', 'p5'], ['6️⃣', 'p6'],
                               ['7️⃣', 'p7'], ['8️⃣', 'p8'], ['9️⃣', 'p9']]

buttons_numbers_emoji_code = [['1️⃣', 'c1'], ['2️⃣', 'c2'], ['3️⃣', 'c3'], ['4️⃣', 'c4'], ['5️⃣', 'c5'], ['6️⃣', 'c6'],
                              ['7️⃣', 'c7'], ['8️⃣', 'c8'], ['9️⃣', 'c9']]

buttons_special_emoji = ["🔄", "0️⃣", "⤴️", "➕"]

for i in range(0, len(buttons_numbers_emoji_code), 3):
    keyboard_phone.row(
        InlineKeyboardButton(buttons_numbers_emoji_phone[i][0], callback_data=buttons_numbers_emoji_phone[i][1]),
        InlineKeyboardButton(buttons_numbers_emoji_phone[i + 1][0],
                             callback_data=buttons_numbers_emoji_phone[i + 1][1]),
        InlineKeyboardButton(buttons_numbers_emoji_phone[i + 2][0],
                             callback_data=buttons_numbers_emoji_phone[i + 2][1]))
    keyboard_code.row(
        InlineKeyboardButton(buttons_numbers_emoji_code[i][0], callback_data=buttons_numbers_emoji_code[i][1]),
        InlineKeyboardButton(buttons_numbers_emoji_code[i + 1][0],
                             callback_data=buttons_numbers_emoji_code[i + 1][1]),
        InlineKeyboardButton(buttons_numbers_emoji_code[i + 2][0],
                             callback_data=buttons_numbers_emoji_code[i + 2][1]))

keyboard_phone.row(InlineKeyboardButton(buttons_special_emoji[0], callback_data="preset"),
                   InlineKeyboardButton(buttons_special_emoji[1], callback_data="p0"),
                   InlineKeyboardButton(buttons_special_emoji[2], callback_data="psend"))

keyboard_code.row(InlineKeyboardButton(buttons_special_emoji[0], callback_data="creset"),
                  InlineKeyboardButton(buttons_special_emoji[1], callback_data="c0"),
                  InlineKeyboardButton(buttons_special_emoji[2], callback_data="csend"))

keyboard_phone.row(InlineKeyboardButton(buttons_special_emoji[3], callback_data="c+"))


def init_chat(id):
    chats[id] = {"image_handler": ImageHandler()}


async def download_image_aio(file_id):
    file = await bot.get_file(file_id)
    file_bytes = io.BytesIO()
    await file.download(destination=file_bytes)
    return file_bytes.getvalue()


async def download_images_aio(file_ids):
    tasks = [download_image_aio(file_id) for file_id in file_ids]
    return await asyncio.gather(*tasks)


async def process_images_aio(file_ids, chat_id):
    image_bytes = await download_images_aio(file_ids)
    for j in range(len(file_ids)):
        image = Image.open(io.BytesIO(image_bytes[j]))
        chats[chat_id]["image_handler"].process_image(image, file_ids[j], "a")


async def process_image_command(message: types.Message):
    args = message.get_args()
    if args == "":
        await message.reply("Шерлоку нужна ваша улика! Пожалуйста введите описание изображения.")
        return

    parts = args.rsplit(" ", 1)
    if len(parts) == 1 or not (parts[-1].isdigit()):
        image_text = args
        count = 1
    else:
        image_text = parts[0]
        count = int(parts[1])

    images_id = chats[message.chat.id]["image_handler"].get_images(image_text, count)
    for (image_id, api_image) in images_id:
        try:
            if api_image == "a":
                await bot.send_photo(chat_id=message.chat.id, photo=image_id)
            elif api_image == "t":
                msg = await chats[message.chat.id]["client"].get_messages(message.chat.id, ids=image_id)
                photo_bytes = await chats[message.chat.id]["client"].download_media(msg.photo, bytes)
                await bot.send_photo(chat_id=message.chat.id, photo=photo_bytes)
            else:
                _ = 1 / 0
        except:
            await bot.send_message(message.chat.id, 'К сожалению, кто-то подтёр улики, поэтому изображение было потеряно, требуется полный перезапуск, для анализа всех изображений, начните со /start')


@dp.message_handler(commands=["image"])
async def process_image_command_handler(message: types.Message):
    await process_image_command(message)


@dp.message_handler(content_types=["photo"])
async def handle_photos(message: types.Message):
    await process_images_aio([message.photo[-1].file_id], message.chat.id)


@dp.message_handler(commands=["get_history"])
async def get_history_handler(message: types.Message):
    if message.chat.id in chats:
        if "client" in chats[message.chat.id]:
            client = chats[message.chat.id]["client"]
            if await client.is_user_authorized():
                me = await client.get_me()
                count = 0
                if me is not None and me.bot:
                    await bot.send_message(message.chat.id, 'Зафиксирован ботяра, пропуск к истории чата запрещен!')
                else:

                    async for msg in client.iter_messages(message.chat.id, filter=InputMessagesFilterPhotos):
                        count += 1
                        photo_bytes = await client.download_media(msg.photo, bytes)
                        image = Image.open(io.BytesIO(photo_bytes))
                        chats[message.chat.id]["image_handler"].process_image(image, msg.id, "t")

                    await bot.send_message(message.chat.id, f'Успех! Сохранено {count} изображений.')
            else:
                await bot.send_message(message.chat.id, 'Вы не авторизованы!')
        else:
            await bot.send_message(message.chat.id, 'Вы не добавили рут пользователя чата!')
    else:
        await bot.send_message(message.chat.id, 'Чат не стартовал даже :)')


@dp.message_handler(commands=["disconnect"])
async def disconnect_handler(message: types.Message):
    if message.chat.id in chats:
        if "client" in chats[message.chat.id]:
            client = chats[message.chat.id]["client"]
            client.disconnect()
            await bot.send_message(message.chat.id, 'Успешно вышли!')
        else:
            await bot.send_message(message.chat.id, 'Вы не добавили рут пользователя чата!')
        chats[message.chat.id] = {}
    else:
        await bot.send_message(message.chat.id, 'Чат не стартовал даже :)')


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    init_chat(message.chat.id)
    await bot.send_message(chat_id=message.chat.id, text='Приветствую!')


@dp.message_handler(commands=["help"])
async def help_handler(message: types.Message):
    await message.reply(text=HELP_COMMAND, parse_mode='HTML')


@dp.message_handler(commands=['auth'])
async def auth_handler(message: types.Message):
    chat_id = message.chat.id

    if chat_id in chats:
        chats[chat_id]["phone"] = ""
        chats[chat_id]["client"] = TelegramClient(f"src/{chat_id}", API_ID, API_HASH, system_version="4.16.30-vxCUSTOM")
        await chats[chat_id]["client"].connect()
    else:
        await message.reply('Бот не был добавлен в данный чат')

    if await chats[chat_id]["client"].is_user_authorized():
        await bot.send_message(chat_id=message.chat.id, text='Сохранена авторизация с прошлого запуска!')
    else:
        await bot.send_message(chat_id=message.chat.id, text='Введите номер телефона:', reply_markup=keyboard_phone)


@dp.callback_query_handler(lambda c: True)
async def process_callback_button(callback_query: types.CallbackQuery):
    button = callback_query.data
    chat_id = callback_query.message.chat.id
    state = "phone" if button[0] == "p" else "code"
    if button[1:] == "reset":
        chats[chat_id][state] = ""
        await bot.answer_callback_query(callback_query.id, text='Выполнен сброс')
    elif button[1:] == "send":
        if state == "phone":
            try:
                await chats[chat_id]["client"].send_code_request(chats[chat_id]["phone"])
                await bot.answer_callback_query(callback_query.id,
                                                text="Номер телефона был получен, подтвердите авторизацию")
                await bot.delete_message(chat_id=callback_query.message.chat.id,
                                         message_id=callback_query.message.message_id)
                chats[chat_id]["code"] = ""
                await bot.send_message(chat_id=chat_id, text='Введите код:', reply_markup=keyboard_code)
            except:
                await bot.delete_message(chat_id=callback_query.message.chat.id,
                                         message_id=callback_query.message.message_id)
                await bot.answer_callback_query(callback_query.id,
                                                text="Номер телефона неверный")
        else:
            try:
                code = chats[chat_id]["code"]
                await chats[chat_id]["client"].sign_in(chats[chat_id]["phone"], code)
                chats[chat_id]["client"].session.save()
                await bot.answer_callback_query(callback_query.id, text='Авторизация прошла успешно!')
                await bot.delete_message(chat_id=callback_query.message.chat.id,
                                         message_id=callback_query.message.message_id)
            except:
                await bot.delete_message(chat_id=callback_query.message.chat.id,
                                         message_id=callback_query.message.message_id)
                await bot.answer_callback_query(callback_query.id,
                                                text="Код неверный")

    elif button[1:] in "+0123456789":
        chats[chat_id][state] = chats[chat_id][state] + button[1:]
        await bot.answer_callback_query(callback_query.id)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)