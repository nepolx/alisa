import requests

from googletrans import Translator


#
# # https://www.themealdb.com/api.php
# # https://pypi.org/search/?q=translator
# # pip install googletrans==4.0.0-rc1
# url = "http://www.themealdb.com/api/json/v1/1/search.php?s=tofu"
# url1 = "http://www.themealdb.com/api/json/v1/1/random.php"
# url2 = "http://www.themealdb.com/api/json/v1/1/search.php?f=a"
#
# response = requests.request("GET", url)
# r1 = requests.request("GET", url1)
# r2 = requests.request("GET", url2)
# # Преобразуем ответ в json-объект
# json_response = response.json()
# json1_response = r1.json()
# j2 = r2.json()
# # Получаем первый топоним из ответа геокодера.
# # Согласно описанию ответа, он находится по следующему пути:
# toponym = json_response['meals'][0]['strInstructions']
# x = json1_response
#
# # print(toponym)
#
# translator = Translator()
# a = translator.translate(toponym, dest='ru').text


# print(a)


# print(j2)

def searching_recipe_name(meal):
    translator = Translator()
    meal = '_'.join(translator.translate(meal, dest='en').text.split())
    url = f"http://www.themealdb.com/api/json/v1/1/search.php?s={meal}"
    try:
        response = requests.request("GET", url)
        json_response = response.json()
        # recipe = json_response['meals'][0]['strInstructions']
        # recipe = translator.translate(recipe, dest='ru').text
        video = json_response['meals'][0]['strYoutube']
        return video
    except:
        return ''


def searching_recipe_product(product):
    translator = Translator()
    product = '_'.join(translator.translate(product, dest='en').text.split())
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


def searching_by_id(id):
    url = f"http://www.themealdb.com/api/json/v1/1/lookup.php?i={id}"
    response = requests.request("GET", url)
    json_response = response.json()
    video = json_response['meals'][0]['strYoutube']
    return video


searching_recipe_product('сыр')


def random_meal():
    url = "http://www.themealdb.com/api/json/v1/1/random.php"
    response = requests.request("GET", url)
    json_response = response.json()
    video = json_response['meals'][0]['strYoutube']
    return video


def list_areas(area):
    translator = Translator()
    area = translator.translate(area, dest='en').text
    url = 'https://www.themealdb.com/api/json/v1/1/list.php?a=list'
    areas = []
    response = requests.request("GET", url)
    json_response = response.json()
    for el in json_response['meals']:
        areas.append(el['strArea'])
    if area in areas:
        return True
    return False


def searching_recipe_area(area):
    translator = Translator()
    area = '_'.join(translator.translate(area, dest='en').text.split())
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


print(list_areas('китайская'))
