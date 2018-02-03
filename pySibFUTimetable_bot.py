#!/usr/bin/python3
import constants
import telebot
import SibFUTimetableParser as tt
import dbworker
import datetime
import os

bot = telebot.TeleBot(constants.TOKEN)
groups = tt.read(constants.GROUPS_FILENAME)


current_process_pid = os.getpid()
with open(constants.PID_FILENAME, 'w') as pid:
    pid.write(str(current_process_pid))


# START
@bot.message_handler(commands=['start'],
                     func=lambda message: dbworker.get_current_state(
                             message.from_user.id) == constants.States.START.value)
def handler_start(message):
    # keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
    # keyboard.row('/group')

    dbworker.insert_or_update(message.from_user.id, message.from_user.first_name, "")
    bot.send_message(message.from_user.id, constants.START_MESSAGE)  # (, reply_markup=keyboard)


# HELP
@bot.message_handler(commands=['help'])
def handler_group(message):
    bot.send_message(message.from_user.id, constants.HELP_MESSAGE)


# RESET
@bot.message_handler(commands=['reset'], func=lambda message: dbworker.get_current_state(
                             message.from_user.id) > constants.States.START.value)
def handler_reset(message):
    keyboard = telebot.types.ReplyKeyboardRemove
    dbworker.set_state(message.from_user.id, constants.States.START.value)
    dbworker.insert_or_update(message.from_user.id, message.from_user.first_name, '')
    bot.send_message(message.from_user.id, 'Сброс сделан. Теперь я тебя не знаю ^_^', reply_markup=keyboard)


# GROUP
@bot.message_handler(commands=['group'])
def handler_add_group(message):
    bot.send_message(message.from_user.id, "Введи группу:")
    dbworker.set_state(message.from_user.id, constants.States.CHOICE_GROUP.value)


@bot.message_handler(content_types=['text'],
                     func=lambda message: dbworker.get_current_state(
                             message.from_user.id) == constants.States.CHOICE_GROUP.value)
def handler_choice_group(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
    dbworker.insert_or_update(message.from_user.id, message.from_user.first_name, message.text)

    guess = []
    choisen_group = message.text  # здесь введенная группа
    keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
    for i in groups:
        if choisen_group.upper() in i[0].upper() and len(choisen_group) >= 3:
            tmp = i[0]
            try:
                tmp += ' ' + i[1]
            except IndexError:
                pass
            guess.append(i)
    if not guess:
        bot.send_message(message.from_user.id, "Не смог найти такую группу. Попробуй еще раз")
        return

    for i in guess:
        tmp = i[0]
        try:
            tmp += ' ' + i[1]
        except IndexError:
            pass
        keyboard.add(telebot.types.KeyboardButton(tmp))
    bot.send_message(message.from_user.id, constants.CHOICE_GROUP_MESSAGE, reply_markup=keyboard)
    dbworker.set_state(message.from_user.id, constants.States.ACCEPT_GROUP.value)


@bot.message_handler(content_types=['text'],
                     func=lambda message: dbworker.get_current_state(
                             message.from_user.id) == constants.States.ACCEPT_GROUP.value)
def accept_group(message):
    dbworker.insert_or_update(message.from_user.id, message.from_user.first_name, message.text)
    dbworker.set_state(message.from_user.id, constants.States.MAIN_MENU.value)
    keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
    bot.send_message(message.from_user.id, 'Успех!')
    main_menu(message)


# MAIN_MENU
@bot.message_handler(content_types=['text'],
                     func=lambda message: dbworker.get_current_state(message.from_user.id) == constants.States.MAIN_MENU.value)
def main_menu(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
    keyboard.row('На сегодня', 'На завтра', 'На неделю')
    keyboard.row('Настройки')
    bot.send_message(message.from_user.id, "Make your choice:", reply_markup=keyboard)

    dbworker.set_state(message.from_user.id, constants.States.COMMANDS_HANDLE.value)


@bot.message_handler(content_types=['text'],
                     func=lambda message: dbworker.get_current_state(message.from_user.id) == constants.States.COMMANDS_HANDLE.value)
def commands_handler(message):
    guess = []
    keyboard = telebot.types.ReplyKeyboardMarkup(True, True)

    if message.text == 'На сегодня':
        send_timetable(message, dbworker.get_element('`group`', message.from_user.id))
    elif message.text == 'На завтра':
        send_timetable(message,
                       dbworker.get_element('`group`', message.from_user.id),
                       day=datetime.datetime.today().weekday() + 1)
    elif message.text == 'На неделю':
        send_timetable(message,
                       dbworker.get_element('`group`', message.from_user.id),
                       foraweek=True)
    elif message.text == 'Настройки':
        keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
        keyboard.row('1 час', '30 минут', '15 минут')
        keyboard.row('Не присылать')
        bot.send_message(message.from_user.id, 'За какое время до начало первой ленты присылать расписание?',
                         reply_markup=keyboard)
        dbworker.set_state(message.from_user.id, constants.States.SETTINGS.value)
    else:
        for i in groups:
            if message.text.upper() in i[0].upper() and len(message.text) >= 3:
                tmp = i[0]
                try:
                    tmp += ' ' + i[1]
                except IndexError:
                    pass
                guess.append(i)
        if not guess:
            bot.send_message(message.from_user.id, "Не смог разобрать команду ;(")
            main_menu(message)
            return
        for i in guess:
            tmp = i[0]
            try:
                tmp += ' ' + i[1]
            except IndexError:
                pass
            keyboard.add(telebot.types.KeyboardButton(tmp))
        if len(guess) > 1:
            bot.send_message(message.from_user.id, "Какая именно?", reply_markup=keyboard)
            dbworker.set_state(message.from_user.id, constants.States.SEND_TIMETABLE.value)
        else:
            send_timetable(message, message.text)


@bot.message_handler(content_types=['text'],
                     func = lambda message: dbworker.get_current_state(message.from_user.id) == constants.States.SEND_TIMETABLE.value)
def send_timetable(message, group, foraweek=False, day=datetime.datetime.today().weekday()):
    foraweek = 6 if foraweek else 1
    msg = ''
    for i in range(foraweek):
        if foraweek == 6:
            day = i

        raw_timetable = tt.get_raw_day(group, day=day)
        if raw_timetable is None:
            msg += '<i>' + constants.DAYS_WEEK[day] + ' ' + str(datetime.datetime.today().date()) + '</i>\n'
            msg += 'Выходной\n\n'
            continue
        msg_to_user = '<i>' + constants.DAYS_WEEK[day] + ' ' + str(datetime.datetime.today().date()) + '</i>\n'
        for lesson in raw_timetable:
            for j, val in enumerate(lesson):
                if j == 0:
                    msg_to_user += '<b>' + val + '</b> '
                else:
                    msg_to_user += val + '\n'
            msg_to_user += '\n'
        msg += msg_to_user + '\n\n'

    bot.send_message(message.from_user.id, msg, parse_mode='HTML')
    dbworker.set_state(message.from_user.id, constants.States.MAIN_MENU.value)
    main_menu(message)


@bot.message_handler(content_types=['text'],
                     func=lambda message: dbworker.get_current_state(message.from_user.id) == constants.States.SETTINGS.value)
def settings(message):
    if message.text == '1 час':
        dbworker.set_time(message.from_user.id, 60)
    elif message.text == '30 минут':
        dbworker.set_time(message.from_user.id, 30)
    elif message.text == '15 минут':
        dbworker.set_time(message.from_user.id, 15)
    elif message.text == 'Не присылать':
        dbworker.set_time(message.from_user.id, -1)
    else:
        bot.send_message(message.from_user.id, 'Что-то непонятное. Я оставил все, как было.')
    dbworker.set_state(message.from_user.id, constants.States.MAIN_MENU.value)
    main_menu(message)


# bot.set_update_listener(commands_handler)
bot.polling(none_stop=True, interval=0)


