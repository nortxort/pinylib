""" Functions to make GET requests, POST login and find mod/pro hashes. """
import requests

#  A session that all requests will use.
_request_session = requests.session()


def new_session():
    """
    Start a new request.session object.
    """
    global _request_session
    _request_session = requests.session()


def delete_login_cookies():
    """
    Delete tinychat login cookies, thereby login us out.
    :return: True if logged in else False
    """
    if 'pass' in _request_session.cookies:
        del _request_session.cookies['pass']
        del _request_session.cookies['hash']
        del _request_session.cookies['user']
        del _request_session.cookies['tcuid']
        return True
    return False


def get_request(url, json=False, proxy=None):
    """
    All functions/methods using GET will use this function.
    :param url: str the url to the web content.
    :param json: bool True if the response is expected to be json.
    :param proxy: str use proxy for this request.
    :return: dict{'content', 'cookies', 'headers', 'status_code'}
    """
    header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:44.0) Gecko/20100101 Firefox/44.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'http://tinychat.com'
        }

    if proxy:
        proxy = {'http': 'http://' + proxy}
    try:
        gr = _request_session.request(method='GET', url=url, headers=header, proxies=proxy, timeout=20)
        if json:
            try:
                content = gr.json()
            except ValueError:
                return None
        else:
            content = gr.text
        return {'content': content, 'cookies': gr.cookies, 'headers': gr.headers, 'status_code': gr.status_code}
    except (requests.ConnectionError, requests.RequestException):
        return None


def post_login(account, password):
    """
    Makes a POST to log us in to tinychat.
    :param account: str the tinychat account name
    :param password: str the tinychat login password
    :return: dict{'content', 'cookies', 'headers', 'status_code'}
    """
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:44.0) Gecko/20100101 Firefox/44.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Referer': 'http://tinychat.com/login'
    }

    form_data = {
        'form_sent': '1',
        'referer': '',
        'next': '',
        'username': account,
        'password':  password,
        'passwordfake': 'Password',
        'remember': '1'
    }

    try:
        post_url = 'http://tinychat.com/login'
        pr = _request_session.request(method='POST', url=post_url, data=form_data, headers=header, allow_redirects=False)

        return {'content': pr.text, 'cookies': pr.cookies, 'headers': pr.headers, 'status_code': pr.status_code}
    except (requests.HTTPError, requests.RequestException):
        return None


def find_hashes(url, proxy=None):
    """
    Find the hashes needed to become mod/pro.
    :param url: str the url to the profile page.
    :return: dict {'autoop', 'prohash'} str hashes.
    """
    autoop = u'none'
    prohash = None

    html = get_request(url, proxy=proxy)
    if html is not None:
        if ', autoop: "' in html['content']:
            autoop = html['content'].split(', autoop: "')[1].split('"')[0]
        if ', prohash: "' in html['content']:
            prohash = html['content'].split(', prohash: "')[1].split('"')[0]

        return {'autoop': autoop, 'prohash': prohash}
