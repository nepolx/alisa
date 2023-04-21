import requests

from googletrans import Translator

translator = Translator()
areas = ['American', 'British', 'Canadian', 'Chinese', 'Croatian', 'Dutch', 'Egyptian', 'French',
         'Greek', 'Indian', 'Irish', 'Italian', 'Jamaican', 'Japanese', 'Kenyan', 'Malaysian',
         'Mexican', 'Moroccan', 'Polish', 'Portuguese', 'Russian', 'Spanish', 'Thai', 'Tunisian',
         'Turkish', 'Vietnamese']


def translate_try(s, type='def'):  # перевод
    while True:
        try:
            if type == 'def':
                s = translator.translate(s, dest='en', src='ru').text
            elif type == 'name':
                s = translator.translate(s, dest='ru', src='en').text
            else:
                # s = translator.translate(s, dest='ru', src='en').text.splitlines()
                s = translator.translate(s, dest='ru', src='en').text
            return s
        except:
            print(1)
            continue


def list_areas(area):  # проверка, есть ли в апи такая область
    area = translate_try(area)
    if area in areas:
        return True
    return False


def searching_recipe_name(meal):  # поиск по названию
    meal = '_'.join(translate_try(meal).split())
    url = f"http://www.themealdb.com/api/json/v1/1/search.php?s={meal}"
    try:
        response = requests.request("GET", url)
        json_response = response.json()
        # recipe = translate_try(json_response['meals'][0]['strInstructions'], type='recipe')
        recipe = json_response['meals'][0]['strInstructions'].splitlines()
        # recipe = json_response['meals'][0]['strInstructions'].splitlines()
        # print(translator.translate(recipe, dest='ru'))
        video = json_response['meals'][0]['strYoutube']
        name = translate_try(json_response['meals'][0]['strMeal'], type='name')
        return video, recipe, name
    except:
        return ''


def searching_recipe_product(product):  # поиск по ингедиенту
    product = '_'.join(translate_try(product).split())
    url = f"http://www.themealdb.com/api/json/v1/1/filter.php?i={product}"
    try:
        response = requests.request("GET", url)
        json_response = response.json()
        id_meals = []
        for el in json_response['meals']:
            id_meals.append(el['idMeal'])
        return id_meals
    except:
        return ''


def searching_by_id(id):  # поиск по id
    url = f"http://www.themealdb.com/api/json/v1/1/lookup.php?i={id}"
    response = requests.request("GET", url)
    json_response = response.json()
    video = json_response['meals'][0]['strYoutube']
    # recipe = translate_try(json_response['meals'][0]['strInstructions'], type='recipe')
    recipe = json_response['meals'][0]['strInstructions'].splitlines()
    name = translate_try(json_response['meals'][0]['strMeal'], type='name')
    return video, recipe, name


def random_meal():  # рандомное блюдо
    url = "http://www.themealdb.com/api/json/v1/1/random.php"
    response = requests.request("GET", url)
    json_response = response.json()
    name = translate_try(json_response['meals'][0]['strMeal'], type='name')
    video = json_response['meals'][0]['strYoutube']
    # recipe = translate_try(json_response['meals'][0]['strInstructions'], type='recipe')
    recipe = json_response['meals'][0]['strInstructions'].splitlines()
    return video, recipe, name


def searching_recipe_area(area):  # рецт по области
    area = '_'.join(translate_try(area).split())
    url = f"http://www.themealdb.com/api/json/v1/1/filter.php?a={area}"
    try:
        response = requests.request("GET", url)
        json_response = response.json()
        id_meals = []
        for el in json_response['meals']:
            id_meals.append(el['idMeal'])
        return id_meals
    except:
        return ''
