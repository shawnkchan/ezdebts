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
from xmlrpc.client import boolean
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
	level=logging.DEBUG
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

	async def sendMessage(self, message: string):
		await self.bot.send_message(chat_id=self.chatId, text=message)
		logging.debug("Error message sent")

# class createAccountMessage():
# 	pass

# class DebtMessage():
# 	def __init__(self) -> None:
# 		pass
	
# 	def return

# class MessageFactoryInterface():
# 	pass

class MentionsChecker():
	def __init__(self, message: telegram.Message) -> None:
		self.tagged_users_count = 0
		self.mentioned_users = []
		self.mentioned_users_count = 0
		self.message = message
		self.message_list = message.text.split()
	
	def _countIntendedMentions(self) -> int:
		for word in self.message_list:
			if word[0] == '@':
				self.tagged_users_count += 1

	def _countActualMentionsCount(self) -> int:
		mentions_dict = self.message.parse_entities(['mention', 'text_mention'])
		for key in mentions_dict:
			self.mentioned_users.append(mentions_dict[key])
			self.mentioned_users_count += 1

	def allValidMentions(self):
		self._countActualMentionsCount()
		self._countIntendedMentions()
		if self.mentioned_users_count != self.tagged_users_count:
			return False
		return True


class User():
	def __init__(self, telegram_user: telegram.User) -> None:
		self.user_id = telegram_user.id
		self.user_handle = telegram_user.name
		self.user_full_name = telegram_user.full_name
		self.user_first_name = ''
		self.user_last_name = ''

	async def _checkIfUserExists(self, user_handle: str) -> bool:
		return await sync_to_async(UserData.objects.filter(username=user_handle).exists)()

	async def createAccount(self):
		user_full_name_list = self.user_full_name.split()
		if len(user_full_name_list) > 1:
			self.user_last_name = user_full_name_list[-1]
		self.user_first_name = user_full_name_list[0]

		user_exists = await self._checkIfUserExists(self.user_handle)
		if user_exists:
			return False

		new_account = UserData(id=self.user_id, first_name=self.user_first_name, last_name=self.user_last_name, username=self.user_handle)
		await sync_to_async(new_account.save)()
		return True

	async def _returnNonExistentMentions(self, mentions: list) -> list:
		for mention in mentions:
			user_exists = await self._checkIfUserExists(mention)
			if user_exists:
				mentions.remove(mention)
		return mentions

	async def addDebts(self, mentions: list, debt: list) -> list:
		if len(self._returnNonExistentMentions(mentions)) != 0:
			return mentions
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
			return []

# ---USER FUNCTIONS---

#  ---CREATE ACCOUNT---
'''
Handles the registration of a user in the DB
inputs: Update, Context
outputs: None
'''
async def createAccount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	telegram_user = update.effective_user
	chat_id = update.effective_chat.id
	bot = context.bot

	context_bot = ContextBot(bot, chat_id)
	current_user = User(telegram_user, context_bot)
	success = await current_user.createAccount()
	if not success:
		await context_bot.sendMessage(f"The user {current_user.user_handle} already has an account with EzDebts")


# ---ADD EXPENSE---
'''
adds an expense to the Expense Model in DB if user calls /addExepnse
inputs: Update, ContextType
outputs: NIL, updates the DB
'''

def _checkExpenseMessage(message_list: list):
	pass

async def addExpense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	telegram_user = update.effective_user
	chat_id = update.effective_chat.id
	bot = context.bot
	message = update.message

	context_bot = ContextBot(bot, chat_id)
	current_user = User(telegram_user, context_bot)
	mentions_checker = MentionsChecker(message)

	if not mentions_checker.allValidMentions():
		await context_bot.sendMessage("An invalid user had been tagged")

	nonExistentMentions = await current_user.addDebts()
	if nonExistentMentions:
		await context_bot.sendMessage(f"The users {nonExistentMentions} do not have registered EzDebts accounts")
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