from contextvars import Context
from distutils.cmd import Command
from email.headerregistry import MessageIDHeader
from email.message import Message
import os
from urllib.request import UnknownHandler
from dotenv import load_dotenv
import telegram
import django
import logging
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ezdebts.settings')
django.setup()
from ezdebts.settings import DATABASES
from ezdebts_app.models import UserData
from telegram import Update, MessageEntity
from telegram.ext import Updater, CommandHandler, CallbackContext, ApplicationBuilder, ContextTypes, MessageHandler, filters
from asgiref.sync import sync_to_async

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.WARNING
)

# DEMO FUNCTIONS
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user_id = update.effective_user.id
	await update.message.reply_text(f"userid: {user_id}")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await context.bot.send_message(chat_id=update.effective_chat.id, text="Unknown command")

# ---USER FUNCTIONS---

#  ---CREATE ACCOUNT---
'''
Splits a string into a list of words
inputs: string of words
outputs: list of individual words as strings
'''
def _splitName(full_name: str) -> list[str]:
	names = full_name.split()
	return names

'''
Handles the registration of a user in the DB
inputs: Update, Context
outputs: None
'''
async def createAccount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	# chat metadata
	chat_id = update.effective_chat.id
	user = update.effective_user

	# user variables
	user_id = user.id
	user_handle = user.name
	user_full_name = user.full_name
	user_full_name_list = _splitName(user_full_name)
	user_first_name = user_full_name_list[0]

	# retrieve the user's last name
	if len(user_full_name_list) > 1:
		user_last_name = user_full_name_list[-1]
	else:
		user_last_name = ''
	
	# check if user exists in the DB
	user_exists = await sync_to_async(UserData.objects.filter(username=user_handle).exists)()
	if user_exists:
		await context.bot.send_message(chat_id=chat_id, text="You have already registered for an account")
		return

	new_account = UserData(id=user_id, first_name=user_first_name, last_name=user_last_name, username=user_handle)

	await sync_to_async(new_account.save)()
	logging.info("added new account to db")
	await context.bot.send_message(chat_id=chat_id, text="You have successfully registered an account!")

# ---ADD EXPENSE---
'''
Filters out any mentions in the text
inputs: Update object containing the message data
output: List of Mentions 
'''
def _filterMentions(message: Message) -> list[str]:
	mentions = []
	mentions_dict = message.parse_entities(['mention', 'text_mention'])
	for key in mentions_dict:
		mentions.append(mentions_dict[key])
	return mentions
	
# Checks database for existence of user
'''
adds an expense to the Expense Model in DB if user calls /addExepnse
inputs: Update, ContextType
outputs: NIL, updates the DB
'''
async def addExpense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	#inform user about format to enter expense: <mention> <quantity> <currency>
	message = update.message
	mentions = _filterMentions(message)
	print(mentions)

if __name__ == '__main__':
	application = ApplicationBuilder().token(BOT_TOKEN).build()
	
	start_handler = CommandHandler('start', start)
	echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
	callback_handler = CommandHandler('callback', callback)
	createAcc_handler = CommandHandler('register', createAccount)
	addExpense_handler = CommandHandler('addexpense', addExpense)
	unkown_handler = MessageHandler(filters.COMMAND, unknown)

	application.add_handler(start_handler)
	application.add_handler(echo_handler)
	application.add_handler(callback_handler)
	application.add_handler(createAcc_handler)
	application.add_handler(addExpense_handler)
	application.add_handler(unkown_handler)
	
	application.run_polling()