import requests

from googletrans import Translator


def searching_recipe_name(meal):
    translator = Translator()
    meal = '_'.join(translator.translate(meal, dest='en').text.split())
    url = f"http://www.themealdb.com/api/json/v1/1/search.php?s={meal}"
    try:
        response = requests.request("GET", url)
        json_response = response.json()
        recipe = json_response['meals'][0]['strInstructions'].splitlines()
        print(recipe)
        # print(translator.translate(recipe, dest='ru'))
        # recipe = translator.translate(recipe, dest='ru').text
        video = json_response['meals'][0]['strYoutube']
        return video, recipe
    except:
        return ''

searching_recipe_name('омлет')
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


def random_meal():
    url = "http://www.themealdb.com/api/json/v1/1/random.php"
    response = requests.request("GET", url)
    json_response = response.json()
    video = json_response['meals'][0]['strYoutube']
    return video


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
