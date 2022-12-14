import re
import os
import logging

logger = logging.getLogger(__file__)


def get_questions(qa_dir=None):
    questions = {}
    if qa_dir:
        for filename in os.listdir(qa_dir):
            path = os.path.join(qa_dir, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding='KOI8-R') as file:
                text = file.read()
        
            blocks = text.split('\n\n')
            for block in blocks:
                block = block.lstrip()
                if block.startswith('Вопрос'):
                    question = '\n'.join(block.split('\n')[1:])
                if block.startswith('Ответ'):
                    answer = '\n'.join(block.split('\n')[1:])
                    questions[question] = answer
    
    return questions

def is_answer_correct(correct_answer, user_answer):
    return any(
        # Проверка: ответ юзера соответствует одному из фрагментов из заглавных букв в правильном ответе
        user_answer.upper() in re.findall(r'[A-ZА-Я]{3,}', correct_answer),
        # Проверка: ответ юзера соответствует части правильного ответа до точки
        user_answer.lower() == correct_answer.split('.')[0].strip().lower(),
        # Проверка: ответ юзера соответствует части правильного ответа до скобки
        user_answer.lower() == correct_answer.split('(')[0].strip().lower(),
        # Проверка: ответ юзера соответствует началу  ответа до точки
        correct_answer.lower().startswith(user_answer.lower()) and len(user_answer) > 2,
    )
