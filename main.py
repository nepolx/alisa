from flask import Flask, request
import logging
import json
from googletrans import Translator
from a import searching_recipe_name, random_meal, searching_recipe_product, searching_by_id, searching_recipe_area
from app import get_cor, get_shops, YandexImages
import requests

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

buttons = ['Таймер', 'Поиск рецептов', 'Ближайший магазин', 'Пока']
btn_recipes = ['По названию', 'По ингридиенту', 'По области', 'Любое блюдо', 'Другое']
btn_recipes_1 = ['video', 'Режим готовки', 'Хочу еще спросить!', 'Пока']
user_id = 0
sessionStorage = {}  # для каждого юзера своя инфа
# dict_for_srp = {}  # ключ - продукт, значение: список из списка id блюд и номер, которое нужно показать

yandex = YandexImages()
yandex.set_auth_token(token='y0_AgAAAABDXC3pAAT7owAAAADdHZRtE0yZizUfTESzM4BFRe8lhS52uFA')
yandex.skills = 'dd9896e2-415e-493c-8dd2-dda4d5e6dac9'

url = 'https://www.themealdb.com/api/json/v1/1/list.php?a=list'
areas = []
response = requests.request("GET", url)
json_response = response.json()
for el in json_response['meals']:
    areas.append(el['strArea'])


def list_areas(area):
    translator = Translator()
    area = translator.translate(area, dest='en').text
    if area in areas:
        return True
    return False


@app.route('/post', methods=['POST'])
def main():
    logging.info(f'Request: {request.json!r}')
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info(f'Response: {response!r}')
    return json.dumps(response)


def handle_dialog(res, req):
    global user_id
    user_id = req['session']['user_id']

    # если пользователь новый, то просим его представиться.
    if req['session']['new']:
        res['response']['text'] = 'Привет! Давай знакомиться. Как тебя зовут?'
        # создаем словарь в который в будущем положим имя пользователя
        sessionStorage[user_id] = {
            'first_name': None
        }
        sessionStorage[user_id]["status"] = 0
        sessionStorage[user_id]["dict_for_srp"] = {}
        sessionStorage[user_id]["dict_for_sra"] = {}
        sessionStorage[user_id]["cooking_mode"] = {}

        return

    # если пользователь не новый, то попадаем сюда.
    # если поле имени пустое, то это говорит о том,
    # что пользователь еще не представился.
    if sessionStorage[user_id]['first_name'] is None:
        # в последнем его сообщение ищем имя.
        first_name = get_first_name(req)
        # если не нашли, то сообщаем пользователю что не расслышали.
        if first_name is None:
            res['response']['text'] = \
                'Не расслышала имя. Повтори, пожалуйста!'
        # если нашли, то приветствуем пользователя.
        # И спрашиваем какой город он хочет увидеть.
        else:
            sessionStorage[user_id]['first_name'] = first_name.lower().capitalize()
            res['response'][
                'text'] = 'Приятно познакомиться, ' \
                          + first_name.title() \
                          + '. Я - Алиса. Чем я могу тебе помочь?'
            # получаем варианты buttons из ключей нашего словаря cities
            res['response']['buttons'] = [
                {
                    'title': el,
                    'hide': True
                } for el in buttons
            ]
    # если мы знакомы с пользователем и он нам что-то написал,
    # то это говорит о том, что он уже говорит о городе,
    # что хочет увидеть.
    else:
        if not sessionStorage[user_id]["status"] or sessionStorage[user_id]["status"] == 'error':
            get_answer(req, res)
        elif sessionStorage[user_id]["status"] == 'recipes':
            recipes(req, res)
        elif 'search_recipe' in sessionStorage[user_id]["status"]:
            search_recipe(req, res)
        elif sessionStorage[user_id]["status"] == 'choice':
            after_answer(req, res)
        elif sessionStorage[user_id]["status"] == 'random_recipe':
            random_recipe(req, res)
        elif sessionStorage[user_id]["status"] == 'shops' or sessionStorage[user_id]["status"] == 'get_address':
            near_market(req, res)
        elif sessionStorage[user_id]["status"] == 'cooking_mode':
            cooking_mode(req, res)

        # # если этот город среди известных нам,
        # # то показываем его (выбираем одну из двух картинок случайно)
        # if city in cities:
        #     res['response']['card'] = {}
        #     res['response']['card']['type'] = 'BigImage'
        #     res['response']['card']['title'] = 'Этот город я знаю.'
        #     res['response']['card']['image_id'] = random.choice(cities[city])
        #     res['response']['text'] = 'Я угадал!'


def get_recipe_for_mode(recipe):
    res = []
    for el in recipe:
        el = list(map(lambda x: x + '.' if x[-1] != '.' else x + '', el.split('. ')))
        for x in el:
            res.append(x)
    return res


def cooking_mode(req, res):
    for el in req['request']['nlu']['tokens']:
        print(el)
        if 'не' in el or 'пока' in el or 'выйти' in el:
            print(1)
            after_answer(req, res)
            return
        elif 'да' in el or 'начина' in el or 'приступ' in el or 'начн' in el or 'точно':
            #print(sessionStorage[user_id]["cooking_mode"]["recipe"])
            recipe = get_recipe_for_mode(sessionStorage[user_id]["cooking_mode"]["recipe"])
            print(recipe)
        return
    res['response']['text'] = 'Я тебя не понимаю. Попробуй использовать подсказки. Начинаем?'
    res['response']['buttons'] = [
        {
            'title': 'Да',
            'hide': True
        }, {'title': 'Нет',
            'hide': True}]


def after_answer(req, res):
    sessionStorage[user_id]["status"] = 0
    for el in req['request']['nlu']['tokens']:
        if 'пока' in el:
            res['response']['text'] = 'Была рада тебе помочь. Пока!'
            yandex.deleteAllImage()  # проверка на память
            res['response']['end_session'] = True
            return
    if req['request']['command'] == 'режим готовки':
        res['response']['text'] = 'режим готовки трали вали. Начинаем?'
        res['response']['buttons'] = [
            {
                'title': 'Да',
                'hide': True
            }, {'title': 'Нет',
                'hide': True}]
        sessionStorage[user_id]["status"] = 'cooking_mode'
        return
    res['response']['text'] = 'Я могу еще чем-то помочь?'
    res['response']['buttons'] = [
        {
            'title': el,
            'hide': True
        } for el in buttons
    ]


def get_answer(req, res):  # рецепт, таймер ил итд
    a = False
    for el in req['request']['nlu']['tokens']:
        if 'таймер' in el:
            timer(req, res)
            sessionStorage[user_id]["status"] = 'timer'
            a = True
        elif 'рецепт' in el:
            a = True
            sessionStorage[user_id]["status"] = 'recipes'
            res['response']['text'] = 'Я могу показать тебе рецепт определенного блюда, рецепт рандомного блюда и тд.'
            res['response']['buttons'] = [
                {
                    'title': el,
                    'hide': True
                } for el in btn_recipes
            ]

        elif 'магазин' in el:  # пересмотреть
            a = True
            sessionStorage[user_id]["status"] = 'shops'
            res['response'][
                'text'] = 'Скажи полный адрес своего местоположения. Например, город Пушкина, ул Колотушкина, д 7'
        elif 'пока' in el:
            res['response']['text'] = 'Была рада тебе помочь. Пока!'
            res['response']['end_session'] = True
            return
    if not a:
        sessionStorage[user_id]["status"] = 'error'
        res['response']['text'] = 'Я не понимаю тебя. Попробуй воспользоваться подсказками!'
        res['response']['buttons'] = [
            {
                'title': el,
                'hide': True
            } for el in buttons
        ]
    return


def timer(req, res):
    res['response']['text'] = 'Ты можешь поставить таймер.'


def recipes(req, res):
    cur_status = ''
    options = {'name_recipe': 0, 'random_recipe': 0,
               'product_recipe': 0, 'exit': 0, 'area_recipe': 0}  # необходимое количество соответсвенно 1, 2, 2, 1, 2
    for el in req['request']['nlu']['tokens']:
        if 'люб' in el:
            options['random_recipe'] += 1
        elif 'блюдо' in el or 'рецепт' in el:
            options['name_recipe'] += 1
            options['random_recipe'] += 1
            options['product_recipe'] += 1
            options['area_recipe'] += 1
        elif 'продукт' in el or 'ингридиент' in el:
            options['product_recipe'] += 1
        elif 'не' in el:
            options['name_recipe'] -= 1
            options['random_recipe'] -= 1
            options['product_recipe'] -= 1
        elif 'другое' in el or 'таймер' in el or 'магаз' in el or 'назад' in el:
            options['exit'] += 1
        elif 'област' in el or 'кухн' in el or 'стран' in el:
            options['area_recipe'] += 1

    if options['random_recipe'] == 2 and options['random_recipe'] > options['product_recipe'] and options[
        'area_recipe'] != 2:
        cur_status = 'random_recipe'
    elif options['product_recipe'] == 2 and options['random_recipe'] < options['product_recipe'] and options[
        'area_recipe'] != 2:
        cur_status = 'product_recipe'
    elif options['area_recipe'] == 2:
        cur_status = 'area_recipe'
    elif options['name_recipe'] == 1:
        cur_status = 'name_recipe'

    if req['request']['command'] == 'по названию' or cur_status == 'name_recipe':
        res['response'][
            'text'] = f'{sessionStorage[user_id]["first_name"]}! Скажи только блюдо, рецепт которого ты хочешь найти.'
        sessionStorage[user_id]["status"] = 'search_recipe_name'
    elif req['request']['command'] == 'любое блюдо' or cur_status == 'random_recipe':  # не знаю что выбрать
        random_recipe(req, res)
    elif req['request']['command'] == 'по ингридиенту' or cur_status == 'product_recipe':
        res['response'][
            'text'] = f'{sessionStorage[user_id]["first_name"]}! Скажи только продукт, который есть в блюде.'
        sessionStorage[user_id]["status"] = 'search_recipe_product'
    elif req['request']['command'] == 'по области' or cur_status == 'area_recipe':
        res['response'][
            'text'] = f'{sessionStorage[user_id]["first_name"]}! Скажи вид нужной кухни. Например, китайская.'
        sessionStorage[user_id]["status"] = 'search_recipe_area'
    elif options['exit'] > 0:
        after_answer(req, res)
    else:
        res['response']['buttons'] = [
            {
                'title': el,
                'hide': True
            } for el in btn_recipes
        ]
        res['response']['text'] = 'Я тебя не понимаю. Попробуй использовать подсказки!'


def search_recipe(req, res):
    # print(req['request']['command'])
    if sessionStorage[user_id]["status"] == 'search_recipe_name':
        sessionStorage[user_id]["status"] = 'choice'
        video, recipe = searching_recipe_name(req['request']['command'])[0], \
                        searching_recipe_name(req['request']['command'])[1]
        sessionStorage[user_id]["cooking_mode"]["recipe"] = recipe  # рецепт для режима готовки
        if recipe:
            res['response']['buttons'] = [
                {
                    'title': el,
                    'hide': True
                } for el in btn_recipes_1
            ]
            res['response']['buttons'][0] = {
                'title': 'Вот твой рецепт!',
                'hide': True,
                'url': video
            }
            res['response']['text'] = f"Я нашла рецепт!"
        else:
            res['response']['text'] = f"Извини, я такого блюда не знаю..."
    elif sessionStorage[user_id]["status"] == 'search_recipe_product':
        sessionStorage[user_id]["status"] = 'choice'
        recipe = searching_recipe_product(req['request']['command'])
        if recipe:
            if req['request']['command'] not in sessionStorage[user_id]["dict_for_srp"]:
                sessionStorage[user_id]["dict_for_srp"][req['request']['command']] = [recipe, 0]
            else:
                # print(len(dict_for_srp[req['request']['command']][0]))
                if sessionStorage[user_id]["dict_for_srp"][req['request']['command']][1] + 1 == \
                        len(sessionStorage[user_id]["dict_for_srp"][req['request']['command']][0]):
                    sessionStorage[user_id]["dict_for_srp"][req['request']['command']][1] = 0
                else:
                    sessionStorage[user_id]["dict_for_srp"][req['request']['command']][1] += 1
            recipe = searching_by_id(
                sessionStorage[user_id]["dict_for_srp"][req['request']['command']][0][
                    sessionStorage[user_id]["dict_for_srp"][req['request']['command']][1]])
            res['response']['buttons'] = [
                {
                    'title': el,
                    'hide': True
                } for el in btn_recipes_1
            ]
            res['response']['buttons'][0] = {
                'title': 'Вот твой рецепт!',
                'hide': True,
                'url': recipe
            }
            res['response']['text'] = f"Я нашла рецепт!"
        else:
            res['response']['text'] = f"Извини, я не смогла найти что-то подходящее..."
    else:
        sessionStorage[user_id]["status"] = 'choice'
        if list_areas(req['request']['command']):
            if req['request']['command'] not in sessionStorage[user_id]["dict_for_sra"]:
                sessionStorage[user_id]["dict_for_sra"][req['request']['command']] = [
                    searching_recipe_area(req['request']['command']), 0]
            else:
                if sessionStorage[user_id]["dict_for_sra"][req['request']['command']][1] + 1 \
                        == len(sessionStorage[user_id]["dict_for_sra"][req['request']['command']][0]):
                    sessionStorage[user_id]["dict_for_sra"][req['request']['command']][1] = 0
                else:
                    # print(len(dict_for_sra[req['request']['command']][0]))
                    sessionStorage[user_id]["dict_for_sra"][req['request']['command']][1] += 1
            recipe = searching_by_id(
                sessionStorage[user_id]["dict_for_sra"][req['request']['command']][0][
                    sessionStorage[user_id]["dict_for_sra"][req['request']['command']][1]])
            res['response']['buttons'] = [
                {
                    'title': el,
                    'hide': True
                } for el in btn_recipes_1
            ]
            res['response']['buttons'][0] = {
                'title': 'Вот и рецепт.',
                'hide': True,
                'url': recipe
            }
            res['response']['text'] = f"Попробуй приготовить это!"
        else:
            res['response']['text'] = f"Извини, я не смогла найти что-то подходящее..."


def random_recipe(req, res):
    sessionStorage[user_id]["status"] = 'choice'
    recipe = random_meal()
    res['response']['text'] = "Попробуй приготовить это!"
    res['response']['buttons'] = [
        {
            'title': el,
            'hide': True
        } for el in btn_recipes_1
    ]
    res['response']['buttons'][0] = {
        'title': 'Вот твой рецепт!',
        'hide': True,
        'url': recipe
    }


def near_market(req, res):
    address = req['request']['command']
    if sessionStorage[user_id]["status"] == 'get_address':
        if 'выйти' in address:  # другие варианты
            sessionStorage[user_id]["status"] = 'choice'
            after_answer(req, res)
            return
    sessionStorage[user_id]["status"] = 'get_address'
    cor = get_cor(address)
    if cor:
        shops = get_shops(cor)
        if shops:
            image_id = yandex.downloadImageFile('map.png')['id']
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            ad1, ad2 = ' '.join(shops[0].split(', ')[:-2]), ' '.join(shops[1].split(', ')[:-2])
            text = f"Я нашла магазины по адресам: {ad1}, {ad2}. "
            res['response']['card']['title'] = text + 'Вперед за покупками!'
            res['response']['card']['image_id'] = image_id
            res['response']['text'] = 'Я отметила на карте ближайшие к тебе магазины. Вперед за покупками!'
            sessionStorage[user_id]["status"] = 'choice'
        else:
            res['response']['text'] = 'Я не нашла магазинов поблизости. Используй нашу Яндекс Доставку!'
            res['response']['buttons'] = [
                {
                    'title': 'Выйти',
                    'hide': True
                }]
    else:
        res['response']['text'] = 'Я не могу найти тебя. Попробуй сказать так: город А улица Б дом 1'
        res['response']['buttons'] = [
            {
                'title': 'Выйти',
                'hide': True
            }]


def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name',
            # то возвращаем ее значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()
