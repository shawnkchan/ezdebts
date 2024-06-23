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
from django.shortcuts import get_object_or_404
from ezdebts.settings import DATABASES
from ezdebts_app.models import Currencies, Expenses, UserData
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
Checks if a user's handle exists in the DB
inputs: string of the user's handle
outputs: boolean, whether the user is registered in the DB
'''
async def _userExists(user_handle: str) -> bool:
	user_exists = await sync_to_async(UserData.objects.filter(username=user_handle).exists)()
	return user_exists

async def _currencyExists(currency_code: str) -> bool:
	currency_exists = await sync_to_async(Currencies.objects.filter(code=currency_code).exists)()
	return currency_exists

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
	userExists = await _userExists(user_handle)
	if userExists:
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

'''
adds an expense to the Expense Model in DB if user calls /addExepnse
inputs: Update, ContextType
outputs: NIL, updates the DB
'''
async def addExpense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	chat_id = update.effective_chat.id

	#inform user about format to enter expense: <mention> <quantity> <currency code>

	# check that user input is formatted correctly
	message = update.message
	message_text = message.text
	message_text_list = message_text.split()
	print(message)
	print(type(message))
	
	# count number of intended mentions
	tagged_users = 0
	for word in message_text_list:
		if word[0] == '@':
			tagged_users += 1

	# filter out mentioned users
	mentions = _filterMentions(message)
	print(f"mentions: {mentions}")
	if len(mentions) == 0:
		await context.bot.send_message(chat_id=chat_id, text="You have 0 valid users mentioned")
		return
	if len(mentions) < tagged_users:
		await context.bot.send_message(chat_id=chat_id, text="Non-existent user tagged")
		return

	# filter out expenses metadata
	currency_code = message_text_list[-1].upper()
	quantity = message_text_list[-2]

	# # check if currency code is valid
	# currency_exists = await _currencyExists(currency_code)
	# if not currency_exists:
	# 	await context.bot.send_message(chat_id=chat_id, text=f"{currency_code} is not a valid currency code")
	# 	return

	# if type(int(quantity)) != int:
	# 	await context.bot.send_message(chat_id=chat_id, text="No value detected. Please input a quantity")
	# 	return

	# check for existence of mentioned users
	for mention in mentions:
		userExists = await _userExists(mention)
		if not userExists:
			await context.bot.send_message(chat_id=chat_id, text=f"{mention} does not have a registered account.")
			return
		else:
			print('all users found')
	
	print('@' + message.from_user.username)

	lender_model = await sync_to_async(get_object_or_404)(UserData, username='@' + message.from_user.username)
	debtors = mentions
	quantity_divided = round((int(quantity) / len(mentions)), 2)
	currency_model = await sync_to_async(get_object_or_404)(Currencies, code=currency_code)
	# assuming we split evenly
	for debtor in debtors:
		debtor_model = await sync_to_async(get_object_or_404)(UserData, username=debtor)
		new_expense = Expenses(lender=lender_model, debtor=debtor_model, quantity=quantity_divided, currency=currency_model)
		await sync_to_async(new_expense.save)()
	print('expenses added')
		

	






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