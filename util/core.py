""" Contains functions to fetch info from tinychat's API. """
import logging
import random
import time
import webbrowser
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

from util import web

log = logging.getLogger(__name__)


def get_roomconfig_xml(room, roompass=None, proxy=None):
    """
    Finds room configuration for a given room name.
    :param room: str the room name to find info for.
    :param roompass: str the password to the room. Defaults to None.
    :param proxy: str use a proxy for this request.
    :return: dict {'tcurl', 'ip', 'port', 'app', 'roomtype', 'greenroom=bool', 'bpassword'}
    """
    if roompass:
        xmlurl = 'https://apl.tinychat.com/api/find.room/%s?site=tinychat&password=%s&url=tinychat.com' % \
                 (room, roompass)
    else:
        xmlurl = 'https://apl.tinychat.com/api/find.room/%s?site=tinychat&url=tinychat.com' % room

    response = web.http_get(xmlurl, proxy=proxy)
    log.debug('response: %s' % response)
    if response['content'] is not None:
        try:
            xml = parseString(response['content'])
        except ExpatError:
            xml = None
        if xml is not None:
            broadcast_pass = None
            root = xml.getElementsByTagName('response')[0]
            result = root.getAttribute('result')
            if result == 'PW':
                return result
            else:
                roomtype = root.getAttribute('roomtype')
                tc_url = root.getAttribute('rtmp')
                ip = tc_url.split('/')[2].split(':')[0]
                port = int(tc_url.split('/')[2].split(':')[1])
                app = tc_url.split('/')[3]

                if 'bpassword' in response['content']:
                    broadcast_pass = root.getAttribute('bpassword')
                if root.getAttribute('greenroom'):
                    greenroom = True
                else:
                    greenroom = False

                return {
                    'tcurl': tc_url,
                    'ip': ip,
                    'port': port,
                    'app': app,
                    'roomtype': roomtype,
                    'greenroom': greenroom,
                    'bpassword': broadcast_pass
                }
        return None


def get_greenroom_xml(room, proxy=None):
    """

    :param room: str room name.
    :param proxy: str use proxy for this request.
    :return: dict {}
    """
    xmlurl = 'https://apl.tinychat.com/api/find.room/%s?site=greenroom' % room

    response = web.http_get(xmlurl, proxy=proxy)
    if response['content'] is not None:
        xml = parseString(response['content'])

        root = xml.getElementsByTagName('response')[0]
        result = root.getAttribute('result')
        if result == 'PW':  # i don't think this is needed since greenrooms can't have password enabled.
            return result
        else:
            roomtype = root.getAttribute('roomtype')
            tc_url = root.getAttribute('rtmp')
            ip = tc_url.split('/')[2].split(':')[0]
            port = int(tc_url.split('/')[2].split(':')[1])
            app = tc_url.split('/')[3]

            return {
                'tcurl': tc_url,
                'ip': ip,
                'port': port,
                'app': app,
                'roomtype': roomtype
            }


def tinychat_user_info(tc_account):
    """
    Finds info for a given tinychat account name.
    :param tc_account: str the account name.
    :return: dict {'username', 'tinychat_id', 'last_active', 'name', 'location', 'biography'} or None on error.
    """
    url = 'https://tinychat.com/api/tcinfo?username=%s' % tc_account
    response = web.http_get(url=url, json=True)
    log.debug('respnse: %s' % response)
    if response['json'] is not None:
        if 'error' not in response['json']:
            username = response['json']['username']
            user_id = response['json']['id']
            last_active = time.ctime(int(response['json']['last_active']))
            name = response['json']['name']
            location = response['json']['location']
            biography = response['json']['biography']

            return {
                'username': username,
                'tinychat_id': user_id,
                'last_active': last_active,
                'name': name,
                'location': location,
                'biography': biography
            }
        else:
            return None


def spy_info(room):
    """
    Finds info for a given room name.

    The info shows how many mods, broadcasters and total users(list)

    :param room: str the room name to get spy info for.
    :return: dict{'mod_count', 'broadcaster_count', 'total_count', list('users')} or {'error'}
    """
    url = 'https://api.tinychat.com/%s.json' % room
    response = web.http_get(url, json=True)
    log.debug('response: %s' % response)
    if response['json'] is not None:
        if 'error' not in response['json']:
            mod_count = response['json']['mod_count']
            broadcaster_count = response['json']['broadcaster_count']
            total_count = response['json']['total_count']
            if total_count > 0:
                users = response['json']['names']
                return {
                    'mod_count': mod_count,
                    'broadcaster_count': broadcaster_count,
                    'total_count': total_count,
                    'users': users
                }
        else:
            return {'error': response['json']['error']}


def get_bauth_token(roomname, nick, uid, greenroom, proxy=None):
    """
    Find the bauth token needed before we can start a broadcast.
    NOTE: Might need some more work related to green room.
    :param roomname: str the room name.
    :param nick: str the nick we use in the room.
    :param uid: str our ID in the room.
    :param greenroom: bool should be True if greenroom is enabled.
    :param proxy: str use a proxy for this request.
    :return: str token or PW if a password is needed to broadcast.
    """
    if greenroom:
        xmlurl = 'https://tinychat.com/api/broadcast.pw?site=greenroom&name=%s&nick=%s&id=%s' % (roomname, nick, uid)
    else:
        xmlurl = 'https://tinychat.com/api/broadcast.pw?site=tinychat&name=%s&nick=%s&id=%s' % (roomname, nick, uid)

    response = web.http_get(xmlurl, proxy=proxy)
    log.debug('response: %s' % response)
    if response['content'] is not None:
        xml = parseString(response['content'])
        root = xml.getElementsByTagName('response')[0]
        result = root.getAttribute('result')
        if result == 'PW':
            return result
        else:
            token = root.getAttribute('token')
            return token


def get_captcha_key(roomname, uid, proxy=None):
    """
    Find the captcha key needed before we can send messages in a room.
    :param roomname: str the room name.
    :param uid: str the ID we have in the room.
    :param proxy: str use a proxy for this request.
    :return: str the captcha key or None on captcha enabled room.
    """
    url = 'https://tinychat.com/api/captcha/check.php?room=tinychat^%s&guest_id=%s' % (roomname, uid)
    response = web.http_get(url, json=True, proxy=proxy)
    log.debug('response: %s' % response)
    if response['json'] is not None:
        if 'key' in response['json']:
            return response['json']['key']
        else:
            return None


def get_cauth_cookie(roomname, proxy=None):
    """
    Find the cauth 'cookie' needed to make a successful connection.

    NOTE: This is not really a cookie, but named so after its name in the json response.
    :param roomname: str the room name.
    :param proxy: str use a proxy for this request.
    :return: str the 'cookie'
    """
    ts = int(round(time.time() * 1000))
    url = 'https://tinychat.com/cauth?room=%s&t=%s' % (roomname, ts)
    response = web.http_get(url, json=True, proxy=proxy)
    log.debug('response: %s' % response)
    if response['json'] is not None:
        if 'cookie' in response['json']:
            return response['json']['cookie']
        return None


def recaptcha(proxy=None):
    """
    Check if we have to solve a captcha before we can connect.
    If yes, then it will open in the default browser.
    :param proxy: str use a proxy for this request.
    :return: dict{'cookies'} this is NOT used in the code , but are left here for debugging purpose.
    """
    t = str(random.uniform(0.9, 0.10))
    url = 'https://tinychat.com/cauth/captcha?%s' % t
    response = web.http_get(url, json=True, proxy=proxy)
    log.debug('response: %s' % response)
    if response['json'] is not None:
        if response['json']['need_to_solve_captcha'] == 1:
            link = 'https://tinychat.com/cauth/recaptcha?token=%s' % response['json']['token']
            webbrowser.open(link, new=1)
            print (link)
            raw_input('Solve the captcha and click enter to continue.')
        return response['cookies']
