""" Contains functions to make http GET and http POST with. """
import time
import logging
import requests

log = logging.getLogger(__name__)

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


def is_cookie_expired(cookie_name):
    """
    Check if a cookie is expired.

    :param cookie_name: str the name of the cookie to check.
    :return: True if expired else False or None if no cookie by that name was found.
    """
    if cookie_name:
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


def delete_cookie(cookie_name):
    """
    Delete a cookie by name.
    :param cookie_name: str the cookie name.
    :return: True if deleted else False
    """
    if cookie_name in _request_session.cookies:
        del _request_session.cookies[cookie_name]
        return True
    return False


def http_get(url, json=False, proxy=None, header=None, timeout=20):
    """
    All functions/methods using GET will use this function.

    :param url: str the url to the web content.
    :param json: bool True if the response is expected to be json.
    :param proxy: str use proxy for this request.
    :param header: dict additional header key/value pairs.
    :param timeout int timeout in seconds.
    :return: dict{'content', 'json', 'cookies', 'headers', 'status_code'}
    """
    if header is not None and type(header) is dict:
        DEFAULT_HEADER.update(header)

    if proxy:
        proxy = {'http': 'http://' + proxy}

    gr = None
    json_response = None

    try:
        gr = _request_session.request(method='GET', url=url, headers=DEFAULT_HEADER, proxies=proxy, timeout=timeout)
    except (requests.ConnectionError, requests.RequestException) as re:
        log.error('http_get error: %s' % re)
    finally:
        if gr is None:
            return {
                'content': None,
                'json': None,
                'cookies': None,
                'headers': None,
                'status_code': None
            }
        if json:
            try:
                json_response = gr.json()
            except ValueError as ve:
                log.error('error while decoding %s to json: %s' % (url, ve))
        return {
            'content': gr.text,
            'json': json_response,
            'cookies': gr.cookies,
            'headers': gr.headers,
            'status_code': gr.status_code
        }


def http_post(post_url, post_data, header=None, json=False, proxy=None, timeout=20):
    """
    Makes POST request to a web page.

    :param post_url: str the url to the web page.
    :param post_data: dict or list the post data to send, usually some form data.
    :param header: dict additional header key/value pair.
    :param json: boolean True if the response is expected to be json.
    :param proxy: str use a proxy for this request.
    :param timeout: int timeout in seconds.
    :return: dict{'content', 'json', 'cookies', 'headers', 'status_code'} or None on error.
    """
    if not post_url:
        raise ValueError('web_request.http_post: no post_url provided. post_url=%s'
                         % post_url)

    elif proxy is not None and type(proxy) is not str:
        raise TypeError('web_request.http_post: proxy must be of type str and in the format ip:port. proxy type=%s'
                        % type(proxy))
    else:
        if header is not None and type(header) is dict:
            DEFAULT_HEADER.update(header)

        if proxy:
            proxy = {'http': 'http://' + proxy}

        pr = None
        json_response = None

        try:
            pr = _request_session.request(method='POST', url=post_url, data=post_data, headers=DEFAULT_HEADER,
                                          allow_redirects=False, proxies=proxy, timeout=timeout)
        except (requests.HTTPError, requests.RequestException) as pe:
            log.error('http_post error %s' % pe)
        finally:
            if pr is None:
                return {
                    'content': None,
                    'json': None,
                    'cookies': None,
                    'headers': None,
                    'status_code': None
                }
            if json:
                try:
                    json_response = pr.json()
                except ValueError as ve:
                    log.error('error while decoding %s to json: %s' % (post_url, ve))
            return {
                'content': pr.text,
                'json': json_response,
                'cookies': pr.cookies,
                'headers': pr.headers,
                'status_code': pr.status_code
            }
