import requests
import json


class YandexImages(object):  # класс картинок, которые загружаются в ресурсы Алисы
    def __init__(self):
        self.SESSION = requests.Session()
        # self.SESSION.headers.update(AUTH_HEADER)
        self.API_VERSION = 'v1'
        self.API_BASE_URL = 'https://dialogs.yandex.net/api'
        self.API_URL = self.API_BASE_URL + '/' + self.API_VERSION + '/'
        self.skills = ''

    # подключение

    def set_auth_token(self, token):
        self.SESSION.headers.update(self.get_auth_header(token))

    def get_auth_header(self, token):
        return {
            'Authorization': 'OAuth %s' % token
        }

    def log(self, error_text, response):
        log_file = open('YandexApi.log', 'a')
        log_file.write(error_text + '\n')  # +response)
        log_file.close()

    def validate_api_response(self, response, required_key_name=None):
        content_type = response.headers['Content-Type']
        content = json.loads(response.text) if 'application/json' in content_type else None

        if response.status_code == 200:
            if required_key_name and required_key_name not in content:
                self.log('Unexpected API response. Missing required key: %s' % required_key_name, response=response)
                return None
        elif content and 'error_message' in content:
            self.log('Error API response. Error message: %s' % content['error_message'], response=response)
            return None
        elif content and 'message' in content:
            self.log('Error API response. Error message: %s' % content['message'], response=response)
            return None
        else:
            response.raise_for_status()

        return content

    # Проверить занятое место
    def checkOutPlace(self):
        result = self.SESSION.get(self.API_URL + 'status')
        content = self.validate_api_response(result)
        if content != None:
            return content['images']['quota']
        return None

    # Загрузка изображения из файла
    def downloadImageFile(self, img):
        path = 'skills/{skills_id}/images'.format(skills_id=self.skills)
        result = self.SESSION.post(url=self.API_URL + path, files={'file': (img, open(img, 'rb'))})
        content = self.validate_api_response(result)
        if content != None:
            return content['image']
        return None

    def getLoadedImages(self):
        path = 'skills/{skills_id}/images'.format(skills_id=self.skills)
        result = self.SESSION.get(url=self.API_URL + path)
        content = self.validate_api_response(result)
        if content != None:
            return content['images']
        return None

    def deleteImage(self, img_id):  # удаление изображения
        path = 'skills/{skills_id}/images/{img_id}'.format(skills_id=self.skills, img_id=img_id)
        result = self.SESSION.delete(url=self.API_URL + path)
        content = self.validate_api_response(result)
        if content != None:
            return content['result']
        return None

    def deleteAllImage(self):  # удаление всех изображений
        success = 0
        fail = 0
        images = self.getLoadedImages()
        for image in images:
            image_id = image['id']
            if image_id:
                if self.deleteImage(image_id):
                    success += 1
                else:
                    fail += 1
            else:
                fail += 1

        return {'success': success, 'fail': fail}


def get_cor(address):  # получение координат введенного адреса
    g = f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode={address}&format=json"
    response = requests.get(g)
    if response:
        try:
            json_response = response.json()
            toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
            toponym_coodrinates = toponym["Point"]["pos"]
            cor = toponym_coodrinates.split()[0] + ',' + toponym_coodrinates.split()[1]
            return cor
        except:
            return ''
    else:
        return ''


def get_shops(cor):  # получение самих магазинов
    map_request = f"https://search-maps.yandex.ru/v1/?text=магазин&type=biz&ll={cor}&spn=0.00107,0.00199&lang=ru_RU&apikey=f66421bb-4c50-4ab7-a329-852d1e17fb13"
    response = requests.get(map_request).json()
    shops = []
    addresses = []
    names = []
    for i in range(len(response["features"])):
        t = response["features"][i]["geometry"]["coordinates"]
        shops.append(str(t[0]) + ',' + str(t[1]))
        addresses.append(response["features"][i]["properties"]["description"])
        # print(response["features"][i]["properties"]["description"])  # адрес
        names.append(response["features"][i]["properties"]["CompanyMetaData"]["name"])

    if shops:
        map_request = f"https://static-maps.yandex.ru/1.x/?l=map&pt={cor},pm2vvm~{shops[0]},pm2blm~{shops[1]},pm2blm"
        response = requests.get(map_request)
    else:
        return False

    if not response:
        print("Ошибка выполнения запроса:")
        print(map_request)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        return False

    # Запишем полученное изображение в файл.
    map_file = "map.png"
    with open(map_file, "wb") as file:
        file.write(response.content)

    return addresses, names

# cor = get_cor('г магнитогорск ул советская д 10')
# get_shops(cor)
