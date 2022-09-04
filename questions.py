import re
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__file__)


def get_questions():
    n = 0
    questions = {}
    for filename in os.listdir('QA'):
        path = os.path.join('QA', filename)
        if not os.path.isfile(path):
            continue
        with open(path, encoding='KOI8-R') as file:
            text = file.read()
    
        blocks = text.split('\n\n')
        for block in blocks:
            block = block.lstrip()
            if block.startswith('Вопрос'):
                n += 1
                question = '\n'.join(block.split('\n')[1:])
            if block.startswith('Ответ'):
                answer = '\n'.join(block.split('\n')[1:])
                questions[n] = {'q': question, 'a': answer}
    
    return questions

def is_answer_correct(correct_answer, user_answer):
    # Проверка: ответ юзера соответствует одному из фрагментов из заглавных букв в правильном ответе
    if user_answer.upper() in re.findall(r'[A-ZА-Я]{3,}', correct_answer):
        return True
    if user_answer.lower() == correct_answer.split('.')[0].strip().lower():
        return True
    if user_answer.lower() == correct_answer.split('(')[0].strip().lower():
        return True
    if correct_answer.lower().startswith(user_answer.lower()) and len(user_answer) > 2:
        return True
    return False