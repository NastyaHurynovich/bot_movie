import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import markdown
from dotenv import load_dotenv

import movie

load_dotenv()
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    raise Exception("Токен не найден")

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)


class UserState(StatesGroup):
    movie = State()
    movie_detail_menu = State()
    cast = State()


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.reply("Добро пожаловать в бота-помощника по выбору фильма!")


def get_movie_caption(movie_instance) -> str:
    movie_dict = dict(movie_instance)
    rating = movie_dict["rating"]
    genres = " ".join(movie_dict["genres"])
    title = movie_dict["localized title"]
    caption = markdown.text(
        markdown.text(markdown.bold("Название фильма: "), title),
        markdown.text(markdown.bold("Рейтинг: "), rating),
        markdown.text(markdown.bold("Жанр: "), genres),
        sep="\n",
    )
    return caption


def get_movie_image(movie_instance) -> str:
    movie_dict = dict(movie_instance)
    image = movie_dict["full-size cover url"]
    return image


def get_movie_cast(movie_instance) -> str:
    movie_dict = dict(movie_instance)
    cast = movie_dict["cast"]
    message = "\n".join([f"{index + 1}: {actor}" for index, actor in enumerate(cast)])
    return message


@dp.message_handler(commands=["random", "help"])
async def send_random_movie(message: types.Message, state):
    movie_instance = movie.get_random_movie()
    await UserState.movie.set()
    async with state.proxy() as data:
        data["movie"] = movie_instance.movieID
    markup = types.ReplyKeyboardMarkup()
    markup.add("Подробнее")
    await bot.send_photo(
        message.chat.id,
        get_movie_image(movie_instance),
        caption=get_movie_caption(movie_instance),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=markup,
    )


@dp.message_handler(lambda message: message.text == "Подробнее", state=UserState.movie)
async def movie_detail(message: types.Message, state):
    await UserState.next()
    markup = types.ReplyKeyboardMarkup()
    markup.add("Показать актёров")
    markup.add("Показать режисёров")
    await message.reply("Выберите действие 👇", reply_markup=markup)


@dp.message_handler(lambda message: message.text == "Показать актёров", state=UserState.movie_detail_menu)
async def movie_cast(message: types.Message, state):
    await UserState.cast.set()
    async with state.proxy() as data:
        movie_id = data["movie"]
        movie_instance = movie.ia.get_movie(movie_id)
        message_text = get_movie_cast(movie_instance)
        await bot.send_message(message.chat.id, message_text)


# You can use state '*' if you need to handle all states
@dp.message_handler(state="*", commands="cancel")
@dp.message_handler(Text(equals="cancel", ignore_case=True), state="*")
async def cancel_handler(message: types.Message, state):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply("Cancelled.", reply_markup=types.ReplyKeyboardRemove())


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
