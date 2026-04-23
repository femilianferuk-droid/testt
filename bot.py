import os
import json
import asyncio
import logging
import random
import uuid
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

LZT_API_KEY = os.getenv("LZT_API_KEY")

CRYPTO_BOT_API = "465788:AAOxwPgMIPTheqZpyAyN2JotJ9U8fREP7rl"
CRYPTO_API_URL = "https://pay.crypt.bot/api"

LZT_SHOP_ID = 2387
LZT_API_URL = "https://api.lzt.market"

ADMIN_IDS = [7973988177]
SUPPORT_USERNAME = "VestSupport"
BOT_USERNAME = "vestCasinoBot"
PRIVACY_URL = "https://telegra.ph/-04-23-2406"

USDT_RUB_RATE = 90

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== БАЗА ДАННЫХ ==========
DB_FILE = "users_db.json"

def load_db():
    """Загрузка базы данных"""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_db(data):
    """Сохранение базы данных"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(user_id):
    """Получение данных пользователя"""
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "balance": 0.0,
            "username": "",
            "first_name": "",
            "privacy_accepted": False,
            "stats": {
                "dice": {"wins": 0, "losses": 0},
                "basketball": {"wins": 0, "losses": 0},
                "football": {"wins": 0, "losses": 0},
                "blackjack": {"wins": 0, "losses": 0},
                "slots": {"wins": 0, "losses": 0},
                "roulette": {"wins": 0, "losses": 0},
                "total_won": 0.0,
                "total_lost": 0.0
            }
        }
        save_db(db)
    return db[uid]

def update_balance(user_id, amount):
    """Обновление баланса пользователя"""
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        get_user(user_id)
        db = load_db()
    db[uid]["balance"] = round(db[uid]["balance"] + amount, 2)
    if amount > 0:
        db[uid]["stats"]["total_won"] = round(db[uid]["stats"].get("total_won", 0) + amount, 2)
    else:
        db[uid]["stats"]["total_lost"] = round(db[uid]["stats"].get("total_lost", 0) + abs(amount), 2)
    save_db(db)
    return db[uid]["balance"]

def set_balance(user_id, amount):
    """Установка баланса пользователя"""
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        get_user(user_id)
        db = load_db()
    old_balance = db[uid]["balance"]
    db[uid]["balance"] = round(amount, 2)
    save_db(db)
    return old_balance, amount

def accept_privacy(user_id):
    """Принятие политики конфиденциальности"""
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        get_user(user_id)
        db = load_db()
    db[uid]["privacy_accepted"] = True
    save_db(db)

def add_game_stat(user_id, game, is_win):
    """Добавление статистики игры"""
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        get_user(user_id)
        db = load_db()
    if is_win:
        db[uid]["stats"][game]["wins"] += 1
    else:
        db[uid]["stats"][game]["losses"] += 1
    save_db(db)

def get_all_users():
    """Получение всех пользователей"""
    return load_db()

def update_user_info(user_id, username, first_name):
    """Обновление информации о пользователе"""
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        get_user(user_id)
        db = load_db()
    db[uid]["username"] = username or ""
    db[uid]["first_name"] = first_name or ""
    save_db(db)

# ========== ПРЕМИУМ ЭМОДЗИ ID ==========
EMOJI = {
    "settings": "5870982283724328568",
    "profile": "5870994129244131212",
    "wallet": "5769126056262898415",
    "dice": "5931754764612346688",
    "basketball": "5931840547685471475",
    "football": "5931844971057783046",
    "blackjack": "5931757626524760583",
    "slots": "5931771266437025976",
    "roulette": "5931775854535181369",
    "money": "5904462880941545555",
    "check": "5870633910337015697",
    "cross": "5870657884844462243",
    "back": "6037249452824072506",
    "info": "6028435952299413210",
    "stats": "5870921681735781843",
    "crypto": "5260752406890711732",
    "graph": "5870930636742595124",
    "home": "5873147866364514353",
    "edit": "5870676941614354370",
    "users": "5870772616305839506",
    "broadcast": "5370599459661045441",
    "loading": "5345906554510012647",
    "link": "5769289093221454192",
    "gift": "6032644646587338669",
    "send": "5963103826075456248",
    "games": "5778672437122045013",
    "withdraw": "5890848474563352982",
    "support": "6030400221232501136",
    "rub": "5904462880941545555",
    "lzt": "5260752406890711732",
    "star": "6032644646587338669",
}

def e(emoji_id):
    """Форматирование премиум эмодзи"""
    return f'<tg-emoji emoji-id="{emoji_id}">⚡</tg-emoji>'

# ========== FSM ==========
class DepositState(StatesGroup):
    """Состояния для пополнения"""
    waiting_for_amount_crypto = State()
    waiting_for_amount_rub = State()

class WithdrawState(StatesGroup):
    """Состояния для вывода"""
    waiting_for_amount = State()

class AdminStates(StatesGroup):
    """Состояния для админ-панели"""
    waiting_for_broadcast = State()
    waiting_for_edit_balance = State()

# ========== КЛАВИАТУРЫ ==========
def main_menu_keyboard():
    """Главное меню под полем ввода"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Профиль", icon_custom_emoji_id=EMOJI["profile"])],
            [KeyboardButton(text="Игры", icon_custom_emoji_id=EMOJI["games"])],
            [
                KeyboardButton(text="Пополнить", icon_custom_emoji_id=EMOJI["wallet"]),
                KeyboardButton(text="Вывод", icon_custom_emoji_id=EMOJI["withdraw"])
            ],
            [
                KeyboardButton(text="Помощь", icon_custom_emoji_id=EMOJI["info"]),
                KeyboardButton(text="Поддержка", icon_custom_emoji_id=EMOJI["support"])
            ],
        ],
        resize_keyboard=True
    )

def deposit_method_keyboard():
    """Клавиатура выбора способа пополнения"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Crypto Bot (USDT)",
        callback_data="deposit_crypto",
        icon_custom_emoji_id=EMOJI["crypto"]
    ))
    builder.row(InlineKeyboardButton(
        text="Рубли (LZT.Market)",
        callback_data="deposit_rub",
        icon_custom_emoji_id=EMOJI["rub"]
    ))
    builder.row(InlineKeyboardButton(
        text="Звёзды Telegram",
        callback_data="deposit_stars",
        icon_custom_emoji_id=EMOJI["star"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_menu_msg",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def privacy_keyboard():
    """Клавиатура принятия политики конфиденциальности"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Политика конфиденциальности",
        url=PRIVACY_URL,
        icon_custom_emoji_id=EMOJI["info"]
    ))
    builder.row(InlineKeyboardButton(
        text="Я ознакомился",
        callback_data="accept_privacy",
        icon_custom_emoji_id=EMOJI["check"],
        style="success"
    ))
    return builder.as_markup()

def games_menu_keyboard():
    """Меню выбора игр"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Кубик",
        callback_data="game_dice_start",
        icon_custom_emoji_id=EMOJI["dice"]
    ))
    builder.row(InlineKeyboardButton(
        text="Баскетбол",
        callback_data="game_basketball_start",
        icon_custom_emoji_id=EMOJI["basketball"]
    ))
    builder.row(InlineKeyboardButton(
        text="Футбол",
        callback_data="game_football_start",
        icon_custom_emoji_id=EMOJI["football"]
    ))
    builder.row(InlineKeyboardButton(
        text="Блэкджек",
        callback_data="game_blackjack_start",
        icon_custom_emoji_id=EMOJI["blackjack"]
    ))
    builder.row(InlineKeyboardButton(
        text="Слоты",
        callback_data="game_slots_start",
        icon_custom_emoji_id=EMOJI["slots"]
    ))
    builder.row(InlineKeyboardButton(
        text="Рулетка",
        callback_data="game_roulette_start",
        icon_custom_emoji_id=EMOJI["roulette"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_menu_msg",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def back_to_menu_keyboard():
    """Клавиатура возврата в меню"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Назад в меню",
        callback_data="back_to_menu_msg",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def back_to_admin_keyboard():
    """Клавиатура возврата в админ-панель"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="admin_panel",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def cancel_keyboard():
    """Клавиатура отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Отмена",
        callback_data="cancel_action",
        icon_custom_emoji_id=EMOJI["cross"]
    ))
    return builder.as_markup()

def support_keyboard():
    """Клавиатура поддержки"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Написать в поддержку",
        url=f"https://t.me/{SUPPORT_USERNAME}",
        icon_custom_emoji_id=EMOJI["support"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_menu_msg",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def admin_panel_keyboard():
    """Клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Рассылка",
        callback_data="admin_broadcast",
        icon_custom_emoji_id=EMOJI["broadcast"]
    ))
    builder.row(InlineKeyboardButton(
        text="Изменить баланс",
        callback_data="admin_edit_balance",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Статистика",
        callback_data="admin_stats",
        icon_custom_emoji_id=EMOJI["stats"]
    ))
    builder.row(InlineKeyboardButton(
        text="Пользователи",
        callback_data="admin_users_list",
        icon_custom_emoji_id=EMOJI["users"]
    ))
    builder.row(InlineKeyboardButton(
        text="Закрыть",
        callback_data="close_admin",
        icon_custom_emoji_id=EMOJI["cross"]
    ))
    return builder.as_markup()

def dice_mode_keyboard():
    """Клавиатура выбора режима кубика"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="1-3 / 4-6 (x1.85)",
        callback_data="dice_mode_highlow",
        icon_custom_emoji_id=EMOJI["dice"]
    ))
    builder.row(InlineKeyboardButton(
        text="Чёт / Нечет (x1.85)",
        callback_data="dice_mode_evenodd",
        icon_custom_emoji_id=EMOJI["dice"]
    ))
    builder.row(InlineKeyboardButton(
        text="Угадать число (x5)",
        callback_data="dice_mode_number",
        icon_custom_emoji_id=EMOJI["dice"]
    ))
    builder.row(InlineKeyboardButton(
        text="Два кубика: сумма 7 (x4)",
        callback_data="dice_mode_twodice",
        icon_custom_emoji_id=EMOJI["dice"]
    ))
    builder.row(InlineKeyboardButton(
        text="Три кубика: 10-11 (x3)",
        callback_data="dice_mode_threedice",
        icon_custom_emoji_id=EMOJI["dice"]
    ))
    builder.row(InlineKeyboardButton(
        text="Счастливое: 1 или 6 (x2.5)",
        callback_data="dice_mode_lucky",
        icon_custom_emoji_id=EMOJI["dice"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def dice_choice_keyboard(mode: str):
    """Клавиатура выбора варианта в кубике"""
    builder = InlineKeyboardBuilder()
    
    if mode == "highlow":
        builder.row(
            InlineKeyboardButton(text="1-3", callback_data="dice_low", icon_custom_emoji_id=EMOJI["dice"]),
            InlineKeyboardButton(text="4-6", callback_data="dice_high", icon_custom_emoji_id=EMOJI["dice"])
        )
    elif mode == "evenodd":
        builder.row(
            InlineKeyboardButton(text="Чётное", callback_data="dice_even", icon_custom_emoji_id=EMOJI["dice"]),
            InlineKeyboardButton(text="Нечётное", callback_data="dice_odd", icon_custom_emoji_id=EMOJI["dice"])
        )
    elif mode == "number":
        for i in range(1, 7):
            builder.add(InlineKeyboardButton(text=str(i), callback_data=f"dice_num_{i}", icon_custom_emoji_id=EMOJI["dice"]))
        builder.adjust(3)
    elif mode == "lucky":
        builder.row(
            InlineKeyboardButton(text="1", callback_data="dice_lucky_1", icon_custom_emoji_id=EMOJI["dice"]),
            InlineKeyboardButton(text="6", callback_data="dice_lucky_6", icon_custom_emoji_id=EMOJI["dice"])
        )
    
    builder.row(InlineKeyboardButton(
        text="Изменить ставку",
        callback_data="dice_change_bet",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад к режимам",
        callback_data="dice_back_modes",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def dice_bet_keyboard():
    """Клавиатура выбора ставки для кубика"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="0.1", callback_data="dice_bet_0.1", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="0.5", callback_data="dice_bet_0.5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="1", callback_data="dice_bet_1", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(
        InlineKeyboardButton(text="5", callback_data="dice_bet_5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="10", callback_data="dice_bet_10", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="50", callback_data="dice_bet_50", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(InlineKeyboardButton(
        text="Своя сумма",
        callback_data="dice_bet_custom",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def blackjack_bet_keyboard():
    """Клавиатура выбора ставки для блэкджека"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="0.1", callback_data="blackjack_bet_0.1", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="0.5", callback_data="blackjack_bet_0.5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="1", callback_data="blackjack_bet_1", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(
        InlineKeyboardButton(text="5", callback_data="blackjack_bet_5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="10", callback_data="blackjack_bet_10", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="50", callback_data="blackjack_bet_50", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(InlineKeyboardButton(
        text="Своя сумма",
        callback_data="blackjack_bet_custom",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def blackjack_game_keyboard():
    """Клавиатура действий в блэкджеке"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Взять", callback_data="bj_hit", icon_custom_emoji_id=EMOJI["blackjack"], style="primary"),
        InlineKeyboardButton(text="Пас", callback_data="bj_stand", icon_custom_emoji_id=EMOJI["cross"], style="danger")
    )
    return builder.as_markup()

def slots_bet_keyboard():
    """Клавиатура выбора ставки для слотов"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="0.1", callback_data="slots_bet_0.1", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="0.5", callback_data="slots_bet_0.5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="1", callback_data="slots_bet_1", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(
        InlineKeyboardButton(text="5", callback_data="slots_bet_5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="10", callback_data="slots_bet_10", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="50", callback_data="slots_bet_50", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(InlineKeyboardButton(
        text="Своя сумма",
        callback_data="slots_bet_custom",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def roulette_bet_keyboard():
    """Клавиатура выбора ставки для рулетки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="0.1", callback_data="roulette_bet_0.1", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="0.5", callback_data="roulette_bet_0.5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="1", callback_data="roulette_bet_1", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(
        InlineKeyboardButton(text="5", callback_data="roulette_bet_5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="10", callback_data="roulette_bet_10", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="50", callback_data="roulette_bet_50", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(InlineKeyboardButton(
        text="Своя сумма",
        callback_data="roulette_bet_custom",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def roulette_choice_keyboard():
    """Клавиатура выбора исхода в рулетке"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Красное (x2)", callback_data="roulette_red", icon_custom_emoji_id=EMOJI["roulette"], style="danger"),
        InlineKeyboardButton(text="Чёрное (x2)", callback_data="roulette_black", icon_custom_emoji_id=EMOJI["roulette"])
    )
    builder.row(
        InlineKeyboardButton(text="Чётное (x2)", callback_data="roulette_even", icon_custom_emoji_id=EMOJI["roulette"]),
        InlineKeyboardButton(text="Нечётное (x2)", callback_data="roulette_odd", icon_custom_emoji_id=EMOJI["roulette"])
    )
    builder.row(InlineKeyboardButton(
        text="Число (x36)",
        callback_data="roulette_number",
        icon_custom_emoji_id=EMOJI["roulette"],
        style="primary"
    ))
    builder.row(InlineKeyboardButton(
        text="Изменить ставку",
        callback_data="roulette_change_bet",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def basketball_bet_keyboard():
    """Клавиатура выбора ставки для баскетбола"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="0.1", callback_data="basketball_bet_0.1", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="0.5", callback_data="basketball_bet_0.5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="1", callback_data="basketball_bet_1", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(
        InlineKeyboardButton(text="5", callback_data="basketball_bet_5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="10", callback_data="basketball_bet_10", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="50", callback_data="basketball_bet_50", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(InlineKeyboardButton(
        text="Своя сумма",
        callback_data="basketball_bet_custom",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def basketball_choice_keyboard():
    """Клавиатура выбора исхода в баскетболе"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Попадание (1.85x)",
        callback_data="basketball_hit",
        icon_custom_emoji_id=EMOJI["basketball"],
        style="success"
    ))
    builder.row(InlineKeyboardButton(
        text="Промах (1.5x)",
        callback_data="basketball_miss",
        icon_custom_emoji_id=EMOJI["basketball"],
        style="danger"
    ))
    builder.row(InlineKeyboardButton(
        text="Попадание 2 раза (3x)",
        callback_data="basketball_double",
        icon_custom_emoji_id=EMOJI["basketball"],
        style="primary"
    ))
    builder.row(InlineKeyboardButton(
        text="Изменить ставку",
        callback_data="basketball_change_bet",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def football_mode_keyboard():
    """Клавиатура выбора режима футбола"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="Гол (x1.85)",
        callback_data="football_mode_goal",
        icon_custom_emoji_id=EMOJI["football"],
        style="success"
    ))
    builder.row(InlineKeyboardButton(
        text="Промах (x1.5)",
        callback_data="football_mode_miss",
        icon_custom_emoji_id=EMOJI["football"],
        style="danger"
    ))
    builder.row(InlineKeyboardButton(
        text="Пенальти (x2)",
        callback_data="football_mode_penalty",
        icon_custom_emoji_id=EMOJI["football"],
        style="primary"
    ))
    builder.row(InlineKeyboardButton(
        text="Штанга/Перекладина (x4)",
        callback_data="football_mode_post",
        icon_custom_emoji_id=EMOJI["football"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def football_bet_keyboard():
    """Клавиатура выбора ставки для футбола"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="0.1", callback_data="football_bet_0.1", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="0.5", callback_data="football_bet_0.5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="1", callback_data="football_bet_1", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(
        InlineKeyboardButton(text="5", callback_data="football_bet_5", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="10", callback_data="football_bet_10", icon_custom_emoji_id=EMOJI["money"]),
        InlineKeyboardButton(text="50", callback_data="football_bet_50", icon_custom_emoji_id=EMOJI["money"])
    )
    builder.row(InlineKeyboardButton(
        text="Своя сумма",
        callback_data="football_bet_custom",
        icon_custom_emoji_id=EMOJI["edit"]
    ))
    builder.row(InlineKeyboardButton(
        text="Назад",
        callback_data="back_to_games",
        icon_custom_emoji_id=EMOJI["back"]
    ))
    return builder.as_markup()

def play_again_keyboard(game: str):
    """Клавиатура для повторной игры"""
    builder = InlineKeyboardBuilder()
    
    game_map = {
        "dice": "dice_change_bet",
        "basketball": "basketball_change_bet",
        "football": "football_change_bet",
        "blackjack": "blackjack_change_bet",
        "slots": "slots_change_bet",
        "roulette": "roulette_change_bet"
    }
    
    cb = game_map.get(game, "back_to_games")
    
    builder.row(InlineKeyboardButton(
        text="Играть ещё",
        callback_data=cb,
        icon_custom_emoji_id=EMOJI.get(game, EMOJI["home"]),
        style="primary"
    ))
    builder.row(InlineKeyboardButton(
        text="В меню",
        callback_data="back_to_menu_msg",
        icon_custom_emoji_id=EMOJI["home"]
    ))
    return builder.as_markup()

# ========== LZT.MARKET API ==========
pending_rub_payments = {}

async def create_lzt_invoice(amount_rub: float, user_id: int):
    """Создание счёта через LZT.Market"""
    if not LZT_API_KEY:
        logger.error("LZT_API_KEY не установлен!")
        return None
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {LZT_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payment_id = f"vest_{user_id}_{random.randint(100000, 999999)}"
        
        data = {
            "currency": "rub",
            "amount": float(amount_rub),
            "payment_id": payment_id,
            "comment": f"Vest Casino - user {user_id}",
            "url_success": f"https://t.me/{BOT_USERNAME}",
            "merchant_id": LZT_SHOP_ID
        }
        
        logger.info(f"LZT Request: {json.dumps(data)}")
        
        try:
            async with session.post(f"{LZT_API_URL}/invoice", headers=headers, json=data) as resp:
                response_text = await resp.text()
                logger.info(f"LZT Response [{resp.status}]: {response_text}")
                
                if resp.status == 200:
                    result = json.loads(response_text)
                    
                    # Пробуем разные форматы ответа
                    invoice = result.get("invoice") or result.get("result") or result
                    
                    if invoice:
                        invoice_id = invoice.get("invoice_id") or invoice.get("id")
                        pay_url = invoice.get("url") or invoice.get("pay_url")
                        
                        if pay_url:
                            logger.info(f"LZT Invoice created: ID={invoice_id}, URL={pay_url}")
                            return {
                                "pay_url": pay_url,
                                "invoice_id": invoice_id,
                                "amount_rub": amount_rub,
                                "amount_usdt": round(amount_rub / USDT_RUB_RATE, 2),
                            }
                        else:
                            logger.error(f"LZT: URL not found in response. Full invoice: {invoice}")
                    else:
                        logger.error(f"LZT: Invoice data not found. Response: {result}")
                elif resp.status == 401:
                    logger.error("LZT: Unauthorized! Check API key and permissions (need 'invoice' scope)")
                elif resp.status == 400:
                    error_data = json.loads(response_text)
                    logger.error(f"LZT: Bad request - {error_data}")
                
                return None
        except Exception as e:
            logger.error(f"LZT API exception: {e}")
            return None

async def check_lzt_invoice(invoice_id: int):
    """Проверка статуса счёта LZT.Market"""
    if not LZT_API_KEY:
        return False
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {LZT_API_KEY}"}
        
        try:
            async with session.get(f"{LZT_API_URL}/invoice/{invoice_id}", headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    invoice = result.get("invoice") or result.get("result") or result
                    if invoice:
                        status = invoice.get("status", "")
                        logger.info(f"LZT Invoice {invoice_id}: status={status}")
                        return status.lower() in ["paid", "success", "completed"]
                return False
        except Exception as e:
            logger.error(f"LZT check error: {e}")
            return False

async def lzt_payment_check_loop(user_id: int, message: Message, amount_usdt: float, amount_rub: float, invoice_id: int):
    """Цикл проверки оплаты LZT"""
    logger.info(f"Starting LZT payment check for user {user_id}, invoice {invoice_id}")
    
    for i in range(120):
        await asyncio.sleep(5)
        
        paid = await check_lzt_invoice(invoice_id)
        if paid:
            logger.info(f"LZT payment confirmed for user {user_id}!")
            update_balance(user_id, amount_usdt)
            new_balance = get_user(user_id)["balance"]
            
            pending_rub_payments.pop(user_id, None)
            
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"{e(EMOJI['check'])} <b>Оплата LZT!</b>\n\n"
                        f"👤 User: <code>{user_id}</code>\n"
                        f"💎 {amount_usdt:.2f} USDT\n"
                        f"₽ {amount_rub}₽",
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
            
            try:
                await message.edit_text(
                    f"{e(EMOJI['check'])} <b>ОПЛАЧЕНО!</b>\n\n"
                    f"{e(EMOJI['money'])} +{amount_usdt:.2f} USDT\n"
                    f"{e(EMOJI['wallet'])} Баланс: <b>{new_balance:.2f} USDT</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=back_to_menu_keyboard()
                )
            except:
                pass
            return
    
    pending_rub_payments.pop(user_id, None)
    try:
        await message.edit_text(
            f"{e(EMOJI['cross'])} <b>Время оплаты истекло</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_keyboard()
        )
    except:
        pass

# ========== CRYPTO BOT API ==========
async def create_crypto_invoice(amount: float):
    """Создание счёта через Crypto Bot"""
    async with aiohttp.ClientSession() as session:
        headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_API}
        data = {
            "asset": "USDT",
            "amount": str(amount),
            "description": "Vest Casino",
            "paid_btn_name": "callback",
            "paid_btn_url": f"https://t.me/{BOT_USERNAME}"
        }
        async with session.post(f"{CRYPTO_API_URL}/createInvoice", headers=headers, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("ok"):
                    return result["result"]
            logger.error(f"Crypto Bot API error: {await resp.text()}")
            return None

async def check_crypto_invoice(invoice_id: int):
    """Проверка статуса счёта Crypto Bot"""
    async with aiohttp.ClientSession() as session:
        headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_API}
        data = {"invoice_ids": [invoice_id]}
        async with session.post(f"{CRYPTO_API_URL}/getInvoices", headers=headers, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("ok") and result["result"]["items"]:
                    return result["result"]["items"][0]
            return None

async def crypto_payment_check_loop(user_id: int, message: Message, invoice_id: int):
    """Цикл проверки оплаты Crypto Bot"""
    for i in range(120):
        await asyncio.sleep(5)
        
        invoice = await check_crypto_invoice(invoice_id)
        if invoice and invoice["status"] == "paid":
            amount = float(invoice["amount"])
            update_balance(user_id, amount)
            new_balance = get_user(user_id)["balance"]
            
            try:
                await message.edit_text(
                    f"{e(EMOJI['check'])} <b>ОПЛАЧЕНО!</b>\n\n"
                    f"{e(EMOJI['money'])} +{amount:.2f} USDT\n"
                    f"{e(EMOJI['wallet'])} Баланс: <b>{new_balance:.2f} USDT</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=back_to_menu_keyboard()
                )
            except:
                pass
            return

async def create_check(amount: float):
    """Создание чека на вывод"""
    async with aiohttp.ClientSession() as session:
        headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_API}
        data = {"asset": "USDT", "amount": str(amount)}
        async with session.post(f"{CRYPTO_API_URL}/createCheck", headers=headers, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("ok"):
                    return result["result"]
            logger.error(f"Crypto Bot check error: {await resp.text()}")
            return None

# ========== БЛЭКДЖЕК ==========
def create_deck():
    """Создание колоды карт"""
    cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'] * 4
    random.shuffle(cards)
    return cards

def get_card_value(card):
    """Получение значения карты"""
    if card in ['J', 'Q', 'K']:
        return 10
    if card == 'A':
        return 11
    return int(card)

def get_hand_value(hand):
    """Подсчёт очков в руке"""
    value = sum(get_card_value(c) for c in hand)
    aces = hand.count('A')
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
    return value

def format_hand(hand):
    """Форматирование карт в руке"""
    return ' '.join(hand)

# ========== СЛОТЫ ==========
SLOT_SYMBOLS = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣']

# ========== РУЛЕТКА ==========
RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]

# ========== ИНИЦИАЛИЗАЦИЯ ==========
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

user_bets = {}

# ========== КОМАНДЫ ==========
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    user = get_user(message.from_user.id)
    
    welcome_text = f"""
{e(EMOJI['home'])} <b>Vest Casino</b>

{e(EMOJI['games'])} <b>Игры:</b>
{e(EMOJI['dice'])} Кубик
{e(EMOJI['basketball'])} Баскетбол
{e(EMOJI['football'])} Футбол
{e(EMOJI['blackjack'])} Блэкджек
{e(EMOJI['slots'])} Слоты
{e(EMOJI['roulette'])} Рулетка

{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>
{e(EMOJI['support'])} Поддержка: @{SUPPORT_USERNAME}
"""
    await message.answer(welcome_text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработчик команды /admin"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(f"{e(EMOJI['cross'])} Нет доступа", parse_mode=ParseMode.HTML)
        return
    await message.answer(
        f"{e(EMOJI['settings'])} <b>Админ-панель</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard()
    )

@router.message(Command("support"))
async def cmd_support(message: Message):
    """Обработчик команды /support"""
    await message.answer(
        f"{e(EMOJI['support'])} <b>ПОДДЕРЖКА</b>\n\n"
        f"{e(EMOJI['link'])} <b><a href='https://t.me/{SUPPORT_USERNAME}'>@{SUPPORT_USERNAME}</a></b>",
        parse_mode=ParseMode.HTML,
        reply_markup=support_keyboard()
    )

@router.message(Command("id"))
async def cmd_id(message: Message):
    """Обработчик команды /id"""
    await message.answer(f"Ваш ID: <code>{message.from_user.id}</code>", parse_mode=ParseMode.HTML)

# ========== ОБРАБОТЧИКИ ТЕКСТОВЫХ КНОПОК ==========
@router.message(F.text == "Профиль")
async def profile(message: Message):
    """Профиль пользователя"""
    user = get_user(message.from_user.id)
    s = user["stats"]
    
    text = f"""
{e(EMOJI['profile'])} <b>ПРОФИЛЬ</b>

{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>

{e(EMOJI['stats'])} <b>СТАТИСТИКА:</b>

{e(EMOJI['dice'])} Кубик: {e(EMOJI['check'])}{s['dice']['wins']} {e(EMOJI['cross'])}{s['dice']['losses']}
{e(EMOJI['basketball'])} Баскетбол: {e(EMOJI['check'])}{s['basketball']['wins']} {e(EMOJI['cross'])}{s['basketball']['losses']}
{e(EMOJI['football'])} Футбол: {e(EMOJI['check'])}{s['football']['wins']} {e(EMOJI['cross'])}{s['football']['losses']}
{e(EMOJI['blackjack'])} Блэкджек: {e(EMOJI['check'])}{s['blackjack']['wins']} {e(EMOJI['cross'])}{s['blackjack']['losses']}
{e(EMOJI['slots'])} Слоты: {e(EMOJI['check'])}{s['slots']['wins']} {e(EMOJI['cross'])}{s['slots']['losses']}
{e(EMOJI['roulette'])} Рулетка: {e(EMOJI['check'])}{s['roulette']['wins']} {e(EMOJI['cross'])}{s['roulette']['losses']}

{e(EMOJI['graph'])} <b>ВСЕГО:</b>
{e(EMOJI['money'])} Выиграно: {s['total_won']:.2f} USDT
{e(EMOJI['cross'])} Проиграно: {s['total_lost']:.2f} USDT
"""
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.message(F.text == "Игры")
async def games_menu(message: Message):
    """Меню игр"""
    await message.answer(
        f"{e(EMOJI['games'])} <b>ВЫБЕРИТЕ ИГРУ</b>\n\nМинимальная ставка: <b>0.1 USDT</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=games_menu_keyboard()
    )

@router.message(F.text == "Поддержка")
async def support_button(message: Message):
    """Кнопка поддержки"""
    await message.answer(
        f"{e(EMOJI['support'])} <b>ПОДДЕРЖКА</b>\n\n"
        f"{e(EMOJI['link'])} <b><a href='https://t.me/{SUPPORT_USERNAME}'>@{SUPPORT_USERNAME}</a></b>",
        parse_mode=ParseMode.HTML,
        reply_markup=support_keyboard()
    )

@router.message(F.text == "Пополнить")
async def deposit_start(message: Message):
    """Начало пополнения"""
    user = get_user(message.from_user.id)
    
    if not user.get("privacy_accepted"):
        await message.answer(
            f"{e(EMOJI['info'])} <b>ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ</b>\n\n"
            f"Перед пополнением баланса необходимо ознакомиться с политикой конфиденциальности.\n\n"
            f"{e(EMOJI['link'])} <b><a href='{PRIVACY_URL}'>Ознакомиться</a></b>",
            parse_mode=ParseMode.HTML,
            reply_markup=privacy_keyboard()
        )
        return
    
    await message.answer(
        f"{e(EMOJI['wallet'])} <b>ПОПОЛНЕНИЕ БАЛАНСА</b>\n\n"
        f"{e(EMOJI['crypto'])} Crypto Bot\n"
        f"{e(EMOJI['rub'])} Рубли (LZT)\n"
        f"{e(EMOJI['star'])} Звёзды",
        parse_mode=ParseMode.HTML,
        reply_markup=deposit_method_keyboard()
    )

@router.callback_query(F.data == "accept_privacy")
async def accept_privacy_callback(callback: CallbackQuery):
    """Принятие политики конфиденциальности"""
    accept_privacy(callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer(
        f"{e(EMOJI['check'])} <b>Спасибо!</b>\n\nТеперь вы можете пополнить баланс.",
        parse_mode=ParseMode.HTML
    )
    await deposit_start(callback.message)
    await callback.answer()

@router.callback_query(F.data == "deposit_crypto")
async def deposit_crypto_start(callback: CallbackQuery, state: FSMContext):
    """Пополнение через Crypto Bot"""
    await callback.message.edit_text(
        f"{e(EMOJI['crypto'])} <b>ПОПОЛНЕНИЕ CRYPTO BOT</b>\n\nВведите сумму в USDT (мин. 0.1):",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(DepositState.waiting_for_amount_crypto)
    await callback.answer()

@router.message(DepositState.waiting_for_amount_crypto)
async def deposit_crypto_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения Crypto Bot"""
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 0.1:
            await message.answer(f"{e(EMOJI['cross'])} Минимум 0.1 USDT", parse_mode=ParseMode.HTML)
            return
        
        invoice = await create_crypto_invoice(amount)
        if invoice:
            pay_url = invoice['pay_url']
            text = f"""
{e(EMOJI['crypto'])} <b>СЧЁТ НА ОПЛАТУ</b>

{e(EMOJI['money'])} Сумма: <b>{amount:.2f} USDT</b>
{e(EMOJI['link'])} <b><a href='{pay_url}'>НАЖМИТЕ ДЛЯ ОПЛАТЫ</a></b>
"""
            msg = await message.answer(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            asyncio.create_task(crypto_payment_check_loop(message.from_user.id, msg, invoice["invoice_id"]))
        else:
            await message.answer(f"{e(EMOJI['cross'])} Ошибка создания счёта", parse_mode=ParseMode.HTML)
    except ValueError:
        await message.answer(f"{e(EMOJI['cross'])} Введите число", parse_mode=ParseMode.HTML)
    await state.clear()

@router.callback_query(F.data == "deposit_rub")
async def deposit_rub_start(callback: CallbackQuery, state: FSMContext):
    """Пополнение рублями через LZT"""
    await callback.message.edit_text(
        f"{e(EMOJI['rub'])} <b>ПОПОЛНЕНИЕ РУБЛЯМИ (LZT)</b>\n\n"
        f"Курс: 1 USDT = {USDT_RUB_RATE}₽\n\n"
        f"Введите сумму в USDT (мин. 0.1):",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(DepositState.waiting_for_amount_rub)
    await callback.answer()

@router.message(DepositState.waiting_for_amount_rub)
async def deposit_rub_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения рублями"""
    try:
        amount_usdt = float(message.text.replace(",", "."))
        if amount_usdt < 0.1:
            await message.answer(f"{e(EMOJI['cross'])} Минимум 0.1 USDT", parse_mode=ParseMode.HTML)
            return
        
        amount_rub = round(amount_usdt * USDT_RUB_RATE, 2)
        invoice_data = await create_lzt_invoice(amount_rub, message.from_user.id)
        
        if invoice_data:
            pending_rub_payments[message.from_user.id] = {
                "amount_usdt": amount_usdt,
                "amount_rub": amount_rub,
                "invoice_id": invoice_data["invoice_id"]
            }
            
            text = f"""
{e(EMOJI['lzt'])} <b>ПОПОЛНЕНИЕ ЧЕРЕЗ LZT</b>

{e(EMOJI['money'])} Сумма: <b>{amount_usdt:.2f} USDT</b> ({amount_rub}₽)
{e(EMOJI['link'])} <b><a href='{invoice_data['pay_url']}'>НАЖМИТЕ ДЛЯ ОПЛАТЫ</a></b>
"""
            msg = await message.answer(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            asyncio.create_task(lzt_payment_check_loop(
                message.from_user.id,
                msg,
                amount_usdt,
                amount_rub,
                invoice_data["invoice_id"]
            ))
        else:
            await message.answer(
                f"{e(EMOJI['cross'])} Ошибка создания платежа.\n\n"
                f"Проверьте API ключ или попробуйте Crypto Bot.\n\n"
                f"Поддержка: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
    except ValueError:
        await message.answer(f"{e(EMOJI['cross'])} Введите число", parse_mode=ParseMode.HTML)
    await state.clear()

@router.callback_query(F.data == "deposit_stars")
async def deposit_stars_callback(callback: CallbackQuery):
    """Пополнение звёздами"""
    await callback.message.edit_text(
        f"{e(EMOJI['star'])} <b>ПОПОЛНЕНИЕ ЗВЁЗДАМИ</b>\n\n"
        f"Напишите в поддержку:\n"
        f"{e(EMOJI['link'])} <b><a href='https://t.me/{SUPPORT_USERNAME}'>@{SUPPORT_USERNAME}</a></b>\n\n"
        f"Ваш ID: <code>{callback.from_user.id}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu_keyboard()
    )
    await callback.answer()

@router.message(F.text == "Вывод")
async def withdraw_start(message: Message, state: FSMContext):
    """Начало вывода средств"""
    user = get_user(message.from_user.id)
    if user['balance'] < 0.5:
        await message.answer(f"{e(EMOJI['cross'])} Минимум 0.5 USDT", parse_mode=ParseMode.HTML)
        return
    
    await message.answer(
        f"{e(EMOJI['withdraw'])} <b>ВЫВОД СРЕДСТВ</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Введите сумму (мин. 0.5):",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(WithdrawState.waiting_for_amount)

@router.message(WithdrawState.waiting_for_amount)
async def withdraw_amount(message: Message, state: FSMContext):
    """Обработка суммы вывода"""
    try:
        amount = float(message.text.replace(",", "."))
        user = get_user(message.from_user.id)
        
        if amount < 0.5:
            await message.answer(f"{e(EMOJI['cross'])} Минимум 0.5 USDT", parse_mode=ParseMode.HTML)
            return
        if amount > user['balance']:
            await message.answer(f"{e(EMOJI['cross'])} Недостаточно средств", parse_mode=ParseMode.HTML)
            return
        
        check_data = await create_check(amount)
        if check_data:
            update_balance(message.from_user.id, -amount)
            new_balance = get_user(message.from_user.id)['balance']
            check_link = f"https://t.me/send?start={check_data['check_id']}"
            
            await message.answer(
                f"{e(EMOJI['check'])} <b>ЧЕК НА ВЫВОД!</b>\n\n"
                f"{e(EMOJI['money'])} {amount:.2f} USDT\n"
                f"{e(EMOJI['link'])} <b><a href='{check_link}'>ПОЛУЧИТЬ</a></b>\n\n"
                f"{e(EMOJI['wallet'])} Баланс: <b>{new_balance:.2f} USDT</b>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=main_menu_keyboard()
            )
        else:
            await message.answer(f"{e(EMOJI['cross'])} Ошибка вывода", parse_mode=ParseMode.HTML)
        await state.clear()
    except ValueError:
        await message.answer(f"{e(EMOJI['cross'])} Введите число", parse_mode=ParseMode.HTML)

@router.message(F.text == "Помощь")
async def help_cmd(message: Message):
    """Помощь"""
    await message.answer(
        f"{e(EMOJI['info'])} <b>ПОМОЩЬ</b>\n\n"
        f"{e(EMOJI['wallet'])} Пополнение: Crypto Bot / LZT / Звёзды\n"
        f"Курс: 1 USDT = {USDT_RUB_RATE}₽\n"
        f"Вывод от 0.5 USDT\n"
        f"Ставки от 0.1 USDT\n\n"
        f"{e(EMOJI['settings'])} /admin /id /support",
        parse_mode=ParseMode.HTML
    )

# ========== ОБРАБОТЧИКИ ИГР ==========
@router.callback_query(F.data == "back_to_games")
async def back_to_games(callback: CallbackQuery):
    """Возврат к меню игр"""
    await callback.message.edit_text(
        f"{e(EMOJI['games'])} <b>ВЫБЕРИТЕ ИГРУ</b>\n\nМин. ставка: <b>0.1 USDT</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=games_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_menu_msg")
async def back_to_menu_msg(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.delete()
    await callback.message.answer(
        f"{e(EMOJI['home'])} <b>Vest Casino</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

# ========== КУБИК ==========
@router.callback_query(F.data == "game_dice_start")
async def game_dice_start(callback: CallbackQuery):
    """Начало игры в кубик"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите режим:",
        parse_mode=ParseMode.HTML,
        reply_markup=dice_mode_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("dice_mode_"))
async def dice_mode_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор режима кубика"""
    mode = callback.data.replace("dice_mode_", "")
    await state.update_data(dice_mode=mode)
    user = get_user(callback.from_user.id)
    
    multipliers = {"highlow": 1.85, "evenodd": 1.85, "number": 5, "twodice": 4, "threedice": 3, "lucky": 2.5}
    mode_names = {"highlow": "1-3 / 4-6", "evenodd": "Чёт / Нечет", "number": "Угадать число", "twodice": "Два кубика: сумма 7", "threedice": "Три кубика: 10-11", "lucky": "Счастливое: 1 или 6"}
    
    await callback.message.edit_text(
        f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n"
        f"Режим: <b>{mode_names[mode]}</b>\n"
        f"Множитель: <b>x{multipliers[mode]}</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=dice_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "dice_back_modes")
async def dice_back_modes(callback: CallbackQuery):
    """Возврат к режимам кубика"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите режим:",
        parse_mode=ParseMode.HTML,
        reply_markup=dice_mode_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("dice_bet_"))
async def dice_set_bet(callback: CallbackQuery, state: FSMContext):
    """Установка ставки в кубике"""
    parts = callback.data.split("_")
    bet_type = parts[2]
    user_id = callback.from_user.id
    user = get_user(user_id)
    data = await state.get_data()
    mode = data.get("dice_mode", "highlow")
    
    if bet_type == "custom":
        await callback.message.edit_text(
            f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n"
            f"{e(EMOJI['wallet'])} Баланс: {user['balance']:.2f} USDT\n\n"
            f"Введите сумму ставки (мин. 0.1):",
            parse_mode=ParseMode.HTML
        )
        user_bets[user_id] = {"game": "dice", "mode": mode, "awaiting_custom": True}
        await callback.answer()
        return
    
    bet = float(bet_type)
    if user["balance"] < bet:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    if bet < 0.1:
        await callback.answer("Мин. 0.1 USDT", show_alert=True)
        return
    
    user_bets[user_id] = {"game": "dice", "mode": mode, "bet": bet, "awaiting_custom": False}
    
    if mode in ["twodice", "threedice"]:
        await dice_play_auto(callback, user_id, bet, mode)
    else:
        await callback.message.edit_text(
            f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n"
            f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n"
            f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
            f"Выберите вариант:",
            parse_mode=ParseMode.HTML,
            reply_markup=dice_choice_keyboard(mode)
        )
    await callback.answer()

async def dice_play_auto(callback: CallbackQuery, user_id: int, bet: float, mode: str):
    """Автоматическая игра в кубик (два/три кубика)"""
    user = get_user(user_id)
    
    if mode == "twodice":
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        is_win = (d1 + d2) == 7
        mult = 4
        result = f"Кубики: {d1} + {d2} = {d1 + d2}"
    else:
        d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2 + d3
        is_win = 10 <= total <= 11
        mult = 3
        result = f"Кубики: {d1} + {d2} + {d3} = {total}"
    
    if is_win:
        win_amount = bet * mult
        update_balance(user_id, win_amount - bet)
        add_game_stat(user_id, "dice", True)
        text = f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n{result}\n\n{e(EMOJI['check'])} <b>ПОБЕДА!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
    else:
        update_balance(user_id, -bet)
        add_game_stat(user_id, "dice", False)
        text = f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n{result}\n\n{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
    
    new_balance = get_user(user_id)["balance"]
    text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{new_balance:.2f} USDT</b>"
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("dice"))

@router.callback_query(F.data == "dice_change_bet")
async def dice_change_bet(callback: CallbackQuery, state: FSMContext):
    """Изменение ставки в кубике"""
    user = get_user(callback.from_user.id)
    data = await state.get_data()
    mode = data.get("dice_mode", "highlow")
    multipliers = {"highlow": 1.85, "evenodd": 1.85, "number": 5, "twodice": 4, "threedice": 3, "lucky": 2.5}
    mode_names = {"highlow": "1-3 / 4-6", "evenodd": "Чёт / Нечет", "number": "Угадать число", "twodice": "Два кубика: сумма 7", "threedice": "Три кубика: 10-11", "lucky": "Счастливое: 1 или 6"}
    
    await callback.message.edit_text(
        f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n"
        f"Режим: <b>{mode_names[mode]}</b>\n"
        f"Множитель: <b>x{multipliers[mode]}</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=dice_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("dice_"))
async def dice_play_action(callback: CallbackQuery):
    """Игра в кубик"""
    user_id = callback.from_user.id
    
    if user_id not in user_bets:
        await callback.answer("Выберите ставку!", show_alert=True)
        return
    
    bet_data = user_bets[user_id]
    bet = bet_data["bet"]
    mode = bet_data["mode"]
    user = get_user(user_id)
    
    if user["balance"] < bet:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    
    choice = callback.data
    roll = random.randint(1, 6)
    is_win = False
    mult = {"highlow": 1.85, "evenodd": 1.85, "number": 5, "lucky": 2.5}[mode]
    
    if mode == "highlow":
        is_win = (choice == "dice_low" and roll <= 3) or (choice == "dice_high" and roll >= 4)
        choice_text = "1-3" if choice == "dice_low" else "4-6"
    elif mode == "evenodd":
        is_win = (choice == "dice_even" and roll % 2 == 0) or (choice == "dice_odd" and roll % 2 != 0)
        choice_text = "Чётное" if choice == "dice_even" else "Нечётное"
    elif mode == "number":
        num = int(choice.split("_")[-1])
        is_win = roll == num
        choice_text = f"Число {num}"
    elif mode == "lucky":
        num = int(choice.split("_")[-1])
        is_win = roll == num
        choice_text = f"Число {num}"
    
    if is_win:
        win_amount = bet * mult
        update_balance(user_id, win_amount - bet)
        add_game_stat(user_id, "dice", True)
        text = f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\nВыбор: <b>{choice_text}</b>\nВыпало: <b>{roll}</b>\n\n{e(EMOJI['check'])} <b>ПОБЕДА!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
    else:
        update_balance(user_id, -bet)
        add_game_stat(user_id, "dice", False)
        text = f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\nВыбор: <b>{choice_text}</b>\nВыпало: <b>{roll}</b>\n\n{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
    
    new_balance = get_user(user_id)["balance"]
    text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{new_balance:.2f} USDT</b>"
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("dice"))
    await callback.answer()

# ========== БАСКЕТБОЛ ==========
@router.callback_query(F.data == "game_basketball_start")
async def game_basketball_start(callback: CallbackQuery):
    """Начало игры в баскетбол"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['basketball'])} <b>БАСКЕТБОЛ</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"{e(EMOJI['money'])} Множители:\n"
        f"• Попадание: <b>x1.85</b>\n"
        f"• Промах: <b>x1.5</b>\n"
        f"• 2 раза: <b>x3</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=basketball_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("basketball_bet_"))
async def basketball_set_bet(callback: CallbackQuery):
    """Установка ставки в баскетболе"""
    parts = callback.data.split("_")
    bet_type = parts[2]
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if bet_type == "custom":
        await callback.message.edit_text(
            f"{e(EMOJI['basketball'])} <b>БАСКЕТБОЛ</b>\n\n"
            f"{e(EMOJI['wallet'])} Баланс: {user['balance']:.2f} USDT\n\n"
            f"Введите сумму (мин. 0.1):",
            parse_mode=ParseMode.HTML
        )
        user_bets[user_id] = {"game": "basketball", "awaiting_custom": True}
        await callback.answer()
        return
    
    bet = float(bet_type)
    if user["balance"] < bet:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    if bet < 0.1:
        await callback.answer("Мин. 0.1 USDT", show_alert=True)
        return
    
    user_bets[user_id] = {"game": "basketball", "bet": bet, "awaiting_custom": False}
    
    await callback.message.edit_text(
        f"{e(EMOJI['basketball'])} <b>БАСКЕТБОЛ</b>\n\n"
        f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите исход:",
        parse_mode=ParseMode.HTML,
        reply_markup=basketball_choice_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "basketball_change_bet")
async def basketball_change_bet(callback: CallbackQuery):
    """Изменение ставки в баскетболе"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['basketball'])} <b>БАСКЕТБОЛ</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"{e(EMOJI['money'])} Множители:\n"
        f"• Попадание: <b>x1.85</b>\n"
        f"• Промах: <b>x1.5</b>\n"
        f"• 2 раза: <b>x3</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=basketball_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.in_(["basketball_hit", "basketball_miss", "basketball_double"]))
async def basketball_play_action(callback: CallbackQuery):
    """Игра в баскетбол"""
    user_id = callback.from_user.id
    
    if user_id not in user_bets:
        await callback.answer("Выберите ставку!", show_alert=True)
        return
    
    bet = user_bets[user_id]["bet"]
    user = get_user(user_id)
    
    if user["balance"] < bet:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    
    choice = callback.data
    is_win = random.random() < 0.2
    
    if choice == "basketball_hit":
        choice_text, mult = "Попадание", 1.85
        result_desc = "Попадание!" if is_win else "Промах!"
    elif choice == "basketball_miss":
        choice_text, mult = "Промах", 1.5
        result_desc = "Промах!" if is_win else "Попадание!"
    else:
        choice_text, mult = "2 раза", 3
        is_win = random.random() < 0.04
        result_desc = "2 раза!" if is_win else "Промах!"
    
    if is_win:
        win_amount = bet * mult
        update_balance(user_id, win_amount - bet)
        add_game_stat(user_id, "basketball", True)
        text = f"{e(EMOJI['basketball'])} <b>БАСКЕТБОЛ</b>\n\nВыбор: <b>{choice_text}</b>\nРезультат: <b>{result_desc}</b>\n\n{e(EMOJI['check'])} <b>ПОБЕДА!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
    else:
        update_balance(user_id, -bet)
        add_game_stat(user_id, "basketball", False)
        text = f"{e(EMOJI['basketball'])} <b>БАСКЕТБОЛ</b>\n\nВыбор: <b>{choice_text}</b>\nРезультат: <b>{result_desc}</b>\n\n{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
    
    new_balance = get_user(user_id)["balance"]
    text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{new_balance:.2f} USDT</b>"
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("basketball"))
    await callback.answer()

# ========== ФУТБОЛ ==========
@router.callback_query(F.data == "game_football_start")
async def game_football_start(callback: CallbackQuery):
    """Начало игры в футбол"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['football'])} <b>ФУТБОЛ</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите режим:",
        parse_mode=ParseMode.HTML,
        reply_markup=football_mode_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("football_mode_"))
async def football_mode_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор режима футбола"""
    mode = callback.data.replace("football_mode_", "")
    await state.update_data(football_mode=mode)
    user = get_user(callback.from_user.id)
    
    mults = {"goal": 1.85, "miss": 1.5, "penalty": 2, "post": 4}
    names = {"goal": "Гол", "miss": "Промах", "penalty": "Пенальти", "post": "Штанга/Перекладина"}
    
    await callback.message.edit_text(
        f"{e(EMOJI['football'])} <b>ФУТБОЛ</b>\n\n"
        f"Режим: <b>{names[mode]}</b>\n"
        f"Множитель: <b>x{mults[mode]}</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=football_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("football_bet_"))
async def football_set_bet(callback: CallbackQuery, state: FSMContext):
    """Установка ставки в футболе"""
    parts = callback.data.split("_")
    bet_type = parts[2]
    user_id = callback.from_user.id
    user = get_user(user_id)
    data = await state.get_data()
    mode = data.get("football_mode", "goal")
    
    if bet_type == "custom":
        await callback.message.edit_text(
            f"{e(EMOJI['football'])} <b>ФУТБОЛ</b>\n\n"
            f"{e(EMOJI['wallet'])} Баланс: {user['balance']:.2f} USDT\n\n"
            f"Введите сумму (мин. 0.1):",
            parse_mode=ParseMode.HTML
        )
        user_bets[user_id] = {"game": "football", "mode": mode, "awaiting_custom": True}
        await callback.answer()
        return
    
    bet = float(bet_type)
    if user["balance"] < bet:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    if bet < 0.1:
        await callback.answer("Мин. 0.1 USDT", show_alert=True)
        return
    
    user_bets[user_id] = {"game": "football", "mode": mode, "bet": bet, "awaiting_custom": False}
    await football_play_auto(callback, user_id, bet, mode)
    await callback.answer()

async def football_play_auto(callback: CallbackQuery, user_id: int, bet: float, mode: str):
    """Автоматическая игра в футбол"""
    user = get_user(user_id)
    mults = {"goal": 1.85, "miss": 1.5, "penalty": 2, "post": 4}
    mult = mults[mode]
    names = {"goal": "Гол", "miss": "Промах", "penalty": "Пенальти", "post": "Штанга/Перекладина"}
    
    if mode == "post":
        is_win = random.random() < 0.1
        result = "Штанга!" if is_win else "Мимо!"
    elif mode == "penalty":
        is_win = random.random() < 0.3
        result = "ГОЛ!" if is_win else "Вратарь!"
    else:
        is_win = random.random() < 0.2
        if mode == "goal":
            result = "ГОЛ!" if is_win else "Промах!"
        else:
            result = "Промах!" if is_win else "ГОЛ!"
    
    if is_win:
        win_amount = bet * mult
        update_balance(user_id, win_amount - bet)
        add_game_stat(user_id, "football", True)
        text = f"{e(EMOJI['football'])} <b>ФУТБОЛ</b>\n\nРежим: <b>{names[mode]}</b>\nРезультат: <b>{result}</b>\n\n{e(EMOJI['check'])} <b>ПОБЕДА!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
    else:
        update_balance(user_id, -bet)
        add_game_stat(user_id, "football", False)
        text = f"{e(EMOJI['football'])} <b>ФУТБОЛ</b>\n\nРежим: <b>{names[mode]}</b>\nРезультат: <b>{result}</b>\n\n{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
    
    new_balance = get_user(user_id)["balance"]
    text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{new_balance:.2f} USDT</b>"
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("football"))

@router.callback_query(F.data == "football_change_bet")
async def football_change_bet(callback: CallbackQuery, state: FSMContext):
    """Изменение ставки в футболе"""
    user = get_user(callback.from_user.id)
    data = await state.get_data()
    mode = data.get("football_mode", "goal")
    mults = {"goal": 1.85, "miss": 1.5, "penalty": 2, "post": 4}
    names = {"goal": "Гол", "miss": "Промах", "penalty": "Пенальти", "post": "Штанга/Перекладина"}
    
    await callback.message.edit_text(
        f"{e(EMOJI['football'])} <b>ФУТБОЛ</b>\n\n"
        f"Режим: <b>{names[mode]}</b>\n"
        f"Множитель: <b>x{mults[mode]}</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=football_bet_keyboard()
    )
    await callback.answer()

# ========== БЛЭКДЖЕК ==========
@router.callback_query(F.data == "game_blackjack_start")
async def game_blackjack_start(callback: CallbackQuery):
    """Начало игры в блэкджек"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n"
        f"{e(EMOJI['money'])} Множитель: <b>x2</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=blackjack_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("blackjack_bet_"))
async def blackjack_set_bet(callback: CallbackQuery):
    """Установка ставки в блэкджеке"""
    parts = callback.data.split("_")
    bet_type = parts[2]
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if bet_type == "custom":
        await callback.message.edit_text(
            f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
            f"{e(EMOJI['wallet'])} Баланс: {user['balance']:.2f} USDT\n\n"
            f"Введите сумму (мин. 0.1):",
            parse_mode=ParseMode.HTML
        )
        user_bets[user_id] = {"game": "blackjack", "awaiting_custom": True}
        await callback.answer()
        return
    
    bet = float(bet_type)
    if user["balance"] < bet:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    if bet < 0.1:
        await callback.answer("Мин. 0.1 USDT", show_alert=True)
        return
    
    deck = create_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    user_bets[user_id] = {"game": "blackjack", "bet": bet, "deck": deck, "player_hand": player_hand, "dealer_hand": dealer_hand}
    
    player_value = get_hand_value(player_hand)
    await callback.message.edit_text(
        f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
        f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n\n"
        f"Ваши карты: <b>{format_hand(player_hand)}</b> ({player_value})\n"
        f"Карта дилера: <b>{dealer_hand[0]}</b> + ?\n\n"
        f"Выберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=blackjack_game_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "blackjack_change_bet")
async def blackjack_change_bet(callback: CallbackQuery):
    """Изменение ставки в блэкджеке"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n"
        f"{e(EMOJI['money'])} Множитель: <b>x2</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=blackjack_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.in_(["bj_hit", "bj_stand"]))
async def blackjack_play_action(callback: CallbackQuery):
    """Игра в блэкджек"""
    user_id = callback.from_user.id
    
    if user_id not in user_bets or user_bets[user_id].get("game") != "blackjack":
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    game_data = user_bets[user_id]
    bet = game_data["bet"]
    deck = game_data["deck"]
    player_hand = game_data["player_hand"]
    dealer_hand = game_data["dealer_hand"]
    
    if callback.data == "bj_hit":
        player_hand.append(deck.pop())
        player_value = get_hand_value(player_hand)
        
        if player_value > 21:
            update_balance(user_id, -bet)
            add_game_stat(user_id, "blackjack", False)
            dealer_value = get_hand_value(dealer_hand)
            
            text = f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
            text += f"Ваши карты: <b>{format_hand(player_hand)}</b> ({player_value}) — <b>ПЕРЕБОР!</b>\n"
            text += f"Карты дилера: <b>{format_hand(dealer_hand)}</b> ({dealer_value})\n\n"
            text += f"{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
            text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{get_user(user_id)['balance']:.2f} USDT</b>"
            
            await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("blackjack"))
            del user_bets[user_id]
            await callback.answer()
            return
        
        await callback.message.edit_text(
            f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
            f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n\n"
            f"Ваши карты: <b>{format_hand(player_hand)}</b> ({player_value})\n"
            f"Карта дилера: <b>{dealer_hand[0]}</b> + ?\n\n"
            f"Выберите действие:",
            parse_mode=ParseMode.HTML,
            reply_markup=blackjack_game_keyboard()
        )
        await callback.answer()
        return
    
    # Stand - дилер добирает до 17
    while get_hand_value(dealer_hand) < 17:
        dealer_hand.append(deck.pop())
    
    player_value = get_hand_value(player_hand)
    dealer_value = get_hand_value(dealer_hand)
    
    if dealer_value > 21 or player_value > dealer_value:
        win_amount = bet * 2
        update_balance(user_id, win_amount - bet)
        add_game_stat(user_id, "blackjack", True)
        text = f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
        text += f"Ваши карты: <b>{format_hand(player_hand)}</b> ({player_value})\n"
        text += f"Карты дилера: <b>{format_hand(dealer_hand)}</b> ({dealer_value})\n\n"
        text += f"{e(EMOJI['check'])} <b>ПОБЕДА!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
    elif player_value == dealer_value:
        text = f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
        text += f"Ваши карты: <b>{format_hand(player_hand)}</b> ({player_value})\n"
        text += f"Карты дилера: <b>{format_hand(dealer_hand)}</b> ({dealer_value})\n\n"
        text += f"<b>НИЧЬЯ!</b>\nСтавка возвращена."
    else:
        update_balance(user_id, -bet)
        add_game_stat(user_id, "blackjack", False)
        text = f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
        text += f"Ваши карты: <b>{format_hand(player_hand)}</b> ({player_value})\n"
        text += f"Карты дилера: <b>{format_hand(dealer_hand)}</b> ({dealer_value})\n\n"
        text += f"{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
    
    text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{get_user(user_id)['balance']:.2f} USDT</b>"
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("blackjack"))
    del user_bets[user_id]
    await callback.answer()

# ========== СЛОТЫ ==========
@router.callback_query(F.data == "game_slots_start")
async def game_slots_start(callback: CallbackQuery):
    """Начало игры в слоты"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['slots'])} <b>СЛОТЫ</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Множители:\n"
        f"🍒🍒🍒 x2\n🍋🍋🍋 x3\n🍊🍊🍊 x5\n🍇🍇🍇 x10\n💎💎💎 x50\n7️⃣7️⃣7️⃣ x100\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=slots_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("slots_bet_"))
async def slots_set_bet(callback: CallbackQuery):
    """Установка ставки в слотах"""
    parts = callback.data.split("_")
    bet_type = parts[2]
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if bet_type == "custom":
        await callback.message.edit_text(
            f"{e(EMOJI['slots'])} <b>СЛОТЫ</b>\n\n"
            f"{e(EMOJI['wallet'])} Баланс: {user['balance']:.2f} USDT\n\n"
            f"Введите сумму (мин. 0.1):",
            parse_mode=ParseMode.HTML
        )
        user_bets[user_id] = {"game": "slots", "awaiting_custom": True}
        await callback.answer()
        return
    
    bet = float(bet_type)
    if user["balance"] < bet:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    if bet < 0.1:
        await callback.answer("Мин. 0.1 USDT", show_alert=True)
        return
    
    s1 = random.choice(SLOT_SYMBOLS)
    s2 = random.choice(SLOT_SYMBOLS)
    s3 = random.choice(SLOT_SYMBOLS)
    mult = 0
    
    if s1 == s2 == s3:
        if s1 == '🍒':
            mult = 2
        elif s1 == '🍋':
            mult = 3
        elif s1 == '🍊':
            mult = 5
        elif s1 == '🍇':
            mult = 10
        elif s1 == '💎':
            mult = 50
        elif s1 == '7️⃣':
            mult = 100
    
    if mult > 0:
        win_amount = bet * mult
        update_balance(user_id, win_amount - bet)
        add_game_stat(user_id, "slots", True)
        text = f"{e(EMOJI['slots'])} <b>СЛОТЫ</b>\n\n[{s1}] [{s2}] [{s3}]\n\n{e(EMOJI['check'])} <b>ВЫИГРЫШ x{mult}!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
    else:
        update_balance(user_id, -bet)
        add_game_stat(user_id, "slots", False)
        text = f"{e(EMOJI['slots'])} <b>СЛОТЫ</b>\n\n[{s1}] [{s2}] [{s3}]\n\n{e(EMOJI['cross'])} <b>ПРОИГРЫШ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
    
    new_balance = get_user(user_id)["balance"]
    text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{new_balance:.2f} USDT</b>"
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("slots"))
    await callback.answer()

@router.callback_query(F.data == "slots_change_bet")
async def slots_change_bet(callback: CallbackQuery):
    """Изменение ставки в слотах"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['slots'])} <b>СЛОТЫ</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=slots_bet_keyboard()
    )
    await callback.answer()

# ========== РУЛЕТКА ==========
@router.callback_query(F.data == "game_roulette_start")
async def game_roulette_start(callback: CallbackQuery):
    """Начало игры в рулетку"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Множители:\n"
        f"Красное/Чёрное x2\nЧёт/Нечет x2\nЧисло x36\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=roulette_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("roulette_bet_"))
async def roulette_set_bet(callback: CallbackQuery):
    """Установка ставки в рулетке"""
    parts = callback.data.split("_")
    bet_type = parts[2]
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if bet_type == "custom":
        await callback.message.edit_text(
            f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\n"
            f"{e(EMOJI['wallet'])} Баланс: {user['balance']:.2f} USDT\n\n"
            f"Введите сумму (мин. 0.1):",
            parse_mode=ParseMode.HTML
        )
        user_bets[user_id] = {"game": "roulette", "awaiting_custom": True}
        await callback.answer()
        return
    
    bet = float(bet_type)
    if user["balance"] < bet:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    if bet < 0.1:
        await callback.answer("Мин. 0.1 USDT", show_alert=True)
        return
    
    user_bets[user_id] = {"game": "roulette", "bet": bet, "awaiting_custom": False}
    
    await callback.message.edit_text(
        f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\n"
        f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите исход:",
        parse_mode=ParseMode.HTML,
        reply_markup=roulette_choice_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "roulette_change_bet")
async def roulette_change_bet(callback: CallbackQuery):
    """Изменение ставки в рулетке"""
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
        f"Выберите ставку:",
        parse_mode=ParseMode.HTML,
        reply_markup=roulette_bet_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("roulette_"))
async def roulette_play_action(callback: CallbackQuery):
    """Игра в рулетку"""
    user_id = callback.from_user.id
    
    if user_id not in user_bets or user_bets[user_id].get("game") != "roulette":
        await callback.answer("Выберите ставку!", show_alert=True)
        return
    
    bet = user_bets[user_id]["bet"]
    user = get_user(user_id)
    
    if user["balance"] < bet:
        await callback.answer("Недостаточно средств!", show_alert=True)
        return
    
    choice = callback.data.replace("roulette_", "")
    number = random.randint(0, 36)
    
    is_red = number in RED_NUMBERS
    is_black = number not in RED_NUMBERS and number != 0
    is_even = number % 2 == 0 and number != 0
    is_odd = number % 2 != 0
    
    color = "🔴" if is_red else ("⚫" if is_black else "🟢")
    
    if choice == "red":
        is_win, mult, choice_text = is_red, 2, "Красное"
    elif choice == "black":
        is_win, mult, choice_text = is_black, 2, "Чёрное"
    elif choice == "even":
        is_win, mult, choice_text = is_even, 2, "Чётное"
    elif choice == "odd":
        is_win, mult, choice_text = is_odd, 2, "Нечётное"
    elif choice == "number":
        await callback.message.edit_text(
            f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\n"
            f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n\n"
            f"Введите число от 0 до 36:",
            parse_mode=ParseMode.HTML
        )
        user_bets[user_id]["mode"] = "number"
        await callback.answer()
        return
    else:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    if is_win:
        win_amount = bet * mult
        update_balance(user_id, win_amount - bet)
        add_game_stat(user_id, "roulette", True)
        text = f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\nВыбор: <b>{choice_text}</b>\nВыпало: {color} <b>{number}</b>\n\n{e(EMOJI['check'])} <b>ПОБЕДА!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
    else:
        update_balance(user_id, -bet)
        add_game_stat(user_id, "roulette", False)
        text = f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\nВыбор: <b>{choice_text}</b>\nВыпало: {color} <b>{number}</b>\n\n{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
    
    text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{get_user(user_id)['balance']:.2f} USDT</b>"
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("roulette"))
    del user_bets[user_id]
    await callback.answer()

# ========== СВОЯ СТАВКА ==========
@router.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def handle_custom_bet(message: Message, state: FSMContext):
    """Обработка своей ставки"""
    user_id = message.from_user.id
    
    # Проверка для рулетки (выбор числа)
    if user_id not in user_bets or not user_bets[user_id].get("awaiting_custom"):
        if user_id in user_bets and user_bets[user_id].get("game") == "roulette" and user_bets[user_id].get("mode") == "number":
            try:
                chosen_num = int(message.text.strip())
                if chosen_num < 0 or chosen_num > 36:
                    raise ValueError
                
                bet = user_bets[user_id]["bet"]
                user = get_user(user_id)
                number = random.randint(0, 36)
                is_win = number == chosen_num
                mult = 36
                
                if is_win:
                    win_amount = bet * mult
                    update_balance(user_id, win_amount - bet)
                    add_game_stat(user_id, "roulette", True)
                    text = f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\nСтавка на: <b>{chosen_num}</b>\nВыпало: <b>{number}</b>\n\n{e(EMOJI['check'])} <b>ПОБЕДА!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
                else:
                    update_balance(user_id, -bet)
                    add_game_stat(user_id, "roulette", False)
                    text = f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\nСтавка на: <b>{chosen_num}</b>\nВыпало: <b>{number}</b>\n\n{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
                
                text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{get_user(user_id)['balance']:.2f} USDT</b>"
                await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("roulette"))
                del user_bets[user_id]
            except ValueError:
                await message.answer(f"{e(EMOJI['cross'])} Введите число от 0 до 36", parse_mode=ParseMode.HTML)
        return
    
    try:
        bet = float(message.text.replace(",", "."))
        game = user_bets[user_id]["game"]
        user = get_user(user_id)
        
        if bet < 0.1:
            await message.answer(f"{e(EMOJI['cross'])} Минимум 0.1 USDT", parse_mode=ParseMode.HTML)
            return
        if user["balance"] < bet:
            await message.answer(f"{e(EMOJI['cross'])} Недостаточно средств!", parse_mode=ParseMode.HTML)
            return
        
        user_bets[user_id]["bet"] = bet
        user_bets[user_id]["awaiting_custom"] = False
        
        if game == "dice":
            mode = user_bets[user_id]["mode"]
            if mode in ["twodice", "threedice"]:
                await dice_play_auto_msg(message, user_id, bet, mode)
            else:
                await message.answer(
                    f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n"
                    f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n"
                    f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
                    f"Выберите вариант:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=dice_choice_keyboard(mode)
                )
        elif game == "basketball":
            await message.answer(
                f"{e(EMOJI['basketball'])} <b>БАСКЕТБОЛ</b>\n\n"
                f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n"
                f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
                f"Выберите исход:",
                parse_mode=ParseMode.HTML,
                reply_markup=basketball_choice_keyboard()
            )
        elif game == "football":
            mode = user_bets[user_id]["mode"]
            await football_play_auto_msg(message, user_id, bet, mode)
        elif game == "blackjack":
            deck = create_deck()
            player_hand = [deck.pop(), deck.pop()]
            dealer_hand = [deck.pop(), deck.pop()]
            user_bets[user_id] = {"game": "blackjack", "bet": bet, "deck": deck, "player_hand": player_hand, "dealer_hand": dealer_hand}
            player_value = get_hand_value(player_hand)
            await message.answer(
                f"{e(EMOJI['blackjack'])} <b>БЛЭКДЖЕК</b>\n\n"
                f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n\n"
                f"Ваши карты: <b>{format_hand(player_hand)}</b> ({player_value})\n"
                f"Карта дилера: <b>{dealer_hand[0]}</b> + ?\n\n"
                f"Выберите действие:",
                parse_mode=ParseMode.HTML,
                reply_markup=blackjack_game_keyboard()
            )
        elif game == "slots":
            s1 = random.choice(SLOT_SYMBOLS)
            s2 = random.choice(SLOT_SYMBOLS)
            s3 = random.choice(SLOT_SYMBOLS)
            mult = 0
            if s1 == s2 == s3:
                if s1 == '🍒': mult = 2
                elif s1 == '🍋': mult = 3
                elif s1 == '🍊': mult = 5
                elif s1 == '🍇': mult = 10
                elif s1 == '💎': mult = 50
                elif s1 == '7️⃣': mult = 100
            if mult > 0:
                win_amount = bet * mult
                update_balance(user_id, win_amount - bet)
                add_game_stat(user_id, "slots", True)
                text = f"{e(EMOJI['slots'])} <b>СЛОТЫ</b>\n\n[{s1}] [{s2}] [{s3}]\n\n{e(EMOJI['check'])} <b>ВЫИГРЫШ x{mult}!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
            else:
                update_balance(user_id, -bet)
                add_game_stat(user_id, "slots", False)
                text = f"{e(EMOJI['slots'])} <b>СЛОТЫ</b>\n\n[{s1}] [{s2}] [{s3}]\n\n{e(EMOJI['cross'])} <b>ПРОИГРЫШ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
            text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{get_user(user_id)['balance']:.2f} USDT</b>"
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("slots"))
        elif game == "roulette":
            await message.answer(
                f"{e(EMOJI['roulette'])} <b>РУЛЕТКА</b>\n\n"
                f"{e(EMOJI['money'])} Ставка: <b>{bet:.2f} USDT</b>\n"
                f"{e(EMOJI['wallet'])} Баланс: <b>{user['balance']:.2f} USDT</b>\n\n"
                f"Выберите исход:",
                parse_mode=ParseMode.HTML,
                reply_markup=roulette_choice_keyboard()
            )
    except ValueError:
        await message.answer(f"{e(EMOJI['cross'])} Введите число", parse_mode=ParseMode.HTML)

async def dice_play_auto_msg(message: Message, user_id: int, bet: float, mode: str):
    """Автоматическая игра в кубик (сообщение)"""
    user = get_user(user_id)
    if mode == "twodice":
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        is_win = (d1 + d2) == 7
        mult = 4
        result = f"Кубики: {d1} + {d2} = {d1 + d2}"
    else:
        d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2 + d3
        is_win = 10 <= total <= 11
        mult = 3
        result = f"Кубики: {d1} + {d2} + {d3} = {total}"
    
    if is_win:
        win_amount = bet * mult
        update_balance(user_id, win_amount - bet)
        add_game_stat(user_id, "dice", True)
        text = f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n{result}\n\n{e(EMOJI['check'])} <b>ПОБЕДА!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
    else:
        update_balance(user_id, -bet)
        add_game_stat(user_id, "dice", False)
        text = f"{e(EMOJI['dice'])} <b>КУБИК</b>\n\n{result}\n\n{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
    text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{get_user(user_id)['balance']:.2f} USDT</b>"
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("dice"))

async def football_play_auto_msg(message: Message, user_id: int, bet: float, mode: str):
    """Автоматическая игра в футбол (сообщение)"""
    user = get_user(user_id)
    mults = {"goal": 1.85, "miss": 1.5, "penalty": 2, "post": 4}
    mult = mults[mode]
    names = {"goal": "Гол", "miss": "Промах", "penalty": "Пенальти", "post": "Штанга/Перекладина"}
    
    if mode == "post":
        is_win = random.random() < 0.1
        result = "Штанга!" if is_win else "Мимо!"
    elif mode == "penalty":
        is_win = random.random() < 0.3
        result = "ГОЛ!" if is_win else "Вратарь!"
    else:
        is_win = random.random() < 0.2
        if mode == "goal":
            result = "ГОЛ!" if is_win else "Промах!"
        else:
            result = "Промах!" if is_win else "ГОЛ!"
    
    if is_win:
        win_amount = bet * mult
        update_balance(user_id, win_amount - bet)
        add_game_stat(user_id, "football", True)
        text = f"{e(EMOJI['football'])} <b>ФУТБОЛ</b>\n\nРежим: <b>{names[mode]}</b>\nРезультат: <b>{result}</b>\n\n{e(EMOJI['check'])} <b>ПОБЕДА!</b>\n\n{e(EMOJI['money'])} +{win_amount - bet:.2f} USDT"
    else:
        update_balance(user_id, -bet)
        add_game_stat(user_id, "football", False)
        text = f"{e(EMOJI['football'])} <b>ФУТБОЛ</b>\n\nРежим: <b>{names[mode]}</b>\nРезультат: <b>{result}</b>\n\n{e(EMOJI['cross'])} <b>ПОРАЖЕНИЕ</b>\n\n{e(EMOJI['money'])} -{bet:.2f} USDT"
    text += f"\n{e(EMOJI['wallet'])} Баланс: <b>{get_user(user_id)['balance']:.2f} USDT</b>"
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=play_again_keyboard("football"))

# ========== АДМИН-ПАНЕЛЬ ==========
@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    """Админ-панель"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        f"{e(EMOJI['settings'])} <b>Админ-панель</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика бота"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    db = get_all_users()
    total_users = len(db)
    total_balance = sum(u["balance"] for u in db.values())
    total_bets = sum(u["stats"][g]["wins"] + u["stats"][g]["losses"] for u in db.values() for g in ["dice", "basketball", "football", "blackjack", "slots", "roulette"])
    total_wins = sum(u["stats"][g]["wins"] for u in db.values() for g in ["dice", "basketball", "football", "blackjack", "slots", "roulette"])
    
    await callback.message.edit_text(
        f"{e(EMOJI['stats'])} <b>СТАТИСТИКА</b>\n\n"
        f"{e(EMOJI['users'])} Пользователей: <b>{total_users}</b>\n"
        f"{e(EMOJI['wallet'])} Баланс: <b>{total_balance:.2f} USDT</b>\n\n"
        f"{e(EMOJI['dice'])} Ставок: <b>{total_bets}</b>\n"
        f"{e(EMOJI['check'])} Побед: <b>{total_wins}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_admin_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_users_list")
async def admin_users_list(callback: CallbackQuery):
    """Список пользователей"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    db = get_all_users()
    if not db:
        text = f"{e(EMOJI['users'])} <b>Нет</b>"
    else:
        text = f"{e(EMOJI['users'])} <b>ПОЛЬЗОВАТЕЛИ:</b>\n\n"
        for uid, data in list(db.items())[:20]:
            name = data.get("first_name", "") or data.get("username", "") or uid
            text += f"• <code>{uid}</code> — {name} — {data['balance']:.2f} USDT\n"
        if len(db) > 20:
            text += f"\n... ещё {len(db) - 20}"
    
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_to_admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_edit_balance")
async def admin_edit_balance_start(callback: CallbackQuery, state: FSMContext):
    """Изменение баланса пользователя"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{e(EMOJI['edit'])} <b>ИЗМЕНЕНИЕ БАЛАНСА</b>\n\n"
        f"{e(EMOJI['info'])} Отправьте: <code>ID СУММА</code>\n\n"
        f"<i>Пример: 123456789 100</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_edit_balance)
    await callback.answer()

@router.message(AdminStates.waiting_for_edit_balance)
async def admin_edit_balance_process(message: Message, state: FSMContext):
    """Обработка изменения баланса"""
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            raise ValueError("Неверный формат")
        
        user_id = int(parts[0])
        new_balance = float(parts[1].replace(",", "."))
        if new_balance < 0:
            raise ValueError("Отрицательный баланс")
        
        db = get_all_users()
        uid = str(user_id)
        if uid not in db:
            await message.answer(f"{e(EMOJI['cross'])} Пользователь не найден", parse_mode=ParseMode.HTML, reply_markup=cancel_keyboard())
            return
        
        old_balance, new_balance = set_balance(user_id, new_balance)
        name = db[uid].get("first_name", "") or db[uid].get("username", "") or user_id
        
        try:
            await bot.send_message(user_id, f"{e(EMOJI['wallet'])} Баланс изменён!\n\n{e(EMOJI['edit'])} Новый: <b>{new_balance:.2f} USDT</b>", parse_mode=ParseMode.HTML)
        except:
            pass
        
        await message.answer(
            f"{e(EMOJI['check'])} <b>Готово!</b>\n\n"
            f"{e(EMOJI['profile'])} {name}\n"
            f"{e(EMOJI['info'])} ID: <code>{user_id}</code>\n"
            f"{e(EMOJI['wallet'])} {old_balance:.2f} → <b>{new_balance:.2f} USDT</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer(f"{e(EMOJI['cross'])} Формат: <code>ID СУММА</code>", parse_mode=ParseMode.HTML, reply_markup=cancel_keyboard())

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Рассылка сообщений"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{e(EMOJI['broadcast'])} <b>РАССЫЛКА</b>\n\n"
        f"{e(EMOJI['info'])} Отправьте сообщение:",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext):
    """Отправка рассылки"""
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return
    
    db = get_all_users()
    success = 0
    failed = 0
    
    await message.answer(f"{e(EMOJI['loading'])} <b>Рассылка...</b>", parse_mode=ParseMode.HTML)
    
    for user_id in db.keys():
        try:
            await bot.send_message(int(user_id), message.html_text or message.text, parse_mode=ParseMode.HTML)
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await message.answer(
        f"{e(EMOJI['check'])} <b>Готово!</b>\n\n✅ {success}\n❌ {failed}",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard()
    )
    await state.clear()

@router.callback_query(F.data == "close_admin")
async def close_admin(callback: CallbackQuery):
    """Закрытие админ-панели"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.delete()
    await callback.answer()

# ========== ОБЩИЕ ==========
@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    if callback.from_user.id in ADMIN_IDS:
        await callback.message.edit_text(
            f"{e(EMOJI['cross'])} <b>Отменено</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_panel_keyboard()
        )
    else:
        await callback.message.delete()
        await callback.message.answer(
            f"{e(EMOJI['home'])} <b>Vest Casino</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard()
        )
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    """Запуск бота"""
    logger.info("Vest Casino bot started!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
