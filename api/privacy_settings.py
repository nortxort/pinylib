import web_request
from bs4 import BeautifulSoup


class TinychatPrivacyPage:
    """
    This class represents tinychats privacy page for a room.

    It contains methods to change a rooms privacy settings.
    """
    def __init__(self, proxy):
        self._proxy = proxy
        self._privacy_url = 'http://tinychat.com/settings/privacy'
        self._validation_key = ''
        self._allow_guests = ''
        self._room_password = ''
        self._broadcast_password = ''
        self._public_directory = ''
        self._push2talk = ''
        self._greenroom = ''
        self.room_moderators = list()

    @staticmethod
    def _is_tc_account(account_name):
        """
        Helper method to check if a user account is a valid account name.
        :param account_name: str the account name to check.
        :return: bool True if it is a valid account, False if invalid account
        """
        url = 'http://tinychat.com/api/tcinfo?username=%s' % account_name
        json_data = web_request.get_request(url=url, json=True)
        if json_data is not None and json_data['content'] is not None:
            if 'error' not in json_data['content']:
                return True
            return False

    def clear_bans(self):
        """ Clear all room bans. """
        url = 'http://tinychat.com/ajax/user/clearbans'
        header = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self._privacy_url
        }
        response = web_request.post_request(url, post_data={}, header=header, json=True, proxy=self._proxy)
        if response['content']['room'] is not None:
            return True
        return False

    def parse_privacy_settings(self, response=None):
        """ Parse privacy settings. """
        header = {
            'Referer': self._privacy_url
        }
        if response is None:
            response = web_request.get_request(self._privacy_url, header=header, proxy=self._proxy)

        if response is not None and response['content'] is not None:
            soup = BeautifulSoup(response['content'], 'html.parser')
            # validation hash key
            validate = soup.find('input', {'type': 'hidden', 'name': 'validate'})
            self._validation_key = validate.get('value')
            # guest mode
            guest_settings = soup.find('select', {'name': 'allowGuests'})
            allow_guests_type = guest_settings.find('option', {'selected': True})
            self._allow_guests = str(allow_guests_type.get('value'))
            # public directory listing
            directory_settings = soup.find('select', {'name': 'public_directory'})
            directory_value = directory_settings.find('option', {'selected': True})
            self._public_directory = str(directory_value.get('value'))
            # push2talk
            push2talk_setting = soup.find('select', {'name': 'push2talk'})
            push2talk_value = push2talk_setting.find('option', {'selected': True})
            self._push2talk = str(push2talk_value.get('value'))
            # green room
            greenroom_setting = soup.find('select', {'name': 'greenroom'})
            greenroom_value = greenroom_setting.find('option', {'selected': True})
            self._greenroom = str(greenroom_value.get('value'))
            # moderators
            moderators = soup.findAll('input', {'type': 'hidden', 'name': 'mods[]'})
            if moderators:
                for mod in moderators:
                    mod_account = str(mod.get('value'))
                    if mod_account not in self.room_moderators:
                        self.room_moderators.append(mod_account)

    def set_room_password(self, password=None):
        """
        Set a room password or clear the password.
        :param password: str the room password or None to clear.
        """
        if password is None:
            self._room_password = ''
        else:
            self._room_password = password
        self._update()

    def set_broadcast_password(self, password=None):
        """
        Set a broadcast password or clear the password.
        :param password: str the broadcast password or None to clear.
        """
        if self._greenroom == '0':
            if password is None:
                self._broadcast_password = ''
            else:
                self._broadcast_password = password
            self._update()

    def make_moderator(self, account):
        """
        Make a user account a moderator.
        :param account: str the account to make a moderator.
        :return bool True if the account was added as a moderator, False if already a moderator
        or None on invalid account name.
        """
        if self._is_tc_account(account):
            if account not in self.room_moderators:
                self.room_moderators.append(account)
                self._update()
                return True
            return False
        return None

    def remove_moderator(self, account):
        """
        Remove a room moderator.
        :param account: str the moderator account
        :return: bool True if removed else False
        """
        if account in self.room_moderators:
            self.room_moderators.remove(account)
            self._update()
            return True
        return False

    def set_guest_mode(self, guest_type):
        """
        Set the guest type mode.
        :param guest_type: str the type of guest allowed.
        """
        if guest_type == 'tw_fb':
            self._allow_guests = '2'
        elif guest_type == 'fb':
            self._allow_guests = '4'
        elif guest_type == 'tw':
            self._allow_guests = '5'
        else:
            self._allow_guests = '1'
        self._update()

    def show_on_directory(self):
        """
        Enables/disables show up on directory setting.
        :return: bool True if enabled else False
        """
        if self._public_directory == '0':
            self._public_directory = '1'
            self._update()
            return True
        elif self._public_directory == '1':
            self._public_directory = '0'
            self._update()
            return False

    def set_push2talk(self):
        """
        Enables/disables push2talk setting.
        :return: bool True if enabled else False
        """
        if self._push2talk == '0':
            self._push2talk = '1'
            self._update()
            return True
        elif self._push2talk == '1':
            self._push2talk = '0'
            self._update()
            return False

    def set_greenroom(self):
        """
        Enables/disables greenroom setting.
        :return: bool True if enabled else False
        """
        if self._greenroom == '0':
            self._greenroom = '1'
            self._update()
            return True
        elif self._greenroom == '1':
            self._greenroom = '0'
            self._update()
            return False

    def _update(self):
        """ Update the privacy settings page. """
        header = {
            'Referer': self._privacy_url
        }

        form_data = [
            ('validate', self._validation_key),
            ('form_sent', '1'),
            ('allowGuests', self._allow_guests),
            ('public_directory', self._public_directory),
            ('push2talk', self._push2talk),
            ('greenroom', self._greenroom),
            ('save', '1'),
            ('roomPassword', self._room_password),
            ('broadcastPassword', self._broadcast_password)
        ]
        for mod in self.room_moderators:
            mod_data = ('mods[]', mod)
            form_data.append(mod_data)

        response = web_request.post_request(self._privacy_url, post_data=form_data, header=header, proxy=self._proxy)
        self.parse_privacy_settings(response=response)
        self._privacy_url = 'http://tinychat.com/settings/privacy?saved=1'
