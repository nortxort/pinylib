import web_request


def soundcloud_search(search):
    """
    Searches soundcloud's API for a given search term.

    :param search: The search term str to search for.
    :return: dict['type=soundcloud', 'video_id', 'video_time', 'video_title'] or None on no match or error.
    """

    if search:
        search_url = 'http://api.soundcloud.com/tracks/?' \
                     'filter=streamable&q=%s&limit=25&client_id=4ce43a6430270a1eea977ff8357a25a3' % search

        response = web_request.get_request(search_url, json=True)

        if response['content'] is not None:
            try:
                track_id = response['content'][0]['id']
                track_time = response['content'][0]['duration']
                track_title = response['content'][0]['title'].encode('ascii', 'ignore')
                return {'type': 'soundCloud', 'video_id': track_id, 'video_time': track_time, 'video_title': track_title}
            except (IndexError, KeyError):
                return None
    return None


def soundcloud_track_info(track_id):
    # user search url http://api.soundcloud.com/users/?q=mbs&client_id=4ce43a6430270a1eea977ff8357a25a3
    # user info url http://api.soundcloud.com/users/63493914?client_id=4ce43a6430270a1eea977ff8357a25a3
    if track_id:
        info_url = 'http://api.soundcloud.com/tracks/%s?client_id=4ce43a6430270a1eea977ff8357a25a3' % track_id
        response = web_request.get_request(info_url, json=True)

        if response['content'] is not None:
            try:
                user_id = response['content'][0]['user_id']
                track_time = response['content'][0]['duration']
                track_title = response['content'][0]['title'].encode('ascii', 'ignore')
                return {'type': 'soundCloud', 'video_id': track_id, 'video_time': track_time,
                        'video_title': track_title, 'user_id': user_id}
            except (IndexError, KeyError):
                return None
    return None