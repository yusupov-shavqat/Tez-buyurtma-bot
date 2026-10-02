"""Русские тексты интерфейса."""

from __future__ import annotations

MESSAGES: dict[str, str] = {
    # ================= ОБЩЕЕ =================
    "lang_name": "Русский 🇷🇺",
    "btn_back": "⬅️ Назад",
    "btn_main_menu": "🏠 Главное меню",
    "btn_cancel": "❌ Отмена",
    "btn_skip": "⏭ Пропустить",
    "btn_yes": "✅ Да",
    "btn_no": "❌ Нет",
    "btn_confirm": "✅ Подтвердить",
    "btn_prev": "⬅️ Предыдущая",
    "btn_next": "Следующая ➡️",
    "btn_search": "🔍 Поиск",
    "btn_promo": "🔥 Акции",
    "btn_catalog": "🛍 Каталог",
    "btn_cart": "🛒 Корзина",
    "btn_orders": "📦 Мои заказы",
    "btn_profile": "👤 Профиль",
    "btn_support": "☎️ Поддержка",
    "btn_admin": "🛠 Управление",
    "error_generic": "⚠️ Произошла ошибка. Попробуйте немного позже.",
    "error_denied": "⛔️ У вас нет прав для этого действия.",
    "error_not_found": "❌ Данные не найдены.",
    "error_stale": "⌛️ Эта кнопка устарела. Пожалуйста, выберите заново из меню.",
    "unknown_message": "🤔 Не понял. Пожалуйста, используйте кнопки меню.",
    "my_id": "🆔 Ваш Telegram ID: <code>{id}</code>",
    "help_text": (
        "ℹ️ <b>Помощь</b>\n\n"
        "Доступные команды:\n"
        "/start — главное меню\n"
        "/catalog — каталог\n"
        "/cart — корзина\n"
        "/orders — мои заказы\n"
        "/language — сменить язык\n"
        "/help — помощь\n\n"
        "По вопросам пишите оператору через «☎️ Поддержка»."
    ),
    # ================= СТАРТ / РЕГИСТРАЦИЯ =================
    "start_language_title": "🌐 <b>Выберите язык</b>\n\nTilni tanlang / Выберите язык",
    "lang_changed": "✅ Язык изменён: <b>{language}</b>",
    "start_welcome": (
        "👋 Добро пожаловать в бот <b>{brand}</b>!\n\n"
        "Здесь вы можете:\n"
        "• 🛍 посмотреть каталог;\n"
        "• 🛒 собрать корзину и оформить заказ;\n"
        "• 📦 отслеживать статус заказа;\n"
        "• ☎️ связаться с оператором."
    ),
    "start_ask_phone": (
        "📱 Отправьте свой номер телефона, чтобы оформить заказ.\n\n"
        "Нажмите «📱 Отправить номер» или введите номер вручную "
        "(например: +998901234567)."
    ),
    "btn_share_phone": "📱 Отправить номер",
    "phone_received": "✅ Ваш номер принят: <b>{phone}</b>",
    "phone_invalid": "❌ Неверный номер телефона. Отправьте снова (например: +998901234567).",
    "phone_wrong_owner": "❌ Можно отправить только свой номер телефона.",
    "welcome_back": "👋 Добро пожаловать, <b>{name}</b>!\n\nВыберите раздел:",
    "start_menu_hint": "Выберите нужный раздел в меню ниже 👇",
    # ================= КАТАЛОГ =================
    "catalog_title": "🛍 <b>Каталог</b>\n\nВыберите категорию:",
    "catalog_empty": "🛍 Каталог пока пуст. Попробуйте позже.",
    "catalog_products_title": "{emoji} <b>{category}</b>\n\nСтраница: {page}/{pages}",
    "catalog_products_empty": "В этой категории нет товаров.",
    "catalog_search_prompt": "🔍 Поиск: отправьте название товара, артикул (SKU) или штрих-код.",
    "catalog_search_results": "🔍 По запросу «{query}» найдено: <b>{count}</b>",
    "catalog_search_empty": "🔍 По запросу «{query}» ничего не найдено.",
    "catalog_promo_title": "🔥 <b>Товары со скидкой</b>",
    "catalog_promo_empty": "🔥 Акций пока нет.",
    "product_sku": "🔖 Артикул: <code>{sku}</code>",
    "product_price": "💵 Цена: <b>{price}</b>",
    "product_old_price": "❌ Старая цена: <s>{price}</s>",
    "product_discount": "🔥 Скидка: <b>-{percent}%</b>",
    "product_box": "📦 1 коробка = {count} {unit} — {price}",
    "product_stock": "📊 На складе: <b>{quantity}</b>",
    "product_out_of_stock": "🚫 Нет в наличии",
    "product_low_stock": "⚠️ Осталось мало",
    "btn_add_to_cart": "➕ В корзину",
    "add_qty_prompt": "Выберите количество или введите вручную:",
    "btn_other_qty": "✏️ Другое количество",
    "add_qty_input_prompt": "✏️ Введите количество цифрой (например: 3 или 2,5):",
    "qty_added": "✅ Добавлено в корзину: <b>{quantity}</b>",
    "qty_invalid": "❌ Неверное количество. Введите число больше нуля.",
    "qty_stock_limit": "⚠️ На складе есть только {quantity}.",
    # ================= КОРЗИНА =================
    "cart_title": "🛒 <b>Корзина</b> — {count} позиций",
    "cart_empty": "🛒 Ваша корзина пуста.\n\nВыберите товары в каталоге.",
    "cart_item": "{index}. <b>{name}</b>\n     {quantity} × {price} = <b>{total}</b>",
    "cart_summary": (
        "➖➖➖➖➖➖➖➖\n"
        "Товары: <b>{subtotal}</b>\n"
        "{discount}🚚 Доставка: <b>{delivery}</b>\n"
        "💰 <b>Итого: {total}</b>"
    ),
    "cart_discount_line": "🎁 Скидка: <b>-{discount}</b>\n",
    "cart_min_amount": (
        "⚠️ Минимальная сумма заказа не достигнута.\n"
        "Добавьте товаров ещё на <b>{amount}</b>."
    ),
    "cart_removed": "🗑 «{name}» удалён из корзины.",
    "cart_cleared": "🗑 Корзина очищена.",
    "cart_updated": "✅ Количество обновлено: <b>{quantity}</b>",
    "btn_checkout": "🚚 Оформить заказ",
    "btn_clear_cart": "🗑 Очистить корзину",
    # ================= ОФОРМЛЕНИЕ ЗАКАЗА =================
    "co_delivery_title": "🚚 <b>Способ получения</b>\n\nКак вы хотите получить заказ?",
    "btn_co_delivery": "🚚 Доставка",
    "btn_co_pickup": "🏬 Самовывоз",
    "co_pickup_address": "🏬 <b>Адрес самовывоза:</b>\n{address}\n\n🕘 Часы работы: {hours}",
    "co_pickup_missing": "🏬 Нет данных об адресе. Свяжитесь с оператором.",
    "co_ask_address": "📍 Отправьте адрес доставки: текстом или через «📍 Отправить локацию».",
    "co_saved_addresses": "📍 Выберите сохранённый адрес или введите новый:",
    "btn_send_location": "📍 Отправить локацию",
    "btn_new_address": "✍️ Новый адрес",
    "co_address_saved": "✅ Адрес сохранён.",
    "co_address_required": "❗️ Пожалуйста, отправьте адрес текстом или локацией.",
    "co_ask_time": "🕑 Когда удобно доставить заказ?",
    "btn_time_asap": "⏰ Как можно быстрее",
    "btn_time_today_am": "🕘 Сегодня 09:00–13:00",
    "btn_time_today_pm": "🕔 Сегодня 14:00–18:00",
    "btn_time_tomorrow": "📅 Завтра",
    "co_ask_comment": (
        "📝 Добавьте комментарий к заказу (например: «2-й этаж», «домофон 45»).\n"
        "Если не нужно — нажмите «⏭ Пропустить»."
    ),
    "co_choose_payment": "💳 Выберите способ оплаты:",
    "btn_pay_cash": "💵 Наличными (при доставке)",
    "btn_pay_transfer": "🏦 Перевод (на расчётный счёт)",
    "btn_pay_card": "💳 Пластиковая карта",
    "btn_pay_online": "🌐 Онлайн оплата",
    "co_online_pending": (
        "🌐 <b>Онлайн оплата</b>\n\nЗаказ: <b>{number}</b>\nСумма: <b>{total}</b>\n\n"
        "Ссылка на оплату: {link}\n\n"
        "После подтверждения платежа статус заказа обновится автоматически."
    ),
    "co_summary_title": "🧾 <b>Проверьте заказ</b>",
    "co_summary_item": "• {name} — {quantity} × {price} = <b>{total}</b>",
    "co_summary_info": (
        "➖➖➖➖➖➖➖➖\n"
        "🧺 Товары: <b>{subtotal}</b>\n"
        "{discount}🚚 Доставка: <b>{delivery}</b>\n"
        "💰 <b>Итого: {total}</b>\n\n"
        "🚚 Способ: {delivery_type}\n"
        "📍 Адрес: {address}\n"
        "🕑 Время: {time}\n"
        "💳 Оплата: {payment}"
    ),
    "co_confirm_ask": "Подтверждаете заказ?",
    "co_created": (
        "✅ <b>Заказ принят!</b>\n\n"
        "🧾 Номер: <b>{number}</b>\n"
        "💰 Сумма: <b>{total}</b>\n\n"
        "Оператор скоро свяжется с вами. Статус заказа можно отслеживать "
        "в разделе «📦 Мои заказы»."
    ),
    "co_cancelled": "❌ Оформление заказа отменено. Корзина сохранена.",
    "co_data_expired": "⌛️ Данные устарели. Пожалуйста, начните заново из корзины.",
    # ================= МОИ ЗАКАЗЫ =================
    "orders_title": "📦 <b>Мои заказы</b>\n\nСтраница: {page}/{pages}",
    "orders_empty": "📦 У вас пока нет заказов.\n\nНачните покупки в каталоге!",
    "orders_item": "{index}. <b>{number}</b> — {status}\n     {date} • {total}",
    "btn_order_detail": "🧾 {number}",
    "order_title": "🧾 <b>Заказ {number}</b>",
    "order_info": (
        "📅 Дата: {date}\n"
        "📊 Статус: <b>{status}</b>\n"
        "💰 Сумма: <b>{total}</b>\n"
        "💳 Оплата: {payment} — {payment_status}"
    ),
    "order_delivery_info": "🚚 {delivery_type}\n📍 {address}\n🕑 {time}",
    "order_items_title": "🧺 <b>Состав заказа:</b>",
    "order_item_line": "• {name} — {quantity} × {price} = {total}",
    "order_comment": "📝 Комментарий: {comment}",
    "order_history_title": "🕘 <b>История статусов:</b>",
    "order_history_line": "• {date} — {status}",
    "btn_order_cancel": "❌ Отменить заказ",
    "btn_order_repeat": "🔁 Повторить заказ",
    "order_cancel_prompt": "❌ Напишите причину отмены:",
    "order_cancelled": "✅ Заказ <b>{number}</b> отменён.",
    "order_cannot_cancel": "⛔️ Этот заказ уже нельзя отменить. Свяжитесь с оператором.",
    "order_repeat_done": (
        "🔁 Добавлено в корзину: <b>{count}</b> позиций.\n"
        "Перейдите в корзину и подтвердите заказ."
    ),
    "order_repeat_empty": "⚠️ Товары из этого заказа сейчас недоступны.",
    # ================= ПРОФИЛЬ =================
    "profile_title": "👤 <b>Профиль</b>",
    "profile_name": "👤 Имя: <b>{value}</b>",
    "profile_phone": "📱 Телефон: <b>{value}</b>",
    "profile_language": "🌐 Язык: <b>{value}</b>",
    "profile_segment": "⭐️ Категория: <b>{value}</b>",
    "profile_debt": "💰 Задолженность: <b>{value}</b>",
    "profile_address": "📍 Адрес: <b>{value}</b>",
    "profile_unknown": "—",
    "btn_change_phone": "📱 Изменить телефон",
    "btn_change_language": "🌐 Изменить язык",
    "profile_phone_prompt": "📱 Отправьте новый номер телефона (кнопкой или текстом):",
    "profile_phone_updated": "✅ Номер телефона обновлён.",
    "btn_my_addresses": "📍 Мои адреса",
    "profile_addresses_title": "📍 <b>Сохранённые адреса</b>",
    "profile_addresses_empty": "📍 Сохранённых адресов нет.",
    "profile_address_line": "{index}. {address}",
    # ================= ПОДДЕРЖКА =================
    "support_title": "☎️ <b>Поддержка</b>",
    "support_menu": "☎️ <b>Помощь</b>\n\nЧто вы хотите сделать?",
    "support_ask": "✍️ Напишите ваш вопрос — оператор ответит.",
    "btn_support_write": "✍️ Написать оператору",
    "btn_support_call": "📞 По телефону",
    "support_call_info": "📞 Телефон поддержки: <b>{phone}</b>",
    "support_call_missing": "📞 Номер пока не указан. Пожалуйста, напишите оператору.",
    "support_sent": "✅ Ваше сообщение принято (#{id}). Оператор скоро ответит.",
    "support_answer": "☎️ <b>Ответ оператора</b> (#{id})\n\n{answer}",
    "support_too_short": "❗️ Сообщение слишком короткое. Пожалуйста, опишите подробнее.",
    # ================= ПАНЕЛЬ СОТРУДНИКА =================
    "admin_staff_only": "⛔️ Этот раздел только для сотрудников.",
    "admin_welcome_staff": "🛠 <b>Режим сотрудника</b>\n\nРоль: <b>{role}</b>",
    "admin_menu_title": "🛠 <b>Панель управления</b>",
    "admin_menu_hint": "Выберите раздел:",
    "btn_admin_stats": "📊 Статистика за сегодня",
    "btn_admin_new_orders": "🆕 Новые заказы ({count})",
    "btn_admin_active_orders": "🚚 Активные заказы",
    "btn_admin_search_order": "🔍 Поиск заказа",
    "btn_admin_low_stock": "📉 Мало на складе",
    "btn_admin_support": "☎️ Обращения ({count})",
    "admin_orders_title": "📦 <b>{title}</b> — {count}\n\nСтраница: {page}/{pages}",
    "admin_orders_empty": "📦 Заказов нет.",
    "admin_orders_new": "🆕 Новые заказы",
    "admin_orders_active": "🚚 Активные заказы",
    "admin_orders_all": "📦 Все заказы",
    "admin_search_prompt": "🔍 Отправьте номер заказа (например: {example}):",
    "admin_search_not_found": "❌ Заказ по запросу «{query}» не найден.",
    "admin_order_caption": (
        "🧾 <b>{number}</b> • {status}\n"
        "👤 {customer} • 📞 {phone}\n"
        "💰 <b>{total}</b> • {payment}\n"
        "📅 {date} • Источник: {source}"
    ),
    "btn_admin_change_status": "🔄 Изменить статус",
    "admin_choose_status": "🔄 Выберите новый статус:",
    "admin_status_changed": "✅ Заказ <b>{number}</b>: {status}",
    "admin_status_invalid": "⛔️ Переход в этот статус невозможен.",
    "admin_status_same": "ℹ️ Заказ уже в этом статусе.",
    "admin_note_prompt": "✍️ Напишите комментарий или нажмите «⏭ Пропустить»:",
    "admin_low_stock_title": "📉 <b>Товары с малым остатком</b>",
    "admin_low_stock_line": "• {name} — <b>{stock}</b> (мин: {min_stock})",
    "admin_low_stock_empty": "✅ Всех товаров достаточно.",
    "admin_stats_title": "📊 <b>Статистика</b>\n📅 {date}",
    "admin_stats_line": (
        "• Заказов: <b>{orders}</b>\n"
        "• Сумма: <b>{amount}</b>\n"
        "• Средний чек: <b>{average}</b>\n"
        "• 🆕 Новые: {new} | ✅ Подтверждены: {confirmed}\n"
        "• 🚚 В пути: {on_the_way} | 📬 Доставлены: {delivered}\n"
        "• ❌ Отменены: {cancelled}"
    ),
    "admin_support_title": "☎️ <b>Открытые обращения</b> ({count})",
    "admin_support_empty": "✅ Открытых обращений нет.",
    "admin_support_line": "#{id} • {date}\n👤 {user} • 📞 {phone}\n\n{message}",
    "btn_admin_reply": "✍️ Ответить (#{id})",
    "admin_reply_prompt": "✍️ Введите текст ответа для обращения #{id}:",
    "admin_reply_sent": "✅ Ответ отправлен.",
    "admin_reply_failed": "⚠️ Ответ не отправлен: возможно, пользователь заблокировал бота.",
    # ================= УВЕДОМЛЕНИЯ =================
    "notif_order_created": (
        "🆕 <b>Новый заказ {number}</b>\n\n"
        "👤 {customer}\n📞 {phone}\n💰 <b>{total}</b>\n"
        "🚚 {delivery_type}\n📍 {address}\n📊 Источник: {source}"
    ),
    "notif_order_status": "📊 <b>Заказ {number}</b>\n\nСтатус: <b>{status}</b>",
    "notif_order_cancelled": "❌ Заказ <b>{number}</b> отменён.\nПричина: {reason}",
    "notif_low_stock": "📉 <b>Товары с малым остатком</b> ({count}):\n\n{lines}",
    "notif_new_support": "☎️ <b>Новое обращение #{id}</b>\n\n👤 {user} • 📞 {phone}\n\n{message}",
    # ================= МЕТКИ =================
    "status_new": "🆕 Новый",
    "status_confirmed": "✅ Подтверждён",
    "status_picking": "🧺 Собирается",
    "status_on_the_way": "🚚 В пути",
    "status_delivered": "📬 Доставлен",
    "status_partially_delivered": "📭 Доставлен частично",
    "status_cancelled": "❌ Отменён",
    "status_returned": "↩️ Возврат",
    "pm_cash": "Наличные",
    "pm_transfer": "Перевод",
    "pm_card": "Карта",
    "pm_payme": "Payme",
    "pm_click": "Click",
    "ps_unpaid": "Не оплачен",
    "ps_partial": "Частично оплачен",
    "ps_paid": "Оплачен",
    "ps_refunded": "Возвращён",
    "dt_delivery": "Доставка",
    "dt_pickup": "Самовывоз",
    "seg_new": "Новый клиент",
    "seg_regular": "Постоянный клиент",
    "seg_vip": "VIP клиент",
    "src_bot": "Telegram bot",
    "src_agent": "Агент",
    "src_admin": "Оператор",
    "src_phone": "Телефон",
    "role_client": "Клиент",
    "role_operator": "Оператор",
    "role_warehouse": "Кладовщик",
    "role_manager": "Менеджер",
    "role_admin": "Администратор",
    # ================= ЕДИНИЦЫ ИЗМЕРЕНИЯ =================
    "unit_pcs": "шт",
    "unit_box": "коробка",
    "unit_pack": "упаковка",
    "unit_kg": "кг",
    "unit_liter": "литр",
}
