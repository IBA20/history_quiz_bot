import logging
import os
import redis

from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters, 
    RegexHandler, 
    ConversationHandler,
)
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from random import randint
from enum import Enum

from questions import get_questions, is_answer_correct

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__file__)


class State(Enum):
    NEW_QUESTION = 0
    ANSWER = 1


def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text(
        'Привет! Начинаем викторину! Нажми «Новый вопрос»', 
        reply_markup=default_markup 
    )
    return State.NEW_QUESTION


def cancel(bot, update):
    update.message.reply_text('Приходите еще!',
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def handle_new_question_request(bot, update):
    n = randint(1, len(questions))
    question = questions[n]['q']
    storage.set(update.message.chat_id, n)
    bot.send_message(
        update.message.chat_id,
        text=question, 
        reply_markup=giveup_markup,
    )

    return State.ANSWER


def handle_solution_attempt(bot, update):
    prev_question_id = int(storage.get(update.message.chat_id).decode())
    if is_answer_correct(questions[prev_question_id]['a'], update.message.text):
        bot.send_message(
            update.message.chat_id, 
            text='Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»', 
            reply_markup=default_markup ,
        )
        storage.delete(update.message.chat_id)
        return State.NEW_QUESTION

    bot.send_message(
        update.message.chat_id, 
        text='Неправильно… Попробуешь ещё раз?',
        reply_markup=giveup_markup,
    )
    return State.ANSWER


def handle_give_up(bot, update):
    prev_question_id = int(storage.get(update.message.chat_id).decode())
    bot.send_message(
            update.message.chat_id, 
            text=f'Правильный ответ: {questions[prev_question_id]["a"]}',
        )
    return handle_new_question_request(bot, update)
    
def handle_arbitrary_message(bot, update):
    bot.send_message(
            update.message.chat_id, 
            text='Нажми «Новый вопрос»', 
            reply_markup=default_markup,
        )
    return State.NEW_QUESTION


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    """Start the bot."""
    try:
        updater = Updater(os.environ['TG_BOT_TOKEN'])
        dp = updater.dispatcher
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                State.NEW_QUESTION: [
                    MessageHandler(Filters.regex('Новый вопрос'), handle_new_question_request),
                    MessageHandler(
                        Filters.text & (~Filters.command) & (~Filters.regex('Завершить')), 
                        handle_arbitrary_message,
                    ),
                ],
    
                State.ANSWER: [
                    MessageHandler(Filters.regex('Сдаться'), handle_give_up),
                    MessageHandler(
                        Filters.text & (~Filters.command) & (~Filters.regex('Завершить')), 
                        handle_solution_attempt,
                    )
                ],
            },
    
            fallbacks=[MessageHandler(Filters.regex('Завершить'), cancel)]
        )
    
        dp.add_handler(conv_handler)
        dp.add_error_handler(error)
    
        updater.start_polling()
        updater.idle()
    except Exception:
        logger.exception('Exception:')


if __name__ == '__main__':
    questions = get_questions()
    
    # Open Redis DB connection
    pool = redis.ConnectionPool.from_url(os.environ['REDIS_URL'])
    storage = redis.Redis(connection_pool=pool)

    keyboard = [
        ['Новый вопрос'], 
        ['Завершить'],
    ]
    default_markup = ReplyKeyboardMarkup(keyboard)

    giveup_keyboard = [
        ['Новый вопрос'], 
        ['Завершить', 'Сдаться'],
    ]
    giveup_markup = ReplyKeyboardMarkup(giveup_keyboard)
    
    main()