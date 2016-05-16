import logging
import web_request
import youtube


log = logging.getLogger(__name__)


def get_lastfm_chart(chart_items=5):
    """
    Finds the currently most played tunes on last.fm and turns them in to a youtube list of tracks.
    :param chart_items: int the amount of tracks we want.
    :return: list[ dict{'type=youtube', 'video_id', 'int(video_time)', 'video_title'} ] or None on error.
    """
    url = 'http://lastfm-ajax-vip1.phx1.cbsig.net/kerve/charts?nr=%s&type=track&format=json' % chart_items
    lastfm = web_request.get_request(url, json=True)
    log.debug(lastfm)
    if lastfm is not None:
        if 'results' in lastfm['content']:
            if 'track' in lastfm['content']['results']:
                if len(lastfm['content']['results']['track']) is not 0:
                    yt_tracks = []
                    for track in lastfm['content']['results']['track']:
                        search_str = '%s - %s' % (track['artist'], track['name'])
                        yt = youtube.youtube_search(search_str)
                        log.info(yt)
                        if yt is not None:
                            yt_tracks.append(yt)
                    return yt_tracks
                return None


def search_lastfm_by_tag(search_str, by_id=True, max_tunes=40):
    """
    Search last.fm for tunes matching the search term and turns them in to a youtube list of tracks.
    :param search_str: str the search term to search for.
    :param by_id: bool if set to True, only tunes that have a youtube id will be added(recommended)
    :param max_tunes: int the max amount of tunes to return.
    :return: list[ dict{'type=youtube', 'video_id', 'int(video_time)', 'video_title'} ] or None on error.
    """
    url = 'http://lastfm-ajax-vip1.phx1.cbsig.net/kerve/charts?nr=%s&type=track&f=tag:%s&format=json' % \
          (max_tunes, search_str)
    lastfm = web_request.get_request(url, json=True)
    log.debug(lastfm)
    if lastfm is not None:
        if 'track' in lastfm['content']['results']:
            if len(lastfm['content']['results']['track']) is not 0:
                yt_tracks = []
                for track in lastfm['content']['results']['track']:
                    search_str = '%s - %s' % (track['artist'], track['name'])
                    if 'playlink' in track:
                        if 'data-youtube-id' in track['playlink']:
                            youtube_id = track['playlink']['data-youtube-id']
                            yt = youtube.youtube_time(youtube_id)
                            log.debug(yt)
                            if yt is not None:
                                yt_tracks.append(yt)
                        else:
                            if not by_id:
                                yt = youtube.youtube_search(search_str)
                                log.debug('search by search string: %s result: %s' % (search_str, yt))
                                if yt is not None:
                                    yt_tracks.append(yt)
                    else:
                        if not by_id:
                            yt = youtube.youtube_search(search_str)
                            log.debug('search by search string: %s result: %s' % (search_str, yt))
                            if yt is not None:
                                yt_tracks.append(yt)
                return yt_tracks
            return None


def lastfm_listening_now(max_tunes, by_id=True):
    """
    Gets a list of tunes other people using last.fm are listening to, and turns them in to a youtube list of tracks.
    :param max_tunes: int the amount of tracks we want.
    :param by_id: bool if set to True, only tunes that have a youtube id will be added(recommended)
    :return: list[ dict{'type=youtube', 'video_id', 'int(video_time)', 'video_title'} ] or None on error.
    """
    url = 'http://lastfm-ajax-vip1.phx1.cbsig.net/kerve/listeningnow?limit=%s&format=json' % max_tunes
    lastfm = web_request.get_request(url, json=True)
    log.debug(lastfm)
    if lastfm is not None:
        if len(lastfm['content']['Users']) is not 0:
            yt_tracks = []
            for user in lastfm['content']['Users']:
                if 'playlink' in user:
                    if 'data-youtube-id' in user['playlink']:
                        youtube_id = user['playlink']['data-youtube-id']
                        yt = youtube.youtube_time(youtube_id)
                        log.debug(yt)
                        if yt is not None:
                            yt_tracks.append(yt)
                else:
                    if 'Track' in user:
                        search_str = '%s - %s' % (user['Track']['Artist'], user['Track']['Name'])
                        if not by_id:
                            yt = youtube.youtube_search(search_str)
                            log.debug('search by search string: %s result: %s' % (search_str, yt))
                            if yt is not None:
                                yt_tracks.append(yt)
            return yt_tracks
        return None
