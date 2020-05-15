# -*- coding: utf-8 -*-
# Код шифрованя был взят из https://www.quickprogrammingtips.com/python/aes-256-encryption-and-decryption-in-python.html

import base64
from Cryptodome.Cipher import AES
from Cryptodome import Random
from Cryptodome.Protocol.KDF import PBKDF2
import random
import os
import models
import telebot
from telebot import *
import json
import requests
import string
import random

# apihelper.proxy = {
#         'https': 'socks5h://{}:{}'.format('127.0.0.1','4444')
#     }

commands = [{'command':'start', 'description':'start'}, {'command':'add', 'description':'add new block'}, {'command':'generate_password', 'description':'generate password [lenght]'}, {'command':'all', 'description':'view all you blocks'}, {'command':'help', 'description':'help'}]

folder = os.path.dirname(os.path.abspath(__file__))

cfg = json.loads(open('cfg.txt', 'r').read())

bot = telebot.TeleBot(cfg['token'])
requests.get(f'https://api.telegram.org/bot{cfg["token"]}/setMyCommands?commands={json.dumps(commands)}')

BLOCK_SIZE = 16
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]

# генерация случайного пароля
def random_password(size = 16):
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + '!$&@*-=+/\\|^:;~`[]{}%()'
    return ''.join(random.choice(chars) for x in range(size))

# создать соль
def get_salt():
    return str(random.randint(100000000000, 999999999999))

# получить хэш пароля
def get_password_hash(password, salt):
    salt = salt.encode()
    kdf = PBKDF2(password, salt, 64, 1000)
    key = kdf[:32]
    return key

# зашифровать
def encrypt(raw, password):
    private_key = password
    raw = pad(raw)
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(private_key, AES.MODE_CBC, iv)
    return bytes.decode(base64.b64encode(iv + cipher.encrypt(raw.encode())))

# расшифровать
def decrypt(enc, password):
    private_key = password
    enc = base64.b64decode(enc)
    iv = enc[:16]
    cipher = AES.new(private_key, AES.MODE_CBC, iv)
    return bytes.decode(unpad(cipher.decrypt(enc[16:])))

# добавить блок
def add_data(user, data, name, password, login=False, other=False):
    salt1 = get_salt()
    hash1 = get_password_hash(password, salt1)
    if login != False:
        login = encrypt(login, hash1)
    if other != False:
        other = encrypt(other, hash1)
    data = models.Data.create(user=user, data=encrypt(data, hash1), login=login, name=name, salt=salt1, other=other)
    data.save()
    return data

# расшифровать блок
def get_data(data, password):
    salt = data.salt
    hash = get_password_hash(password, salt)
    enc = decrypt(data.data, hash)
    if str(data.login) != str(False):
        enc1 = decrypt(data.login, hash)
    else:
        enc1 = None
    if str(data.other) != str(False):
        enc2 = decrypt(data.other, hash)
    else:
        enc2 = None
    return (enc, enc1, enc2)

def easy_encrypt(text, password, salt):
    hash = get_password_hash(password, salt)
    return encrypt(text, hash)

# добавить/обновить пользвателя
def add_user(id, username = False, firstname = False, lastname = False):
    try:
        user = models.User.get(user_id=id)
        if username:
            user.username = username or False
        if firstname:
            user.firstname = firstname or False
        if lastname:
            user.lastname = lastname or False
    except:
        user = models.User.create(user_id = id, username = username or False, firstname = firstname or False, lastname = lastname or False)
    user.save()
    return user

def return_settings(block):
    keyboard = types.InlineKeyboardMarkup()
    button_1 = types.InlineKeyboardButton(text='Удалить', callback_data=f'1')
    keyboard.add(button_1)
    button_1 = types.InlineKeyboardButton(text='Блок', callback_data=f'delete_{block.uuid}')
    button_2 = types.InlineKeyboardButton(text='Сообщение', callback_data=f'delete-message')
    keyboard.add(button_1, button_2)
    button_1 = types.InlineKeyboardButton(text='Переименовать Блок', callback_data=f'rename_{block.uuid}')
    keyboard.add(button_1)
    button_1 = types.InlineKeyboardButton(text='Изменить', callback_data=f'1')
    keyboard.add(button_1)
    button_1 = types.InlineKeyboardButton(text='Пароль', callback_data=f'reset-pass_{block.uuid}')
    button_2 = types.InlineKeyboardButton(text='Логин', callback_data=f'reset-data-login_{block.uuid}')
    keyboard.add(button_1, button_2)
    button_1 = types.InlineKeyboardButton(text='Данные', callback_data=f'reset-data-pass_{block.uuid}')
    button_2 = types.InlineKeyboardButton(text='Заметку', callback_data=f'reset-data-note_{block.uuid}')
    keyboard.add(button_1, button_2)
    button_1 = types.InlineKeyboardButton(text='Обновить', callback_data=f'update-block-msg_{block.uuid}')
    keyboard.add(button_1)
    button_1 = types.InlineKeyboardButton(text='Поделиться', switch_inline_query=f'{block.uuid}')
    keyboard.add(button_1)
    return keyboard

def return_block_text(block, data):
    return f"""Блок {block.name}
Логин: {data[1]}
Данные: {data[0]}
Заметка: {data[2]}

Удалите это сообщение по завершении."""

def return_block_text_enc(block):
    return f'Блок {block.name}\n\nДата создания: {block.creation_date}\nСоль: {block.salt}\nUUID: {block.uuid}\nЛогин: {block.login}\nДанные: {block.data}\nЗаметка: {block.other}\n\nДля расшифровки требуется пароль, чтобы расшифровать напишите @safepass_bot {block.uuid} [пароль]'

@bot.inline_handler(lambda query: query.query)
def query_text(inline_query):
    uid = inline_query.from_user.id
    user = add_user(uid)
    text = inline_query.query
    spl = text.split(' ')
    for i in range(9):
        try:
            spl[i]
        except:
            spl.append('')
    if spl[0] == 'all':
        blocks = models.Data.filter(user=user)
        if len(blocks) == 0:
            r = types.InlineQueryResultArticle(1, "У вас нет блоков!", types.InputTextMessageContent('У вас нет блоков!'))
            bot.answer_inline_query(inline_query.id, [r], cache_time=1, is_personal=True)
        else:
            r = []
            i = 1
            for block in blocks:
                r.append(types.InlineQueryResultArticle(i, block.name + ' encrypted', types.InputTextMessageContent(return_block_text_enc(block))))
                i+=1
            bot.answer_inline_query(inline_query.id, r, cache_time=1, is_personal=True)
    else:
        try:
            block = models.Data.get(uuid=spl[0])
            if block.user != user:
                r = types.InlineQueryResultArticle(1, "Блок не найден!", types.InputTextMessageContent('Блок не найден!'))
                bot.answer_inline_query(inline_query.id, [r])
            else:
                if spl[1] != '':
                    data = get_data(block, spl[1])
                    if data[0] == '':
                        r = types.InlineQueryResultArticle(1, 'Неверный пароль!', types.InputTextMessageContent('Неверный пароль!'))
                        r1 = types.InlineQueryResultArticle(2, block.name + ' encrypted', types.InputTextMessageContent(return_block_text_enc(block)))
                        bot.answer_inline_query(inline_query.id, [r, r1], is_personal=True)
                    else:
                        r = types.InlineQueryResultArticle(1, f'Блок {block.name}', types.InputTextMessageContent(return_block_text(block, data)))
                        bot.answer_inline_query(inline_query.id, [r], is_personal=True, cache_time=1)
                else:
                    r = types.InlineQueryResultArticle(1, "Введите пароль", types.InputTextMessageContent('Введите пароль'))
                    r1 = types.InlineQueryResultArticle(2, block.name + ' encrypted', types.InputTextMessageContent(return_block_text_enc(block)))
                    bot.answer_inline_query(inline_query.id, [r, r1], is_personal=True)
        except Exception as e:
            r = types.InlineQueryResultArticle(1, "Блок не найден!", types.InputTextMessageContent('Блок не найден!'))
            bot.answer_inline_query(inline_query.id, [r])

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    text = call.data
    uid = call.from_user.id
    mid = call.message.message_id
    spl = text.split('_')
    id = int(call.message.json['chat']['id'])
    for i in range(9):
        try:
            spl[i]
        except:
            spl.append('')
    if spl[0] == 'delete-message':
        bot.delete_message(id, mid)
    elif spl[0] == 'delete':
        models.Data.get(uuid=spl[1]).delete_instance()
        bot.delete_message(id, mid)
    elif spl[0] == 'rename':
        bot.send_message(id, 'Напишите новое название:')
        user = models.User.get(user_id=uid)
        user.action = text
        user.save()
    elif spl[0] == 'reset-pass':
        bot.send_message(id, 'Введите старый пароль от Блока:')
        user = models.User.get(user_id=uid)
        user.action = text
        user.save()
    elif spl[0] == 'reset-data-login':
        bot.send_message(id, 'Введите пароль от Блока:')
        user = models.User.get(user_id=uid)
        user.action = text
        user.save()
    elif spl[0] == 'reset-data-pass':
        bot.send_message(id, 'Введите пароль от Блока:')
        user = models.User.get(user_id=uid)
        user.action = text
        user.save()
    elif spl[0] == 'update-block-msg':
        bot.send_message(id, 'Введите пароль')
        user = models.User.get(user_id=uid)
        user.action = text + '_' + str(mid)
        user.save()
    elif spl[0] == 'reset-data-note':
        bot.send_message(id, 'Введите пароль')
        user = models.User.get(user_id=uid)
        user.action = text
        user.save()

@bot.message_handler(commands=['admin_recover_bd'])
def admin_recover_bd(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    if uid == int(cfg['id']):
        bot.send_document(id, open('db.db', 'rb'), caption = '#db')

@bot.message_handler(commands=['start'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    bot.send_message(id, f"""Привет {user.firstname}, я бот который будет надёжно хранить твои данные в безопасном хранилище!
● Надёжное AES-256 шифрование твоим паролем
● Пароль нигде не хранится (даже хэш), сообщение с ним удаляется
● Полностью открытый <a href="https://github.com/TheAngryPython/SecurePass-TG">исходный код</a>. Ты можешь сам убедиться в нашей честности.

Для того чтобы начать напиши /add""", disable_web_page_preview=True, parse_mode='html')

@bot.message_handler(commands=['help'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    bot.send_message(id, f"""Команды:
/start - старт
/help - помощь
/all - все блоки
/add - добавить новый блок
/generate_password [длина (16)] - генерироваь сложный пароль

https://teletype.in/@safepass/2LDYgGrKq""", parse_mode='html')

@bot.message_handler(commands=['generate_password'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    spl = text.split()
    try:
        i = int(spl[1])
        if i > 4096:
            i = 4096
        pas = random_password(i)
    except:
        pas = random_password()
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    bot.send_message(id, f"""{str(pas)}""", disable_web_page_preview=True, parse_mode='html')

@bot.message_handler(commands=['add'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    if len(models.Data.filter(user=user)) >= 50:
        bot.send_message(id, 'Вы превысили лимит в 50 блоков, для его увелечения обратитесь к @EgTer')
    else:
        user.action = 'data_name'
        user.save()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cancel = types.KeyboardButton('Остановить')
        markup.row(cancel)
        bot.send_message(id, f"""{user.firstname}, напиши название блока (не шифруется, для вашего удобства). (Помните, что во время создания блока данные хранятся в незашифрованном виде)""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)

@bot.message_handler(commands=['all'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    user.action = 'block_see'
    user.tmp = False
    user.save()
    blocks = models.Data.filter(user=user)
    if len(blocks) != 0:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for block in blocks:
            btn = types.KeyboardButton(block.name)
            markup.row(btn)
        bot.send_message(id, f"""Вот твои блоки""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
    else:
        markup = types.ReplyKeyboardRemove()
        bot.send_message(id, f"""У тебя нет блоков. Создать /add""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)

@bot.message_handler(content_types=['text'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    mid = m.message_id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    spl = user.action.split('_')
    try:
        bot.delete_message(id, mid)
        bot.delete_message(id, mid - 1)
    except:
        pass
    for i in range(9):
        try:
            spl[i]
        except:
            spl.append('')
    if text.lower() == 'Остановить'.lower() or text.lower() == 'Stop'.lower():
        user.action = False
        user.tmp = False
        user.save()
        markup = types.ReplyKeyboardRemove()
        bot.send_message(id, f"""Действие прервано""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
    elif user.action == 'data_name':
        try:
            t = True
            models.Data.get(user=user,name=text)
        except:
            t = False
            if len(text) >= 50:
                bot.send_message(id, 'Слишком длинное название!')
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                cancel = types.KeyboardButton('Остановить')
                no = types.KeyboardButton('Нет')
                markup.row(no, cancel)
                tmp = {'name': text}
                user.tmp = json.dumps(tmp)
                bot.send_message(id, f"""Хорошо, теперь отправь логин (если не требуется нажми "Нет").""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
                user.action = 'data_login'
                user.save()
        if t:
            bot.send_message(id, f"""У вас уже есть блок с таким названием.""", disable_web_page_preview=True, parse_mode='html')
    elif user.action == 'data_login':
        if len(text) >= 100:
            bot.send_message(id, 'Слишком длинный логин')
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            cancel = types.KeyboardButton('Остановить')
            markup.row(cancel)
            tmp = json.loads(user.tmp)
            if text.lower() == 'Нет'.lower() or text.lower() == 'No'.lower():
                tmp['login'] = False
            else:
                tmp['login'] = text
            user.tmp = json.dumps(tmp)
            bot.send_message(id, f"""Дальше идёт сам блок с данными (пароль, пин-код, кодовое слово).""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
            user.action = 'data_password'
            user.save()
    elif user.action == 'data_password':
        if len(text) >= 3000:
            bot.send_message(id, 'Слишком длинный текст')
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            cancel = types.KeyboardButton('Остановить')
            no = types.KeyboardButton('Нет')
            markup.row(no, cancel)
            tmp = json.loads(user.tmp)
            tmp['password'] = text
            user.tmp = json.dumps(tmp)
            bot.send_message(id, f"""Напишите заметку к блоку""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
            user.action = 'data_other'
            user.save()
    elif user.action == 'data_other':
        if len(text) >= 800:
            bot.send_message(id, 'Слишком длинный текст')
        else:
            tmp = json.loads(user.tmp)
            if text.lower() == 'Нет'.lower() or text.lower() == 'No'.lower():
                tmp['other'] = False
            else:
                tmp['other'] = text
            user.tmp = json.dumps(tmp)
            bot.send_message(id, f"""Теперь нужен ключ для шифрования всех этих данных.""", disable_web_page_preview=True, parse_mode='html')
            user.action = 'data_key'
            user.save()
    elif user.action == 'data_key':
        tmp = json.loads(user.tmp)
        add_data(user, tmp['password'], tmp['name'], text, login=tmp['login'], other=tmp['other'])
        bot.send_message(id, f"""Блок создан!

Просмореть все блоки: /all""", disable_web_page_preview=True, parse_mode='html')
        user.action = False
        user.save()
    elif user.action == 'block_see':
        try:
            models.Data.get(user=user,name=text)
            user.action = 'block_open'
            user.tmp = text
            user.save()
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            cancel = types.KeyboardButton('Остановить')
            markup.row(cancel)
            bot.send_message(id, f"""Введи пароль от блока""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
        except:
            bot.send_message(id, f"""Такого блока не существует""", disable_web_page_preview=True, parse_mode='html')
    elif user.action == 'block_open':
        try:
            block = models.Data.get(user=user,name=user.tmp)
            data = get_data(block, text)
            if not data[0]:
                markup = types.ReplyKeyboardRemove()
                bot.send_message(id, f"""Неправильный пароль от блока {block.name}""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
            else:
                user.action = False
                user.save()
                bot.send_message(id, return_block_text(block, data), disable_web_page_preview=True, parse_mode='html', reply_markup=return_settings(block))
        except:
            markup = types.ReplyKeyboardRemove()
            bot.send_message(id, f"""Блок не найден!""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
    elif spl[0] == 'rename':
        try:
            models.Data.get(name=text)
            bot.send_message(id, 'Блок с таким названием уже есть!')
        except:
            if len(text) >= 50:
                bot.send_message(id, 'Слишком длинное название!')
            else:
                user.action = False
                user.save()
                block = models.Data.get(uuid=spl[1])
                block.name = text
                block.save()
                bot.send_message(id, 'Успешно!')
    elif spl[0] == 'reset-pass':
        block = models.Data.get(uuid=spl[1])
        if get_data(block, text)[0] == '':
            bot.send_message(id, 'Неверный пароль!')
        else:
            user.tmp = text
            user.action = 'reset-pass-done_'+spl[1]
            user.save()
            bot.send_message(id, 'Введите новый пароль:')
    elif spl[0] == 'reset-pass-done':
        block = models.Data.get(uuid=spl[1])
        data = get_data(block, user.tmp)
        block.salt = get_salt()
        block.data = easy_encrypt(data[0], text, block.salt)
        block.login = easy_encrypt(str(data[1]), text, block.salt)
        block.save()
        user.tmp = False
        user.action = False
        user.save()
        bot.send_message(id, 'Пароль изменён!')
    elif spl[0] == 'reset-data-login':
        block = models.Data.get(uuid=spl[1])
        if get_data(block, text)[0] == '':
            bot.send_message(id, 'Неверный пароль!')
        else:
            user.tmp = text
            user.action = 'reset-data-login-done_'+spl[1]
            user.save()
            bot.send_message(id, 'Введите новый логин:')
    elif spl[0] == 'reset-data-login-done':
        block = models.Data.get(uuid=spl[1])
        block.login = easy_encrypt(text, user.tmp, block.salt)
        block.save()
        user.tmp = False
        user.action = False
        user.save()
        bot.send_message(id, 'Успешно!')
    elif spl[0] == 'reset-data-pass':
        block = models.Data.get(uuid=spl[1])
        if get_data(block, text)[0] == '':
            bot.send_message(id, 'Неверный пароль!')
        else:
            user.tmp = text
            user.action = 'reset-data-pass-done_'+spl[1]
            user.save()
            bot.send_message(id, 'Введите новые данные:')
    elif spl[0] == 'reset-data-pass-done':
        block = models.Data.get(uuid=spl[1])
        block.data = easy_encrypt(text, user.tmp, block.salt)
        block.save()
        user.tmp = False
        user.action = False
        user.save()
        bot.send_message(id, 'Успешно!')
    elif spl[0] == 'reset-data-note':
        block = models.Data.get(uuid=spl[1])
        if get_data(block, text)[0] == '':
            bot.send_message(id, 'Неверный пароль!')
        else:
            user.tmp = text
            user.action = 'reset-data-note-done_'+spl[1]
            user.save()
            bot.send_message(id, 'Введите новые данные:')
    elif spl[0] == 'reset-data-note-done':
        if len(text) >= 800:
            bot.send_message(id, 'Слишком длинная заметка')
        else:
            block = models.Data.get(uuid=spl[1])
            block.other = easy_encrypt(text, user.tmp, block.salt)
            block.save()
            user.tmp = False
            user.action = False
            user.save()
            bot.send_message(id, 'Успешно!')
    elif spl[0] == 'update-block-msg':
        block = models.Data.get(uuid=spl[1])
        data = get_data(block, text)
        if data[0] == '':
            bot.send_message(id, 'Неверный пароль!')
        else:
            user.action = False
            user.save()
            try:
                bot.edit_message_text(chat_id=id, message_id=int(spl[2]), text = return_block_text(block, data), disable_web_page_preview=True, parse_mode='html', reply_markup=return_settings(block))
            except:
                pass

bot.polling(none_stop=True, timeout=123)
