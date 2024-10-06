import requests

from environs import Env
import redis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler


def start(update, context):
    print('start')
    products = context.bot_data['products']
    keyboard = [[InlineKeyboardButton(product['title'], callback_data=int(product['id']))] for product in products]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text='Привет!', reply_markup=reply_markup)
    return 'HANDLE_MENU'


def handle_menu(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    product_id = int(query.data)
    products = context.bot_data['products']
    selected_product = next((product for product in products if product['id'] == product_id), None)
    if selected_product:
        query.edit_message_text(text=f"{selected_product['title']} ({selected_product['price']} руб. за кг)"
                                     f"\n\n{selected_product['description']}")
    return 'START'


def handle_users_reply(update, context):
    db = context.bot_data['redis_connection']
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu
    }
    state_handler = states_functions[user_state]
    print(state_handler)
    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
        print(f"State updated to {next_state}")
    except Exception as err:
        print(err)


def main():
    env = Env()
    env.read_env()
    token = env.str('TG_BOT_TOKEN')
    redis_host = env.str('REDIS_HOST')
    redis_port = env.int('REDIS_PORT')
    redis_password = env.str('REDIS_PASSWORD')
    strapi_token = env('STRAPI_TOKEN')
    url = 'http://127.0.0.1:1337/api/products'
    params = {
        'fields': 'title, description, price',
    }
    headers = {'Authorization': f'Bearer {strapi_token}'}
    updater = Updater(token)
    dispatcher = updater.dispatcher
    response = requests.get(url, headers=headers, params=params)
    products = response.json()['data']
    dispatcher.bot_data['products'] = products
    redis_connection = redis.Redis(host=redis_host, port=redis_port,
                                   password=redis_password, db=0)
    dispatcher.bot_data['redis_connection'] = redis_connection

    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()



