"""O'zbek tilidagi matnlar (lotin yozuvi)."""

from __future__ import annotations

MESSAGES: dict[str, str] = {
    # ================= UMUMIY =================
    "lang_name": "O'zbekcha 🇺🇿",
    "btn_back": "⬅️ Orqaga",
    "btn_main_menu": "🏠 Asosiy menyu",
    "btn_cancel": "❌ Bekor qilish",
    "btn_skip": "⏭ O'tkazib yuborish",
    "btn_yes": "✅ Ha",
    "btn_no": "❌ Yo'q",
    "btn_confirm": "✅ Tasdiqlash",
    "btn_prev": "⬅️ Oldingi",
    "btn_next": "Keyingi ➡️",
    "btn_search": "🔍 Qidiruv",
    "btn_promo": "🔥 Aksiyalar",
    "btn_catalog": "🛍 Katalog",
    "btn_cart": "🛒 Savat",
    "btn_orders": "📦 Buyurtmalarim",
    "btn_profile": "👤 Profil",
    "btn_support": "☎️ Yordam",
    "btn_admin": "🛠 Boshqaruv",
    "error_generic": "⚠️ Xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.",
    "error_denied": "⛔️ Bu amal uchun ruxsatingiz yo'q.",
    "error_not_found": "❌ Ma'lumot topilmadi.",
    "error_stale": "⌛️ Bu tugma eskirgan. Iltimos, menyudan qaytadan tanlang.",
    "unknown_message": "🤔 Tushunmadim. Iltimos, menyudagi tugmalardan foydalaning.",
    "my_id": "🆔 Sizning Telegram ID: <code>{id}</code>",
    "help_text": (
        "ℹ️ <b>Yordam</b>\n\n"
        "Botdan foydalanish uchun quyidagi buyruqlar mavjud:\n"
        "/start — bosh menyu\n"
        "/catalog — katalog\n"
        "/cart — savat\n"
        "/orders — buyurtmalarim\n"
        "/language — tilni o'zgartirish\n"
        "/help — yordam\n\n"
        "Savollar bo'lsa «☎️ Yordam» bo'limidan operatorga yozing."
    ),
    # ================= START / RO'YXATDAN O'TISH =================
    "start_language_title": "🌐 <b>Tilni tanlang</b>\n\nTilni tanlang / Выберите язык",
    "lang_changed": "✅ Til o'zgartirildi: <b>{language}</b>",
    "start_welcome": (
        "👋 <b>{brand}</b> botiga xush kelibsiz!\n\n"
        "Bu yerda siz:\n"
        "• 🛍 katalogni ko'rib chiqasiz;\n"
        "• 🛒 mahsulotni savatga qo'shib buyurtma berasiz;\n"
        "• 📦 buyurtma holatini kuzatasiz;\n"
        "• ☎️ operator bilan bog'lanasiz."
    ),
    "start_ask_phone": (
        "📱 Buyurtma berish uchun telefon raqamingizni yuboring.\n\n"
        "«📱 Raqamni ulashish» tugmasini bosing yoki raqamni qo'lda yozing "
        "(masalan: +998901234567)."
    ),
    "btn_share_phone": "📱 Raqamni ulashish",
    "phone_received": "✅ Raqamingiz qabul qilindi: <b>{phone}</b>",
    "phone_invalid": "❌ Telefon raqam noto'g'ri. Qaytadan yuboring (masalan: +998901234567).",
    "phone_wrong_owner": "❌ Faqat o'zingizning raqamingizni ulashingiz mumkin.",
    "welcome_back": "👋 Xush kelibsiz, <b>{name}</b>!\n\nKerakli bo'limni tanlang:",
    "start_menu_hint": "Kerakli bo'limni pastdagi menyudan tanlang 👇",
    # ================= KATALOG =================
    "catalog_title": "🛍 <b>Katalog</b>\n\nKategoriyani tanlang:",
    "catalog_empty": "🛍 Katalog hozircha bo'sh. Keyinroq urinib ko'ring.",
    "catalog_products_title": "{emoji} <b>{category}</b>\n\nSahifa: {page}/{pages}",
    "catalog_products_empty": "Bu kategoriyada mahsulot yo'q.",
    "catalog_search_prompt": "🔍 Qidiruv: mahsulot nomi, artikuli (SKU) yoki shtrix-kodini yuboring.",
    "catalog_search_results": "🔍 «{query}» bo'yicha topildi: <b>{count}</b> ta",
    "catalog_search_empty": "🔍 «{query}» bo'yicha hech narsa topilmadi.",
    "catalog_promo_title": "🔥 <b>Chegirmadagi mahsulotlar</b>",
    "catalog_promo_empty": "🔥 Hozircha aksiya yo'q.",
    "product_sku": "🔖 Artikul: <code>{sku}</code>",
    "product_price": "💵 Narx: <b>{price}</b>",
    "product_old_price": "❌ Eski narx: <s>{price}</s>",
    "product_discount": "🔥 Chegirma: <b>-{percent}%</b>",
    "product_box": "📦 1 quti = {count} {unit} — {price}",
    "product_stock": "📊 Omborda: <b>{quantity}</b>",
    "product_out_of_stock": "🚫 Omborda tugagan",
    "product_low_stock": "⚠️ Omborda kam qoldi",
    "btn_add_to_cart": "➕ Savatga qo'shish",
    "add_qty_prompt": "Miqdorni tanlang yoki qo'lda kiriting:",
    "btn_other_qty": "✏️ Boshqa miqdor",
    "add_qty_input_prompt": "✏️ Miqdorni raqam bilan kiriting (masalan: 3 yoki 2,5):",
    "qty_added": "✅ Savatga qo'shildi: <b>{quantity}</b>",
    "qty_invalid": "❌ Miqdor noto'g'ri. Noldan katta raqam kiriting.",
    "qty_stock_limit": "⚠️ Omborda faqat {quantity} mavjud.",
    # ================= SAVAT =================
    "cart_title": "🛒 <b>Savat</b> — {count} pozitsiya",
    "cart_empty": "🛒 Savatingiz bo'sh.\n\nKatalogdan mahsulot tanlang.",
    "cart_item": "{index}. <b>{name}</b>\n     {quantity} × {price} = <b>{total}</b>",
    "cart_summary": (
        "➖➖➖➖➖➖➖➖\n"
        "Mahsulotlar: <b>{subtotal}</b>\n"
        "{discount}🚚 Yetkazish: <b>{delivery}</b>\n"
        "💰 <b>Jami: {total}</b>"
    ),
    "cart_discount_line": "🎁 Chegirma: <b>-{discount}</b>\n",
    "cart_min_amount": (
        "⚠️ Minimal buyurtma summasi yetarli emas.\n"
        "Savatga yana <b>{amount}</b> qiymatida mahsulot qo'shing."
    ),
    "cart_removed": "🗑 «{name}» savatdan olib tashlandi.",
    "cart_cleared": "🗑 Savat tozalandi.",
    "cart_updated": "✅ Miqdor yangilandi: <b>{quantity}</b>",
    "btn_checkout": "🚚 Buyurtma berish",
    "btn_clear_cart": "🗑 Savatni tozalash",
    # ================= BUYURTMA BERISH =================
    "co_delivery_title": "🚚 <b>Yetkazish turi</b>\n\nBuyurtmani qanday qabul qilmoqchisiz?",
    "btn_co_delivery": "🚚 Yetkazib berish",
    "btn_co_pickup": "🏬 O'zi olib ketish",
    "co_pickup_address": (
        "🏬 <b>Olib ketish manzili:</b>\n{address}\n\n🕘 Ish vaqti: {hours}"
    ),
    "co_pickup_missing": "🏬 Manzil haqida ma'lumot yo'q. Operator bilan bog'laning.",
    "co_ask_address": "📍 Yetkazish manzilini yuboring: matn ko'rinishida yoki «📍 Lokatsiya yuborish» orqali.",
    "co_saved_addresses": "📍 Saqlangan manzillarni tanlang yoki yangisini kiriting:",
    "btn_send_location": "📍 Lokatsiya yuborish",
    "btn_new_address": "✍️ Yangi manzil",
    "co_address_saved": "✅ Manzil saqlandi.",
    "co_address_required": "❗️ Iltimos, manzilni matn yoki lokatsiya ko'rinishida yuboring.",
    "co_ask_time": "🕑 Qachon yetkazib berish qulay?",
    "btn_time_asap": "⏰ Imkon qadar tez",
    "btn_time_today_am": "🕘 Bugun 09:00–13:00",
    "btn_time_today_pm": "🕔 Bugun 14:00–18:00",
    "btn_time_tomorrow": "📅 Ertaga",
    "co_ask_comment": (
        "📝 Buyurtmaga izoh yozing (masalan: «2-qavat», «domofon 45»).\n"
        "Kerak bo'lmasa — «⏭ O'tkazib yuborish» tugmasini bosing."
    ),
    "co_choose_payment": "💳 To'lov usulini tanlang:",
    "btn_pay_cash": "💵 Naqd (yetkazishda)",
    "btn_pay_transfer": "🏦 O'tkazma (hisob raqamga)",
    "btn_pay_card": "💳 Plastik karta",
    "btn_pay_online": "🌐 Onlayn to'lov",
    "co_online_pending": (
        "🌐 <b>Onlayn to'lov</b>\n\nBuyurtma: <b>{number}</b>\nSumma: <b>{total}</b>\n\n"
        "To'lov havolasi: {link}\n\n"
        "To'lov tizimdan tasdiqlangach buyurtma holati avtomatik yangilanadi."
    ),
    "co_summary_title": "🧾 <b>Buyurtmani tekshirib ko'ring</b>",
    "co_summary_item": "• {name} — {quantity} × {price} = <b>{total}</b>",
    "co_summary_info": (
        "➖➖➖➖➖➖➖➖\n"
        "🧺 Mahsulotlar: <b>{subtotal}</b>\n"
        "{discount}🚚 Yetkazish: <b>{delivery}</b>\n"
        "💰 <b>Jami: {total}</b>\n\n"
        "🚚 Turi: {delivery_type}\n"
        "📍 Manzil: {address}\n"
        "🕑 Vaqt: {time}\n"
        "💳 To'lov: {payment}"
    ),
    "co_confirm_ask": "Buyurtmani tasdiqlaysizmi?",
    "co_created": (
        "✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        "🧾 Raqam: <b>{number}</b>\n"
        "💰 Summa: <b>{total}</b>\n\n"
        "Operator yaqin orada siz bilan bog'lanadi. Holatni «📦 Buyurtmalarim» "
        "bo'limida kuzatib borishingiz mumkin."
    ),
    "co_cancelled": "❌ Buyurtma berish bekor qilindi. Savat saqlanib qoldi.",
    "co_data_expired": "⌛️ Ma'lumotlar eskirgan. Iltimos, savatdan qaytadan boshlang.",
    # ================= BUYURTMALARIM =================
    "orders_title": "📦 <b>Buyurtmalarim</b>\n\nSahifa: {page}/{pages}",
    "orders_empty": "📦 Sizda hali buyurtma yo'q.\n\nKatalogdan xaridni boshlang!",
    "orders_item": "{index}. <b>{number}</b> — {status}\n     {date} • {total}",
    "btn_order_detail": "🧾 {number}",
    "order_title": "🧾 <b>Buyurtma {number}</b>",
    "order_info": (
        "📅 Sana: {date}\n"
        "📊 Holat: <b>{status}</b>\n"
        "💰 Summa: <b>{total}</b>\n"
        "💳 To'lov: {payment} — {payment_status}"
    ),
    "order_delivery_info": "🚚 {delivery_type}\n📍 {address}\n🕑 {time}",
    "order_items_title": "🧺 <b>Tarkibi:</b>",
    "order_item_line": "• {name} — {quantity} × {price} = {total}",
    "order_comment": "📝 Izoh: {comment}",
    "order_history_title": "🕘 <b>Holatlar tarixi:</b>",
    "order_history_line": "• {date} — {status}",
    "btn_order_cancel": "❌ Buyurtmani bekor qilish",
    "btn_order_repeat": "🔁 Qaytadan buyurtma",
    "order_cancel_prompt": "❌ Bekor qilish sababini yozing:",
    "order_cancelled": "✅ Buyurtma <b>{number}</b> bekor qilindi.",
    "order_cannot_cancel": "⛔️ Bu buyurtmani endi bekor qilib bo'lmaydi. Operator bilan bog'laning.",
    "order_repeat_done": (
        "🔁 <b>{count}</b> pozitsiya savatga qo'shildi.\nSavatga o'tib buyurtmani tasdiqlang."
    ),
    "order_repeat_empty": "⚠️ Bu buyurtmadagi mahsulotlar hozir mavjud emas.",
    # ================= PROFIL =================
    "profile_title": "👤 <b>Profil</b>",
    "profile_name": "👤 Ism: <b>{value}</b>",
    "profile_phone": "📱 Telefon: <b>{value}</b>",
    "profile_language": "🌐 Til: <b>{value}</b>",
    "profile_segment": "⭐️ Toifa: <b>{value}</b>",
    "profile_debt": "💰 Qarzdorlik: <b>{value}</b>",
    "profile_address": "📍 Manzil: <b>{value}</b>",
    "profile_unknown": "—",
    "btn_change_phone": "📱 Telefonni o'zgartirish",
    "btn_change_language": "🌐 Tilni o'zgartirish",
    "profile_phone_prompt": "📱 Yangi telefon raqamni yuboring (tugma orqali yoki matn bilan):",
    "profile_phone_updated": "✅ Telefon raqam yangilandi.",
    "btn_my_addresses": "📍 Manzillarim",
    "profile_addresses_title": "📍 <b>Saqlangan manzillar</b>",
    "profile_addresses_empty": "📍 Saqlangan manzillar yo'q.",
    "profile_address_line": "{index}. {address}",
    # ================= QO'LLAB-QUVVATLASH =================
    "support_title": "☎️ <b>Qo'llab-quvvatlash</b>",
    "support_menu": "☎️ <b>Yordam</b>\n\nNima qilmoqchisiz?",
    "support_ask": "✍️ Savolingizni yozing — operator javob beradi.",
    "btn_support_write": "✍️ Operatorga yozish",
    "btn_support_call": "📞 Telefon orqali",
    "support_call_info": "📞 Qo'llab-quvvatlash raqami: <b>{phone}</b>",
    "support_call_missing": "📞 Raqam hozircha kiritilmagan. Iltimos, operatorga yozing.",
    "support_sent": "✅ Xabaringiz qabul qilindi (#{id}). Operator tez orada javob beradi.",
    "support_answer": "☎️ <b>Operator javobi</b> (#{id})\n\n{answer}",
    "support_too_short": "❗️ Xabar juda qisqa. Iltimos, batafsilroq yozing.",
    # ================= XODIM (ADMIN) PANELI =================
    "admin_staff_only": "⛔️ Bu bo'lim faqat xodimlar uchun.",
    "admin_welcome_staff": "🛠 <b>Xodim rejimi</b>\n\nRol: <b>{role}</b>",
    "admin_menu_title": "🛠 <b>Boshqaruv paneli</b>",
    "admin_menu_hint": "Bo'limni tanlang:",
    "btn_admin_stats": "📊 Bugungi statistika",
    "btn_admin_new_orders": "🆕 Yangi buyurtmalar ({count})",
    "btn_admin_active_orders": "🚚 Faol buyurtmalar",
    "btn_admin_search_order": "🔍 Buyurtma qidirish",
    "btn_admin_low_stock": "📉 Kam qoldiq",
    "btn_admin_support": "☎️ Murojaatlar ({count})",
    "admin_orders_title": "📦 <b>{title}</b> — {count} ta\n\nSahifa: {page}/{pages}",
    "admin_orders_empty": "📦 Buyurtmalar yo'q.",
    "admin_orders_new": "🆕 Yangi buyurtmalar",
    "admin_orders_active": "🚚 Faol buyurtmalar",
    "admin_orders_all": "📦 Barcha buyurtmalar",
    "admin_search_prompt": "🔍 Buyurtma raqamini yuboring (masalan: {example}):",
    "admin_search_not_found": "❌ «{query}» bo'yicha buyurtma topilmadi.",
    "admin_order_caption": (
        "🧾 <b>{number}</b> • {status}\n"
        "👤 {customer} • 📞 {phone}\n"
        "💰 <b>{total}</b> • {payment}\n"
        "📅 {date} • Manba: {source}"
    ),
    "btn_admin_change_status": "🔄 Holatni o'zgartirish",
    "admin_choose_status": "🔄 Yangi holatni tanlang:",
    "admin_status_changed": "✅ Buyurtma <b>{number}</b>: {status}",
    "admin_status_invalid": "⛔️ Bu holatga o'tish mumkin emas.",
    "admin_status_same": "ℹ️ Buyurtma allaqachon shu holatda.",
    "admin_note_prompt": "✍️ Izoh yozing yoki «⏭ O'tkazib yuborish» tugmasini bosing:",
    "admin_low_stock_title": "📉 <b>Kam qolgan mahsulotlar</b>",
    "admin_low_stock_line": "• {name} — <b>{stock}</b> (min: {min_stock})",
    "admin_low_stock_empty": "✅ Barcha mahsulotlar yetarli miqdorda.",
    "admin_stats_title": "📊 <b>Statistika</b>\n📅 {date}",
    "admin_stats_line": (
        "• Buyurtmalar: <b>{orders}</b>\n"
        "• Summa: <b>{amount}</b>\n"
        "• O'rtacha chek: <b>{average}</b>\n"
        "• 🆕 Yangi: {new} | ✅ Tasdiqlangan: {confirmed}\n"
        "• 🚚 Yo'lda: {on_the_way} | 📬 Yetkazilgan: {delivered}\n"
        "• ❌ Bekor qilingan: {cancelled}"
    ),
    "admin_support_title": "☎️ <b>Ochiq murojaatlar</b> ({count})",
    "admin_support_empty": "✅ Ochiq murojaatlar yo'q.",
    "admin_support_line": "#{id} • {date}\n👤 {user} • 📞 {phone}\n\n{message}",
    "btn_admin_reply": "✍️ Javob berish (#{id})",
    "admin_reply_prompt": "✍️ #{id} murojaat uchun javob matnini yozing:",
    "admin_reply_sent": "✅ Javob yuborildi.",
    "admin_reply_failed": "⚠️ Javob yuborilmadi: foydalanuvchi botni bloklagan bo'lishi mumkin.",
    # ================= BILDIRISHNOMALAR =================
    "notif_order_created": (
        "🆕 <b>Yangi buyurtma {number}</b>\n\n"
        "👤 {customer}\n📞 {phone}\n💰 <b>{total}</b>\n"
        "🚚 {delivery_type}\n📍 {address}\n📊 Manba: {source}"
    ),
    "notif_order_status": "📊 <b>Buyurtma {number}</b>\n\nHolat: <b>{status}</b>",
    "notif_order_cancelled": "❌ Buyurtma <b>{number}</b> bekor qilindi.\nSabab: {reason}",
    "notif_low_stock": "📉 <b>Kam qolgan mahsulotlar</b> ({count} ta):\n\n{lines}",
    "notif_new_support": "☎️ <b>Yangi murojaat #{id}</b>\n\n👤 {user} • 📞 {phone}\n\n{message}",
    # ================= LABELLAR =================
    "status_new": "🆕 Yangi",
    "status_confirmed": "✅ Tasdiqlangan",
    "status_picking": "🧺 Yig'ilmoqda",
    "status_on_the_way": "🚚 Yo'lda",
    "status_delivered": "📬 Yetkazildi",
    "status_partially_delivered": "📭 Qisman yetkazildi",
    "status_cancelled": "❌ Bekor qilindi",
    "status_returned": "↩️ Qaytarildi",
    "pm_cash": "Naqd",
    "pm_transfer": "O'tkazma",
    "pm_card": "Karta",
    "pm_payme": "Payme",
    "pm_click": "Click",
    "ps_unpaid": "To'lanmagan",
    "ps_partial": "Qisman to'langan",
    "ps_paid": "To'langan",
    "ps_refunded": "Qaytarilgan",
    "dt_delivery": "Yetkazib berish",
    "dt_pickup": "O'zi olib ketish",
    "seg_new": "Yangi mijoz",
    "seg_regular": "Doimiy mijoz",
    "seg_vip": "VIP mijoz",
    "src_bot": "Telegram bot",
    "src_agent": "Agent",
    "src_admin": "Operator",
    "src_phone": "Telefon",
    "role_client": "Mijoz",
    "role_operator": "Operator",
    "role_warehouse": "Ombor xodimi",
    "role_manager": "Menejer",
    "role_admin": "Administrator",
    # ================= O'LCHOV BIRLIKLARI =================
    "unit_pcs": "dona",
    "unit_box": "quti",
    "unit_pack": "paket",
    "unit_kg": "kg",
    "unit_liter": "litr",
}
