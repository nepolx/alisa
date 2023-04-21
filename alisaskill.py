from flask import Flask, request
import logging
import json
from recipes import *
from shops import get_cor, get_shops, YandexImages

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

buttons = ['Поиск рецептов', 'Ближайший магазин', 'Пока']  # варианты подсказок
btn_recipes = ['По названию', 'По ингредиенту', 'По области', 'Любое блюдо', 'Другое']
btn_recipes_1 = ['video', 'Режим готовки', 'Хочу еще спросить!', 'Пока']
btn_cooking_mode = ['Назад', 'Дальше', 'Хватит']
user_id = 0
sessionStorage = {}  # для каждого юзера своя инфа

yandex = YandexImages()
yandex.set_auth_token(token='y0_AgAAAABDXC3pAAT7owAAAADdHZRtE0yZizUfTESzM4BFRe8lhS52uFA')
yandex.skills = 'dd9896e2-415e-493c-8dd2-dda4d5e6dac9'


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
        res['response']['text'] = 'Привет! Я - твой кухонный помощник Алиса. Давай знакомиться. Как тебя зовут?'
        # создаем словарь в который в будущем положим имя пользователя
        sessionStorage[user_id] = {
            'first_name': None
        }
        sessionStorage[user_id]["status"] = 0  # статус, который определяет: какую вызывать функцию
        sessionStorage[user_id][
            "dict_for_srp"] = {}  # ключ - продукт, значение: список из списка id блюд и номер, которое нужно показать
        sessionStorage[user_id]["dict_for_sra"] = {}
        sessionStorage[user_id]["cooking_mode"] = {}  # режим готовки
        sessionStorage[user_id]["stop"] = 0  # если пользователь много ошибается - выдается подсказка

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
        else:
            sessionStorage[user_id]['first_name'] = first_name.lower().capitalize()
            res['response'][
                'text'] = 'Приятно познакомиться, ' \
                          + first_name.title() \
                          + '. Я могу сказать рецепты по разным категориям, а также показать ближайшие к тебе магазины. ' \
                            'Если ты захочешь выйти из навыка или вернуться в меню, скажи "пока", "хватит" соответственно.' \
                            ' Чем я могу помочь?'
            res['response']['buttons'] = [
                {
                    'title': el,
                    'hide': True
                } for el in buttons
            ]
    # если мы знакомы с пользователем и он нам что-то написал
    else:
        if not sessionStorage[user_id]["status"] or sessionStorage[user_id]["status"] == 'error':
            get_answer(req, res)
        elif sessionStorage[user_id]["status"] == 'recipes':
            recipes(req, res)
        elif 'search_recipe' in sessionStorage[user_id]["status"]:
            search_recipe_res(req, res)
        elif sessionStorage[user_id]["status"] == 'choice':
            after_answer(req, res)
        elif sessionStorage[user_id]["status"] == 'random_recipe':
            random_recipe(req, res)
        elif sessionStorage[user_id]["status"] == 'shops' or sessionStorage[user_id]["status"] == 'get_address':
            near_market(req, res)
        elif sessionStorage[user_id]["status"] == 'cooking_mode_action':
            cooking_mode_action(req, res)
        elif sessionStorage[user_id]["status"] == 'cooking_mode':
            cooking_mode(req, res)


def end(req, res):  # выход из сессии, если пользователь говорит "пока"
    if 'пока ' in req['request']['command'] or req['request']['command'].split()[-1] == 'пока':
        res['response']['text'] = 'Была рада тебе помочь. Пока!'
        yandex.deleteAllImage()  # очистка созданных изображений
        res['response']['end_session'] = True
        return True


def get_recipe_for_mode(recipe):  # обработка рецепта в нормальный вид
    res = []
    for el in recipe:
        el = el.replace(';', '.')
        el = list(map(lambda x: x + '.' if x and x[-1] not in '.!' else x + '', el.split('.')))
        for x in el:
            res.append(x.strip())
    res = list(filter(lambda x: x != '' and not x[0:len(x) - 1].isdigit(), res))
    return res


def cooking_mode_on(req, res):  # приготовление рецепта для вывода
    part = sessionStorage[user_id]["cooking_mode"]["part"]
    recipe = sessionStorage[user_id]["cooking_mode"]["recipe"]
    ans = recipe[part:part + 1 if (part + 1) < len(recipe) else len(recipe)]
    ans = translate_try(' '.join(ans), type='recipe')
    # print(ans)
    res['response']['text'] = ans
    if part == 0:
        btn = btn_cooking_mode[1:]
    elif part >= len(recipe):
        btn = btn_cooking_mode[2]
    else:
        btn = btn_cooking_mode
    res['response']['buttons'] = [
        {
            'title': el,
            'hide': True
        } for el in btn
    ]
    sessionStorage[user_id]["cooking_mode"]["part"] += 1
    sessionStorage[user_id]["status"] = 'cooking_mode_action'


def cooking_mode_action(req, res):  # вывод рецепта
    if end(req, res):
        return
    for el in req['request']['nlu']['tokens']:
        if 'назад' in el or 'вернись' in el or 'повтор' in el:  # шаг назад
            # print(sessionStorage[user_id]["cooking_mode"]["part"])
            if sessionStorage[user_id]["cooking_mode"]["part"] != 1:
                sessionStorage[user_id]["cooking_mode"]["part"] -= 2
                cooking_mode_on(req, res)
                return
            else:
                res['response']['text'] = 'Я не могу вернуться назад. Мы только начали!'
                res['response']['buttons'] = [
                    {
                        'title': el,
                        'hide': True
                    } for el in btn_cooking_mode[1:]
                ]
            return
        if 'дальше' in el or 'след' in el:  # шаг вперед
            if sessionStorage[user_id]["cooking_mode"]["part"] < len(sessionStorage[user_id]["cooking_mode"]["recipe"]):
                cooking_mode_on(req, res)
                return
            else:
                res['response']['text'] = 'Готовка уже завершена.'
                res['response']['buttons'] = [
                    {
                        'title': 'Хватит',
                        'hide': True
                    }]

            return
        if 'хватит' in el or 'прекрат' in el or 'кон' in el or 'выйти' in el:  # выход из режима
            after_answer(req, res)
            return
    res['response']['text'] = 'Я тебя не понимаю. Попробуй использовать подсказки. Продолжаем готовку?'
    res['response']['buttons'] = [
        {
            'title': el,
            'hide': True
        } for el in btn_cooking_mode
    ]


def cooking_mode(req, res):  # активация режима
    if end(req, res):
        return
    el = req['request']['command']
    if 'не' in el or 'вернись' in el or 'выйти' in el or 'хватит' in el:
        after_answer(req, res)
        return
    elif 'да' in el or 'начина' in el or 'приступ' in el or 'начн' in el or 'точно':
        recipe = get_recipe_for_mode(sessionStorage[user_id]["cooking_mode"]["recipe"])
        sessionStorage[user_id]["cooking_mode"]["recipe"] = recipe

        sessionStorage[user_id]["cooking_mode"]["part"] = 0
        cooking_mode_on(req, res)
        return
    res['response']['text'] = 'Я тебя не понимаю. Попробуй использовать подсказки. Начинаем?'
    res['response']['buttons'] = [
        {
            'title': 'Да',
            'hide': True
        }, {'title': 'Нет',
            'hide': True}]


def after_answer(req, res):  # после ответы Алисы, возможные дальннейшие дейсвтия
    if end(req, res):
        return

    if req['request']['command'] == 'вот твой рецепт':
        # если пользователь перезлдит по ссылке, то снова показываются все подсказки сам рецепт
        res['response']['buttons'] = [
            {
                'title': el,
                'hide': True
            } for el in btn_recipes_1
        ]
        res['response']['buttons'][0] = {
            'title': 'Вот твой рецепт!',
            'hide': True,
            'url': sessionStorage[user_id]["cooking_mode"]["video"]
        }
        res['response'][
            'text'] = f'Вот рецепт блюда "{sessionStorage[user_id]["cooking_mode"]["name"]}"! Если хочешь приготовить его со мной, скажи "режим готовки".'
        return
    if req['request']['command'] == 'режим готовки':  # переход в режим готовки
        res['response'][
            'text'] = f'В этом режиме ты сможешь приготовить блюдо {sessionStorage[user_id]["cooking_mode"]["name"]}. ' \
                      f'Я буду поэтапно озвучивать рецепт. Если ты захочешь вернуться или продолжить, ' \
                      f'скажи "назад" и "дальше" соответственно. Если захочешь покинуть режим, скажи "хватит". ' \
                      f'Начинаем?'
        res['response']['buttons'] = [
            {
                'title': 'Да',
                'hide': True
            }, {'title': 'Нет',
                'hide': True}]
        sessionStorage[user_id]["status"] = 'cooking_mode'
        return
    sessionStorage[user_id]["status"] = 0  # выход в меню
    res['response']['text'] = 'Я могу еще чем-то помочь?'
    res['response']['buttons'] = [
        {
            'title': el,
            'hide': True
        } for el in buttons
    ]


def get_answer(req, res):  # меню. поиск рецепта или магазинов
    if end(req, res):
        return

    el = req['request']['command']
    if 'рецепт' in el or 'готовить' in el or 'блюдо' in el:
        sessionStorage[user_id]["status"] = 'recipes'
        sessionStorage[user_id]["stop"] = 0
        res['response']['text'] = 'Я могу показать тебе рецепт определенного блюда, рецепт блюда по ингредиенту ' \
                                  'или по области, рецепт рандомного блюда.'
        res['response']['buttons'] = [
            {
                'title': el,
                'hide': True
            } for el in btn_recipes
        ]
        return

    elif 'магазин' in el or 'купить' in el and (
            'продукт' in el or 'ингредиент' in el) or 'супермаркет' in el:  # пересмотреть
        sessionStorage[user_id]["stop"] = 0
        sessionStorage[user_id]["status"] = 'shops'
        res['response'][
            'text'] = 'Скажи полный адрес своего местоположения. Например, город Пушкина, ул Колотушкина, д 7'
        res['response']['buttons'] = [
            {
                'title': 'Хватит',
                'hide': True
            }
        ]
        return
    sessionStorage[user_id]["status"] = 'error'
    res['response']['text'] = 'Я не понимаю тебя. Попробуй воспользоваться подсказками!'
    res['response']['buttons'] = [
        {
            'title': el,
            'hide': True
        } for el in buttons
    ]


def recipes(req, res):  # определение того, какой способ поиска рецепта выбрал пользователь
    if end(req, res):
        return
    cur_status = ''
    options = {'name_recipe': 0, 'random_recipe': 0,
               'product_recipe': 0, 'exit': 0, 'area_recipe': 0}  # необходимое количество соответсвенно 1, 2, 2, 1, 2
    el = req['request']['command']

    if 'люб' in el or 'рандомн' in el:
        options['random_recipe'] += 1
    if 'блюд' in el or 'рецепт' in el:
        options['name_recipe'] += 1
        options['random_recipe'] += 1
        options['product_recipe'] += 1
        options['area_recipe'] += 1
    if 'продукт' in el or 'ингредиент' in el:
        options['product_recipe'] += 1
    if ' не ' in el:
        options['name_recipe'] -= 1
        options['random_recipe'] -= 1
        options['product_recipe'] -= 1
    if 'другое' in el or 'магаз' in el or 'назад' in el or 'вернись' in el:
        options['exit'] += 1
    if 'област' in el or 'кухн' in el or 'стран' in el:
        options['area_recipe'] += 1

    if options['random_recipe'] == 2 and options['random_recipe'] > options['product_recipe'] and options[
        'area_recipe'] != 2:  # если набирается достаточное количество для поиска по области и тд
        cur_status = 'random_recipe'
    elif options['product_recipe'] == 2 and options['random_recipe'] < options['product_recipe'] and options[
        'area_recipe'] != 2:
        cur_status = 'product_recipe'
    elif options['area_recipe'] == 2:
        cur_status = 'area_recipe'
    elif options['name_recipe'] == 1:
        cur_status = 'name_recipe'

    if req['request']['command'] == 'по названию' or cur_status == 'name_recipe':
        sessionStorage[user_id]["stop"] = 0
        res['response'][
            'text'] = f'{sessionStorage[user_id]["first_name"]}! Скажи только блюдо, рецепт которого ты хочешь найти.'
        sessionStorage[user_id]["status"] = 'search_recipe_name'
        return
    elif req['request']['command'] == 'любое блюдо' or cur_status == 'random_recipe':
        sessionStorage[user_id]["stop"] = 0
        random_recipe(req, res)
        return
    elif req['request']['command'] == 'по ингредиенту' or cur_status == 'product_recipe':
        sessionStorage[user_id]["stop"] = 0
        res['response'][
            'text'] = f'{sessionStorage[user_id]["first_name"]}! Скажи только продукт, который есть в блюде.'
        sessionStorage[user_id]["status"] = 'search_recipe_product'
        return
    elif req['request']['command'] == 'по области' or cur_status == 'area_recipe':
        sessionStorage[user_id]["stop"] = 0
        res['response'][
            'text'] = f'{sessionStorage[user_id]["first_name"]}! Скажи только вид нужной кухни. Например, китайская.'
        sessionStorage[user_id]["status"] = 'search_recipe_area'
        return
    elif options['exit'] > 0:
        after_answer(req, res)
        return
    res['response']['buttons'] = [
        {
            'title': el,
            'hide': True
        } for el in btn_recipes
    ]
    if sessionStorage[user_id]["stop"] < 1:
        res['response']['text'] = 'Я не понимаю тебя. Попробуй воспользоваться подсказками!'
        sessionStorage[user_id]["stop"] += 1
    else:
        res['response']['text'] = 'Я не понимаю тебя. Если ты хочешь найти что-то другое. Скажи "хватит".'


def search_recipe_res(req, res):  # вывод рецепта, если он есть
    search_recipe(req, res)
    if sessionStorage[user_id]["status"] == 0:
        return
    if sessionStorage[user_id]["cooking_mode"]["answer"]:
        sessionStorage[user_id]["stop"] = 0
        sessionStorage[user_id]["status"] = 'choice'
        sessionStorage[user_id]["cooking_mode"]["answer"] = False
        res['response']['buttons'] = [
            {
                'title': el,
                'hide': True
            } for el in btn_recipes_1
        ]
        if sessionStorage[user_id]["cooking_mode"]["video"]:
            res['response']['buttons'][0] = {
                'title': f'Вот твой рецепт!',
                'hide': True,
                'url': sessionStorage[user_id]["cooking_mode"]["video"]
            }
        else:
            del res['response']['buttons'][0]
        res['response'][
            'text'] = f'Я знаю рецепт блюда "{sessionStorage[user_id]["cooking_mode"]["name"]}"! ' \
                      f'Если хочешь приготовить его со мной, скажи "режим готовки".'
    elif sessionStorage[user_id]["stop"] < 1:  # если пользователь пишет что-то не то
        sessionStorage[user_id][
            "stop"] += 1  # накопление переменной, чтобы потом напомнить о возможности выхода в мини-меню
        res['response']['text'] = 'Извини, я не смогла найти чего-то подходящего...'
    else:
        res['response'][
            'text'] = 'Извини, я не смогла найти чего-то подходящего... Если ты хочешь найти другое, скажи "хватит".'  # само напоминание


def search_recipe(req, res):  # получение и сохранение данных в зависимости от выбранного спосбо поиска рецепта
    # print(req['request']['command'])

    if end(req, res):
        return
    el = req['request']['command']
    if 'не' in el or 'вернись' in el or 'выйти' in el or 'хватит' in el:
        after_answer(req, res)
        return
    if sessionStorage[user_id]["status"] == 'search_recipe_name':  # поиск по названию
        ans = searching_recipe_name(req['request']['command'])
        if ans:
            video, recipe, name = ans[0], ans[1], ans[2]
            sessionStorage[user_id]["cooking_mode"]["recipe"] = recipe  # рецепт для режима готовки
            sessionStorage[user_id]["cooking_mode"]["video"] = video
            sessionStorage[user_id]["cooking_mode"]["name"] = name
            sessionStorage[user_id]["cooking_mode"]["answer"] = True

        else:
            sessionStorage[user_id]["cooking_mode"]["answer"] = False
        return
    elif sessionStorage[user_id]["status"] == 'search_recipe_product':  # поиск по ингредиенту
        recipe = searching_recipe_product(str(req['request']['command']))
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
            r = searching_by_id(
                sessionStorage[user_id]["dict_for_srp"][req['request']['command']][0][
                    sessionStorage[user_id]["dict_for_srp"][req['request']['command']][1]])
            video, recipe, name = r[0], r[1], r[2]
            sessionStorage[user_id]["cooking_mode"]["recipe"] = recipe
            sessionStorage[user_id]["cooking_mode"]["video"] = video
            sessionStorage[user_id]["cooking_mode"]["name"] = name
            sessionStorage[user_id]["cooking_mode"]["answer"] = True
        else:
            sessionStorage[user_id]["cooking_mode"]["answer"] = False
        return
    else:  # поиск по области
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
            r = searching_by_id(
                sessionStorage[user_id]["dict_for_sra"][req['request']['command']][0][
                    sessionStorage[user_id]["dict_for_sra"][req['request']['command']][1]])
            video, recipe, name = r[0], r[1], r[2]
            sessionStorage[user_id]["cooking_mode"]["recipe"] = recipe
            sessionStorage[user_id]["cooking_mode"]["video"] = video
            sessionStorage[user_id]["cooking_mode"]["name"] = name
            sessionStorage[user_id]["cooking_mode"]["answer"] = True
        else:
            sessionStorage[user_id]["cooking_mode"]["answer"] = False
        return


def random_recipe(req, res):  # рецепт для рандомного блюда
    sessionStorage[user_id]["status"] = 'choice'
    r = random_meal()
    video, recipe, name = r[0], r[1], r[2]
    sessionStorage[user_id]["cooking_mode"]["recipe"] = recipe
    sessionStorage[user_id]["cooking_mode"]["video"] = video
    sessionStorage[user_id]["cooking_mode"]["name"] = name
    res['response'][
        'text'] = f'Попробуй приготовить {name}! Если хочешь приготовить его со мной, скажи "режим готовки".'
    res['response']['buttons'] = [
        {
            'title': el,
            'hide': True
        } for el in btn_recipes_1
    ]
    if sessionStorage[user_id]["cooking_mode"]["video"]:
        res['response']['buttons'][0] = {
            'title': f'Вот твой рецепт!',
            'hide': True,
            'url': sessionStorage[user_id]["cooking_mode"]["video"]
        }
    else:
        del res['response']['buttons'][0]


def near_market(req, res):  # вывод ближайшего магазина
    if end(req, res):
        return
    address = req['request']['command']
    if 'выйти' in address or 'хватит' in address or 'назад' in address:
        sessionStorage[user_id]["status"] = 'choice'
        after_answer(req, res)
        return
    sessionStorage[user_id]["status"] = 'get_address'
    cor = get_cor(address)
    if cor:  # если пользователь вводит корректный адрес
        x = get_shops(cor)
        shops, names = x[0], x[1]
        if x:
            image_id = yandex.downloadImageFile('map.png')['id']
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            ad1, ad2 = ' '.join(shops[0].split(', ')[:-2]), ' '.join(shops[1].split(', ')[:-2])
            text = f"Я нашла магазины: {names[0]}, {names[1]} по адресам: {ad1}, {ad2}. "
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
