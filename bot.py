from contextvars import Context
from distutils.cmd import Command
from email.headerregistry import MessageIDHeader
from email.message import Message
import os
import string
from dotenv import load_dotenv
import telegram
import django
import logging
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ezdebts.settings')
django.setup()
from django.shortcuts import get_object_or_404
from ezdebts_app.models import Currencies, Expenses, UserData
from telegram import Update, MessageEntity, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, ApplicationBuilder, ContextTypes, MessageHandler, filters
from asgiref.sync import sync_to_async
from django.db.models import F

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

logging.basicConfig(
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
class MessageProcessor():
	def __init__(self, message: telegram.Message) -> None:
		self.mentionedUsers = []
		self.currencies = []
		self.quantities = []
		self.message = message
		self.messageList = message.text.split()

	def retrieveQuantities(self) -> None:
		for word in self.messageList:
			if word.isdigit():
				self.quantities.append(float(word))

	async def retrieveCurrencies(self) -> None:
		for word in self.messageList:
			currencyExists = await sync_to_async(Currencies.objects.filter(code=word.upper()).exists)()
			if currencyExists:
				self.currencies.append(word.upper())

	async def retrieveMentions(self) -> None:
		mentionsChecker = MentionsChecker(self.message)
		self.mentionedUsers = mentionsChecker.self

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

	async def _checkIfUserExists(self, user_handle: str) -> bool:
		return await sync_to_async(UserData.objects.filter(username=user_handle).exists)()

	async def returnNonExistentUsers(self) -> list:
		logging.debug(self.mentioned_users)
		mentions = self.mentioned_users.copy()
		for mention in self.mentioned_users:
			user_exists = await self._checkIfUserExists(mention)
			if user_exists:
				mentions.remove(mention)
		return mentions

class User():
	def __init__(self, telegram_user: telegram.User) -> None:
		self.user_id = telegram_user.id
		self.user_handle = telegram_user.name
		self.user_full_name = telegram_user.full_name
		self.user_first_name = ''
		self.user_last_name = ''
		# self.userModel = await get_object_or_404(UserData, username=telegram_user.name)

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

	'''Check DB for any existing debts of the same currency between lender and debtors.
	'''
	async def debtExists(self, lender_username: str, debtor_username: str, currency_code: str):
		lender = await sync_to_async(UserData.objects.get)(username=lender_username)
		debtor = await sync_to_async(UserData.objects.get)(username=debtor_username)
		currency = await sync_to_async(Currencies.objects.get)(code=currency_code)
		
		# Use filter with exists on the QuerySet
		debt_exists = await sync_to_async(Expenses.objects.filter(
			lender=lender, debtor=debtor, currency=currency
		).exists)()
		return debt_exists

	'''
	Adds a debt to the DB. 
	Assumes that debt is equally split amongst all mentions (not including the user adding the debt)
	If an existing debt relation exists in the same currency, the debt is updated.
	Else, a new debt is created
	TODO: Add function that enables debts to be split equally, unequally, or by a user specified fraction
	'''
	async def addDebts(self, mentions: list, debt: list):
		logging.debug('adding debts')
		quantity = debt[0]
		currency_code = debt[1].upper()
		lender_model = await sync_to_async(get_object_or_404)(UserData, username=self.user_handle)
		quantity_divided = round((int(quantity) / len(mentions)), 2)
		currency_model = await sync_to_async(get_object_or_404)(Currencies, code=currency_code)

		for mention in mentions:
			debtor_model = await sync_to_async(get_object_or_404)(UserData, username=mention)
			debt_exists = await self.debtExists(self.user_handle, mention, currency_code)
			if debt_exists:
				edited_expense = await sync_to_async(Expenses.objects.get)(lender=lender_model, debtor=debtor_model, currency=currency_model)
				await sync_to_async(Expenses.objects.filter(pk=edited_expense.pk).update)(quantity=F('quantity') + quantity_divided)
				logging.debug(f'update {currency_code} debt for {mention}')
			else:
				new_expense = Expenses(lender=lender_model, debtor=debtor_model, quantity=quantity_divided, currency=currency_model)
				await sync_to_async(new_expense.save)()
				logging.debug(f'added debt for {mention}')

	'''
	Creates a dictionary of debtors or lenders in the following format:
	dict[str <debtor__username>] = [str(<quantity> <currency>)]
	'''
	def _createCounterpartyDict(self, counterparties: list, findingDebtors: bool):
		if findingDebtors:
			counterparty__username = 'debtor__username'
		else:
			counterparty__username = 'lender__username'

		counterparties_dict = {}
		for counterparty in counterparties:
			username = counterparty[counterparty__username]
			quantity = counterparty['quantity']
			currency = counterparty['currency__code']

			debt_details = str(quantity) + ' ' + currency
			
			if username not in counterparties_dict:
				counterparties_dict[username] = []

			counterparties_dict[username].append(debt_details)
		return counterparties_dict

	def _createFormattedMessage(self, counterparties_dict: dict) -> str:
		formatted_counterparties_message = []

		for username in counterparties_dict:
			formatted_counterparties_message.append(username + ':\n')
			for debt in counterparties_dict[username]:
				formatted_counterparties_message.append(debt + '\n')
			formatted_counterparties_message.append('\n')

		formatted_counterparties_message_string = ''.join(formatted_counterparties_message)
		return formatted_counterparties_message_string


	async def viewDebtors(self):
		lender_model = await sync_to_async(get_object_or_404)(UserData, username=self.user_handle)
		debtors = await sync_to_async(list)(
            Expenses.objects.filter(lender=lender_model).values('debtor__username', 'quantity', 'currency__code')
        )
		indiv_debtors_dict = self._createCounterpartyDict(debtors, findingDebtors=True)
		view_debtors_as_string = self._createFormattedMessage(indiv_debtors_dict)
		return view_debtors_as_string


	async def viewLenders(self):
		borrower_model = await sync_to_async(get_object_or_404)(UserData, username=self.user_handle)
		lenders = await sync_to_async(list)(Expenses.objects.filter(debtor=borrower_model).values('lender__username', 'quantity', 'currency__code'))
		indiv_lenders_dict = self._createCounterpartyDict(lenders, findingDebtors=False)
		view_lenders_as_string = self._createFormattedMessage(indiv_lenders_dict)
		return view_lenders_as_string

	'''
	deletes a single debt as a lender

	'''
	async def deleteSingleDebt(self, mention: str, currency_code: str):
		lenderModel = await sync_to_async(get_object_or_404)(UserData, username=self.user_handle)
		debtorModel = await sync_to_async(get_object_or_404)(UserData, username=mention)
		currencyModel = await sync_to_async(get_object_or_404)(Currencies, code=currency_code)
		await sync_to_async(Expenses.objects.filter(lender=lenderModel, debtor=debtorModel, currency=currencyModel).delete)()
		print('success')


	async def deleteDebts(self, mentionedUsers: list):
		pass


	'''
	Future features: 
	automatic conversion and collation of debts in different currencies
	delete multiple debts
	'''

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
	current_user = User(telegram_user)
	success = await current_user.createAccount()
	if not success:
		await context_bot.sendMessage(f"The user {current_user.user_handle} already has an account with EzDebts")


# ---ADD EXPENSE---
'''
adds an expense to the Expense Model in DB if user calls /addExepnse
inputs: Update, ContextType
outputs: NIL, updates the DB
'''

async def addExpense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	# expected format: <command> <mention> <quantity> <currency code>
	telegram_user = update.effective_user
	chat_id = update.effective_chat.id
	bot = context.bot
	message = update.message
	message_list = message.text.split()

	context_bot = ContextBot(bot, chat_id)
	current_user = User(telegram_user)
	mentions_checker = MentionsChecker(message)
	debt = message_list[-2 : ]

	if not mentions_checker.allValidMentions():
		await context_bot.sendMessage("An invalid user has been tagged")

	nonExistentMentions = await mentions_checker.returnNonExistentUsers()
	if nonExistentMentions:
		nonExistentMentionsString = ",".join(nonExistentMentions)
		await context_bot.sendMessage(f"The users {nonExistentMentionsString} do not have registered EzDebts accounts")
	else:
		await current_user.addDebts(mentions_checker.mentioned_users, debt)
		await context_bot.sendMessage(f"Debt has been added for {mentions_checker.mentioned_users}")
		logging.debug("Successfully added debt")

async def viewCounterparties(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	telegram_user = update.effective_user
	chat_id = update.effective_chat.id
	bot = context.bot
	message_list = update.message.text.split()

	context_bot = ContextBot(bot, chat_id)
	current_user = User(telegram_user)

	if message_list[0] == '/viewdebtors':
		view_debtors_as_string = await current_user.viewDebtors()
		return_counterparties_string = 'Your debtors: \n' + view_debtors_as_string
	else:
		view_lenders_as_string = await current_user.viewLenders()
		return_counterparties_string = 'Your lenders: \n' + view_lenders_as_string

	await context_bot.sendMessage(return_counterparties_string)

async def deleteDebt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	# User should only need to tag counterparty (or more than one) and the currency of the debt they want to delete
	# assuming that only one user is tagged
	telegram_user = update.effective_user
	chatId = update.effective_chat.id
	bot = context.bot
	message = update.message
	message_list = update.message.text.split()

	contextBot = ContextBot(bot, chatId)
	mentionsChecker = MentionsChecker(message)
	current_user = User(telegram_user)

	if not mentionsChecker.allValidMentions():
		nonExistentUsers = await mentionsChecker.returnNonExistentUsers
		await contextBot.sendMessage(f"The users {nonExistentUsers} do not have registered EzDebts accounts")

	currency = message_list[-1].upper()
	await current_user.deleteSingleDebt(mentionsChecker.mentioned_users[0], currency)

# improve experience by integrating chatgpt to talk naturally?
if __name__ == '__main__':
	application = ApplicationBuilder().token(BOT_TOKEN).build()
	
	start_handler = CommandHandler('start', start)
	echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
	callback_handler = CommandHandler('callback', callback)
	createAcc_handler = CommandHandler('register', createAccount)
	addExpense_handler = CommandHandler('addexpense', addExpense)
	viewDebtors_handler = CommandHandler('viewdebtors', viewCounterparties)
	viewLenders_handler = CommandHandler('viewlenders', viewCounterparties)
	deleteDebtHandler = CommandHandler('deletedebt', deleteDebt)
	unkown_handler = MessageHandler(filters.COMMAND, unknown)

	application.add_handler(start_handler)
	application.add_handler(echo_handler)
	application.add_handler(callback_handler)
	application.add_handler(createAcc_handler)
	application.add_handler(addExpense_handler)
	application.add_handler(viewDebtors_handler)
	application.add_handler(viewLenders_handler)
	application.add_handler(deleteDebtHandler)
	application.add_handler(unkown_handler)

	application.run_polling()