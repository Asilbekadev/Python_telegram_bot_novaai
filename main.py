import sqlite3
import warnings
import os
import json
import asyncio
from datetime import datetime
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Warning'larni yashirish
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

# Bot TOKEN
TOKEN = os.getenv('BOT_TOKEN', '8481686583:AAFXLD_hjHHxN1pRzg-wxBBnRmGIoUElKS0')

# ============================================
# NAVBAT MEXANIZMI - SERVER QAYTA ISHGA TUSHGANDA AMALLARNI ESLAB QOLISH
# ============================================

PENDING_ACTIONS_FILE = 'pending_actions.json'


def load_pending_actions():
    """Kutilayotgan amallarni yuklash"""
    try:
        with open(PENDING_ACTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"❌ Pending actions yuklashda xato: {e}")
        return []


def save_pending_action(user_id, action_type, data):
    """Yangi amalni navbatga qo'shish"""
    try:
        actions = load_pending_actions()

        # Eski amallarni o'chirish (faqat oxirgi amalini saqlash)
        actions = [a for a in actions if a['user_id'] != user_id or a['action_type'] != action_type]

        actions.append({
            'user_id': user_id,
            'action_type': action_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })

        with open(PENDING_ACTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(actions, f, ensure_ascii=False, indent=2)

        print(f"✅ Amal navbatga qo'shildi: {action_type} for user {user_id}")
    except Exception as e:
        print(f"❌ Amalni saqlashda xato: {e}")


def clear_pending_actions():
    """Barcha navbatdagi amallarni o'chirish"""
    try:
        with open(PENDING_ACTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("✅ Navbat tozalandi")
    except Exception as e:
        print(f"❌ Navbatni tozalashda xato: {e}")


async def send_main_menu_to_user(app, user_id, lang="uz"):
    """Foydalanuvchiga asosiy menyuni yuborish"""
    try:
        if lang == "uz":
            text = (
                "✅ *Bot qayta ishga tushdi!*\n\n"
                "🏛️ *Qoraqalpoğiston Respublikasi*\n"
                "*Mahalla xodimlari ma'lumot tizimi*\n\n"
                "Quyidagi bo'limlardan birini tanlang:"
            )
            buttons = [
                [InlineKeyboardButton("📰 So'nggi yangiliklar", callback_data="news_uz")],
                [InlineKeyboardButton("📊 Statistika", callback_data="stats_uz")],
                [InlineKeyboardButton("🏘️ Mening mahallam", callback_data="mahalla_uz")],
            ]
        else:
            text = (
                "✅ *Бот перезапущен!*\n\n"
                "🏛️ *Республика Каракалпакстан*\n"
                "*Информационная система сотрудников махалли*\n\n"
                "Выберите раздел:"
            )
            buttons = [
                [InlineKeyboardButton("📰 Последние новости", callback_data="news_ru")],
                [InlineKeyboardButton("📊 Статистика", callback_data="stats_ru")],
                [InlineKeyboardButton("🏘️ Моя махалля", callback_data="mahalla_ru")],
            ]

        reply_markup = InlineKeyboardMarkup(buttons)
        await app.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"❌ Foydalanuvchiga xabar yuborishda xato (user {user_id}): {e}")


async def send_mahalla_list_to_user(app, user_id, tuman_kodi, lang="uz"):
    """Foydalanuvchiga mahallalar ro'yxatini yuborish"""
    conn = sqlite3.connect('qoraqalpogiston_mahalla.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT m.mahalla_nomi, t.tuman_nomi 
            FROM mahallalar m 
            JOIN tumanlar t ON m.tuman_id = t.tuman_id 
            WHERE t.tuman_kodi = ? 
            ORDER BY m.mahalla_nomi
        ''', (tuman_kodi,))
        result = cursor.fetchall()

        if result:
            mahallalar = [row[0] for row in result]
            tuman_nomi = result[0][1]
        else:
            mahallalar = []
            tuman_nomi = "Noma'lum tuman"

    except Exception as e:
        print(f"❌ Mahallalar ro'yxatini olishda xato: {e}")
        mahallalar = []
        tuman_nomi = "Xato"
    finally:
        conn.close()

    if lang == "uz":
        text = f"🏘️ *{tuman_nomi}*\n\n📍 Mahallalar ro'yxati:\nKerakli mahallani tanlang:"
        back_text = "🔙 Orqaga"
    else:
        text = f"🏘️ *{tuman_nomi}*\n\n📍 Список махаллей:\nВыберите нужную махаллю:"
        back_text = "🔙 Назад"

    keyboard = []
    for i in range(0, len(mahallalar), 2):
        row = []
        if i < len(mahallalar):
            row.append(InlineKeyboardButton(
                f"🏘{mahallalar[i]}",
                callback_data=f"mahalla_detail_{lang}_{tuman_kodi}_{i}"
            ))
        if i + 1 < len(mahallalar):
            row.append(InlineKeyboardButton(
                f"🏘{mahallalar[i + 1]}",
                callback_data=f"mahalla_detail_{lang}_{tuman_kodi}_{i + 1}"
            ))
        keyboard.append(row)

    main_back_data = "mahalla_uz" if lang == "uz" else "mahalla_ru"
    keyboard.append([InlineKeyboardButton(back_text, callback_data=main_back_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await app.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"❌ Foydalanuvchiga mahallalar yuborishda xato (user {user_id}): {e}")


async def send_mahalla_details_to_user(app, user_id, tuman_kodi, lang, mahalla_index):
    """Foydalanuvchiga mahalla detallarini yuborish"""
    conn = sqlite3.connect('qoraqalpogiston_mahalla.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT m.mahalla_nomi, m.mahalla_id, t.tuman_nomi
            FROM mahallalar m 
            JOIN tumanlar t ON m.tuman_id = t.tuman_id 
            WHERE t.tuman_kodi = ? 
            ORDER BY m.mahalla_nomi
        ''', (tuman_kodi,))
        mahallalar = cursor.fetchall()

        if mahalla_index >= len(mahallalar):
            selected_mahalla = "Noma'lum mahalla"
            mahalla_id = None
            tuman_nomi = "Noma'lum tuman"
        else:
            selected_mahalla, mahalla_id, tuman_nomi = mahallalar[mahalla_index]

        positions_order = [
            "Mahalla raisi",
            "Profilaktika inspektori",
            "Xotin-qizlar faoli",
            "Xokim yordamchisi",
            "Yoshlar yetakchisi",
            "Ijtimoiy xodimi",
            "Soliq xodimi"
        ]

        xodimlar = []
        if mahalla_id:
            for pos in positions_order:
                cursor.execute('''
                    SELECT position, full_name, phone
                    FROM xodimlar
                    WHERE mahalla_id = ? AND position = ?
                ''', (mahalla_id, pos))
                row = cursor.fetchone()
                if row:
                    xodimlar.append(row)
                else:
                    xodimlar.append((pos, "VAKANT", "VAKANT"))
        else:
            xodimlar = []

    except Exception as e:
        print(f"❌ Mahalla detallarini olishda xato: {e}")
        selected_mahalla = "Xato"
        tuman_nomi = "Xato"
        xodimlar = []
    finally:
        conn.close()

    emoji_list = ["👨‍💼", "👮‍♂️", "👩‍💼", "🏛️", "👨‍🎓", "📋", "💰"]

    if lang == "uz":
        text_lines = [
            f"🏘️ *{selected_mahalla}*",
            f"📍 *{tuman_nomi}*",
            "",
            "*Mahalla xodimlari:*",
            ""
        ]
    else:
        text_lines = [
            f"🏘️ *{selected_mahalla}*",
            f"📍 *{tuman_nomi}*",
            "",
            "*Сотрудники махалли:*",
            ""
        ]

    for idx, xodim in enumerate(xodimlar):
        position, full_name, phone = xodim
        emoji = emoji_list[idx % len(emoji_list)]

        text_lines.append(f"{emoji} *{position}:*")
        text_lines.append(f"👤 {full_name}")

        if phone != "VAKANT":
            clean_phone = "".join(filter(str.isdigit, phone))
            if len(clean_phone) == 9:
                formatted_phone = "+998" + clean_phone
            elif len(clean_phone) == 12 and clean_phone.startswith("998"):
                formatted_phone = "+" + clean_phone
            else:
                formatted_phone = phone

            text_lines.append(f"📞 [{formatted_phone}](tel:{formatted_phone.replace('+', '')})")
        else:
            text_lines.append("📞 *VAKANT*")

        text_lines.append("")

    text = "\n".join(text_lines).strip()

    if lang == "uz":
        back_text = "🔄 Boshqa mahalla"
        main_text = "🔙 Tumanlar ro'yxati"
        district_data = f"tuman_{lang}_{tuman_kodi}"
        main_data = "mahalla_uz"
    else:
        back_text = "🔄 Другая махалля"
        main_text = "🔙 Список районов"
        district_data = f"tuman_{lang}_{tuman_kodi}"
        main_data = "mahalla_ru"

    keyboard = [
        [InlineKeyboardButton(back_text, callback_data=district_data)],
        [InlineKeyboardButton(main_text, callback_data=main_data)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await app.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"❌ Foydalanuvchiga mahalla detallari yuborishda xato (user {user_id}): {e}")


async def process_pending_actions(app):
    """Bot qayta ishga tushganda kutilayotgan amallarni qayta ishlash"""
    actions = load_pending_actions()
    if not actions:
        print("ℹ️ Qayta ishlash uchun kutilayotgan amallar yo'q")
        return

    print(f"🔄 {len(actions)} ta amal qayta ishlanmoqda...")

    for action in actions:
        try:
            user_id = action['user_id']
            action_type = action['action_type']
            data = action['data']

            # Har bir amal turini qayta ishlash
            if action_type == 'language_selection':
                lang = data.get('lang')
                await send_main_menu_to_user(app, user_id, lang)

            elif action_type == 'mahalla_request':
                tuman_kodi = data.get('tuman_kodi')
                lang = data.get('lang')
                await send_mahalla_list_to_user(app, user_id, tuman_kodi, lang)

            elif action_type == 'mahalla_details':
                tuman_kodi = data.get('tuman_kodi')
                lang = data.get('lang')
                mahalla_index = data.get('mahalla_index')
                await send_mahalla_details_to_user(app, user_id, tuman_kodi, lang, mahalla_index)

            print(f"✅ Amal bajarildi: {action_type} for user {user_id}")

        except Exception as e:
            print(f"❌ Amalni qayta ishlashda xato: {e}")
            continue

    # Barcha amallar bajarilgandan keyin navbatni tozalash
    clear_pending_actions()


def init_db():
    """Ma'lumotlar bazasini yaratish va sozlash (bir martalik)"""
    conn = sqlite3.connect('qoraqalpogiston_mahalla.db')
    cursor = conn.cursor()

    try:
        # Jadvallarni yaratish
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tumanlar (
                tuman_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tuman_nomi TEXT NOT NULL UNIQUE,
                tuman_kodi TEXT NOT NULL UNIQUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mahallalar (
                mahalla_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mahalla_nomi TEXT NOT NULL,
                tuman_id INTEGER NOT NULL,
                sektor INTEGER,
                FOREIGN KEY (tuman_id) REFERENCES tumanlar(tuman_id),
                UNIQUE(mahalla_nomi, tuman_id, sektor)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS xodimlar (
                xodim_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mahalla_id INTEGER NOT NULL,
                position TEXT NOT NULL,
                full_name TEXT NOT NULL DEFAULT 'VAKANT',
                phone TEXT NOT NULL DEFAULT 'VAKANT',
                FOREIGN KEY (mahalla_id) REFERENCES mahallalar(mahalla_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS foydalanuvchilar (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                phone TEXT DEFAULT 'YASHIRIN',
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 17 ta tuman qo'shish
        tumanlar_list = [
            ("Nukus shaxar", "nukus_shahar"),
            ("Beruniy tumani", "beruniy"),
            ("Amudaryo tumani", "amudaryo"),
            ("Bo'zatov tumani", "bozatov"),
            ("Kegeyli tumani", "kegeyli"),
            ("Qanli ko'l tumani", "qanli_kol"),
            ("Qarao'zek tumani", "qaraozek"),
            ("Qo'ng'irot tumani", "qongirot"),
            ("Mo'ynoq tumani", "moynoq"),
            ("Nukus tumani", "nukus_tuman"),
            ("Taxiyatash tumani", "taxiyatash"),
            ("Taxtako'pir tumani", "taxtakopir"),
            ("To'rtko'l tumani", "tortkol"),
            ("Xo'jayli tumani", "xojayli"),
            ("Shimbay tumani", "shimbay"),
            ("Shomanay tumani", "shomanay"),
            ("Ellikqal'a tumani", "ellikqala")
        ]

        cursor.executemany(
            "INSERT OR IGNORE INTO tumanlar (tuman_nomi, tuman_kodi) VALUES (?, ?)",
            tumanlar_list
        )

        # Namuna mahallalar
        sample_mahallalar = [
            ("Botanika MFY", 1, 1), ("Hawa joli MFY", 1, 1), ("Aydin jol MFY", 1, 1),
            ("Shimbay shayxana MFY", 1, 2), ("Xalqlar dostlig'i MFY", 1, 2), ("Shig'is MFY", 1, 2),
            ("Shayirlar awili MFY", 1, 3), ("Tinishliq MFY", 1, 3), ("Dosliq MFY", 1, 3),
            ("Sarbinaz MFY", 1, 3), ("Tong'ish Konis MFY", 1, 3), ("Qosko'l", 1, 3),
            ("Almazar MFY", 1, 3), ("Eli Abat MFY", 1, 3), ("Darbent", 1, 1),
            ("Bayterek MFY", 1, 4), ("Naupir MFY", 1, 4), ("Kattag'ar MFY", 1, 3), ("Go'ne qala MFY", 1, 4),
            ("Taslaq MFY", 1, 2), ("Jolshilar MFY", 1, 2), ("Qum awil MFY", 1, 2), ("Jeke Terek MFY", 1, 1),
            ("Turan MFY", 1, 4), ("Ko'k o'zek MFY", 1, 4), ("Temir jol MFY", 1, 1), ("O'rnek MFY", 1, 3),
            ("Nur MFY", 1, 3), ("Baqshilik MFY", 1, 3), ("Janabazar MFY", 1, 1), ("Qosbulaq MFY", 1, 4),
            ("Qizil qum MFY", 1, 1), ("Jayxun MFY", 1, 1), ("Nawriz MFY", 1, 1), ("Nawqan MFY", 1, 1),
            ("Juwazshi MFY", 1, 1), ("Bes To'be MFY", 1, 1), ("Jiydeli Baysin MFY", 1, 4), ("Amudarya MFY", 1, 4),
            ("Kattag'or MFY", 1, 4), ("Samanbay MFY", 1, 4), ("Anasay MFY", 1, 4), ("Qarataw MFY", 1, 1),
            ("Bo'z awil MFY", 1, 4), ("Qutli Kon'is MFY", 1, 2), ("Qumbuz awil MFY", 1, 4), ("Aq otaw MFY", 1, 3),
            ("Guzar MFY", 1, 1), ("Bereket MFY", 1, 1), ("G'aresizlik MFY", 1, 3), ("Nawbahar MFY", 1, 1),
            ("Allaniyaz Qaharman MFY", 1, 2), ("Qutli makan MFY", 1, 2), ("Jipek joli MFY", 1, 2),
            ("Dosliq guzari MFY", 1, 2),
            ("Gulzar MFY", 1, 3), ("Tele oray MFY", 1, 4), ("Vatanparvar MFY", 1, 3), ("Shimbay guzari MFY", 1, 2),
            ("Atamakan MFY", 1, 2), ("Uzun ko'l MFY", 1, 2), ("Amanliq guzari MFY", 1, 2), ("Altin jag'is MFY", 1, 4),
            ("Shadli awil MFY", 1, 4), ("Jasilbag' MFY", 1, 2), ("Nurli Bo'stan MFY", 1, 1), ("Jan'a Bazar MFY", 1, 3),
            ("Ishbilarmon MFY", 1, 1), ("Abat makan MFY", 1, 2), ("Jas awlad MFY", 1, 2),
            ("Abay OFY", 2, 1), ("Biybazar OFY", 2, 1), ("Beruniy OFY", 2, 1),
            ("Qang'ashortal MFY", 2, 1), ("Nayman MFY", 2, 1), ("Oltinsoy OFY", 2, 1),
            ("Mustaqillik MFY", 2, 1), ("Guliston MFY", 2, 1), ("Qiyot MFY", 2, 1),
            ("Palvosh  MFY", 2, 2), ("Sarkop MFY", 2, 2), ("Tinchlik MFY", 2, 2),
            ("Paxtakor  MFY", 2, 2), ("Navruz MFY", 2, 2), ("Birlik MFY", 2, 2),
            ("Bo'ston  MFY", 2, 2), ("Lolazor MFY", 2, 2), ("Do'stlik MFY", 2, 3),
            ("Qizilqal'a  OFY", 2, 3), ("Mahtumquli OFY", 2, 3), ("Ozod OFY", 2, 3),
            ("Navoiy  MFY", 2, 3), ("Yangiobod MFY", 2, 3), ("A.Temur MFY", 2, 3),
            ("Jayxun  MFY", 2, 3), ("Do'stlik MFY", 2, 3), ("Turon MFY", 2, 4),
            ("I.Sino  MFY", 2, 4), ("Shobboz OFY", 2, 4), ("Shimom MFY", 2, 4),
            ("Markaziy  MFY", 2, 4), ("Istiqlol MFY", 2, 4), ("Bunyodkor MFY", 2, 4),
            ("To'qimachi  MFY", 2, 4), ("Shabboz MFY", 2, 4), ("Sarayko'l MFY", 2, 4), ("Abuhayot  MFY", 2, 4),
            ("Amudaryo OFY", 3, 4), ("Tosh yop OFY", 3, 4), ("O'rta qal'a OFY", 3, 2), ("Arna bo'yi", 3, 4),
            ("Bog' OFY", 3, 2), ("Qilichboy OFY", 3, 2), ("Xizr eli MFY", 3, 2), ("Besh ovul MYF", 3, 2),
            ("Tosh qal'a  MFY", 3, 2), ("Yuqori qishloq  MFY", 3, 2), ("Xolimbeg OFY", 3, 2), ("Ayokchi MYF", 3, 2),
            ("Do'rman OFY", 3, 2), ("Qoramon  MFY", 3, 2), ("Bo'z solma  MFY", 3, 2), ("Bo'z yop OYF", 3, 3),
            ("Xitoy OFY", 3, 3), ("Tor yop  MFY", 3, 3), ("Namuna  MFY", 3, 4), ("Kuyuk ko'pir OYF", 3, 3),
            ("O'zbekiston MFY", 3, 3), ("Qizilcholi  MFY", 3, 3), ("Jumurtov  SHFY", 3, 3), ("Z.M.Bobur OYF", 3, 3),
            ("Jumur ovul MFY", 3, 3), ("Oq oltin  OFY", 3, 3), ("To'lqin OFY", 3, 1), ("Choyko'l OFY", 3, 1),
            ("Bosuv MFY", 3, 1), ("Qipchoq OFY", 3, 1), ("Daryo bo'yi MFY", 3, 1), ("Uyshin MFY", 3, 1),
            ("Besh tom MFY", 3, 1), ("Qipchoq ShFY", 3, 1), ("Qangli OFY", 3, 4), ("Qum yop MFY", 3, 4),
            ("Nazarxon OFY", 3, 1), ("Beruniyi MFY", 3, 4), ("Navoiy MFY", 3, 4), ("Chordara MFY", 3, 4),
            ("Bo'ston MFY", 3, 4), ("Boy ovul MFY", 3, 3), ("Durunki MFY", 3, 3), ("Oybek MFY", 3, 1),
            ("Olmazor MFY", 3, 1), ("Gulzor MFY", 3, 1), ("Do'stlik MFY", 3, 4), ("Yangiobod MFY", 3, 4),
            ("Farovon MFY", 3, 1),
            ("Bo'zatov OFY", 4, 1), ("Aspantay OFY", 4, 1), ("Qo'sqanatov OFY", 4, 2), ("Kuk suv  OFY", 4, 3),
            ("Erkindaryo' OFY", 4, 4),
            ("Juzim bag' OFY", 5, 1), ("Nurli bostan MFY", 5, 1), ("Abat makan MFY", 5, 1), ("Kөkөzek OFY", 5, 1),
            ("Jan'abazar OFY", 5, 2), ("Jilwan jap MFY", 5, 2), ("Iyshan qala OFY", 5, 2), ("Quyashli MFY", 5, 2),
            ("Jalpaq jap OFY", 5, 3), ("Ma'deniyat MFY", 5, 3), ("Abat OFY", 5, 3), ("Xalqabad MFY", 5, 3),
            ("Qumshungul OFY", 5, 4), ("Baxitli MFY", 5, 4), ("Gujim terek MFY", 5, 4), ("Aqtuba OFY", 5, 4),
            ("Besko'pir SHFY", 6, 1), ("Navro'z OFY", 6, 1), ("Altinko'l OFY", 6, 1), ("Jana qala OFY", 6, 1),
            ("Bo'ston OFY", 6, 2), ("Madaniyat OFY", 6, 2), ("Saraltin OFY", 6, 2), ("Jayxun MFY", 6, 3),
            ("Do'stlik MFY", 6, 4), ("Arzimbetqum OFY", 6, 4), ("Qonliko'l SHFY", 6, 4),
            ("Berdax OFY", 7, 1), ("S.Kamalov OFY", 7, 1), ("Yesim  MFY", 7, 1),
            ("Koybak OFY", 7, 1), ("A.Dosnazarov OFY", 7, 2), ("Quralpa  MFY", 7, 2),
            ("Qorao'zak SHFY", 7, 3), ("Garezsizlik guzari MFY", 7, 3), ("Ata makan MFY", 7, 3),
            ("Madeniyat OFY", 7, 3), ("Yesimo'zak OFY", 7, 4), ("Qorao'zak  OFY", 7, 4),
            ("Kutli makan OFY", 7, 4),
            ("Almazar MFY", 8, 1), ("Taraqli MFY", 8, 1), ("Gulabod MFY", 8, 1),
            ("Tallik MFY", 8, 1), ("Xanjap MFY", 8, 1), ("Adebiyat OFY", 8, 1),
            ("O'rnek OFY", 8, 1), ("Xorezm OFY", 8, 1), ("Kiyet MFY", 8, 1),
            ("Jasliq SHFY", 8, 1), ("Temir jol MFY", 8, 2), ("Qashi MFY", 8, 2),
            ("Berdax MFY", 8, 2), ("Monshaqli MFY", 8, 2), ("Ajiniyaz OFY", 8, 2),
            ("Qan'li OFY", 8, 2), ("Qon'irat OFY", 8, 2), ("Ustirt OFY", 8, 2),
            ("Yelabad SHFY", 8, 2), ("Qiriq qiz SHFY", 8, 2), ("Min'jarg'an MFY", 8, 3),
            ("Qumbiz MFY", 8, 3), ("Qaratal MFY", 8, 3), ("Xakim-ata MFY", 8, 3),
            ("Rawshan OFY", 8, 3), ("Ko'kdarya OFY", 8, 3), ("Miynetabad OFY", 8, 3),
            ("Turkistan MFY", 8, 3), ("Altinkol SHFY", 8, 3), ("Qaraqalpaqstan SHFY", 8, 3),
            ("Bostan MFY", 8, 4), ("Turan MFY", 8, 4), ("Qon'irat MFY", 8, 4),
            ("Azatliq MFY", 8, 4), ("Sanaat MFY", 8, 4), ("Jinishke MFY", 8, 4),
            ("Qipshaq OFY", 8, 4), ("Navoiy MFY", 8, 4), ("Suyenli OFY", 8, 4),
            ("Tik wo'zak  OFY", 9, 1), ("Bo'zatov MFY", 9, 1), ("Hakim ota MFY", 9, 2),
            ("Qizil jar OFY", 9, 1), ("Aral MFY", 9, 1), ("Jayxun  MFY", 9, 2),
            ("Talli wo'zak MFY", 9, 1), ("Uchsoy OFY", 9, 1), ("Madeli  OFY", 9, 2),
            ("Qazoqdaryo OFY", 9, 3), ("Mo'ynoq OFY", 9, 4), ("Do'stlik MFY", 9, 4),
            ("Akterek MFY", 10, 1), ("Kirantov OFY", 10, 1), ("Taqirko'l OFY", 10, 1),
            ("Diyxan arna MFY", 10, 1), ("Bakanshali MFY", 10, 2), ("Darsan OFY", 10, 2),
            ("Kutankul MFY", 10, 2), ("Arbashi OFY", 10, 3), ("Kerder OFY", 10, 3),
            ("Tuktov MFY", 10, 3), ("Akmangit SHFY", 10, 4), ("Samanbay OFY", 10, 4),
            ("Ulgili makan MFY", 10, 4),
            ("Naymanko'l OFY", 11, 1), ("Dostlik MFY", 11, 1), ("Yangi makon MFY", 11, 2),
            ("Nurli kelajak OFY", 11, 1), ("Keneges OFY", 11, 2), ("Oydin yo'l MFY", 11, 2),
            ("Taxiatosh MFY", 11, 2), ("Qushchilik MFY", 11, 3), ("Shamchiroq MFY", 11, 3),
            ("Sarayko'l MFY", 11, 3), ("Obod makon MFY", 11, 3), ("Markaziy MFY", 11, 4),
            ("Xalqlar do'stligi MFY", 11, 4), ("Jayxun' MFY", 11, 4),
            ("Atakol OFY", 12, 1), ("Dawir MFY", 12, 1), ("Janadarya OFY", 12, 1),
            ("Aydin jol MFY ", 12, 2), ("Dawqara OFY", 12, 2), ("Qarateren' MFY", 12, 2),
            ("Beltaw OFY ", 12, 2), ("G'arezsizlik MFY", 12, 3), ("Qaraoy  MFY", 12, 3),
            ("O'zbekiston MFY ", 12, 3), ("Marjankol MFY", 12, 3), ("Taxtako'pir  SHFY", 12, 4),
            ("A.Adilov OFY ", 12, 4), ("Mulik OFY", 12, 4), ("Dawitsay  MFY", 12, 4),
            ("Kong'iratko'l OFY ", 12, 4), ("Qostruba  MFY", 12, 4),
            ("Atawba OFY", 13, 2), ("Anxorli MFY", 13, 1), ("Beruniy MFY", 13, 2),
            ("Bog'yop MFY", 13, 3), ("G'alaba MFY", 13, 4), ("Guliston MFY", 13, 3),
            ("Do'stlik MFY", 13, 1), ("Yonboshqal'a OFY", 13, 1), ("Yoshlik MFY", 13, 1),
            ("Jayxun MFY", 13, 1), ("Ibn Sino OFY", 13, 3), ("Istiqlol MFY", 13, 1),
            ("Kaltaminor OFY", 13, 2), ("Ko'kcha OFY", 13, 3), ("Kumbasqan  MFY", 13, 4),
            ("Mustaqillik OFY", 13, 3), ("Navoiy MFY", 13, 3), ("Navro'z MFY", 13, 4),
            ("Oqboshli OFY", 13, 1), ("Oqqamish OFY", 13, 3), ("'Ota yurt OFY", 13, 3),
            ("O'zbekiston OFY", 13, 2), ("Paxtaobod OFY", 13, 2), ("Paxtachi OFY", 13, 1),
            ("Tinchlik MFY", 13, 4), ("Tozabog'yop OFY", 13, 4), ("Toshkent MFY", 13, 4),
            ("Turkiston MFY", 13, 4), ("Markazobod MFY", 13, 4), ("Uzbekiston MFY", 13, 4),
            ("Ullubog' OFY", 13, 4), ("Sho'raxon OFY", 13, 1), ("Yangiobod OFY", 13, 3),
            ("Shodlik MFY", 13, 2), ("Mash'al MFY", 13, 2), ("Ko'na To'rtko'l OFY", 13, 1),
            ("To'rtko'l MFY", 13, 4), ("Bazirgon MFY", 13, 2), ("Miskin OFY", 13, 3),
            ("Bahor MFY", 13, 1), ("Yangi hayot MFY", 13, 1), ("Nurota MFY", 13, 3),
            ("Tozabo'zyop MFY", 13, 3), ("Ziyokor MFY", 13, 1), ("Nurli yo'l MFY", 13, 4),
            ("Yashnobod MFY", 13, 1), ("Yaxtilik MFY", 13, 2), ("Yakkatol MFY", 13, 4),
            ("Turkman ko'li MFY", 13, 2),
            ("Bayterek MFY", 14, 2), ("Juzimzar MFY", 14, 1), ("Tinchlik MFY", 14, 2),
            ("Kun nuri MFY", 14, 3), ("Obod MFY", 14, 1), ("Murtazabiy MFY", 14, 4),
            ("Tasko'pir MFY", 14, 2), ("Madaniyat MFY", 14, 4), ("Nurli jol MFY", 14, 1),
            ("Qirqinshi MFY", 14, 3), ("Suenli MFY", 14, 3), ("Parvoz MFY", 14, 4),
            ("Qumbiz MFY", 14, 3), ("Shag'alako'l MFY", 14, 4), ("Tutzar MFY", 14, 1),
            ("Bunyodkor MFY", 14, 3), ("Navro'z MFY", 14, 1), ("Janqonirat MFY", 14, 3),
            ("Jayxun SHFY", 14, 4), ("Amudaryo OFY", 14, 3), ("Qulob OFY", 14, 2),
            ("Qumjiqqin OFY", 14, 1), ("Sarishingul OFY", 14, 2), ("Samanko'l OFY", 14, 1),
            ("Jana-jap OFY", 14, 4), ("Bagman MFY", 14, 1), ("Sabik MFY", 14, 2),
            ("Mustaqillik OFY", 14, 4),
            ("Kokshi qala OFY", 15, 1), ("Kenes OFY", 15, 1), ("Kosterek OFY", 15, 1),
            ("Tazajol OFY", 15, 1), ("Qarakol MFY", 15, 2), ("Konshi MFY", 15, 2),
            ("Temir jol guzari MFY", 15, 2), ("Gulistan MFY", 15, 2), ("Tazgara OFY", 15, 2),
            ("Tagjap OFY", 15, 2), ("Gujimli MFY", 15, 3), ("Baxitli OFY", 15, 3),
            ("Kizil-uzak OFY", 15, 3), ("Pashent taw OFY", 15, 3), ("Mayjap OFY", 15, 3),
            ("Abat makan MFY", 15, 4), ("Berdaq MFY", 15, 4), ("Doslik MFY", 15, 4),
            ("Shaxtemir MFY", 15, 4), ("Orjap MFY", 15, 4), ("Jipek joli MFY", 15, 4),
            ("Kamis-arik OFY", 15, 4),
            ("Aybuyir MFY", 16, 1), ("Aq jap OFY", 16, 1), ("Mamiy OFY", 16, 1),
            ("Monshaqli MFY", 16, 1), ("Diyxanabad OFY", 16, 2), ("Ketenler OFY", 16, 2),
            ("Begjap OFY", 16, 2), ("Birleshik OFY", 16, 3), ("Karabayli MFY", 16, 3),
            ("Madeniyat MFY", 16, 4), ("Nawriz MFY", 16, 4), ("Sarmanbayko'l OFY", 16, 4),
            ("Taza bazar MFY", 16, 4),
            ("Toza bog' OFY", 17, 1), ("Jasorat MFY", 17, 1), ("Navbahor MFY", 17, 1),
            ("Guldursin OFY", 17, 1), ("Saxtiyon ShFY", 17, 1), ("Chuqurqoq MFY", 17, 1),
            ("Guliston OFY", 17, 1), ("Qizilqum OFY", 17, 1), ("Qirqqizobod OFY", 17, 1),
            ("Burgutqal'a MFY", 17, 1), ("Oq-Oltin MFY", 17, 1), ("Yangi O'zbekiston MFY", 17, 1),
            ("Navoiy OFY", 17, 2), ("Iftixor MFY", 17, 2), ("Kichik Guldursun  MFY", 17, 2),
            ("Aqchako'l OFY", 17, 2), ("Sharq-Yulduzi OFY", 17, 2), ("Tuproqqal'a MFY", 17, 2),
            ("Do'stlik OFY", 17, 3), ("Amirobod OFY", 17, 3), ("To'rt devor MFY", 17, 3),
            ("Ixlos MFY", 17, 3), ("Koinot MFY", 17, 3), ("Sarabiy OFY", 17, 3),
            ("Barhayot MFY", 17, 3), ("Dumanqal'a MFY", 17, 3), ("Qoshqo'ra MFY", 17, 3),
            ("Qilichinoq OFY", 17, 3), ("Paxtachi MFY", 17, 3),
            ("Cho'pon MFY", 17, 3), ("Ellikqal'a OFY", 17, 4), ("Ayozqal'a MFY", 17, 4),
            ("Bo'ston MFY", 17, 4), ("Ibn Sino MFY", 17, 4), ("A.Navoiy MFY", 17, 4),
            ("Abay MFY", 17, 4), ("Toshkent MFY", 17, 4), ("Qavatqal'a MFY", 17, 4),
            ("Istiqlol MFY", 17, 4), ("Iqbol MFY", 17, 4),
        ]

        for mahalla_nomi, tuman_id, sektor in sample_mahallalar:
            cursor.execute('''
                INSERT OR IGNORE INTO mahallalar (mahalla_nomi, tuman_id, sektor)
                VALUES (?, ?, ?)
            ''', (mahalla_nomi, tuman_id, sektor))

        print("✅ Namuna mahallalar bazaga qo'shildi (dublikatlarni oldini olindi).")

        # Xodim pozitsiyalari
        positions = [
            "Mahalla raisi",
            "Profilaktika inspektori",
            "Xotin-qizlar faoli",
            "Xokim yordamchisi",
            "Yoshlar yetakchisi",
            "Ijtimoiy xodimi",
            "Soliq xodimi"
        ]

        cursor.execute("SELECT COUNT(*) FROM xodimlar")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT mahalla_id FROM mahallalar")
            mahalla_ids = [row[0] for row in cursor.fetchall()]
            for mahalla_id in mahalla_ids:
                for position in positions:
                    cursor.execute('''
                        INSERT INTO xodimlar (mahalla_id, position, full_name, phone)
                        VALUES (?, ?, ?, ?)
                    ''', (mahalla_id, position, "VAKANT", "VAKANT"))
            print(f"✅ {len(mahalla_ids)} ta mahallaga xodimlar uchun joylar yaratildi.")

        # Namuna xodimlar ma'lumotlari
        sample_data = {
            "Toza bog' OFY": [
                ("Mahalla raisi", "Seytimov Aytboy", "88-059-05-65"),
                ("Profilaktika inspektori", "Joldasov Asilbek", "91-001-30-28"),
                ("Xotin-qizlar faoli", "Babayeva Anargul", "97-508-90-39"),
                ("Xokim yordamchisi", "Qurbonboyev Muxammadsafo", "97-474-00-17"),
                ("Yoshlar yetakchisi", "Sapayev Adilbek", "97-926-57-00"),
                ("Ijtimoiy xodimi", "VAKANT", "VAKANT"),
                ("Soliq xodimi", "Bekjasarov Musabek", "97-829-55-44")
            ],
            "Beruniy OFY": [
                ("Mahalla raisi", "Nazarov Bekzod", "97-111-22-33"),
                ("Profilaktika inspektori", "VAKANT", "VAKANT"),
                ("Xotin-qizlar faoli", "Yusupova Guzal", "98-222-33-44"),
                ("Xokim yordamchisi", "Ibragimov Rustam", "99-333-44-55"),
                ("Yoshlar yetakchisi", "VAKANT", "VAKANT"),
                ("Ijtimoiy xodimi", "Xamidova Nodira", "90-444-55-66"),
                ("Soliq xodimi", "Qosimov Farrux", "91-555-66-77")
            ]
        }

        for mahalla_nomi, xodimlar in sample_data.items():
            cursor.execute('''
                SELECT mahalla_id FROM mahallalar WHERE mahalla_nomi = ?
            ''', (mahalla_nomi,))
            result = cursor.fetchone()
            if result:
                mahalla_id = result[0]
                for pos, name, phone in xodimlar:
                    cursor.execute('''
                        UPDATE xodimlar
                        SET full_name = ?, phone = ?
                        WHERE mahalla_id = ? AND position = ?
                    ''', (name, phone, mahalla_id, pos))

        print("✅ Namuna xodimlar ma'lumotlari kiritildi.")
        conn.commit()

    except Exception as e:
        print(f"❌ Ma'lumotlar bazasi xatoligi: {e}")
        conn.rollback()
    finally:
        conn.close()


async def save_or_update_user(update, context):
    """Foydalanuvchini bazaga saqlash yoki yangilash"""
    user = update.effective_user
    conn = sqlite3.connect('qoraqalpogiston_mahalla.db')
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT phone FROM foydalanuvchilar WHERE user_id = ?", (user.id,))
        result = cursor.fetchone()

        if result:
            phone = result[0]
            if phone == "YASHIRIN":
                return False
            else:
                cursor.execute('''
                    UPDATE foydalanuvchilar 
                    SET last_seen = CURRENT_TIMESTAMP, full_name = ?, username = ?
                    WHERE user_id = ?
                ''', (user.full_name, user.username or "N/A", user.id))
                conn.commit()
                return True
        else:
            cursor.execute('''
                INSERT INTO foydalanuvchilar (user_id, full_name, username, phone)
                VALUES (?, ?, ?, ?)
            ''', (user.id, user.full_name, user.username or "N/A", "YASHIRIN"))
            conn.commit()
            print(f"🆕 Yangi foydalanuvchi: {user.full_name} ({user.id})")
            return False

    except Exception as e:
        print(f"❌ Foydalanuvchi saqlashda xato: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


async def ask_contact(update, context):
    """Foydalanuvchiga kontakt so'rash"""
    button = KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "⚠️ Iltimos, telefon raqamingizni yuboring, shunda sizga mahalla ma'lumotlarini ko'rsatish imkoniyati beriladi.",
        reply_markup=keyboard
    )


async def contact_handler(update, context):
    """Kontakt qabul qilish va yangilash"""
    try:
        if not update.message or not update.message.contact:
            return

        contact = update.message.contact
        phone = contact.phone_number
        user_id = update.effective_user.id

        conn = sqlite3.connect('qoraqalpogiston_mahalla.db')
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE foydalanuvchilar 
                SET phone = ?, last_seen = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (phone, user_id))
            conn.commit()
            print(f"✅ Foydalanuvchi {user_id} telefon raqamini kiritdi: {phone}")
        except Exception as e:
            print(f"❌ Ma'lumotlar bazasiga saqlashda xato: {e}")
            conn.rollback()
        finally:
            conn.close()

        await update.message.reply_text(
            "✅ *Telefon raqamingiz muvaffaqiyatli saqlandi!*",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )

        keyboard = [
            [
                InlineKeyboardButton("🇺🇿 O'zbek tili", callback_data="lang_uz"),
                InlineKeyboardButton("🇷🇺 Русский язык", callback_data="lang_ru")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🌍 Iltimos, tilni tanlang:", reply_markup=reply_markup)

    except Exception as e:
        print(f"❌ Kontakt qabul qilishda xato: {e}")


async def start(update, context):
    """/start buyrug'i - asosiy logika"""
    phone_exists = await save_or_update_user(update, context)

    if not phone_exists:
        await ask_contact(update, context)
    else:
        keyboard = [
            [
                InlineKeyboardButton("🇺🇿 O'zbek tili", callback_data="lang_uz"),
                InlineKeyboardButton("🇷🇺 Русский язык", callback_data="lang_ru")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "✅ Sizning telefon raqamingiz allaqachon saqlangan!\n\n🌍 Iltimos, tilni tanlang:",
            reply_markup=reply_markup
        )


async def button_handler(update, context):
    """Callback tugmalari uchun handler"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    try:
        if data == "lang_uz":
            save_pending_action(user_id, 'language_selection', {'lang': 'uz'})
            await show_main_menu(update, context, lang="uz")
        elif data == "lang_ru":
            save_pending_action(user_id, 'language_selection', {'lang': 'ru'})
            await show_main_menu(update, context, lang="ru")
        elif data == "back_uz" or data == "back_ru":
            lang = "uz" if data == "back_uz" else "ru"
            await start_from_callback(update, context, lang)
        elif data == "back_to_main_uz" or data == "back_to_main_ru":
            lang = "uz" if data == "back_to_main_uz" else "ru"
            await show_main_menu(update, context, lang=lang)
        elif data == "news_uz" or data == "news_ru":
            lang = "uz" if data == "news_uz" else "ru"
            await send_news(update, context, lang)
        elif data == "stats_uz" or data == "stats_ru":
            lang = "uz" if data == "stats_uz" else "ru"
            await send_stats(update, context, lang)
        elif data == "mahalla_uz" or data == "mahalla_ru":
            lang = "uz" if data == "mahalla_uz" else "ru"
            await show_district_menu(update, context, lang)
        elif data.startswith("tuman_"):
            parts = data.split("_")
            if len(parts) >= 3:
                lang = parts[1]
                tuman_kodi = "_".join(parts[2:])
                save_pending_action(user_id, 'mahalla_request', {
                    'tuman_kodi': tuman_kodi,
                    'lang': lang
                })
                await show_mahalla_list(update, context, tuman_kodi=tuman_kodi, lang=lang)
        elif data.startswith("mahalla_detail_"):
            parts = data.split("_")
            if len(parts) < 4:
                await query.message.reply_text("❌ Noto'g'ri ma'lumot formati.")
                return

            lang = parts[2]
            try:
                mahalla_index = int(parts[-1])
                tuman_kodi = "_".join(parts[3:-1])
                save_pending_action(user_id, 'mahalla_details', {
                    'tuman_kodi': tuman_kodi,
                    'lang': lang,
                    'mahalla_index': mahalla_index
                })
                await show_mahalla_details(update, context, tuman_kodi, lang, mahalla_index)
            except (ValueError, IndexError):
                await query.message.reply_text("❌ Ma'lumotlarni tahlil qilishda xatolik.")
                return
    except Exception as e:
        print(f"❌ Button handler xatosi: {e}")
        save_pending_action(user_id, 'error_recovery', {'callback_data': data})


async def show_main_menu(update, context, lang="uz"):
    """Asosiy menyu"""
    if lang == "uz":
        text = (
            "✅ *Siz O'zbek tilini tanladingiz!*\n\n"
            "🏛️ *Qoraqalpoğiston Respublikasi*\n"
            "*Mahalla xodimlari ma'lumot tizimi*\n\n"
            "Quyidagi bo'limlardan birini tanlang:"
        )
        buttons = [
            [InlineKeyboardButton("📰 So'nggi yangiliklar", callback_data="news_uz")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats_uz")],
            [InlineKeyboardButton("🏘️ Mening mahallam", callback_data="mahalla_uz")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_uz")]
        ]
    else:
        text = (
            "✅ *Вы выбрали русский язык!*\n\n"
            "🏛️ *Республика Каракалпакстан*\n"
            "*Информационная система сотрудников махалли*\n\n"
            "Выберите раздел:"
        )
        buttons = [
            [InlineKeyboardButton("📰 Последние новости", callback_data="news_ru")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats_ru")],
            [InlineKeyboardButton("🏘️ Моя махалля", callback_data="mahalla_ru")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_ru")]
        ]

    reply_markup = InlineKeyboardMarkup(buttons)
    try:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            print(f"❌ Asosiy menyu xatosi ({lang}): {e}")


async def show_district_menu(update, context, lang="uz"):
    """17 ta tumanni ko'rsatish"""
    conn = sqlite3.connect('qoraqalpogiston_mahalla.db')
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT tuman_nomi, tuman_kodi FROM tumanlar ORDER BY tuman_nomi")
        tumanlar = cursor.fetchall()
    except Exception as e:
        print(f"❌ Tumanlar ro'yxatini olishda xato: {e}")
        tumanlar = []
    finally:
        conn.close()

    if lang == "uz":
        text = "🏘️ *\"Mening mahallam\" bo'limi*\n\n📍 Qoraqalpoğiston Respublikasi tumanlari:\n\nO'z tumaningizni tanlang:"
    else:
        text = "🏘️ *Раздел \"Моя махалля\"*\n\n📍 Районы Республики Каракалпакстан:\n\nВыберите ваш район:"

    keyboard = []
    for i in range(0, len(tumanlar), 2):
        row = []
        for j in range(2):
            if i + j < len(tumanlar):
                tuman_nomi, tuman_kodi = tumanlar[i + j]
                row.append(InlineKeyboardButton(
                    f"📍 {tuman_nomi}",
                    callback_data=f"tuman_{lang}_{tuman_kodi}"
                ))
        keyboard.append(row)

    back_data = "back_to_main_uz" if lang == "uz" else "back_to_main_ru"
    keyboard.append([InlineKeyboardButton("🔙 Orqaga" if lang == "uz" else "🔙 Назад", callback_data=back_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            print(f"❌ Tuman menyusi xatosi ({lang}): {e}")


async def show_mahalla_list(update, context, tuman_kodi, lang="uz"):
    """Tanlangan tumandagi mahallalarni ko'rsatish"""
    conn = sqlite3.connect('qoraqalpogiston_mahalla.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
                    SELECT m.mahalla_nomi, t.tuman_nomi 
                    FROM mahallalar m 
                    JOIN tumanlar t ON m.tuman_id = t.tuman_id 
                    WHERE t.tuman_kodi = ? 
                    ORDER BY m.mahalla_nomi
                ''', (tuman_kodi,))
        result = cursor.fetchall()

        if result:
            mahallalar = [row[0] for row in result]
            tuman_nomi = result[0][1]
        else:
            mahallalar = []
            tuman_nomi = "Noma'lum tuman"

    except Exception as e:
        print(f"❌ Mahallalar ro'yxatini olishda xato: {e}")
        mahallalar = []
        tuman_nomi = "Xato"
    finally:
        conn.close()

    if lang == "uz":
        text = f"🏘️ *{tuman_nomi}*\n\n📍 Mahallalar ro'yxati:\nKerakli mahallani tanlang:"
        back_text = "🔙 Orqaga"
    else:
        text = f"🏘️ *{tuman_nomi}*\n\n📍 Список махаллей:\nВыберите нужную махаллю:"
        back_text = "🔙 Назад"

    keyboard = []
    for i in range(0, len(mahallalar), 2):
        row = []
        if i < len(mahallalar):
            row.append(InlineKeyboardButton(
                f"🏘{mahallalar[i]}",
                callback_data=f"mahalla_detail_{lang}_{tuman_kodi}_{i}"
            ))
        if i + 1 < len(mahallalar):
            row.append(InlineKeyboardButton(
                f"🏘{mahallalar[i + 1]}",
                callback_data=f"mahalla_detail_{lang}_{tuman_kodi}_{i + 1}"
            ))
        keyboard.append(row)

    main_back_data = "mahalla_uz" if lang == "uz" else "mahalla_ru"
    keyboard.append([InlineKeyboardButton(back_text, callback_data=main_back_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            print(f"❌ Mahalla ro'yxati xatosi ({tuman_kodi}, {lang}): {e}")


async def show_mahalla_details(update, context, tuman_kodi, lang, mahalla_index):
    """Mahalla xodimlari haqida batafsil ma'lumot"""
    conn = sqlite3.connect('qoraqalpogiston_mahalla.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
                    SELECT m.mahalla_nomi, m.mahalla_id, t.tuman_nomi
                    FROM mahallalar m 
                    JOIN tumanlar t ON m.tuman_id = t.tuman_id 
                    WHERE t.tuman_kodi = ? 
                    ORDER BY m.mahalla_nomi
                ''', (tuman_kodi,))
        mahallalar = cursor.fetchall()

        if mahalla_index >= len(mahallalar):
            selected_mahalla = "Noma'lum mahalla"
            mahalla_id = None
            tuman_nomi = "Noma'lum tuman"
        else:
            selected_mahalla, mahalla_id, tuman_nomi = mahallalar[mahalla_index]

        positions_order = [
            "Mahalla raisi",
            "Profilaktika inspektori",
            "Xotin-qizlar faoli",
            "Xokim yordamchisi",
            "Yoshlar yetakchisi",
            "Ijtimoiy xodimi",
            "Soliq xodimi"
        ]

        xodimlar = []
        if mahalla_id:
            for pos in positions_order:
                cursor.execute('''
                            SELECT position, full_name, phone
                            FROM xodimlar
                            WHERE mahalla_id = ? AND position = ?
                        ''', (mahalla_id, pos))
                row = cursor.fetchone()
                if row:
                    xodimlar.append(row)
                else:
                    xodimlar.append((pos, "VAKANT", "VAKANT"))
        else:
            xodimlar = []

    except Exception as e:
        print(f"❌ Mahalla detallarini olishda xato: {e}")
        selected_mahalla = "Xato"
        tuman_nomi = "Xato"
        xodimlar = []
    finally:
        conn.close()

    emoji_list = ["👨‍💼", "👮‍♂️", "👩‍💼", "🏛️", "👨‍🎓", "📋", "💰"]

    if lang == "uz":
        text_lines = [
            f"🏘️ *{selected_mahalla}*",
            f"📍 *{tuman_nomi}*",
            "",
            "*Mahalla xodimlari:*",
            ""
        ]
    else:
        text_lines = [
            f"🏘️ *{selected_mahalla}*",
            f"📍 *{tuman_nomi}*",
            "",
            "*Сотрудники махалли:*",
            ""
        ]

    for idx, xodim in enumerate(xodimlar):
        position, full_name, phone = xodim
        emoji = emoji_list[idx % len(emoji_list)]

        text_lines.append(f"{emoji} *{position}:*")
        text_lines.append(f"👤 {full_name}")

        if phone != "VAKANT":
            clean_phone = "".join(filter(str.isdigit, phone))
            if len(clean_phone) == 9:
                formatted_phone = "+998" + clean_phone
            elif len(clean_phone) == 12 and clean_phone.startswith("998"):
                formatted_phone = "+" + clean_phone
            else:
                formatted_phone = phone

            text_lines.append(f"📞 [{formatted_phone}](tel:{formatted_phone.replace('+', '')})")
        else:
            text_lines.append("📞 *VAKANT*")

        text_lines.append("")

    text = "\n".join(text_lines).strip()

    if lang == "uz":
        back_text = "🔄 Boshqa mahalla"
        main_text = "🔙 Tumanlar ro'yxati"
        district_data = f"tuman_{lang}_{tuman_kodi}"
        main_data = "mahalla_uz"
    else:
        back_text = "🔄 Другая махалля"
        main_text = "🔙 Список районов"
        district_data = f"tuman_{lang}_{tuman_kodi}"
        main_data = "mahalla_ru"

    keyboard = [
        [InlineKeyboardButton(back_text, callback_data=district_data)],
        [InlineKeyboardButton(main_text, callback_data=main_data)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            print(f"❌ Mahalla detallari xatosi ({tuman_kodi}, {lang}, index={mahalla_index}): {e}")


async def send_news(update, context, lang="uz"):
    """Yangiliklar bo'limi"""
    if lang == "uz":
        text = (
            "📰 *So'nggi yangiliklar (Qoraqalpoğiston):*\n\n"
            "🏛️ *22-oktyabr 2025:* Respublikada mahalla xodimlari uchun yangi axborot tizimi ishga tushirildi.\n\n"
            "📊 *20-oktyabr 2025:* Barcha 17 ta tumandagi mahallalar ma'lumotlar bazasi yangilandi.\n\n"
            "👥 *18-oktyabr 2025:* Mahalla faollari uchun treninglar boshlanishi e'lon qilindi.\n\n"
            "🔐 *15-oktyabr 2025:* Raqamli xizmatlar xavfsizligi kuchaytirildi.\n\n"
            "💡 *12-oktyabr 2025:* Yoshlar uchun yangi loyihalar ishga tushirilmoqda.\n\n"
            "📱 Yangiliklar har kuni yangilanadi!"
        )
        back_data = "back_to_main_uz"
    else:
        text = (
            "📰 *Последние новости (Каракалпакстан):*\n\n"
            "🏛️ *22 октября 2025:* В республике запущена новая информационная система для сотрудников махаллей.\n\n"
            "📊 *20 октября 2025:* Обновлена база данных махаллей во всех 17 районах.\n\n"
            "👥 *18 октября 2025:* Объявлено о начале тренингов для активистов махаллей.\n\n"
            "🔐 *15 октября 2025:* Усилена безопасность цифровых сервисов.\n\n"
            "💡 *12 октября 2025:* Запускаются новые проекты для молодежи.\n\n"
            "📱 Новости обновляются ежедневно!"
        )
        back_data = "back_to_main_ru"

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu" if lang == "uz" else "🔙 Главное меню", callback_data=back_data)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            print(f"❌ Yangiliklar xatosi ({lang}): {e}")


async def send_stats(update, context, lang="uz"):
    """Statistika bo'limi"""
    conn = sqlite3.connect('qoraqalpogiston_mahalla.db')
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM tumanlar")
        tumanlar_soni = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM mahallalar")
        mahallalar_soni = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM xodimlar WHERE full_name != 'VAKANT'")
        band_xodimlar = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM xodimlar")
        jami_xodimlar = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM foydalanuvchilar")
        foydalanuvchilar = cursor.fetchone()[0]

    except Exception as e:
        print(f"❌ Statistika olishda xato: {e}")
        tumanlar_soni = mahallalar_soni = band_xodimlar = jami_xodimlar = foydalanuvchilar = 0
    finally:
        conn.close()

    if lang == "uz":
        text = (
            "📊 *Qoraqalpoğiston Respublikasi statistikasi:*\n\n"
            f"🏛️ **Tumanlar soni:** {tumanlar_soni} ta\n"
            f"🏘️ **Mahallalar soni:** {mahallalar_soni} ta\n"
            f"👥 **Jami xodimlar:** {jami_xodimlar} ta\n"
            f"✅ **Band lavozimlar:** {band_xodimlar} ta\n"
            f"❌ **Bo'sh lavozimlar:** {jami_xodimlar - band_xodimlar} ta\n"
            f"📱 **Bot foydalanuvchilari:** {foydalanuvchilar} ta\n\n"
            f"📈 **To'ldirilganlik:** {round((band_xodimlar / jami_xodimlar) * 100) if jami_xodimlar > 0 else 0}%\n\n"
            "📅 Ma'lumotlar har kuni yangilanadi."
        )
        back_data = "back_to_main_uz"
    else:
        text = (
            "📊 *Статистика Республики Каракалпакстан:*\n\n"
            f"🏛️ **Количество районов:** {tumanlar_soni}\n"
            f"🏘️ **Количество махаллей:** {mahallalar_soni}\n"
            f"👥 **Всего должностей:** {jami_xodimlar}\n"
            f"✅ **Занятые должности:** {band_xodimlar}\n"
            f"❌ **Вакантные должности:** {jami_xodimlar - band_xodimlar}\n"
            f"📱 **Пользователи бота:** {foydalanuvchilar}\n\n"
            f"📈 **Заполненность:** {round((band_xodimlar / jami_xodimlar) * 100) if jami_xodimlar > 0 else 0}%\n\n"
            "📅 Данные обновляются ежедневно."
        )
        back_data = "back_to_main_ru"

    keyboard = [[InlineKeyboardButton("🔙 Bosh menyu" if lang == "uz" else "🔙 Главное меню", callback_data=back_data)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            print(f"❌ Statistika xatosi ({lang}): {e}")


async def start_from_callback(update, context, lang="uz"):
    """Tilni qayta tanlash"""
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O'zbek tili", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский язык", callback_data="lang_ru")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if lang == "uz":
        text = "🌍 *Tilni qayta tanlang:*\n\n🏛️ *Qoraqalpoğiston Respublikasi*\nMahalla xodimlari axborot tizimi"
    else:
        text = "🌍 *Выберите язык:*\n\n🏛️ *Республика Каракалпакстан*\nИнформационная система сотрудников махалли"

    try:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            print(f"❌ Til tanlash xatosi ({lang}): {e}")


def main():
    """Asosiy funksiya"""
    print("🔧 Ma'lumotlar bazasi sozlanmoqda...")
    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    print("🔄 Bot ishga tushirilmoqda...")
    print("✅ Qoraqalpoğiston mahalla xodimlari boti tayyor!")

    # ⭐ BOT ISHGA TUSHGANDA KUTILAYOTGAN AMALLARNI QAYTA ISHLASH
    try:
        asyncio.get_event_loop().run_until_complete(process_pending_actions(app))
    except Exception as e:
        print(f"❌ Pending actions qayta ishlashda xato: {e}")

    print("📱 /start buyrug'ini yuboring.")
    print("📊 17 ta tuman va mahallalar ma'lumotlar bazasiga yuklandi.")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Bot to'xtatildi!")
    except Exception as e:
        print(f"❌ Bot ishga tushirishda xato: {e}")
        import traceback

        traceback.print_exc()