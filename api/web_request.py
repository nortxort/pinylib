""" Functions to make GET and POST requests with. """
import time
import requests

# Default header.
DEFAULT_HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:44.0) Gecko/20100101 Firefox/46.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Referer': 'http://tinychat.com'
}

#  A session that all requests will use.
_request_session = requests.session()


def new_session():
    """ Start a new request.session object. """
    global _request_session
    _request_session = requests.session()


def is_cookie_expired(cookie_name='pass'):
    """
    Check if a cookie is expired.

    NOTE: In the case of tinychat, we only need to check for the cookie named 'pass'
    as all the login cookies ('pass', 'hash' and 'user') expire on the same date.

    :param cookie_name: str the name of the cookie to check.
    :return: True if expired else False or None if no cookie by that name was found.
    """
    expires = int
    timestamp = int(time.time())
    for cookie in _request_session.cookies:
        if cookie.name == cookie_name:
            expires = cookie.expires
        else:
            return None
    if timestamp > expires:
        return True
    return False


def delete_login_cookies():
    """
    Delete tinychat login cookies, thereby login us out.
    :return: True if logged in else False
    """
    if 'pass' in _request_session.cookies:
        del _request_session.cookies['pass']
        del _request_session.cookies['hash']
        del _request_session.cookies['user']
        # del _request_session.cookies['tcuid']
        return True
    return False


def get_request(url, json=False, proxy=None, header=None, timeout=20):
    """
    All functions/methods using GET will use this function.

    :param url: str the url to the web content.
    :param json: bool True if the response is expected to be json.
    :param proxy: str use proxy for this request.
    :param header: dict additional header key/value pairs.
    :param timeout int timeout in seconds.
    :return: dict{'content', 'cookies', 'headers', 'status_code'}
    """
    if header is not None and type(header) is dict:
        DEFAULT_HEADER.update(header)

    if proxy:
        proxy = {'http': 'http://' + proxy}
    try:
        gr = _request_session.request(method='GET', url=url, headers=DEFAULT_HEADER, proxies=proxy, timeout=timeout)
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


def post_request(post_url, post_data, header=None, json=False, proxy=None, timeout=20):
    """
    Makes POST request to a web page.

    :param post_url: str the url to the web page.
    :param post_data: dict or list the post data to send, usually some form data.
    :param header: dict or list additional header key/value pair.
    :param json: boolean True if the response is expected to be json.
    :param proxy: str use a proxy for this request.
    :param timeout: int timeout in seconds.
    :return: dict{'content', 'cookies', 'headers', 'status_code'} or None on error.
    """
    if not post_url:
        raise ValueError('web_request.post_request: no post_url provided. post_url=%s'
                         % post_url)

    elif proxy is not None and type(proxy) is not str:
        raise TypeError('web_request.post_request: proxy must be of type str and in the format ip:port. proxy type=%s'
                        % type(proxy))
    else:
        if header is not None and type(header) is dict:
            DEFAULT_HEADER.update(header)

        if proxy:
            proxy = {'http': 'http://' + proxy}

        try:
            pr = _request_session.request(method='POST', url=post_url, data=post_data, headers=DEFAULT_HEADER,
                                          allow_redirects=False, proxies=proxy, timeout=timeout)
            if json:
                try:
                    content = pr.json()
                except ValueError:
                    return None
            else:
                content = pr.text
            return {'content': content, 'cookies': pr.cookies, 'headers': pr.headers, 'status_code': pr.status_code}
        except (requests.HTTPError, requests.RequestException):
            return None


def post_login(account, password):  # NEW/EDITED/MOVED
    """
    Post tinychat login info.
    :param account: str tinychat account name.
    :param password: str tinychat account password.
    :return: dict{'content', 'cookies', 'headers', 'status_code'} or None on error.
    """
    url = 'http://tinychat.com/login'
    header = {'Referer': url}
    form_data = {
        'form_sent': '1',
        'referer': '',
        'next': '',
        'username': account,
        'password': password,
        'passwordfake': 'Password',
        'remember': '1'
    }
    response = post_request(url, form_data, header=header)
    return response
