# Telegram do'kon boti

Telegram uchun savdo boti (katalog, savat, buyurtma, profil, yordam va
boshqaruv bo'limlari). Poydevor qatlamlari (konfiguratsiya, ma'lumotlar bazasi
(SQLAlchemy 2.0 async), servislar, middleware'lar, klaviaturalar, ikki tilli
(uz/ru) lokalizatsiya) va barcha bo'limlarning handler/router qatlami tayyor:
`start`, `catalog`, `cart`, `checkout`, `orders`, `profile`, `support`,
`admin` hamda `fallback`.

## 1. Talablar

- Python **3.11+** (loyihada 3.13 sinovdan o'tgan)
- Windows PowerShell yoki Linux/macOS terminali
- @BotFather'dan olingan bot tokeni

## 2. O'rnatish

```powershell
cd "C:\Users\Admin\Desktop\telegram bot"

# Virtual muhit (agar hali bo'lmasa)
python -m venv .venv

# Kutubxonalar (dev: pytest bilan)
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 3. `.env` faylini sozlash

```powershell
Copy-Item .env.example .env
```

`.env` ichida kamida quyidagilarni to'ldiring:

| O'zgaruvchi | Izoh |
| --- | --- |
| `BOT_TOKEN` | @BotFather'dan olingan token (majburiy) |
| `ADMIN_IDS` | Adminlar Telegram ID lari (vergul bilan). ID ni `/myid` bilan bilib olasiz |
| `DATABASE_URL` | Dev uchun SQLite: `sqlite+aiosqlite:///./data/distribution.db` |
| `SUPPORT_CHAT_ID` | Operator guruhi (ixtiyoriy, masalan `-1001234567890`) |

Qolgan qiymatlar (`DELIVERY_FEE`, `MIN_ORDER_AMOUNT`, `BRAND_NAME`,
`SUPPORT_PHONE`, `WORKING_HOURS`, `ENABLE_DAILY_JOBS` ...) savdo siyosati va
interfeys sozlamalari - standart qiymatlari bilan ishlayveradi.

> `.env` fayli `.gitignore` da - tokenni hech qachon repoga qo'shmang.

## 4. Ishga tushirish

```powershell
.venv\Scripts\python.exe main.py
```

Ishga tushish tartibi:

```
init_models -> Bot(parse_mode=HTML) -> Dispatcher(MemoryStorage)
-> register_middlewares -> register_routers -> set_my_commands -> start_polling
```

- `BOT_TOKEN` bo'sh bo'lsa bot aniq xato bilan to'xtaydi va nima qilishni aytadi.
- To'xtatish: `Ctrl+C` (log: `Bot to'xtatildi 👋`).
- Buyruqni loyiha ildizidan bering: `main.py` ildizda turgani uchun `bot`
  paketi avtomatik topiladi. Boshqa papkadan chaqirsangiz `PYTHONPATH` ni
  loyiha ildiziga qaratib qo'ying.

## 5. Hozir ishlaydigan buyruqlar va bo'limlar

| Buyruq / tugma | Vazifasi |
| --- | --- |
| `/start` | Tanishish, asosiy menyu, kerak bo'lsa telefon raqamini so'rash |
| `/menu` | Asosiy menyuni qayta ochish |
| `/help` | Botdan foydalanish bo'yicha qisqa ma'lumot |
| `/language` | Tilni almashtirish (o'zbekcha / русский) |
| `/myid` | Telegram ID (admin qilish uchun kerak) |
| `/cancel` | Joriy qadamni to'xtatib menyuga qaytish |
| `/catalog`, `/promo`, `/cart`, `/orders` | Bo'limlarni to'g'ridan-to'g'ri ochish |
| `📱 Raqamni ulashish` | Kontakt orqali yoki qo'lda yozib raqamni saqlash |

Raqam `+998XXXXXXXXX` ko'rinishida normallashtiriladi, boshqa odamning
kontakti rad etiladi, «❌ Bekor qilish» bilan so'rov to'xtatiladi.

Asosiy menyu tugmalari (barchasi ishlaydi, `bot/handlers/__init__.py` dagi
`ROUTER_BUILDERS` tartibida):

| Tugma | Router | Bo'lim |
| --- | --- | --- |
| `🛍 Katalog` | `catalog` | kategoriyalar, mahsulot kartochkasi, qidiruv, savatga qo'shish |
| `🔥 Aksiyalar` | `catalog` | chegirmali mahsulotlar ro'yxati |
| `🛒 Savat` | `cart` | miqdorni o'zgartirish, o'chirish, tozalash, buyurtmaga o'tish |
| `📦 Buyurtmalarim` | `orders` | tarix, kartochka, bekor qilish, takrorlash |
| `👤 Profil` | `profile` | raqamni yangilash, manzillar, til |
| `☎️ Yordam` | `support` | operatorga yozish, qo'ng'iroq raqami |
| `🛠 Boshqaruv` | `admin` | faqat xodimlar: statistika, buyurtmalar, holat, kam qoldiq, murojaatlar |

Savatdagi «🚚 Buyurtma berish» inline tugmasi (`CartCB(action="checkout")`)
`checkout` router'ini ishga tushiradi: yetkazish turi, manzil, vaqt, izoh,
to'lov va tasdiqlash (FSM: `CheckoutStates`).

Har bir inline ekrandagi «🏠 Asosiy menyu» tugmasi (`MenuCB(action="main")`)
holatni tozalaydi, xabarni tahrirlab inline klaviaturani olib tashlaydi va
pastdagi reply menyuni qayta yuboradi.

## 6. Tekshirish (smoke testlar)

Tarmoqqa chiqmaydigan, soxta Bot API sessiyasidan foydalanadigan skriptlar:

```powershell
.venv\Scripts\python.exe scripts\_smoke_keyboards.py    # klaviaturalar + i18n kalitlari
.venv\Scripts\python.exe scripts\_smoke_services.py     # servis qatlami + baza
.venv\Scripts\python.exe scripts\_smoke_middlewares.py  # middleware zanjiri
.venv\Scripts\python.exe scripts\_smoke_handlers.py     # /start oqimi + barcha bo'limlar + main.run() (offline)
```

`_smoke_handlers.py` router'lar tartibini, har bir menyu tugmasini (katalog,
aksiya, savat, buyurtmalar, profil, yordam, boshqaruv), inline «🏠 Asosiy
menyu» tugmasini va `main.run()` ni ham tekshiradi.

Har birining oxirida umumiy natija (`OK`/`FAIL` yoki `muvaffaqiyatli`) chiqadi;
`FAIL` bo'lmasa - hammasi joyida.

## 7. Demo (soxta) katalog ma'lumotlari

Katalog bo'sh bo'lsa ekranlarni sinab ko'rish qiyin. `scripts/seed_demo.py` shu
ish uchun: `.env` dagi bazaga 5 kategoriya va 15 demo mahsulot qo'shadi (4 tasi
aksiyada, 3 tasi kam qoldiqda - barcha bo'limlar ko'rinadigan bo'ladi).

```powershell
.venv\Scripts\python.exe scripts\seed_demo.py             # demo ma'lumot qo'shadi
.venv\Scripts\python.exe scripts\seed_demo.py --preview   # qo'shib, ekranlarni terminalda ko'rsatadi
.venv\Scripts\python.exe scripts\seed_demo.py --preview --raw
.venv\Scripts\python.exe scripts\seed_demo.py --reset     # faqat DEMO-* yozuvlarni o'chiradi
```

- skript idempotent: qayta ishga tushirilsa mavjud yozuvlar yangilanadi;
- `--preview` tarmoqqa chiqmaydi - bot nima yuborishini ketma-ket (kategoriyalar,
  mahsulot kartochkasi, savat, buyurtma qadami) chop etadi;
- demo mahsulot artikuli `DEMO-` bilan boshlanadi, shuning uchun `--reset`
  haqiqiy katalogga tegmaydi;
- `--preview` namunaviy mijoz (`telegram_id=777000111`) yaratadi va oxirida
  savatini bo'shatadi; `--reset` uni ham o'chiradi.

## 8. Loyiha tuzilishi

```
main.py                  # entrypoint: Dispatcher, middleware/router ulash, polling
bot/
  config.py              # .env -> Settings (pydantic-settings)
  database/              # engine, modellar, repository'lar, enums
  services/              # savdo logikasi (catalog, cart, checkout, orders, ...)
  middlewares/           # Throttling -> DbSession -> I18n -> BotContext
  keyboards/             # reply va inline klaviaturalar (+ callback_data fabrikalari)
  locales/               # uz/ru tarjimalar (translate)
  utils/                 # rendering, text (escape), validators, money
  handlers/              # router'lar: start, catalog, cart, checkout, orders,
                         # profile, support, admin, fallback (+ states.py)
scripts/                 # smoke testlar + demo ma'lumot (seed_demo.py)
data/                    # SQLite bazasi (dev)
```

Yangi bo'lim qo'shish tartibi:

1. `bot/handlers/<bolim>.py` ichida `def build_router() -> Router` yozing;
2. `bot/handlers/__init__.py` dagi `ROUTER_BUILDERS` ro'yxatiga fabrikani
   `build_fallback_router` dan **oldin** qo'shing;
3. kerak bo'lsa `bot/handlers/states.py` ga FSM holatlarini qo'shing.

## 9. Ma'lumotlar bazasi

- Dev: SQLite (`data/` papkasida). Jadvallar ishga tushganda avtomatik
  yaratiladi (`init_models`, `create_all`).
- Production: PostgreSQL (`postgresql+asyncpg://...`). Migratsiyalar uchun
  keyinchalik Alembic qo'shiladi.
- Bazani noldan boshlash: `data/` ichidagi `.db` faylni o'chirib, botni qayta
  ishga tushiring.
