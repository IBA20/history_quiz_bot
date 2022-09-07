import os
import logging
import vk_api as vk
import redis
from random import choice
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from argparse import ArgumentParser

from questions import get_questions, is_answer_correct


# Enable logging
logger = logging.getLogger(__file__)


def handle_new_question_request(event, vk_api, questions, storage, keyboard):
    question = choice(list(questions))
    storage.set(event.user_id, question)
    
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard()
    )

def handle_user_message(event, vk_api, questions, storage, keyboard):
    prev_question = storage.get(event.user_id)
    if prev_question:
        prev_question = prev_question.decode()
    if event.text == 'Новый вопрос':
        handle_new_question_request(event, vk_api, questions, storage, keyboard)
    elif event.text == 'Сдаться' and prev_question:
        vk_api.messages.send(
            user_id=event.user_id,
            message=f'Правильный ответ: {questions[prev_question]}',
            random_id=get_random_id(),
        )
        handle_new_question_request(event, vk_api, questions, storage, keyboard)
    elif event.text == 'Завершить':
        vk_api.messages.send(
            user_id=event.user_id,
            message='Приходите еще',
            random_id=get_random_id(),
            keyboard=keyboard.get_empty_keyboard(),
        )
        storage.delete(event.user_id)
    else:
        if prev_question:
            if is_answer_correct(questions[prev_question], event.text):
                vk_api.messages.send(
                    user_id=event.user_id,
                    message='Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»',
                    random_id=get_random_id(),
                    keyboard=keyboard.get_keyboard(),
                )
                storage.delete(event.user_id)
            else:
                vk_api.messages.send(
                    user_id=event.user_id,
                    message='Неправильно… Попробуешь ещё раз?',
                    random_id=get_random_id(),
                    keyboard=keyboard.get_keyboard(),
                )
        else:
            vk_api.messages.send(
                    user_id=event.user_id,
                    message='Нажми «Новый вопрос»',
                    random_id=get_random_id(),
                    keyboard=keyboard.get_keyboard(),
                )


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
    
    argparse = ArgumentParser()
    argparse.add_argument('--qa_dir', default=os.getenv('QA_DIR', 'QA'))
    args = argparse.parse_args()
    if not os.path.isdir(args.qa_dir):
        logging.error('Q&A dir not found')
        exit()
        
    questions = get_questions(args.qa_dir)
    if not questions:
        logger.error('Questions not found')
        exit()
        
    pool = redis.ConnectionPool.from_url(os.environ['REDIS_URL'])
    storage = redis.Redis(connection_pool=pool)
    
    try:
        logger.info('History Quiz bot started')        
        vk_session = vk.VkApi(token=os.environ['VK_TOKEN'])
        vk_api = vk_session.get_api()

        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Новый вопрос', color=VkKeyboardColor.POSITIVE)    
        keyboard.add_line()
        keyboard.add_button('Завершить', color=VkKeyboardColor.NEGATIVE)   
        keyboard.add_button('Сдаться', color=VkKeyboardColor.PRIMARY)
        
        longpoll = VkLongPoll(vk_session)
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                handle_user_message(event, vk_api, questions, storage, keyboard)
    except Exception:
        logger.exception('Exception:')

if __name__ == "__main__":
    main()
    