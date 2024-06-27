from cgitb import text
import code
from contextvars import Context
from distutils.cmd import Command
from email.headerregistry import MessageIDHeader
from email.message import Message
from locale import currency
import os
import string
from tokenize import String
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
from telegram import Update, MessageEntity, KeyboardButton, ReplyKeyboardMarkup
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

# Class based implementation
class ContextBot():
	def __init__(self, bot: telegram.Bot, chatId: int) -> None:
		self.bot = bot
		self.chatId = chatId

	def sendMessage(self, message: string):
		self.bot.send_message(chat_id=self.chatId, text=message)


class User():
	def __init__(self, telegram_user: telegram.User, ContextBot: ContextBot) -> None:
		self.user_id = telegram_user.id
		self.user_handle = telegram_user.name
		self.user_full_name = telegram_user.full_name
		self.user_first_name = ''
		self.user_last_name = ''
		self.ContextBot = ContextBot

	async def _checkIfUserExists(user_handle: str) -> bool:
		return await sync_to_async(UserData.objects.filter(username=user_handle).exists)()

	async def createAccount(self):
		user_full_name_list = self.user_full_name.split()
		if len(user_full_name_list) > 1:
			self.user_last_name = user_full_name_list[-1]
		self.user_first_name = user_full_name_list[0]

		user_exists = await self._checkIfUserExists(self.user_handle)
		if user_exists:
			self.ContextBot.sendMessage("You have already registered for an account")

		new_account = UserData(id=self.user_id, first_name=self.user_first_name, last_name=self.user_last_name, username=self.user_handle)
		await sync_to_async(new_account.save())

	async def _returnNonExistentMention(self, mentions: list) -> list:
		for mention in mentions:
			user_exists = await self._checkIfUserExists(mention)
			if user_exists:
				mentions.remove(mention)
		return mentions
		

	async def addDebts(self, mentions: list, debt: list):
		# check formatting before sending it to this function

		# move this error checking to outside the function
		# message_list = message.split()
		# tagged_users_count = self._countTaggedUsers(message_list)
		# mentions_list = self._returnMentionsList()
		# if not mentions_list:
		# 	return "You have 0 valid users mentioned" 
		# if len(mentions_list) < tagged_users_count:
		# 	return "Non-existent user tagged"
		
		if len(self._returnNonExistentMention(mentions)) != 0:
			missing_mentions = ' '.join(mentions)
			self.ContextBot.sendMessage(f"Unable to add expense. {missing_mentions} do not have registered accounts.")
		else:
			quantity = debt[0]
			currency_code = debt[1]
			lender_model = await sync_to_async(get_object_or_404)(UserData, username='@' + self.user_handle)
			quantity_divided = round((int(quantity) / len(mentions)), 2)
			currency_model = await sync_to_async(get_object_or_404)(Currencies, code=currency_code)
			for mention in mentions:
				debtor_model = await sync_to_async(get_object_or_404)(UserData, username=mention)
				new_expense = Expenses(lender=lender_model, debtor=debtor_model, quantity=quantity_divided, currency=currency_model)
				await sync_to_async(new_expense.save)()
			
			
				
		


# ---USER FUNCTIONS---

#  ---CREATE ACCOUNT---
'''
Handles the registration of a user in the DB
inputs: Update, Context
outputs: None
'''
async def createAccount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	telegram_user = update.effective_user
	chat_id = update.effective_chat
	bot = context.bot

	context_bot = ContextBot(bot, chat_id)
	current_user = User(telegram_user, context_bot)
	current_user.createAccount()


# ---ADD EXPENSE---
'''
adds an expense to the Expense Model in DB if user calls /addExepnse
inputs: Update, ContextType
outputs: NIL, updates the DB
'''
async def addExpense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	pass
	# chat_id = update.effective_chat.id

	# #inform user about format to enter expense: <mention> <quantity> <currency code>

	# # check that user input is formatted correctly
	# message = update.message
	# message_text = message.text
	# message_text_list = message_text.split()
	# print(message)
	# print(type(message))
	
	# # count number of intended mentions
	# tagged_users = 0
	# for word in message_text_list:
	# 	if word[0] == '@':
	# 		tagged_users += 1

	# # filter out mentioned users
	# mentions = _filterMentions(message)
	# print(f"mentions: {mentions}")
	# if len(mentions) == 0:
	# 	await context.bot.send_message(chat_id=chat_id, text="You have 0 valid users mentioned")
	# 	return
	# if len(mentions) < tagged_users:
	# 	await context.bot.send_message(chat_id=chat_id, text="Non-existent user tagged")
	# 	return

	# # filter out expenses metadata
	# currency_code = message_text_list[-1].upper()
	# quantity = message_text_list[-2]

	# # check if currency code is valid
	# currency_exists = await _currencyExists(currency_code)
	# if not currency_exists:
	# 	await context.bot.send_message(chat_id=chat_id, text=f"{currency_code} is not a valid currency code")
	# 	return

	# if type(int(quantity)) != int:
	# 	await context.bot.send_message(chat_id=chat_id, text="No value detected. Please input a quantity")
	# 	return

	# # check for existence of mentioned users
	# for mention in mentions:
	# 	userExists = await _userExists(mention)
	# 	if not userExists:
	# 		await context.bot.send_message(chat_id=chat_id, text=f"{mention} does not have a registered account.")
	# 		return
	# 	else:
	# 		print('all users found')
	
	# print('@' + message.from_user.username)

	# lender_model = await sync_to_async(get_object_or_404)(UserData, username='@' + message.from_user.username)
	# debtors = mentions
	# quantity_divided = round((int(quantity) / len(mentions)), 2)
	# currency_model = await sync_to_async(get_object_or_404)(Currencies, code=currency_code)
	# # assuming we split evenly
	# for debtor in debtors:
	# 	debtor_model = await sync_to_async(get_object_or_404)(UserData, username=debtor)
	# 	new_expense = Expenses(lender=lender_model, debtor=debtor_model, quantity=quantity_divided, currency=currency_model)
	# 	await sync_to_async(new_expense.save)()
	# print('expenses added')
		
	
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