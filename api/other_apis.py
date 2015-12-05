""" Provides functions to search the API of urbandictionary, worldweatheronline , ip-api and api.icndb """
import web_request


def urbandictionary_search(search):
    """
    Searches urbandictionary's API for a given search term.

    :param search: The search term str to search for.
    :return: defenition str or None on no match or error.
    """

    if str(search).strip():
        urban_api_url = 'http://api.urbandictionary.com/v0/define?term=%s' % search
        response = web_request.get_request(urban_api_url, json=True)

        if response:
            try:
                definition = response['content']['list'][0]['definition']
                return definition.encode('ascii', 'ignore')
            except KeyError:
                return None
            except IndexError:
                return None
    else:
        return None


def weather_search(city):
    """
    Searches worldweatheronline's API for weather data for a given city.
    You must have a working API key to be able to use this function.

    :param city: The city str to search for.
    :return: weather data str or None on no match or error.
    """

    if str(city).strip():
        api_key = '' # A valid API key.
        if not api_key:
            return 'Missing api key.'
        else:
            weather_api_url = 'http://api.worldweatheronline.com/free/v2/weather.ashx?' \
                              'q=%s&format=json&key=%s' % (city, api_key)

            response = web_request.get_request(weather_api_url, json=True)

            if response['content'] is not None:
                try:
                    pressure = response['content']['data']['current_condition'][0]['pressure']
                    temp_c = response['content']['data']['current_condition'][0]['temp_C']
                    temp_f = response['content']['data']['current_condition'][0]['temp_F']
                    query = response['content']['data']['request'][0]['query'].encode('ascii', 'ignore')
                    result = query + '. Tempature: ' + temp_c + 'C (' + temp_f + 'F) Pressure: ' + pressure + '  millibars'
                    return result
                except (IndexError, KeyError):
                    return None
    else:
        return None


def whois(ip):
    """
    Searches ip-api for information about a given IP.

    :param ip: The ip str to search for.
    :return: information str or None on error.
    """

    if str(ip).strip():
        url = 'http://ip-api.com/json/%s' % ip
        json_data = web_request.get_request(url, json=True)
        try:
            city = json_data['content']['city']
            country = json_data['content']['country']
            isp = json_data['content']['isp']
            org = json_data['content']['org']
            region = json_data['content']['regionName']
            zipcode = json_data['content']['zip']
            info = country + ', ' + city + ', ' + region + ', Zipcode: ' + zipcode + '  Isp: ' + isp + '/' + org
            return info
        except KeyError:
            return None
    else:
        return None


def chuck_norris():
    """
    Finds a random Chuck Norris joke/quote.

    :return: joke str or None on failure.
    """

    url = 'http://api.icndb.com/jokes/random/?escape=javascript'
    json_data = web_request.get_request(url, json=True)
    if json_data['content']['type'] == 'success':
        joke = json_data['content']['value']['joke'].decode('string_escape')
        return joke
    else:
        return None
