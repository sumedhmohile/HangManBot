import sys
import time
import telepot
import MySQLdb
import random
from pprint import pprint


#Open database connection (replace as needed)
db = MySQLdb.connect(address, user, password, dbname)

# prepare a cursor object using cursor() method
cursor = db.cursor()


def generateWord():
	#generate random word
	word_file = "/usr/share/dict/words"
	words = open(word_file).read().splitlines()
	word = words[random.randrange(0, len(words))]

	return word


def startGame(chat_id):
	"""Starts a new game session for a user"""

	word = generateWord()
	soFar = ''.join(['_' for i in range(len(word))])
	query = "INSERT INTO game(messageID, word, soFar, state, done) VALUES(%s, %s, %s, %s, %s)"
	try:
		cursor.execute(query, (str(chat_id), word, soFar, 0, ""))
		db.commit()
		bot.sendMessage(chat_id, "Game Started!")
		bot.sendMessage(chat_id, soFar)
	except Exception, e:
		if "Duplicate entry" in e[1]:
			#Game already in session
			bot.sendMessage(chat_id, "Game alread in session")
		else:
			bot.sendMessage(chat_id, "Error")							
		db.rollback()


def endGame(chat_id, loud = True):
	"""Ends players current game session"""

	query = "DELETE FROM game WHERE messageID = \'" + str(chat_id) + "\'"
	try:
		cursor.execute(query)
		db.commit()
		if loud:
			bot.sendMessage(chat_id, "Game ended")
	except:
		bot.sendMessage(chat_id, "Error")							
		db.rollback()


def validateGuess(guess):
	"""Performs validation of the message sent by the player"""

	if len(guess) > 1:
		return "Single letter guesses only"
	elif len(guess) < 1:
		return "Invalid guess"
	elif not guess.isalpha():
		return "Letters only"
	return "valid"


def checkGuess(chat_id, guess):
	"""Checks for player's guess"""

	query = "SELECT * FROM game WHERE messageID = \'" + str(chat_id) + "\'"
	try:
		cursor.execute(query)
		db.commit()

		result = cursor.fetchall()[0]
		word = result[2]
		soFar = result[3]
		done = result[4]
		state = result[5]		

		if guess in word and not guess in soFar:
			#new letter guessed correctly
			soFarList = list(soFar)
			for i in range(len(word)):
				if word[i] == guess:
					soFarList[i] = guess

			#check for win
			if ''.join(soFarList) == word:
				return(True, word, True)			

			try:
				cursor.execute("UPDATE game SET soFar = %s WHERE messageID = %s",(''.join(soFarList), str(chat_id)))
				db.commit()
				return (True, ''.join(soFarList))

			except:
				print "Error1"
				db.rollback()
				return (False, "Error")

		else:
			#wrong guess

			#check for loss
			if int(state) >= 6:
				return(False, word, False)

			if not guess in done:
				#new wrong guess
				try: 
					query = "UPDATE game SET state = state + 1, done = %s WHERE messageID = %s"
					cursor.execute(query, (done + guess, str(chat_id)))
					db.commit()
					showScore(chat_id)
					return (False, soFar)
				except Exception, e:
					print e
					db.rollback()
					return (False, "Error")
			else:
				#already attempted guess
				return(False, soFar)

	except Exception, e:
		print e
		db.rollback()
		return (False, "Error")


def showScore(chat_id):
	"""Displays the player's current score"""

	query = "SELECT state FROM game WHERE messageID = \'" + str(chat_id) + "\'"

	try:
		cursor.execute(query)
		db.commit()
		bot.sendMessage(chat_id, "You have " + str(6 - cursor.fetchall()[0][0]) + " chances remaining")
	except:
		bot.sendMessage(chat_id, "Error")


def handle(msg):
	content_type, chat_type, chat_id = telepot.glance(msg)

	if 'entities' in msg:
		#command
		if 'type' in msg['entities'][0]:
			if msg['entities'][0]['type'] == 'bot_command':
				#message is a command
				if msg['text'] == '/start':				
					#start new game
					startGame(chat_id)

				elif msg['text'] == '/end':
					#end current game
					endGame(chat_id)

				elif msg['text'] == '/score':
					#show score
					showScore(chat_id)

	else:
		#message is not a command
		if 'type' in msg['chat']:
			if msg['chat']['type'] == "private":
				#message from single player:
				validationMessage = validateGuess(str(msg['text']))
				if validationMessage == "valid":
					#valid guess
					guessResult = checkGuess(chat_id, msg['text'])
					if guessResult[0]:
						#guessed letter is present

						#check for win
						if len(guessResult) > 2:
							bot.sendMessage(chat_id, "You win! Word was " + guessResult[1])
							endGame(chat_id, False)
						else:
							bot.sendMessage(chat_id, guessResult[1])
					else:
						#guessed letter not present

						#check for loss
						if len(guessResult) > 2:
							bot.sendMessage(chat_id, "You lose. You Word was " + guessResult[1])
							endGame(chat_id, False)
						else:
							bot.sendMessage(chat_id, guessResult[1])
				else:
					#invlalid guess
					bot.sendMessage(chat_id, validationMessage)

TOKEN = "<Your token here>"
bot = telepot.Bot(TOKEN)
bot.message_loop(handle)
print ('Running')

# Keep the program running.
while 1:
    time.sleep(10)