import logging
import os
import redis
import sys

from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters, 
    ConversationHandler,
)
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from random import choice
from enum import Enum
from dataclasses import dataclass
from functools import partial

from questions import get_questions, is_answer_correct

logger = logging.getLogger(__file__)


@dataclass
class BotContext:
    questions: dict
    storage: redis.Redis
    default_markup: ReplyKeyboardMarkup
    giveup_markup: ReplyKeyboardMarkup
    

class State(Enum):
    NEW_QUESTION = 0
    ANSWER = 1


def start(bot, update, bot_context):
    """Send a message when the command /start is issued."""
    update.message.reply_text(
        'Привет! Начинаем викторину! Нажми «Новый вопрос»', 
        reply_markup=bot_context.default_markup 
    )
    return State.NEW_QUESTION


def cancel(bot, update):
    update.message.reply_text('Приходите еще!',
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def handle_new_question_request(bot, update, bot_context):  
    question = choice(list(bot_context.questions))
    bot_context.storage.set(update.message.chat_id, question)
    bot.send_message(
        update.message.chat_id,
        text=question, 
        reply_markup=bot_context.giveup_markup,
    )

    return State.ANSWER


def handle_solution_attempt(bot, update, bot_context):
    prev_question = bot_context.storage.get(update.message.chat_id).decode()
    if is_answer_correct(bot_context.questions[prev_question], update.message.text):
        bot.send_message(
            update.message.chat_id, 
            text='Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»', 
            reply_markup=bot_context.default_markup,
        )
        bot_context.storage.delete(update.message.chat_id)
        return State.NEW_QUESTION

    bot.send_message(
        update.message.chat_id, 
        text='Неправильно… Попробуешь ещё раз?',
        reply_markup=bot_context.giveup_markup,
    )
    return State.ANSWER


def handle_give_up(bot, update, bot_context):
    prev_question = bot_context.storage.get(update.message.chat_id).decode()
    bot.send_message(
            update.message.chat_id, 
            text=f'Правильный ответ: {bot_context.questions[prev_question]}',
        )
    return handle_new_question_request(bot, update, bot_context)
    
def handle_arbitrary_message(bot, update, bot_context):
    bot.send_message(
            update.message.chat_id, 
            text='Нажми «Новый вопрос»', 
            reply_markup=bot_context.default_markup,
        )
    return State.NEW_QUESTION


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

    if len(sys.argv) > 1:
        questions = get_questions(sys.argv[1])
    else:
        questions = get_questions()
    if not questions:
        logger.error('Questions not found')
        return
    
    # Open Redis DB connection
    pool = redis.ConnectionPool.from_url(os.environ['REDIS_URL'])
    storage = redis.Redis(connection_pool=pool)

    keyboard = [
        ['Новый вопрос'], 
        ['Завершить'],
    ]
    
    giveup_keyboard = [
        ['Новый вопрос'], 
        ['Завершить', 'Сдаться'],
    ]
    
    bot_context = BotContext(
        questions=questions, 
        storage=storage, 
        default_markup=ReplyKeyboardMarkup(keyboard), 
        giveup_markup=ReplyKeyboardMarkup(giveup_keyboard),
    )

    """Start the bot."""
    try:
        updater = Updater(os.environ['TG_BOT_TOKEN'])
        dp = updater.dispatcher
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', partial(start, bot_context=bot_context))],
            states={
                State.NEW_QUESTION: [
                    MessageHandler(Filters.regex('Новый вопрос'), partial(handle_new_question_request, bot_context=bot_context)),
                    MessageHandler(
                        Filters.text & (~Filters.command) & (~Filters.regex('Завершить')), 
                        partial(handle_arbitrary_message, bot_context=bot_context),
                    ),
                ],
    
                State.ANSWER: [
                    MessageHandler(Filters.regex('Сдаться'), partial(handle_give_up, bot_context=bot_context)),
                    MessageHandler(
                        Filters.text & (~Filters.command) & (~Filters.regex('Завершить')), 
                        partial(handle_solution_attempt, bot_context=bot_context),
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
    main()
