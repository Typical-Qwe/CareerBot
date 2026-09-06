"""
Демо карьерного Telegram-бота на pyTelegramBotAPI (TeleBot).

Функции демо-версии:
- Тест-опросник из 5 вопросов с кнопками -> подбор 3 профессий по совпадению тегов интересов
- Каталог профессий по категориям (инлайн-кнопки)
- Карточка профессии с полным описанием
- Свободный текстовый запрос (демо-поиск по ключевым словам; точка расширения под LLM/NLU)
- Основное меню в виде reply-кнопок

Запуск:
    export BOT_TOKEN=твой_токен_от_BotFather
    pip install -r requirements.txt
    python bot.py

Примечание про состояние (state):
TeleBot синхронный и не имеет встроенного FSM, как aiogram. Прогресс теста
хранится в простом словаре в памяти процесса (quiz_state) — этого достаточно
для демо, но при перезапуске бота или при масштабировании на несколько
процессов/воркеров это состояние теряется. Для продакшена см. README.md.
"""

import json
import logging
import os
from pathlib import Path

import telebot
from telebot import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_TOKEN_HERE")
DATA_PATH = Path(__file__).parent / "data" / "professions.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    PROFESSIONS = json.load(f)["professions"]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Прогресс теста на пользователя: {user_id: {"step": int, "scores": dict}}
quiz_state = {}


# ---------- Вопросы теста ----------
# Каждый вариант ответа "весит" в пользу одного из тегов интересов.
# Теги должны совпадать с interest_tags в professions.json

QUESTIONS = [
    {
        "text": "1/5. Что тебе больше нравится делать в свободное время?",
        "options": [
            ("Придумывать истории, рисовать, создавать что-то новое", "creative"),
            ("Разбираться, как что-то устроено — от механизмов до кода", "tech"),
            ("Общаться, помогать друзьям разобраться в их проблемах", "people"),
            ("Решать логические задачи, головоломки, считать", "analytical"),
        ],
    },
    {
        "text": "2/5. В групповой работе (школа/универ/проекты) тебе комфортнее...",
        "options": [
            ("Придумывать идею и вести за собой", "leadership"),
            ("Дотошно проверять детали и не допускать ошибок", "detail"),
            ("Предлагать творческие решения", "creative"),
            ("Работать в одиночку и потом показать результат", "independent"),
        ],
    },
    {
        "text": "3/5. Какой школьный предмет был тебе ближе всего?",
        "options": [
            ("Информатика / математика", "tech"),
            ("Обществознание / история / литература", "people"),
            ("Биология / химия / физика", "science"),
            ("ИЗО / технология / музыка", "creative"),
        ],
    },
    {
        "text": "4/5. Что для тебя важнее в будущей работе?",
        "options": [
            ("Стабильность и понятный карьерный путь", "stability"),
            ("Свобода и возможность работать откуда угодно", "freedom"),
            ("Высокий доход, даже если придётся рисковать", "income"),
            ("Ощущение, что я приношу пользу людям", "impact"),
        ],
    },
    {
        "text": "5/5. Если бы не было ограничений, ты бы...",
        "options": [
            ("Запустил(а) свой стартап", "leadership"),
            ("Изучал(а) новые технологии и разрабатывал(а) продукты", "tech"),
            ("Работал(а) с людьми — обучал(а), лечил(а), консультировал(а)", "people"),
            ("Создавал(а) что-то в искусстве, дизайне, медиа", "creative"),
        ],
    },
]


def build_quiz_keyboard(step: int) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    for text, tag in QUESTIONS[step]["options"]:
        markup.add(types.InlineKeyboardButton(text=text, callback_data=f"quiz:{step}:{tag}"))
    return markup


def main_menu_keyboard() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🧭 Пройти тест на профориентацию"))
    markup.add(types.KeyboardButton("📚 Профессии по категориям"))
    markup.add(types.KeyboardButton("💬 Спросить своими словами"))
    markup.add(types.KeyboardButton("ℹ️ О боте"))
    return markup


def categories_keyboard() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    categories = sorted({p["category"] for p in PROFESSIONS})
    for cat in categories:
        markup.add(types.InlineKeyboardButton(text=cat, callback_data=f"cat:{cat}"))
    return markup


# ---------- /start и /help ----------

@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    quiz_state.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "Привет! 👋 Я помогу тебе разобраться, какая профессия может тебе подойти "
        "— или найти новое направление, если ты устал(а) от текущей работы.\n\n"
        "Можно пройти короткий тест (2 минуты), полистать профессии по категориям "
        "или просто написать мне, что тебя беспокоит своими словами.",
        reply_markup=main_menu_keyboard(),
    )


@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message):
    send_help(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "ℹ️ О боте")
def cmd_help_button(message: types.Message):
    send_help(message.chat.id)


def send_help(chat_id: int):
    bot.send_message(
        chat_id,
        "Это демо-версия карьерного бота.\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "/test — пройти тест на профориентацию\n"
        "/professions — посмотреть профессии по категориям\n"
        "/ask — описать запрос своими словами\n\n"
        "Также можно просто написать сообщение — бот постарается понять запрос.",
    )


# ---------- Тест-опросник ----------

@bot.message_handler(commands=["test"])
def cmd_test(message: types.Message):
    start_quiz(message.chat.id, message.from_user.id)


@bot.message_handler(func=lambda m: m.text == "🧭 Пройти тест на профориентацию")
def cmd_test_button(message: types.Message):
    start_quiz(message.chat.id, message.from_user.id)


def start_quiz(chat_id: int, user_id: int):
    quiz_state[user_id] = {"step": 0, "scores": {}}
    bot.send_message(chat_id, QUESTIONS[0]["text"], reply_markup=build_quiz_keyboard(0))


@bot.callback_query_handler(func=lambda call: call.data.startswith("quiz:"))
def process_quiz_answer(call: types.CallbackQuery):
    _, step_str, tag = call.data.split(":")
    step = int(step_str)
    user_id = call.from_user.id

    state = quiz_state.setdefault(user_id, {"step": 0, "scores": {}})
    scores = state["scores"]
    scores[tag] = scores.get(tag, 0) + 1

    next_step = step + 1
    if next_step < len(QUESTIONS):
        state["step"] = next_step
        bot.edit_message_text(
            QUESTIONS[next_step]["text"],
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=build_quiz_keyboard(next_step),
        )
    else:
        bot.edit_message_text(
            "Готово! Считаю результат... 🔎",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )
        show_quiz_results(call.message.chat.id, scores)
        quiz_state.pop(user_id, None)

    bot.answer_callback_query(call.id)


def match_professions(scores: dict, top_n: int = 3):
    ranked = []
    for prof in PROFESSIONS:
        tags = set(prof.get("interest_tags", []))
        weight = sum(scores.get(tag, 0) for tag in tags)
        if weight > 0:
            ranked.append((weight, prof))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked:
        return PROFESSIONS[:top_n]
    return [p for _, p in ranked[:top_n]]


def show_quiz_results(chat_id: int, scores: dict):
    top_matches = match_professions(scores)

    text = "По твоим ответам тебе может подойти:\n\n"
    for i, prof in enumerate(top_matches, start=1):
        text += f"{i}. <b>{prof['name']}</b>\n   {prof['short_description']}\n\n"
    text += "Нажми на профессию ниже, чтобы узнать подробнее 👇"

    markup = types.InlineKeyboardMarkup()
    for p in top_matches:
        markup.add(types.InlineKeyboardButton(text=p["name"], callback_data=f"prof:{p['id']}"))
    markup.add(types.InlineKeyboardButton(text="🔄 Пройти тест заново", callback_data="restart_quiz"))

    bot.send_message(chat_id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "restart_quiz")
def restart_quiz(call: types.CallbackQuery):
    start_quiz(call.message.chat.id, call.from_user.id)
    bot.answer_callback_query(call.id)


# ---------- Каталог по категориям ----------

@bot.message_handler(commands=["professions"])
def cmd_professions(message: types.Message):
    bot.send_message(message.chat.id, "Выбери категорию:", reply_markup=categories_keyboard())


@bot.message_handler(func=lambda m: m.text == "📚 Профессии по категориям")
def cmd_professions_button(message: types.Message):
    bot.send_message(message.chat.id, "Выбери категорию:", reply_markup=categories_keyboard())


@bot.callback_query_handler(func=lambda call: call.data.startswith("cat:"))
def show_category(call: types.CallbackQuery):
    category = call.data.split(":", 1)[1]
    items = [p for p in PROFESSIONS if p["category"] == category]

    markup = types.InlineKeyboardMarkup()
    for p in items:
        markup.add(types.InlineKeyboardButton(text=p["name"], callback_data=f"prof:{p['id']}"))
    markup.add(types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back_to_cats"))

    bot.edit_message_text(
        f"Профессии в категории «{category}»:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup,
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "back_to_cats")
def back_to_categories(call: types.CallbackQuery):
    bot.edit_message_text(
        "Выбери категорию:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=categories_keyboard(),
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("prof:"))
def show_profession_card(call: types.CallbackQuery):
    prof_id = call.data.split(":", 1)[1]
    prof = next((p for p in PROFESSIONS if p["id"] == prof_id), None)
    if not prof:
        bot.answer_callback_query(call.id, "Профессия не найдена", show_alert=True)
        return

    text = (
        f"<b>{prof['name']}</b>\n"
        f"Категория: {prof['category']}\n\n"
        f"{prof['full_description']}\n\n"
        f"<b>Нужные навыки:</b> {', '.join(prof['required_skills'])}\n"
        f"<b>Куда идти учиться:</b> {prof['education_paths']}\n"
        f"<b>Зарплатная вилка (ориентир):</b> {prof['salary_range']}\n"
        f"<b>Перспективы:</b> {prof['growth_outlook']}\n"
    )
    if prof.get("related_professions"):
        text += f"\n<b>Похожие профессии:</b> {', '.join(prof['related_professions'])}"

    bot.send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)


# ---------- Свободный текстовый запрос ----------
# Демо-версия ищет по ключевым словам. Точка расширения: заменить на вызов
# языковой модели (например, Anthropic API) для более гибкого понимания запроса —
# см. раздел "Как расширять" в README.md.

@bot.message_handler(commands=["ask"])
def cmd_ask(message: types.Message):
    ask_free_query(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "💬 Спросить своими словами")
def cmd_ask_button(message: types.Message):
    ask_free_query(message.chat.id)


def ask_free_query(chat_id: int):
    sent = bot.send_message(
        chat_id,
        "Расскажи своими словами, что тебя волнует: например, "
        "«устал(а) от бухгалтерии, хочу что-то творческое» или "
        "«люблю биологию и хочу помогать людям». Я постараюсь подобрать варианты.",
    )
    bot.register_next_step_handler(sent, process_free_text)


def process_free_text(message: types.Message):
    query = (message.text or "").lower()

    scored = []
    for prof in PROFESSIONS:
        haystack = " ".join(
            [prof["name"], prof.get("short_description", "")] + prof.get("keywords", [])
        ).lower()
        score = sum(1 for word in query.split() if len(word) > 3 and word in haystack)
        if score > 0:
            scored.append((score, prof))
    scored.sort(key=lambda x: x[0], reverse=True)
    matches = [p for _, p in scored[:3]]

    if not matches:
        bot.send_message(
            message.chat.id,
            "Пока не нашёл точного совпадения по ключевым словам 🙈\n"
            "В демо-версии поиск простой (по словам из базы). В боевой версии здесь "
            "будет подключена языковая модель, которая понимает запрос глубже.\n\n"
            "Попробуй пройти тест — /test — так результат будет точнее.",
        )
        return

    text = "Вот что удалось подобрать по твоему запросу:\n\n"
    markup = types.InlineKeyboardMarkup()
    for p in matches:
        text += f"• <b>{p['name']}</b> — {p['short_description']}\n"
        markup.add(types.InlineKeyboardButton(text=p["name"], callback_data=f"prof:{p['id']}"))

    bot.send_message(message.chat.id, text, reply_markup=markup)


# ---------- Фолбэк (регистрируется последним) ----------

@bot.message_handler(func=lambda m: True, content_types=["text"])
def fallback(message: types.Message):
    bot.send_message(
        message.chat.id,
        "Не совсем понял 🙂 Выбери действие из меню ниже, или напиши /ask, "
        "чтобы описать свой запрос своими словами.",
        reply_markup=main_menu_keyboard(),
    )


if __name__ == "__main__":
    logger.info("Бот запущен, жду сообщений...")
    bot.infinity_polling(skip_pending=True)