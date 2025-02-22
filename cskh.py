import logging
import sqlite3
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext

# Cấu hình logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Các trạng thái của cuộc hội thoại
CONTACT, SERVICE, ACCOUNT, EXPIRY_DATE, DELETE_ID, EDIT_ID, EDIT_FIELD, EDIT_VALUE = range(8)

# Token Bot Telegram
BOT_TOKEN = "7947199166:AAF46AHEJakYOgkfjwsoqtXyFR3uOgnwh0w"

# Khởi tạo DB
def init_db():
    conn = sqlite3.connect('customers.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact TEXT NOT NULL,
            service TEXT NOT NULL,
            account TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            chat_id INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Lệnh /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🤖 Chào mừng đến với bot quản lý khách hàng!\n"
        "📌 Lệnh hỗ trợ:\n"
        "➖ /add - Thêm khách hàng mới\n"
        "➖ /list - Xem danh sách khách hàng theo dịch vụ\n"
        "➖ /delete - Xóa khách hàng\n"
        "➖ /edit - Sửa thông tin khách hàng"
    )

# Lệnh /add
async def add_customer_start(update: Update, context: CallbackContext):
    await update.message.reply_text("✏️ Nhập thông tin liên hệ của khách hàng:")
    return CONTACT

async def add_customer_contact(update: Update, context: CallbackContext):
    context.user_data['contact'] = update.message.text
    await update.message.reply_text("📌 Nhập dịch vụ sử dụng (Netflix, YouTube, v.v.):")
    return SERVICE

async def add_customer_service(update: Update, context: CallbackContext):
    context.user_data['service'] = update.message.text
    await update.message.reply_text("🔑 Nhập tài khoản sử dụng:")
    return ACCOUNT

async def add_customer_account(update: Update, context: CallbackContext):
    context.user_data['account'] = update.message.text
    await update.message.reply_text("📆 Nhập ngày hết hạn (YYYY-MM-DD):")
    return EXPIRY_DATE

async def add_customer_expiry(update: Update, context: CallbackContext):
    expiry_date = update.message.text
    chat_id = update.message.chat_id
    contact = context.user_data.get('contact')
    service = context.user_data.get('service')
    account = context.user_data.get('account')

    conn = sqlite3.connect('customers.db')
    c = conn.cursor()
    c.execute('INSERT INTO customers (contact, service, account, expiry_date, chat_id) VALUES (?, ?, ?, ?, ?)',
              (contact, service, account, expiry_date, chat_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Đã thêm khách hàng {contact}.")
    return ConversationHandler.END

# Lệnh /list
async def list_customers(update: Update, context: CallbackContext):
    conn = sqlite3.connect('customers.db')
    c = conn.cursor()
    c.execute('SELECT id, contact, service, expiry_date FROM customers')
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("🚫 Không có khách hàng nào trong danh sách.")
        return

    today = datetime.date.today()
    services = {}

    for row in rows:
        id, contact, service, expiry_date_str = row
        expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        days_remaining = (expiry_date - today).days

        if service not in services:
            services[service] = []
        services[service].append((id, contact, days_remaining))

    message = "📌 **DANH SÁCH KHÁCH HÀNG THEO DỊCH VỤ**\n"
    for service, customers in services.items():
        message += f"\n🔹 **{service}**\n"
        for id, contact, days_remaining in customers:
            message += f"  - ID: {id} | 👤 {contact} | ⏳ {days_remaining} ngày\n"

    await update.message.reply_text(message)

# Lệnh /delete
async def delete_customer_start(update: Update, context: CallbackContext):
    await update.message.reply_text("🗑 Nhập ID khách hàng cần xóa:")
    return DELETE_ID

async def delete_customer_confirm(update: Update, context: CallbackContext):
    customer_id = update.message.text
    conn = sqlite3.connect('customers.db')
    c = conn.cursor()
    c.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Đã xóa khách hàng có ID {customer_id}.")
    return ConversationHandler.END

# Lệnh /edit
async def edit_customer_start(update: Update, context: CallbackContext):
    await update.message.reply_text("✏️ Nhập ID khách hàng cần sửa:")
    return EDIT_ID

async def edit_customer_field(update: Update, context: CallbackContext):
    context.user_data['edit_id'] = update.message.text
    await update.message.reply_text("🔄 Nhập trường cần sửa (contact, service, account, expiry_date):")
    return EDIT_FIELD

async def edit_customer_value(update: Update, context: CallbackContext):
    context.user_data['edit_field'] = update.message.text
    await update.message.reply_text("✍️ Nhập giá trị mới:")
    return EDIT_VALUE

async def edit_customer_confirm(update: Update, context: CallbackContext):
    customer_id = context.user_data['edit_id']
    field = context.user_data['edit_field']
    value = update.message.text

    conn = sqlite3.connect('customers.db')
    c = conn.cursor()
    c.execute(f'UPDATE customers SET {field} = ? WHERE id = ?', (value, customer_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Đã cập nhật ID {customer_id}: {field} -> {value}.")
    return ConversationHandler.END

# Hàm khởi chạy bot
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    conv_add = ConversationHandler(
        entry_points=[CommandHandler('add', add_customer_start)],
        states={
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_customer_contact)],
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_customer_service)],
            ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_customer_account)],
            EXPIRY_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_customer_expiry)]
        },
        fallbacks=[]
    )

    conv_delete = ConversationHandler(
        entry_points=[CommandHandler('delete', delete_customer_start)],
        states={DELETE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_customer_confirm)]},
        fallbacks=[]
    )

    conv_edit = ConversationHandler(
        entry_points=[CommandHandler('edit', edit_customer_start)],
        states={
            EDIT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_customer_field)],
            EDIT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_customer_value)],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_customer_confirm)]
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_add)
    application.add_handler(conv_delete)
    application.add_handler(conv_edit)
    application.add_handler(CommandHandler("list", list_customers))

    application.run_polling()

if __name__ == '__main__':
    main()
