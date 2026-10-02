"""Vaqtinchalik smoke-test: klaviaturalar qatlami (TZ 4.4).

Ishlatilishi:  python scripts/_smoke_keyboards.py

Test tarmoqqa ham, bazaga ham bog'lanmaydi: modellar xotirada yaratiladi,
matnlar esa haqiqiy i18n fayllaridan olinadi.
"""

from __future__ import annotations

import asyncio
import re
import sys
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

try:  # Windows konsolida emoji chiqarish uchun
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

from aiogram.types import Chat, Message, User as TelegramUser

from bot.database.enums import (
    DeliveryType,
    OrderStatus,
    PaymentMethod,
    SupportStatus,
    Unit,
)
from bot.database.models import (
    Address,
    CartItem,
    Category,
    Order,
    Product,
    SupportRequest,
)
from bot.keyboards import (
    STATUS_COLUMNS,
    AdminCB,
    CartCB,
    CatalogCB,
    CheckoutCB,
    LangCB,
    MenuCB,
    OrderCB,
    ProductCB,
    ProfileCB,
    SupportCB,
    addresses_inline,
    button_texts,
    cancel_keyboard,
    cart_inline,
    categories_inline,
    checkout_address_inline,
    checkout_comment_inline,
    checkout_confirm_inline,
    checkout_delivery_inline,
    checkout_payment_inline,
    checkout_time_inline,
    empty_cart_inline,
    language_inline,
    location_request,
    main_menu,
    main_only,
    order_cancel_confirm_inline,
    order_detail_inline,
    orders_inline,
    phone_request,
    product_inline,
    products_inline,
    profile_inline,
    profile_language_inline,
    quantity_inline,
    reply_button_filter,
    skip_or_cancel,
    staff_cancel_inline,
    staff_menu_inline,
    staff_order_inline,
    staff_orders_inline,
    staff_status_inline,
    staff_support_inline,
    staff_text_inline,
    support_inline,
)
from bot.locales import TRANSLATIONS, available_languages, is_known_key, translator
from bot.services.cart import CartLine, CartSummary
from bot.services.catalog import CategoryCard
from bot.services.presenters import status_label
from bot.utils.pagination import paginate

KEYBOARDS_DIR = Path("bot/keyboards")
MAX_CALLBACK_BYTES = 64

FAILURES: list[str] = []
T = {code: translator(code) for code in available_languages()}


def check(label: str, condition: bool, extra: object = "") -> None:
    print(f"[{'OK  ' if condition else 'FAIL'}] {label} {extra}")
    if not condition:
        FAILURES.append(label)


# ------------------------- Model konstruktorlari -----------------------
def make_product(
    pid: int = 1,
    *,
    name_uz: str = "Guruch Lazer",
    name_ru: str = "Рис Лазер",
    price: str = "25000",
    discount: str | None = None,
    unit: Unit = Unit.KG,
    stock: str = "10",
    min_stock: str = "2",
    box_size: int = 1,
    is_active: bool = True,
    is_promo: bool = False,
) -> Product:
    return Product(
        id=pid,
        category_id=1,
        sku=f"SKU-{pid:04d}",
        barcode=f"478000000{pid:04d}",
        name_uz=name_uz,
        name_ru=name_ru,
        price=Decimal(price),
        discount_price=Decimal(discount) if discount else None,
        unit=unit,
        box_size=box_size,
        stock=Decimal(stock),
        min_stock=Decimal(min_stock),
        is_active=is_active,
        is_promo=is_promo,
        sort_order=100,
    )


def make_category(
    cid: int = 1, name_uz: str = "Sabzavot", name_ru: str = "Овощи"
) -> Category:
    return Category(
        id=cid,
        name_uz=name_uz,
        name_ru=name_ru,
        emoji="🥬",
        sort_order=cid,
        is_active=True,
    )


def make_order(
    oid: int = 1,
    *,
    number: str = "A-1001",
    status: OrderStatus = OrderStatus.NEW,
    total: str = "125000",
) -> Order:
    return Order(
        id=oid,
        number=number,
        user_id=1,
        status=status,
        delivery_type=DeliveryType.DELIVERY,
        payment_method=PaymentMethod.CASH,
        subtotal=Decimal(total),
        total=Decimal(total),
    )


def make_support(rid: int = 7) -> SupportRequest:
    return SupportRequest(
        id=rid,
        user_id=1,
        message="Buyurtmam qachon yetib keladi?",
        status=SupportStatus.OPEN,
    )


def make_summary(*lines: tuple[Product, str]) -> CartSummary:
    """Savat yakuniy hisob-kitobi (pozitsiyalar: mahsulot, miqdor)."""
    cart_lines = [
        CartLine(
            item=CartItem(
                user_id=1, product_id=product.id, quantity=Decimal(quantity)
            ),
            product=product,
        )
        for product, quantity in lines
    ]
    subtotal = sum((line.total for line in cart_lines), Decimal("0"))
    return CartSummary(
        lines=cart_lines,
        subtotal=subtotal,
        discount=Decimal("0"),
        delivery_fee=Decimal("0"),
        total=subtotal,
    )


# ------------------------- Yordamchilar --------------------------------
def rows(markup) -> list[list]:
    return list(getattr(markup, "inline_keyboard", []) or [])


def flat(markup) -> list:
    return [btn for row in rows(markup) for btn in row]


def texts(markup) -> list[str]:
    return [btn.text for btn in flat(markup)]


def unpacks(markup, cls) -> tuple[list, list[str]]:
    """`cls` prefiksiga mos tugmalarni ochib beradi: (obyektlar, xatolar).

    Boshqa turdagi callback data ga ega tugmalar e'tiborsiz qoldiriladi.
    """
    parsed: list = []
    errors: list[str] = []
    prefix = f"{cls.__prefix__}:"
    for btn in flat(markup):
        data = btn.callback_data
        if data is None:
            errors.append(f"callback_data yo'q: {btn.text}")
            continue
        if len(data.encode()) > MAX_CALLBACK_BYTES:
            errors.append(f"juda uzun ({len(data.encode())}): {data}")
        if not data.startswith(prefix):
            continue
        try:
            parsed.append(cls.unpack(data))
        except Exception as exc:  # noqa: BLE001 - test natijasida ko'rsatiladi
            errors.append(f"{btn.text}: {exc!r}")
    return parsed, errors


def message_with(text: str) -> Message:
    """Filtrni sinash uchun oddiy xabar."""
    return Message(
        message_id=1,
        date=datetime.now(tz=timezone.utc),
        chat=Chat(id=1, type="private"),
        from_user=TelegramUser(id=1, is_bot=False, first_name="Test"),
        text=text,
    )


def check_locale_keys() -> None:
    """Klaviaturalarda ishlatilgan i18n kalitlar mavjudligini tekshiradi."""
    pattern = re.compile(r"""t\(\s*["']([a-z0-9_]+)["']""")
    used: set[str] = set()
    for path in sorted(KEYBOARDS_DIR.glob("*.py")):
        used.update(pattern.findall(path.read_text(encoding="utf-8")))
    missing = sorted(key for key in used if not is_known_key(key))
    check(f"i18n: klaviaturalarda {len(used)} ta kalit ishlatilgan", len(used) >= 40, len(used))
    check("i18n: barcha kalitlar uz/ru da mavjud", not missing, missing)

    # Placeholder'li kalitlar hamma til uchun to'ldirilishi shart.
    placeholders = {"count": 1, "id": 7, "name": "Test", "number": "A-1001", "quantity": "1 kg"}
    for code, t in T.items():
        unfilled = [key for key in sorted(used) if "{" in t(key, **placeholders)]
        check(f"i18n: '{code}' tilida tugma matnlari to'ldirilgan", not unfilled, unfilled)


def check_button_texts_are_filled() -> None:
    """Klaviaturlar matnida to'ldirilmagan `{...}` qolmaganini tekshiradi."""
    markups = [
        main_menu(T["uz"]),
        cancel_keyboard(T["ru"]),
        language_inline(T["uz"]),
        categories_inline(T["uz"], [CategoryCard(category=make_category(), products=2)], lang="uz"),
        staff_menu_inline(T["uz"], new_orders=0, open_requests=0),
        staff_menu_inline(T["ru"], new_orders=3, open_requests=12),
        orders_inline(T["uz"], [make_order()], paginate(1, 1, 5)),
        cart_inline(T["uz"], make_summary((make_product(), "2")), lang="uz"),
    ]
    empty = [f"{markup.__class__.__name__}: {text}" for markup in markups for text in texts(markup) if "{" in text]
    check("i18n: klaviatura matnlarida to'ldirilmagan placeholder yo'q", not empty, empty)


async def check_reply_keyboards() -> None:
    """Reply klaviaturalar: tuzilishi, tarjimasi va filtri."""
    uz, ru = T["uz"], T["ru"]
    menu = main_menu(uz)
    check("reply: asosiy menyu 3 qator", len(menu.keyboard) == 3, len(menu.keyboard))
    check("reply: resize_keyboard yoqilgan", menu.resize_keyboard is True)
    check(
        "reply: placeholder tarjima qilingan",
        menu.input_field_placeholder == uz("start_menu_hint"),
        menu.input_field_placeholder,
    )
    staff_menu = main_menu(uz, is_staff=True)
    check("reply: xodim menyusi 4 qator", len(staff_menu.keyboard) == 4)
    check("reply: xodim tugmasi qo'shiladi", staff_menu.keyboard[-1][0].text == uz("btn_admin"))

    keys = ("btn_catalog", "btn_cart", "btn_orders", "btn_profile", "btn_promo", "btn_support", "btn_admin")
    for key in keys:
        variants = button_texts(key)
        check(
            f"reply: '{key}' barcha tillarda mavjud",
            len(variants) == len(TRANSLATIONS),
            variants,
        )
    check(
        "reply: uz/ru matnlari farq qiladi",
        button_texts("btn_catalog")[0] != button_texts("btn_catalog")[1],
        button_texts("btn_catalog"),
    )

    phone = phone_request(uz, with_cancel=True)
    check("reply: telefon tugmasi kontakt so'raydi", phone.keyboard[0][0].request_contact is True)
    check("reply: telefon so'rovida bekor qilish", phone.keyboard[-1][0].text == uz("btn_cancel"))
    check("reply: lokatsiya tugmasi lokatsiya so'raydi", location_request(uz).keyboard[0][0].request_location is True)
    check("reply: bekor qilish klaviaturasi 1 qator", len(cancel_keyboard(uz).keyboard) == 1)
    check("reply: o'tkazib yuborish + bekor qilish", len(skip_or_cancel(ru).keyboard) == 2)
    check("reply: faqat asosiy menyu", len(main_only(ru).keyboard) == 1)

    catalog_filter = reply_button_filter("btn_catalog")
    for index, lang in enumerate(available_languages()):
        matched = await catalog_filter(message_with(button_texts("btn_catalog")[index]))
        check(f"filter: '{lang}' tilidagi tugma matni tanildi", bool(matched))
    check("filter: begona matn rad etiladi", not await catalog_filter(message_with("/start")))
    upper = button_texts("btn_catalog")[0].upper()
    check(
        "filter: ignore_case bilan ishlaydi",
        bool(await reply_button_filter("btn_catalog", ignore_case=True)(message_with(upper))),
    )
    check(
        "filter: ignore_case siz katta harfni tanimaydi",
        not await catalog_filter(message_with(upper)),
    )
    all_keys = ("btn_cart", "btn_orders", "btn_profile", "btn_promo", "btn_support", "btn_admin", "btn_main_menu")
    for key in all_keys:
        check(f"filter: '{key}' filtri tayyor", reply_button_filter(key) is not None)


def check_catalog_keyboards() -> None:
    """Katalog, mahsulot va miqdor klaviaturalari."""
    uz, ru = T["uz"], T["ru"]
    check("cat: til tanlash 1 qator, 2 tugma", len(rows(language_inline(uz))) == 1)
    check("cat: til tanlashda bekor qilish", len(rows(language_inline(uz, with_cancel=True))) == 2)
    parsed, errors = unpacks(language_inline(uz), LangCB)
    check("cat: LangCB xatosiz", not errors, errors)
    check("cat: tillar callback da", [item.code for item in parsed] == list(available_languages()))

    cards = [CategoryCard(category=make_category(cid), products=cid) for cid in (1, 2, 3)]
    markup = categories_inline(uz, cards)
    parsed, errors = unpacks(markup, CatalogCB)
    check("cat: CatalogCB xatosiz", not errors, errors)
    check("cat: 3 kategoriya + aksiya/qidiruv + menyu", len(rows(markup)) == 4, len(rows(markup)))
    check("cat: 2 ustunli joylashuv", len(rows(markup)[0]) == 2 and len(rows(markup)[1]) == 1)
    ids = [item.category_id for item in parsed if item.action == "category"]
    check("cat: kategoriya id lari to'g'ri", ids == [1, 2, 3], ids)
    check("cat: mahsulot soni tugmada", "(2)" in texts(markup)[1], texts(markup)[1])
    check("cat: aksiya va qidiruv tugmalari", {"promo", "search"} <= {item.action for item in parsed})
    check("cat: ru tilida nom tarjima qilinadi", "Овощи" in texts(categories_inline(ru, cards, lang="ru"))[0])
    check("cat: kategoriyasiz ham ishlaydi", len(rows(categories_inline(uz, []))) == 2)
    check("cat: asosiy menyu tugmasi", [item.action for item in unpacks(markup, MenuCB)[0]] == ["main"])

    products = [make_product(pid) for pid in range(1, 6)]
    back_cb = CatalogCB(action="categories")
    page = products_inline(uz, products, paginate(12, 1, 5), back_cb=back_cb)
    parsed, errors = unpacks(page, ProductCB)
    check("list: ProductCB xatosiz", not errors, errors)
    check("list: 5 mahsulot + sahifalash + orqaga", len(rows(page)) == 7, len(rows(page)))
    check("list: 1-sahifada faqat 'keyingi'", texts(page)[5] == uz("btn_next"), texts(page)[5])
    check("list: mahsulot id lari tartibda", [item.product_id for item in parsed] == [1, 2, 3, 4, 5])
    check("list: narx tugmada ko'rinadi", "25 000" in texts(page)[0], texts(page)[0])
    check("list: orqaga tugmasi kategoriyalarga", uz("btn_back") in texts(page))

    middle = products_inline(uz, products, paginate(12, 2, 5), back_cb=back_cb)
    check(
        "list: o'rta sahifada ikkala yo'nalish",
        texts(middle)[5] == uz("btn_prev") and texts(middle)[6] == uz("btn_next"),
        texts(middle)[5:7],
    )
    last = products_inline(uz, products[:2], paginate(12, 3, 5), back_cb=back_cb)
    check("list: oxirgi sahifada faqat 'oldingi'", texts(last)[2] == uz("btn_prev"), texts(last)[2])
    cat_back = CatalogCB(action="category", category_id=4, page=3)
    last_cat = products_inline(uz, products[:2], paginate(12, 3, 5), back_cb=cat_back)
    prev = CatalogCB.unpack(flat(last_cat)[2].callback_data)
    check(
        "list: sahifalash tugmasi page va kategoriyani saqlaydi",
        prev.action == "category" and prev.page == 2 and prev.category_id == 4,
        prev,
    )

    card = product_inline(uz, make_product(10), back_cb=CatalogCB(action="category", category_id=1, page=2))
    check("card: savatga qo'shish tugmasi bor", uz("btn_add_to_cart") in texts(card))
    parsed = unpacks(card, ProductCB)[0]
    check("card: qo'shish tugmasi", parsed[0].action == "add" and parsed[0].product_id == 10)
    back = unpacks(card, CatalogCB)[0]
    check("card: orqaga havolasi kategoriya+sahifa", back[0].category_id == 1 and back[0].page == 2)
    check("card: qoldiq yo'q -> tugma yo'q", uz("btn_add_to_cart") not in texts(product_inline(uz, make_product(11, stock="0"), back_cb=back_cb)))

    qty = quantity_inline(ru, make_product(12, unit=Unit.KG))
    parsed, errors = unpacks(qty, ProductCB)
    check("qty: ProductCB xatosiz", not errors, errors)
    check("qty: 5 variant + boshqa miqdor + bekor", len(flat(qty)) == 7, len(flat(qty)))
    check("qty: kg uchun qadam 0,5", texts(qty)[0].startswith("0,5") and texts(qty)[2].startswith("1,5"), texts(qty)[:3])
    steps = [item.value for item in parsed if item.action == "qty"]
    check("qty: variantlar 1..10", steps == [1, 2, 3, 5, 10], steps)
    check("qty: o'lchov birligi ko'rsatilgan", texts(qty)[0].endswith("кг"), texts(qty)[0])
    check("qty: 'boshqa miqdor' input action", [item.action for item in parsed if item.action == "input"] == ["input"])
    check("qty: bekor qilish mahsulotga qaytaradi", parsed[-1].action == "open" and parsed[-1].product_id == 12)
    box_qty = quantity_inline(uz, make_product(13, unit=Unit.BOX, box_size=12))
    check("qty: quti uchun qadam box_size", texts(box_qty)[0].startswith("12"), texts(box_qty)[0])
    custom = quantity_inline(uz, make_product(14), back_cb=CatalogCB(action="category", category_id=3))
    check("qty: back_cb bekor qilishga o'tadi", CatalogCB.unpack(flat(custom)[-1].callback_data).category_id == 3)


def check_cart_keyboards() -> None:
    """Savat klaviaturasi."""
    t = T["uz"]
    summary = make_summary((make_product(1, unit=Unit.KG), "2"), (make_product(2, unit=Unit.PCS), "1"))
    markup = cart_inline(t, summary)
    parsed, errors = unpacks(markup, CartCB)
    check("cart: CartCB xatosiz", not errors, errors)
    check("cart: 2 pozitsiya + 3 harakat qatori", len(rows(markup)) == 5, len(rows(markup)))
    check("cart: har pozitsiyada 3 tugma", all(len(row) == 3 for row in rows(markup)[:2]))
    actions = [item.action for item in parsed]
    check("cart: kg pozitsiyada ➖ (dec)", actions[0] == "dec" and parsed[0].product_id == 1, actions)
    check("cart: ➕ (inc) tugmasi", actions[1] == "inc" and parsed[1].product_id == 1, actions)
    check("cart: bitta qadamli pozitsiyada 🗑 (remove)", actions[2] == "remove" and parsed[2].product_id == 2, actions)
    check("cart: ➖ o'rniga 🗑 belgisi", texts(markup)[0] == "➖" and texts(markup)[3] == "🗑", texts(markup)[:4])
    check("cart: miqdor tugmada ko'rinadi", "2 kg" in texts(markup)[1], texts(markup)[1])
    check("cart: pozitsiya tugmasi mahsulotni ochadi", [item.action for item in unpacks(markup, ProductCB)[0]] == ["open", "open"])
    check("cart: buyurtma va tozalash", {"checkout", "clear"} <= set(actions), actions)
    check("cart: asosiy menyu tugmasi", [item.action for item in unpacks(markup, MenuCB)[0]] == ["main"])
    check("cart: rus tilida kilogramm nomi", "кг" in texts(cart_inline(T["ru"], summary))[1])

    empty = empty_cart_inline(t)
    check("cart: bo'sh savatda katalog va menyu", len(rows(empty)) == 2 and t("btn_catalog") in texts(empty))
    check("cart: bo'sh savatdagi havola kategoriyalarga", [item.action for item in unpacks(empty, CatalogCB)[0]] == ["categories"])


def check_checkout_keyboards() -> None:
    """Buyurtma berish (checkout) FSM klaviaturalari."""
    t = T["uz"]
    delivery = checkout_delivery_inline(t)
    parsed, errors = unpacks(delivery, CheckoutCB)
    check("co: CheckoutCB xatosiz", not errors, errors)
    check("co: yetkazish/pickup/bekor", {item.action for item in parsed} == {"delivery", "pickup", "cancel"}, [i.action for i in parsed])
    check("co: yetkazish klaviaturasi 2 qator", len(rows(delivery)) == 2)

    check("co: manzilsiz -> faqat yangi manzil", len(rows(checkout_address_inline(t))) == 2)
    addresses = [
        Address(
            id=index,
            customer_id=1,
            label=f"Manzil {index}",
            address="Toshkent sh., Chilonzor tumani, 5-uy",
            is_default=index == 1,
        )
        for index in range(1, 8)
    ]
    address_markup = checkout_address_inline(t, addresses)
    parsed, errors = unpacks(address_markup, CheckoutCB)
    check("co: CheckoutCB manzillarda xatosiz", not errors, errors)
    check("co: manzillar 5 taga cheklangan", len(parsed) == 7, [i.action for i in parsed])
    check("co: manzil id si callback da", [item.value for item in parsed if item.action == "addr"] == ["1", "2", "3", "4", "5"])
    check("co: yangi manzil + bekor", len(rows(address_markup)) == 7, len(rows(address_markup)))
    check("co: manzil yorlig'i kesiladi", all(len(text) <= 54 for text in texts(address_markup)))
    check("co: yorliqsiz manzil matni", "5-uy" in texts(checkout_address_inline(t, [Address(id=1, customer_id=1, label=None, address="Chilonzor 5-uy")]))[0])

    time_markup = checkout_time_inline(t)
    parsed, errors = unpacks(time_markup, CheckoutCB)
    check("co: CheckoutCB vaqtda xatosiz", not errors, errors)
    check("co: vaqt variantlari", [item.value for item in parsed if item.action == "time"] == ["asap", "today_am", "today_pm", "tomorrow"])
    check("co: vaqt tugmalari 2 tadan joylashadi", len(rows(time_markup)) == 3)

    comment = checkout_comment_inline(t)
    check("co: izohni o'tkazib yuborish + bekor", [item.action for item in unpacks(comment, CheckoutCB)[0]] == ["skip", "cancel"])

    offline = checkout_payment_inline(t)
    methods = [item.value for item in unpacks(offline, CheckoutCB)[0] if item.action == "payment"]
    check("co: to'lov usullari", methods == ["cash", "card", "transfer"], methods)
    check("co: onlayn tugmasi yashirilgan", t("btn_pay_online") not in texts(offline))
    online_methods = [
        item.value for item in unpacks(checkout_payment_inline(t, online=True), CheckoutCB)[0] if item.action == "payment"
    ]
    check("co: onlayn to'lov qo'shiladi", online_methods == ["cash", "card", "transfer", "payme"], online_methods)

    confirm = checkout_confirm_inline(t)
    confirm_parsed = unpacks(confirm, CheckoutCB)[0]
    check("co: tasdiqlash va bekor qilish", [item.action for item in confirm_parsed] == ["confirm", "cancel", "back"], [i.action for i in confirm_parsed])
    check("co: orqaga to'lov qadamiga qaytaradi", confirm_parsed[-1].action == "back")


def check_orders_keyboards() -> None:
    """Mijoz buyurtmalari klaviaturalari."""
    t = T["uz"]
    orders = [
        make_order(1, number="A-1001"),
        make_order(2, number="A-1002", status=OrderStatus.DELIVERED, total="99000"),
    ]
    markup = orders_inline(t, orders, paginate(12, 1, 5))
    parsed, errors = unpacks(markup, OrderCB)
    check("orders: OrderCB xatosiz", not errors, errors)
    check("orders: 2 buyurtma + sahifalash + menyu", len(rows(markup)) == 4, len(rows(markup)))
    check("orders: detail action, id bilan", [item.action for item in parsed] == ["detail", "detail", "list"], [i.action for i in parsed])
    check("orders: «Orqaga» yo'q (bo'lim ildizi)", t("btn_back") not in texts(markup))
    check("orders: birinchi buyurtma id si", parsed[0].order_id == 1)
    check("orders: raqam va summa tugmada", "A-1001" in texts(markup)[0] and "125 000" in texts(markup)[0], texts(markup)[0])
    check("orders: holat yorlig'i tugmada", status_label(T["ru"], OrderStatus.DELIVERED) in texts(orders_inline(T["ru"], orders, paginate(12, 1, 5)))[1])
    check("orders: uzun matn kesiladi", all(len(text) <= 60 for text in texts(markup)))
    check("orders: 'keyingi' tugmasi 2-sahifaga", OrderCB.unpack(flat(markup)[2].callback_data).page == 2)
    page2 = orders_inline(t, orders, paginate(12, 2, 5))
    check("orders: 2-sahifada 'oldingi'", texts(page2)[2] == t("btn_prev"), texts(page2)[2])
    check("orders: orqaga ro'yxatga (1-sahifa)", OrderCB.unpack(flat(page2)[2].callback_data).page == 1)

    detail = order_detail_inline(t, make_order(1), back_page=2)
    check("orders: yangi buyurtmada bekor qilish bor", len(rows(detail)) == 3, len(rows(detail)))
    check("orders: kartochka amallari", [item.action for item in unpacks(detail, OrderCB)[0]] == ["cancel", "repeat", "list"])
    check("orders: orqaga sahifani saqlaydi", unpacks(detail, OrderCB)[0][-1].page == 2)
    closed = order_detail_inline(t, make_order(2, status=OrderStatus.DELIVERED))
    check("orders: yetkazilgan buyurtmada bekor qilish yo'q", "cancel" not in [item.action for item in unpacks(closed, OrderCB)[0]])
    check("orders: yetkazilgan kartochkada orqaga + menyu", len(rows(closed)) == 2 and t("btn_main_menu") in texts(closed))

    confirm = order_cancel_confirm_inline(t, make_order(1))
    check("orders: bekor qilishni tasdiqlash", [item.action for item in unpacks(confirm, OrderCB)[0]] == ["confirm_cancel", "detail"])
    check("orders: tasdiqlashda order_id saqlanadi", unpacks(confirm, OrderCB)[0][0].order_id == 1)


def check_profile_support_keyboards() -> None:
    """Profil va qo'llab-quvvatlash klaviaturalari."""
    t = T["uz"]
    profile = profile_inline(t)
    parsed, errors = unpacks(profile, ProfileCB)
    check("prof: ProfileCB xatosiz", not errors, errors)
    check("prof: profil amallari", [item.action for item in parsed] == ["phone", "language", "addresses"], [i.action for i in parsed])
    check("prof: 3 qator tugma", len(rows(profile)) == 3, len(rows(profile)))
    check("prof: asosiy menyu tugmasi", [item.action for item in unpacks(profile, MenuCB)[0]] == ["main"])

    lang_markup = profile_language_inline(t)
    parsed, errors = unpacks(lang_markup, LangCB)
    check("prof: tillar LangCB bilan", [item.code for item in parsed] == list(available_languages()), errors)
    check("prof: tillar alohida qatorda + orqaga", len(rows(lang_markup)) == 3, len(rows(lang_markup)))
    check("prof: orqaga profilga qaytaradi", [item.action for item in unpacks(lang_markup, ProfileCB)[0]] == ["open"])

    addresses = addresses_inline(t)
    check("prof: manzillar ekranida orqaga + menyu", [item.action for item in unpacks(addresses, ProfileCB)[0]] == ["open"])
    check("prof: manzillar ekranida asosiy menyu", t("btn_main_menu") in texts(addresses))

    support = support_inline(t)
    parsed, errors = unpacks(support, SupportCB)
    check("sup: SupportCB xatosiz", not errors, errors)
    check("sup: yozish va qo'ng'iroq", [item.action for item in parsed] == ["write", "call"], [i.action for i in parsed])
    check("sup: asosiy menyu qatori", len(rows(support)) == 2 and t("btn_main_menu") in texts(support))
    no_phone = support_inline(t, phone_available=False)
    check("sup: telefon yo'q -> faqat yozish", [item.action for item in unpacks(no_phone, SupportCB)[0]] == ["write"])


def check_staff_keyboards() -> None:
    """Xodimlar paneli klaviaturalari."""
    t = T["uz"]
    check("staff: holat ustunlari 2 ta", STATUS_COLUMNS == 2)

    menu = staff_menu_inline(t, new_orders=3, open_requests=12)
    parsed, errors = unpacks(menu, AdminCB)
    check("staff: AdminCB xatosiz", not errors, errors)
    check("staff: 4 qator (3 navigatsiya + menyu)", len(rows(menu)) == 4, len(rows(menu)))
    check(
        "staff: menyu amallari",
        [item.action for item in parsed]
        == ["stats", "new_orders", "active_orders", "search", "low_stock", "support"],
        [i.action for i in parsed],
    )
    check("staff: menyu qatorida asosiy menyu", [item.action for item in unpacks(menu, MenuCB)[0]] == ["main"])
    check("staff: yangi buyurtma soni tugmada", "(3)" in texts(menu)[1], texts(menu)[1])
    check("staff: so'rovlar soni tugmada", "(12)" in texts(menu)[5], texts(menu)[5])
    zero = staff_menu_inline(t)
    check(
        "staff: son nol bo'lsa ham to'ldiriladi",
        "(0)" in texts(zero)[1] and all("{count}" not in text for text in texts(zero)),
        texts(zero)[1],
    )

    orders = [make_order(1, number="A-1001"), make_order(2, number="A-1002", status=OrderStatus.CONFIRMED)]
    listing = staff_orders_inline(t, orders, paginate(9, 1, 5), list_action="new_orders")
    parsed, errors = unpacks(listing, AdminCB)
    check("staff: ro'yxat AdminCB xatosiz", not errors, errors)
    check("staff: 2 buyurtma + sahifalash + orqaga", len(rows(listing)) == 4, len(rows(listing)))
    check("staff: ro'yxat tugmalari buyurtmani ochadi", [item.order_id for item in parsed if item.action == "order"] == [1, 2])
    check("staff: ro'yxat amali saqlanadi", {item.value for item in parsed if item.action == "order"} == {"new_orders"})
    check("staff: raqam/summa/holat tugmada", "A-1001" in texts(listing)[0] and "125 000" in texts(listing)[0] and status_label(t, OrderStatus.NEW) in texts(listing)[0], texts(listing)[0])
    check("staff: ro'yxatda sahifalash amali", [item.action for item in parsed if item.action == "new_orders"] == ["new_orders"])
    check("staff: ro'yxatda orqaga panelga", unpacks(listing, AdminCB)[0][-1].action == "menu")

    order_card = staff_order_inline(t, orders[0], list_action="active_orders")
    parsed = unpacks(order_card, AdminCB)[0]
    check("staff: kartochka amallari", [item.action for item in parsed] == ["status", "reply", "menu"], [i.action for i in parsed])
    check("staff: kartochkada order_id va qaytish amali", parsed[0].order_id == 1 and parsed[0].value == "active_orders")

    transitions = (OrderStatus.CONFIRMED, OrderStatus.DELIVERED, OrderStatus.CANCELLED)
    statuses = staff_status_inline(t, orders[0], transitions, list_action="active_orders")
    parsed, errors = unpacks(statuses, AdminCB)
    check("staff: holat tugmalari AdminCB xatosiz", not errors, errors)
    check("staff: holat o'tishlari", [item.value for item in parsed if item.action == "status_set"] == ["confirmed", "delivered", "cancelled"])
    check("staff: holat tugmalari tarjima qilingan", all(label in texts(statuses) for label in (status_label(t, s) for s in transitions)))
    check("staff: holat tugmalari 2 ustunda", len(rows(statuses)) == 4, len(rows(statuses)))
    check("staff: holatdan orqaga buyurtmaga", [item.action for item in parsed][-2] == "order")
    check("staff: holatsiz o'tish ham ishlaydi", len(rows(staff_status_inline(t, orders[0], ()))) == 2)

    requests = [make_support(7), make_support(8)]
    support = staff_support_inline(t, requests, paginate(12, 1, 5), list_action="support")
    parsed, errors = unpacks(support, AdminCB)
    check("staff: so'rovlar AdminCB xatosiz", not errors, errors)
    check("staff: so'rovlar ro'yxati", [item.request_id for item in parsed if item.action == "reply"] == [7, 8])
    check("staff: so'rov raqami tugmada", f"#{requests[0].id}" in texts(support)[0], texts(support)[0])
    check("staff: so'rovlar sahifalash + orqaga", len(rows(support)) == 4, len(rows(support)))

    text_screen = staff_text_inline(t)
    check("staff: matnli ekranda orqaga + menyu", [item.action for item in unpacks(text_screen, AdminCB)[0]] == ["menu"])
    check("staff: matnli ekranda asosiy menyu", t("btn_main_menu") in texts(text_screen))
    cancel = staff_cancel_inline(t)
    check("staff: bekor qilish panelga qaytaradi", [item.action for item in unpacks(cancel, AdminCB)[0]] == ["menu"])


async def main() -> int:
    checks = (
        ("i18n kalitlari", check_locale_keys),
        ("i18n to'ldirilgan matnlar", check_button_texts_are_filled),
        ("reply klaviaturalar", check_reply_keyboards),
        ("katalog", check_catalog_keyboards),
        ("savat", check_cart_keyboards),
        ("buyurtma berish", check_checkout_keyboards),
        ("buyurtmalar", check_orders_keyboards),
        ("profil/support", check_profile_support_keyboards),
        ("xodim paneli", check_staff_keyboards),
    )
    for title, func in checks:
        print(f"\n=== {title} ===")
        try:
            result = func()
            if result is not None:
                await result
        except Exception:  # noqa: BLE001 - test natijasida ko'rsatiladi
            FAILURES.append(f"{title}: kutilmagan xato")
            traceback.print_exc()

    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} ta tekshiruv muvaffaqiyatsiz:")
        for label in FAILURES:
            print(f"   - {label}")
        return 1
    print("✅ Klaviaturalar qatlami barcha tekshiruvlardan o'tdi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
