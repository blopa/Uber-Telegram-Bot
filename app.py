import sys
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardHide, KeyboardButton, ParseMode)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler)
from api import botan
from geopy.geocoders import Nominatim
import random
import urllib
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_KEY = sys.argv[1]
UBER_KEY = sys.argv[2]
BOTAN_TOKEN = sys.argv[3]
MAIN, LOCATION = range(2)
UBER_URL = "https://m.uber.com/ul/?"  # TODO use "uber://?" ?
CMDS = ["/setpickup", "/setdropoff", "/setpickanddrop", "/applycuppon"]
SCMDS = ["/start", "/about", "/help"]
CMD = {}
PICK = {}
UBER_PROMO = "uberKoehUsaMeuCodigo"


def main():
    updater = Updater(TELEGRAM_KEY)
    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.command, start)],
        states={
            MAIN: [MessageHandler(Filters.command, mainmenu)],
            LOCATION: [MessageHandler(Filters.location, getlocation)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(conv_handler)
    updater.start_polling()


def start(bot, update):
    msg = update.message.text
    if str(msg).startswith(SCMDS[0]):
        update.message.reply_text("Hello, I'm a bot that helps you order a Uber. You can {}, {}, {} or {}.".format(*CMDS))
    elif str(msg).startswith(SCMDS[1]):
        update.message.reply_text("This bot will help you setting up a pickup and/or dropoff location for Uber.\n\nDon't have Uber? Install it now: https://uber.com/invite/uberKoehUsaMeuCodigo. \n\nThis bot was made by @PabloMontenegro and it is in development, you can check the source code at https://github.com/blopa/uber-telegram-bot.\n\nPull requests are welcome.")  # TODO
    elif str(msg).startswith(SCMDS[2]):
        update.message.reply_text("I'm a bot that helps you order a Uber. Try using {}, {} or {}.".format(*CMDS))
    else:
        return mainmenu(bot, update)
    return MAIN


def mainmenu(bot, update):
    usr = update.message.from_user
    msg = update.message.text
    reply = ReplyKeyboardMarkup([[KeyboardButton(text="Current Location", request_location=True)]], one_time_keyboard=True)
    reply_msg = "Alright, send me the {}. You can either select send me the location now or simply select 'Current Location' from the menu. Or /cancel to cancel."
    if str(msg).startswith(CMDS[0]):  # /setpickup
        CMD[usr.id] = CMDS[0]
        update.message.reply_text(reply_msg.format('pickup location'), reply_markup=reply)
        return LOCATION
    elif str(msg).startswith(CMDS[1]):  # /setdropoff
        CMD[usr.id] = CMDS[1]
        update.message.reply_text(reply_msg.format('drop off location'), reply_markup=reply)
        return LOCATION
    elif str(msg).startswith(CMDS[2]):  # /setpickanddrop
        CMD[usr.id] = CMDS[2]
        update.message.reply_text(reply_msg.format('pickup location first'), reply_markup=reply)
        return LOCATION
    elif str(msg).startswith(CMDS[3]):  # /applycuppon
        params = dict(client_id=UBER_KEY, action="applyPromo")
        link = UBER_URL + "promo=" + UBER_PROMO + "&" + urllib.urlencode(params)
        update.message.reply_text('Awesome. Just click <a href="{}">HERE</a> to open the Uber app'.format(link), parse_mode=ParseMode.HTML)
        return MAIN

    if str(msg) in SCMDS:
        return start(bot, update)

    update.message.reply_text("Sorry, I didn't undestanded that. Try sending {}.".format(random.choice(CMDS)))
    return MAIN


def getlocation(bot, update):
    usr = update.message.from_user
    location = update.message.location
    if usr.id in CMD:
        geolocator = Nominatim()
        latiLong = str(location.latitude) + "," + str(location.longitude)
        try:
            loc = geolocator.reverse(latiLong).address
        except Exception:
            loc = ""
        reply_msg = "The {} location set to:\n"
        uber_msg = 'All set! Just click <a href="{}">HERE</a> to open the Uber app.'
        basic_params = dict(client_id=UBER_KEY, action="setPickup")
        if CMD[usr.id] == CMDS[0]:  # /setpickup
            link = UBER_URL + "pickup[latitude]={}&pickup[longitude]={}&".format(location.latitude, location.longitude) + urllib.urlencode(basic_params)
            update.message.reply_text(uber_msg.format(link), parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardHide())
            if loc:
                update.message.reply_text(reply_msg.format('pickup') + loc)
            try:
                botan.track(BOTAN_TOKEN, update.message.from_user.id, {0: 'set pickup'}, 'set pickup')
            except Exception as e:
                logger.exception(e)
        elif CMD[usr.id] == CMDS[1]:  # /setdropoff
            link = UBER_URL + "pickup=my_location&dropoff[latitude]={}&dropoff[longitude]={}&".format(location.latitude, location.longitude) + urllib.urlencode(basic_params)
            update.message.reply_text(uber_msg.format(link), parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardHide())
            if loc:
                update.message.reply_text(reply_msg.format('dropoff') + loc)
            try:
                botan.track(BOTAN_TOKEN, update.message.from_user.id, {0: 'set dropoff'}, 'set dropoff')
            except Exception as e:
                logger.exception(e)
        elif CMD[usr.id] == CMDS[2]:  # /setpickanddrop
            if usr.id in PICK:
                pick = PICK[usr.id].split(",")
                try:
                    loc2 = geolocator.reverse(PICK[usr.id]).address
                except Exception:
                    loc2 = ""
                del PICK[usr.id]
                link = UBER_URL + "pickup[latitude]={}&pickup[longitude]={}&dropoff[latitude]={}&dropoff[longitude]={}&".format(pick[0], pick[1], location.latitude, location.longitude) + urllib.urlencode(basic_params)
                update.message.reply_text(uber_msg.format(link), parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardHide())
                if loc and loc2:
                    update.message.reply_text(reply_msg.format('pickup') + loc2 + "\n\nAnd dropoff location set to:\n" + loc)
                try:
                    botan.track(BOTAN_TOKEN, update.message.from_user.id, {0: 'set pickup and dropoff'}, 'set pickup and dropoff')
                except Exception as e:
                    logger.exception(e)
            else:
                PICK[usr.id] = latiLong
                if loc:
                    update.message.reply_text(reply_msg.format('pickup') + loc)
                update.message.reply_text("Now send me the dropoff location or simply select 'Current Location' from the menu. Or /cancel to cancel.")
                return LOCATION
        else:
            update.message.reply_text("Something went wrong, please try again.")
    else:
        update.message.reply_text("Something went wrong, please try again.")

    return MAIN


def cancel(bot, update):
    update.message.reply_text("Ok, canceled.", reply_markup=ReplyKeyboardHide())
    return MAIN


if __name__ == '__main__':
    main()
