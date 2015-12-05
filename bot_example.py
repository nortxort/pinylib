""" Tinychat bot with some basic commands. """
import re
import random
import thread
import tinychat
from api import soundcloud, youtube, other_apis


#  Bot Settings.
OPTIONS = {
    'prefix': '!',                      # Command prefix.
    'key': 'tyf65rr',                   # unique secret key.
    'auto_message_enabled': True,       # auto message sender.
    'auto_message_interval': 300,       # auto message sender interval in seconds.
    'path': 'files/',                   # the path to files.
    'badnicks': 'badnicks.txt',         # bad nicks file.
    'badstrings': 'badstrings.txt',     # bad words file.
    'badaccounts': 'badaccounts.txt'    # bad accounts file.
}


def eightball():
    """
    Magic eight ball.
    :return: a random answer str
    """
    answers = ['It is certain', 'It is decidedly so', 'without a doubt', 'Yes definitely',
               'You may rely on it', 'As I see it, yes', 'Most likely', 'Outlook good', 'Yes', 'Signs point to yes',
               'Reply hazy try again', 'Ask again later', 'Better not tell you now', 'Cannot predict now',
               'Concentrate and ask again', 'Don\'t count on it', 'My reply is no', 'My sources say no',
               'Outlook not so good', 'Very doubtful']
    return random.choice(answers)


class TinychatBot(tinychat.TinychatRTMPClient):
    """ Overrides event methods in TinychatRTMPClient that client should to react to. """
    key = OPTIONS['key']
    no_cam = False
    no_guests = False
    elapsed_track_time = 0
    remaining_track_time = 0
    playlist = []
    search_list = []
    inowplay = 0
    play = True
    user_obj = object

    def on_joinsdone(self):
        if not self.is_reconnected:
            if OPTIONS['auto_message_enabled']:
                thread.start_new_thread(self.start_auto_msg_sender, ())
        thread.start_new_thread(self.send_userinfo_request_to_all, ())

    def on_avon(self, uid, name):
        if self.no_cam:
            self.send_close_user_msg(name)
        else:
            tinychat.console_write([tinychat.COLOR['cyan'], name + ':' + uid + ' is broadcasting.', self.roomname])

    def on_nick(self, old, new, uid):
        old_info = self.find_user_info(old)
        old_info.nick = new
        if old in self.room_users.keys():
            del self.room_users[old]
            del self.id_and_nick[uid]
            # Update user info
            self.room_users[new] = old_info
            self.id_and_nick[uid] = new
        # Is it a new user joining?
        if str(old).startswith('guest-') and uid != self.client_id:
            bad_nicks = tinychat.fh.file_reader(OPTIONS['path'], OPTIONS['badnicks'])
            # Check if the user name is in the badnicks file.
            if bad_nicks is not None and new in bad_nicks:
                # User name is in the badnicks file, ban the user.
                self.send_ban_msg(new, uid)
            else:
                user = self.find_user_info(new)
                if user.user_account is not None:
                    # If user is signed in, greet with account name.
                    self.send_bot_msg('*Welcome to* ' + self.roomname + ' *' + new + '*:' + user.user_account,
                                      self.is_client_mod)
                else:
                    # Else just greet user.
                    self.send_bot_msg('*Welcome to* ' + self.roomname + ' *' + new + '*', self.is_client_mod)
                # Is media playing?
                if len(self.playlist) is not 0:
                    play_type = self.playlist[self.inowplay]['type']
                    video_id = self.playlist[self.inowplay]['video_id']
                    elapsed_time = str(self.elapsed_track_time)
                    # Play the media at the correct start time.
                    self.send_undercover_msg(new, '/mbs ' + play_type + ' ' + video_id + ' ' + elapsed_time)

        tinychat.console_write([tinychat.COLOR['cyan'], old + ':' + uid + ' changed nick to: ' + new, self.roomname])

    # User Info Events
    def user_is_guest(self, uid):
        """
        The user tells us that they are a guest.
        :param uid: str the user ID of the guest user.
        """
        if self.no_guests and self.is_client_mod:
            # Kick users not signed in.
            self.send_ban_msg(str(self.id_and_nick[uid]), str(uid))
            self.send_forgive_msg(uid)
        else:
            user = self.add_user_info(self.id_and_nick[uid])
            user.account = False
        tinychat.console_write([tinychat.COLOR['bright_yellow'], str(self.id_and_nick[uid]) + ' is not signed in.',
                                self.roomname])

    def user_has_account(self, uid, usr_acc):
        """
        A user replies to our user info request, that they have a account name.
        We look up the account using tinychat's API and add the info to the user object.

        :param uid: str the user ID of the user having an account.
        :param usr_acc: str the account that the user has.
        """
        user = self.add_user_info(self.id_and_nick[uid])
        badaccounts = tinychat.fh.file_reader(OPTIONS['path'], OPTIONS['badaccounts'])
        if badaccounts is not None and usr_acc in badaccounts:
            if self.is_client_mod:
                self.send_ban_msg(user.nick, uid)
                # Remove next line to ban.
                self.send_forgive_msg(uid)
        else:
            user.user_account = usr_acc
            if usr_acc == self.roomname:
                user.is_owner = True

            tc_info = tinychat.tinychat_api.tinychat_user_info(usr_acc)
            if tc_info is not None:
                user.tinychat_id = tc_info['tinychat_id']
                user.last_login = tc_info['last_active']

            tinychat.console_write([tinychat.COLOR['bright_yellow'], str(self.id_and_nick[uid]) +
                                    ' has account: ' + usr_acc, self.roomname])

    def message_handler(self, msg_sender, msg):
        """
        Custom command handler.

        NOTE: Any method using a API will be started in a new thread.
        :param msg_sender: str the user sending a message
        :param msg: str the message
        """
        # Get user info object of the user sending the message..
        self.user_obj = self.find_user_info(msg_sender)

        # Is this a custom command?
        if msg.startswith(OPTIONS['prefix']):
            # Split the message in to parts.
            parts = msg.split(' ')
            # parts[0] is the command..
            cmd = parts[0].lower().strip()
            # The rest is a command argument.
            cmd_arg = ' '.join(parts[1:]).strip()

            # Owner commands.
            if cmd == OPTIONS['prefix'] + 'kill':
                self.do_kill()

            elif cmd == OPTIONS['prefix'] + 'reboot':
                self.do_reboot()

            # Mod and bot controller commands
            elif cmd == OPTIONS['prefix'] + 'close':
                self.do_close(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'clear':
                self.do_clear()

            elif cmd == OPTIONS['prefix'] + 'skip':
                self.do_skip()

            elif cmd == OPTIONS['prefix'] + 'up':
                self.do_up()
                
            elif cmd == OPTIONS['prefix'] + 'down':
                self.do_down()

            elif cmd == OPTIONS['prefix'] + 'nick':
                self.do_nick(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'topic':
                self.do_topic(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'kick':
                self.do_kick(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'ban':
                self.do_ban(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'bn':
                self.do_bad_nick(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'rmbn':
                self.do_remove_bad_nick(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'bs':
                self.do_bad_string(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'rmbs':
                self.do_remove_bad_string(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'ba':
                self.do_bad_account(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'rmba':
                self.do_remove_bad_account(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'list':
                self.do_list_info(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'uinfo':
                self.do_user_info(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'ytsrc':
                thread.start_new_thread(self.do_youtube_search, (cmd_arg, ))

            elif cmd == OPTIONS['prefix'] + 'plys':
                self.do_play_youtube_search(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'adls':
                self.do_add_youtube_search(cmd_arg)

            # Public Commands.
            elif cmd == OPTIONS['prefix'] + 'about':
                self.do_about()

            elif cmd == OPTIONS['prefix'] + 'help':
                self.do_help()

            elif cmd == OPTIONS['prefix'] + 'plugin':
                self.do_plugin()

            elif cmd == OPTIONS['prefix'] + 'uptime':
                self.do_uptime()

            elif cmd == OPTIONS['prefix'] + 'pmme':
                self.do_pmme(msg_sender)

            elif cmd == OPTIONS['prefix'] + 'plstat':
                self.do_playlist_status()

            elif cmd == OPTIONS['prefix'] + 'next?':
                self.do_next_tune_in_playlist()

            elif cmd == OPTIONS['prefix'] + 'adl':
                thread.start_new_thread(self.do_add_youtube_to_playlist, (cmd_arg, ))

            elif cmd == OPTIONS['prefix'] + 'adlsc':
                thread.start_new_thread(self.do_add_soundcloud_to_playlist, (cmd_arg, ))

            elif cmd == OPTIONS['prefix'] + 'ply':
                thread.start_new_thread(self.do_play_youtube, (cmd_arg, ))

            elif cmd == OPTIONS['prefix'] + 'sply':
                thread.start_new_thread(self.do_play_private_youtube, (msg_sender, cmd_arg, ))

            elif cmd == OPTIONS['prefix'] + 'plysc':
                thread.start_new_thread(self.do_play_soundcloud, (cmd_arg, ))

            elif cmd == OPTIONS['prefix'] + 'splysc':
                thread.start_new_thread(self.do_play_private_soundcloud, (msg_sender, cmd_arg, ))

            # Tinychat API commands.
            elif cmd == OPTIONS['prefix'] + 'spy':
                thread.start_new_thread(self.do_spy, (msg_sender, cmd_arg, ))

            elif cmd == OPTIONS['prefix'] + 'usrspy':
                thread.start_new_thread(self.do_account_spy, (msg_sender, cmd_arg, ))

            # Other API commands.
            elif cmd == OPTIONS['prefix'] + 'urb':
                thread.start_new_thread(self.do_search_urban_dictionary, (cmd_arg, ))

            elif cmd == OPTIONS['prefix'] + 'wea':
                thread.start_new_thread(self.do_weather_search, (cmd_arg, ))

            elif cmd == OPTIONS['prefix'] + 'ip':
                thread.start_new_thread(self.do_whois_ip, (cmd_arg, ))

            # Just for fun.
            elif cmd == OPTIONS['prefix'] + 'cn':
                thread.start_new_thread(self.do_chuck_noris, ())

            elif cmd == OPTIONS['prefix'] + '8ball':
                self.do_8ball(cmd_arg)

            #  Print command to console.
            tinychat.console_write([tinychat.COLOR['yellow'], msg_sender + ':' + cmd + ' ' + cmd_arg, self.roomname])
        else:
            #  Print chat message to console.
            tinychat.console_write([tinychat.COLOR['green'], msg_sender + ':' + msg, self.roomname])
            # Only check chat msg for bad string if we are mod.
            if self.is_client_mod:
                thread.start_new_thread(self.check_msg_for_bad_string, (msg, ))

        # add msg to user object last_msg
        self.user_obj.last_msg = msg

    # == Owner Only Command Methods. ==
    def do_kill(self):
        """ Kills the bot. """
        if self.user_obj.is_owner:
            self.disconnect()

    def do_reboot(self):
        """ Reboots the bot. """
        if self.user_obj.is_owner:
            self.reconnect()

    # == Mod And Bot Controller Command Methods. ==
    def do_close(self, user_name):
        """
        Close a user broadcasting.
        :param user_name: str the username to close.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(user_name) is 0:
                    self.send_bot_msg('Missing username.', self.is_client_mod)
                else:
                    user = self.find_user_info(user_name)
                    if user is not None:
                        self.send_close_user_msg(user_name)
                    else:
                        self.send_bot_msg('No user named: ' + user_name, self.is_client_mod)

    def do_clear(self):
        """ Clears the chatbox. """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                for x in range(0, 10):
                    self.send_owner_run_msg(' ')
            else:
                clear = '133,133,133,133,133,133,133,133,133,133,133,133,133,133,133'
                self._sendCommand('privmsg', [clear, tinychat.random_color() + ',en'])

    def do_skip(self):
        """ Play the next item in the playlist. """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if len(self.playlist) is not 0:
                self.play = False

    def do_up(self):
        """ Makes the bot camup. """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            self.send_bauth_msg()
            self._sendCreateStream()
            self._sendPublish()

    def do_down(self):
        """ Makes the bot cam down. """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            self._sendCloseStream()

    def do_nick(self, new_nick):
        """
        Set a new nick for the bot.
        :param new_nick: str the new nick.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if len(new_nick) is 0:
                self.client_nick = tinychat.create_random_string(5, 25)
                self.set_nick()
            else:
                if re.match('^[][\{\}a-zA-Z0-9_-]{1,25}$', new_nick):
                    self.client_nick = new_nick
                    self.set_nick()

    def do_topic(self, topic):
        """
        Sets the room topic.
        :param topic: str the new topic.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(topic) is 0:
                    self.send_topic_msg('')
                    self.send_bot_msg('Topic was cleared.', self.is_client_mod)
                else:
                    self.send_topic_msg(topic)
                    self.send_bot_msg('The room topic was set to: ' + topic, self.is_client_mod)
            else:
                self.send_bot_msg('Command not enabled')

    def do_kick(self, user_name):
        """
        Kick a user out of the room.
        :param user_name: str the username to kick.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(user_name) is 0:
                    self.send_bot_msg('Missing username.', self.is_client_mod)
                elif user_name == self.client_nick:
                    self.send_bot_msg('Action not allowed.', self.is_client_mod)
                else:
                    user = self.find_user_info(user_name)
                    if user is None:
                        self.send_bot_msg('No user named: *' + user_name + '*', self.is_client_mod)
                    else:
                        self.send_ban_msg(user_name, user.id)
                        self.send_forgive_msg(user.id)
            else:
                self.send_bot_msg('Command not enabled.')

    def do_ban(self, user_name):
        """
        Ban a user from the room.
        :param user_name: str the username to ban.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(user_name) is 0:
                    self.send_bot_msg('Missing username.', self.is_client_mod)
                elif user_name == self.client_nick:
                    self.send_bot_msg('Action not allowed.', self.is_client_mod)
                else:
                    user = self.find_user_info(user_name)
                    if user is None:
                        self.send_bot_msg('No user named: *' + user_name + '*', self.is_client_mod)
                    else:
                        self.send_ban_msg(user_name, user.id)

    def do_bad_nick(self, bad_nick):
        """
        Adds a bad username to the bad nicks file.
        :param bad_nick: str the bad nick to write to file.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_nick) is 0:
                    self.send_bot_msg('Missing username.', self.is_client_mod)
                else:
                    badnicks = tinychat.fh.file_reader(OPTIONS['path'], OPTIONS['badnicks'])
                    if badnicks is None:
                        tinychat.fh.file_writer(OPTIONS['path'], OPTIONS['badnicks'], bad_nick)
                    else:
                        if bad_nick in badnicks:
                            self.send_bot_msg(bad_nick + ' is already in list.', self.is_client_mod)
                        else:
                            tinychat.fh.file_writer(OPTIONS['path'], OPTIONS['badnicks'], bad_nick)
                            self.send_bot_msg('*' + bad_nick + '* was added to file.', self.is_client_mod)

    def do_remove_bad_nick(self, bad_nick):
        """
        Removes a bad nick from bad nicks file.
        :param bad_nick: str the bad nick to remove from file.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_nick) is 0:
                    self.send_bot_msg('Missing username', self.is_client_mod)
                else:
                    rem = tinychat.fh.remove_from_file(OPTIONS['path'], OPTIONS['badnicks'], bad_nick)
                    if rem:
                        self.send_bot_msg(bad_nick + ' was removed.', self.is_client_mod)

    def do_bad_string(self, bad_string):
        """
        Adds a bad string to the bad strings file.
        :param bad_string: str the bad string to add to file.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_string) is 0:
                    self.send_bot_msg('Bad string can\'t be blank.', self.is_client_mod)
                elif len(bad_string) < 3:
                    self.send_bot_msg('Bad string to short: ' + str(len(bad_string)), self.is_client_mod)
                else:
                    bad_strings = tinychat.fh.file_reader(OPTIONS['path'], OPTIONS['badstrings'])
                    if bad_strings is None:
                        tinychat.fh.file_writer(OPTIONS['path'], OPTIONS['badstrings'], bad_string)
                    else:
                        if bad_string in bad_strings:
                            self.send_bot_msg(bad_string + ' is already in list.', self.is_client_mod)
                        else:
                            tinychat.fh.file_writer(OPTIONS['path'], OPTIONS['badstrings'], bad_string)
                            self.send_bot_msg('*' + bad_string + '* was added to file.', self.is_client_mod)

    def do_remove_bad_string(self, bad_string):
        """
        Removes a bad string from the bad strings file.
        :param bad_string: str the bad string to remove from file.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_string) is 0:
                    self.send_bot_msg('Missing word string.', self.is_client_mod)
                else:
                    rem = tinychat.fh.remove_from_file(OPTIONS['path'], OPTIONS['badstrings'], bad_string)
                    if rem:
                        self.send_bot_msg(bad_string + ' was removed.', self.is_client_mod)

    def do_bad_account(self, bad_account_name):
        """
        Adds a bad account name to the bad accounts file.
        :param bad_account_name: str the bad account name to add to the bad accounts file.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_account_name) is 0:
                    self.send_bot_msg('Account can\'t be blank.', self.is_client_mod)
                elif len(bad_account_name) < 3:
                    self.send_bot_msg('Account to short: ' + str(len(bad_account_name)), self.is_client_mod)
                else:
                    bad_accounts = tinychat.fh.file_reader(OPTIONS['path'], OPTIONS['badaccounts'])
                    if bad_accounts is None:
                        tinychat.fh.file_writer(OPTIONS['path'], OPTIONS['badaccounts'], bad_account_name)
                    else:
                        if bad_account_name in bad_accounts:
                            self.send_bot_msg(bad_account_name + ' is already in list.', self.is_client_mod)
                        else:
                            tinychat.fh.file_writer(OPTIONS['path'], OPTIONS['badaccounts'], bad_account_name)
                            self.send_bot_msg('*' + bad_account_name + '* was added to file.', self.is_client_mod)

    def do_remove_bad_account(self, bad_account):
        """
        Removes a bad account from the bad accounts file.
        :param bad_account: str the badd account name to remove from file.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_account) is 0:
                    self.send_bot_msg('Missing account.', self.is_client_mod)
                else:
                    rem = tinychat.fh.remove_from_file(OPTIONS['path'], OPTIONS['badaccounts'], bad_account)
                    if rem:
                        self.send_bot_msg(bad_account + ' was removed.', self.is_client_mod)

    def do_list_info(self, list_type):
        """
        Shows info of different lists/files.
        :param list_type: str the type of list to find info for.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(list_type) is 0:
                    self.send_bot_msg('Missing list type.', self.is_client_mod)
                else:
                    if list_type.lower() == 'bn':
                        bad_nicks = tinychat.fh.file_reader(OPTIONS['path'], OPTIONS['badnicks'])
                        if bad_nicks is None:
                            self.send_bot_msg('No items in this list.', self.is_client_mod)
                        else:
                            self.send_bot_msg(str(len(bad_nicks)) + ' bad nicks in list.', self.is_client_mod)

                    elif list_type.lower() == 'bs':
                        bad_strings = tinychat.fh.file_reader(OPTIONS['path'], OPTIONS['badstrings'])
                        if bad_strings is None:
                            self.send_bot_msg('No items in this list.', self.is_client_mod)
                        else:
                            self.send_bot_msg(str(len(bad_strings)) + ' bad strings in list.', self.is_client_mod)

                    elif list_type.lower() == 'ba':
                        bad_accounts = tinychat.fh.file_reader(OPTIONS['path'], OPTIONS['badaccounts'])
                        if bad_accounts is None:
                            self.send_bot_msg('No items in this list.', self.is_client_mod)
                        else:
                            self.send_bot_msg(str(len(bad_accounts)) + ' bad accounts in list.', self.is_client_mod)

                    elif list_type.lower() == 'pl':
                        if len(self.playlist) is not 0:
                            i_count = 0
                            for i in range(self.inowplay, len(self.playlist)):
                                v_time = self.to_human_time(self.playlist[i]['video_time'])
                                v_title = self.playlist[i]['video_title']
                                if i_count <= 4:
                                    if i_count == 0:
                                        self.send_owner_run_msg('*>>> %s* %s' % (v_title, v_time))
                                    else:
                                        self.send_owner_run_msg('(%s) *%s* %s' % (i, v_title, v_time))
                                    i_count += 1

    def do_user_info(self, user_name):
        """
        Shows user object info for a given user name.
        :param user_name: str the user name of the user to show the info for.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(user_name) is 0:
                    self.send_bot_msg('Missing username.', self.is_client_mod)
                else:
                    user = self.find_user_info(user_name)
                    if user is None:
                        self.send_bot_msg('No user named: ' + user_name, self.is_client_mod)
                    else:
                        self.send_owner_run_msg('*ID:* ' + str(user.id))
                        self.send_owner_run_msg('*Is Mod:* ' + str(user.is_mod))
                        self.send_owner_run_msg('*Bot Control:* ' + str(user.has_power))
                        if user.tinychat_id is not None:
                            self.send_owner_run_msg('*Owner:* ' + str(user.is_owner))
                            self.send_owner_run_msg('*Account:* ' + str(user.user_account))
                            self.send_owner_run_msg('*Tinychat ID:* ' + str(user.tinychat_id))
                            self.send_owner_run_msg('*Last login:* ' + str(user.last_login))
                        self.send_owner_run_msg('*Last message:* ' + str(user.last_msg))

    def do_youtube_search(self, search_str):
        """
        Searches youtube for a given search term, and adds the results to a list.
        :param search_str: str the search term to search for.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(search_str) is 0:
                    self.send_bot_msg('Missing search term.', self.is_client_mod)
                else:
                    self.search_list = youtube.youtube_search_list(search_str, results=5)
                    if len(self.search_list) is not 0:
                        for i in range(0, len(self.search_list)):
                            v_time = self.to_human_time(self.search_list[i]['video_time'])
                            v_title = self.search_list[i]['video_title']
                            self.send_owner_run_msg('(%s) *%s* %s' % (i, v_title, v_time))
                    else:
                        self.send_bot_msg('Could not find: ' + search_str, self.is_client_mod)

    def do_play_youtube_search(self, int_choice):
        """
        Plays a youtube from the search list.
        :param int_choice: int the index in the search list to play.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(self.search_list) > 0:
                    try:
                        index_choice = int(int_choice)
                        if 0 <= index_choice <= 4:
                            if len(self.playlist) <= 2:
                                self.play_youtube(self.search_list[index_choice]['video_id'])
                            else:
                                self.send_bot_msg('No can do, when playlist is playing.', self.is_client_mod)
                        else:
                            self.send_bot_msg('Please make a choice between 0-4', self.is_client_mod)
                    except ValueError:
                        self.send_bot_msg('Only numbers allowed.', self.is_client_mod)

    def do_add_youtube_search(self, int_choice):
        """
        Adds a youtube from the search list to the play list.
        :param int_choice: int the index on the search list to add to the play list.
        """
        if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(self.search_list) > 0:
                    try:
                        index_choice = int(int_choice)
                        if 0 <= index_choice <= 4:
                            self.playlist.append(self.search_list[index_choice])
                            video_title = self.search_list[index_choice]['video_title']
                            self.send_bot_msg('*Added:* ' + video_title + ' *to playlist.*', self.is_client_mod)
                            if len(self.playlist) == 2:
                                thread.start_new_thread(self.start_playlist, ())
                        else:
                            self.send_bot_msg('Please make a choice between 0-4', self.is_client_mod)
                    except ValueError:
                        self.send_bot_msg('Only numbers allowed.', self.is_client_mod)

    # == Public Command Methods. ==
    def do_about(self):
        """ Posts a link to github readme/wiki or other info page about the bot. """
        self.send_bot_msg('http://github.com/nortxort/pinylib/wiki', self.is_client_mod)

    def do_help(self):
        """ Posts a link to github readme/wiki or other page about the bot commands. """
        self.send_bot_msg('https://github.com/nortxort/pinylib/wiki/commands', self.is_client_mod)

    def do_plugin(self):
        """ Posts a link to the tinychat modified "flash game maximizer" firefox plugin. """
        self.send_bot_msg('http://www.mediafire.com/download/' +
                          'or62j65oz428igj/flash_game_maximizer-1.3.6-fx6%28tinychat_mod%29.xpi', self.is_client_mod)

    def do_uptime(self):
        """ Shows the bots uptime. """
        self.send_bot_msg('*Uptime: ' + self.to_human_time(self.uptime, is_seconds=True) + '*', self.is_client_mod)

    def do_pmme(self, msg_sender):
        """
        Opens a PM session with the bot.
        :param msg_sender: str the sender to respond to.
        """
        self.send_private_bot_msg('How can i help you *' + msg_sender + '*?', msg_sender)

    #  == Media Related Command Methods. ==
    def do_playlist_status(self):
        """ Shows info about the playlist. """
        if self.is_client_mod:
            if len(self.playlist) is 0:
                self.send_bot_msg('*The playlist is empty.*', self.is_client_mod)
            else:
                inquee = len(self.playlist) - self.inowplay - 1
                self.send_bot_msg(str(len(self.playlist)) + ' *items in the playlist.* ' + str(inquee) +
                                  ' *Still in queue.*', self.is_client_mod)
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_next_tune_in_playlist(self):
        """ Shows next item in the playlist. """
        if self.is_client_mod:
            if len(self.playlist) == 0:
                self.send_bot_msg('No tunes in the playlist.', self.is_client_mod)
            else:
                if self.inowplay + 1 == len(self.playlist):
                    self.send_bot_msg('This is the last tune in the playlist.', self.is_client_mod)
                else:
                    play_time = self.to_human_time(self.playlist[self.inowplay + 1]['video_time'])
                    play_title = self.playlist[self.inowplay + 1]['video_title']
                    self.send_bot_msg('*Next tune is:* ' + play_title + ' ' + play_time, self.is_client_mod)
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_add_youtube_to_playlist(self, search_str):
        """
        Searches for, and adds a youtube video to the playlist.
        :param search_str: str the search term.
        """
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_bot_msg('Please specify youtube title, id or link.', self.is_client_mod)
            else:
                _youtube = youtube.youtube_search(search_str)
                if _youtube is None:
                    self.send_bot_msg('Could not find video: ' + search_str, self.is_client_mod)
                else:
                    play_time = self.to_human_time(_youtube['video_time'])
                    video_title = _youtube['video_title']
                    self.send_bot_msg('*Added:* ' + video_title + ' *to playlist.* ' + play_time, self.is_client_mod)
                    self.playlist.append(_youtube)
                    if len(self.playlist) == 2:
                        # thread.start_new_thread(self.start_playlist, ())
                        self.start_playlist()
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_add_soundcloud_to_playlist(self, search_str):
        """
        Searches for, and adds a soundcloud track to the playlist.
        :param search_str: str the search term.
        """
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_bot_msg('Please specify soundcloud title or id.', self.is_client_mod)
            else:
                _soundcloud = soundcloud.soundcloud_search(search_str)
                if _soundcloud is None:
                    self.send_bot_msg('Could not find video: ' + search_str, self.is_client_mod)
                else:
                    self.send_bot_msg('*Added:* ' + _soundcloud['video_title'] + ' *to playlist.* ' +
                                      self.to_human_time(_soundcloud['video_time']), self.is_client_mod)
                    self.playlist.append(_soundcloud)
                    if len(self.playlist) == 2:
                        # thread.start_new_thread(self.start_playlist, ())
                        self.start_playlist()
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_play_youtube(self, search_str):
        """
        Plays a youtube video matching the search term.
        :param search_str: str the search term.
        """
        if self.is_client_mod:
            if len(self.playlist) >= 2:
                self.send_bot_msg('Cannot play youtube when playlist is playing. Use *!adl* instead.',
                                  self.is_client_mod)
            else:
                if len(search_str) is 0:
                    self.send_bot_msg('Please specify youtube title, id or link.', self.is_client_mod)
                else:
                    _youtube = youtube.youtube_search(search_str)
                    if _youtube is None:
                        self.send_bot_msg('Could not find video: ' + search_str, self.is_client_mod)
                    else:
                        self.play_youtube(_youtube['video_id'])
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_play_private_youtube(self, msg_sender, search_str):
        """
        Plays a youtube matching the search term privately.
        NOTE: The video will only be visible for the message sender.
        :param msg_sender: str the message sender.
        :param search_str: str the search term.
        """
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_undercover_msg(msg_sender, 'Please specify youtube title, id or link.')
            else:
                _youtube = youtube.youtube_search(search_str)
                if _youtube is None:
                    self.send_undercover_msg(msg_sender, 'Could not find video: ' + search_str)
                else:
                    self.send_undercover_msg(msg_sender, '/mbs youTube ' + _youtube['video_id'] + ' 0')
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_play_soundcloud(self, search_str):
        """
        Plays a soundcloud matching the search term.
        :param search_str: str the search term.
        """
        if self.is_client_mod:
            if len(self.playlist) >= 2:
                self.send_bot_msg('Cannot play soundcloud when playlist is playing. Use *!adlsc* instead.',
                                  self.is_client_mod)
            else:
                if len(search_str) is 0:
                    self.send_bot_msg('Please specify soundcloud title or id.', self.is_client_mod)
                else:
                    _soundcloud = soundcloud.soundcloud_search(search_str)
                    if _soundcloud is None:
                        self.send_bot_msg('Could not find soundcloud: ' + search_str, self.is_client_mod)
                    else:
                        self.play_soundcloud(_soundcloud['video_id'])
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_play_private_soundcloud(self, msg_sender, search_str):
        """
        Plays a soundcloud matching the search term privately.
        NOTE: The video will only be visible for the message sender.
        :param msg_sender: str the message sender.
        :param search_str: str the search term.
        """
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_undercover_msg(msg_sender, 'Please specify soundcloud title or id.')
            else:
                _soundcloud = soundcloud.soundcloud_search(search_str)
                if _soundcloud is None:
                    self.send_undercover_msg(msg_sender, 'Could not find video: ' + search_str)
                else:
                    self.send_undercover_msg(msg_sender, '/mbs soundCloud ' + _soundcloud['video_id'] + ' 0')
        else:
            self.send_bot_msg('Not enabled right now..')

    # == Tinychat API Command Methods. ==
    def do_spy(self, msg_sender, roomname):
        """
        Shows info for a given room.
        :param msg_sender: str the message sender.
        :param roomname: str the room name to find info for.
        """
        if self.is_client_mod:
            if len(roomname) is 0:
                self.send_undercover_msg(msg_sender, 'Missing room name.')
            else:
                spy_info = tinychat.tinychat_api.spy_info(roomname)
                if spy_info is None:
                    self.send_undercover_msg(msg_sender, 'The room is empty.')
                elif spy_info == 'PW':
                    self.send_undercover_msg(msg_sender, 'The room is password protected.')
                else:
                    self.send_undercover_msg(msg_sender,
                                             '*mods:* ' + spy_info['mod_count'] +
                                             ' *Broadcasters:* ' + spy_info['broadcaster_count'] +
                                             ' *Users:* ' + spy_info['total_count'])
                    if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
                        users = ', '.join(spy_info['users'])
                        self.send_undercover_msg(msg_sender, '*' + users + '*')

    def do_account_spy(self, msg_sender, account):
        """
        Shows info about a tinychat account.
        :param msg_sender: str the message sender.
        :param account: str tinychat account.
        """
        if self.is_client_mod:
            if len(account) is 0:
                self.send_undercover_msg(msg_sender, 'Missing username to search for.')
            else:
                tc_usr = tinychat.tinychat_api.tinychat_user_info(account)
                if tc_usr is None:
                    self.send_undercover_msg(msg_sender, 'Could not find tinychat info for: ' + account)
                else:
                    self.send_undercover_msg(msg_sender,
                                             'ID: ' + tc_usr['tinychat_id'] +
                                             ', Last login: ' + tc_usr['last_active'])

    # == Other API Command Methods. ==
    def do_search_urban_dictionary(self, search_str):
        """
        Shows urbandictionary definition of search string.
        :param search_str: str the search string to look up a definition for.
        """
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_bot_msg('Please specify something to look up.', self.is_client_mod)
            else:
                urban = other_apis.urbandictionary_search(search_str)
                if urban is None:
                    self.send_bot_msg('Could not find a definition for: ' + search_str, self.is_client_mod)
                else:
                    if len(urban) > 70:
                        urb_parts = str(urban).split('.')
                        self.send_bot_msg(urb_parts[0].strip(), self.is_client_mod)
                        self.send_bot_msg(urb_parts[1].strip(), self.is_client_mod)
                    else:
                        self.send_bot_msg(urban, self.is_client_mod)

    def do_weather_search(self, search_str):
        """
        Shows weather info for a given search string.
        :param search_str: str the search string to find weather data for.
        """
        if len(search_str) is 0:
            self.send_bot_msg('Please specify a city to search for.', self.is_client_mod)
        else:
            weather = other_apis.weather_search(search_str)
            if weather is None:
                self.send_bot_msg('Could not find weather data for: ' + search_str, self.is_client_mod)
            else:
                self.send_bot_msg(weather, self.is_client_mod)

    def do_whois_ip(self, ip_str):
        """
        Shows whois info for a given ip address.
        :param ip_str: str the ip address to find info for.
        """
        if len(ip_str) is 0:
            self.send_bot_msg('Please provide an IP address.', self.is_client_mod)
        else:
            whois = other_apis.whois(ip_str)
            if whois is None:
                self.send_bot_msg('No info found for: ' + ip_str, self.is_client_mod)
            else:
                self.send_bot_msg(whois)

    # == Just For Fun Command Methods. ==
    def do_chuck_noris(self):
        """ Shows a chuck norris joke/quote. """
        chuck = other_apis.chuck_norris()
        if chuck is not None:
            self.send_bot_msg(chuck, self.is_client_mod)

    def do_8ball(self, question):
        """
        Shows magic eight ball answer to a yes/no question.
        :param question: str the yes/no question.
        """
        if len(question) is 0:
            self.send_bot_msg('Question.', self.is_client_mod)
        else:
            self.send_bot_msg('*8Ball* ' + eightball(), self.is_client_mod)

    def private_message_handler(self, msg_sender, private_msg):
        """
        Custom private message commands.
        :param msg_sender: str the user sending the private message.
        :param private_msg: str the private message.
        """

        # Get user info object of the user sending the message..
        self.user_obj = self.find_user_info(msg_sender)

        # Is this a custom PM command?
        if private_msg.startswith(OPTIONS['prefix']):
            # Split the message in to parts.
            pm_parts = private_msg.split(' ')
            # pm_parts[0] is the command.
            pm_cmd = pm_parts[0].lower().strip()
            # The rest is a command argument.
            pm_arg = ' '.join(pm_parts[1:]).strip()

            # Owner commands.
            if pm_cmd == OPTIONS['prefix'] + 'key':
                self.do_key(msg_sender, pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'clrbn':
                self.do_clear_bad_nicks()

            elif pm_cmd == OPTIONS['prefix'] + 'clrbs':
                self.do_clear_bad_strings()

            elif pm_cmd == OPTIONS['prefix'] + 'clrba':
                self.do_clear_bad_accounts()

            # Mod and bot controller commands.
            elif pm_cmd == OPTIONS['prefix'] + 'op':
                self.do_op_user(msg_sender, pm_parts)

            elif pm_cmd == OPTIONS['prefix'] + 'deop':
                self.do_deop_user(msg_sender, pm_parts)

            elif pm_cmd == OPTIONS['prefix'] + 'nocam':
                self.do_nocam(msg_sender, pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'noguest':
                self.do_no_guest(msg_sender, pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'skip':
                self.do_skip()

            # Public commands.
            elif pm_cmd == OPTIONS['prefix'] + 'opme':
                self.do_opme(msg_sender, pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'pm':
                self.do_pm_bridge(msg_sender, pm_parts)

        # Print to console.
        tinychat.console_write([tinychat.COLOR['white'], 'Private message from ' + msg_sender + ':' + private_msg,
                                self.roomname])

    # == Owner Command Methods. ==
    def do_key(self, msg_sender, new_key):
        """
        Shows or sets a new secret key.
        :param msg_sender: str the message sender.
        :param new_key: str the new secret key.
        """
        if self.user_obj.is_owner:
            if len(new_key) is 0:
                self.send_private_bot_msg('The current key is: *' + self.key + '*', msg_sender)
            elif len(new_key) < 6:
                self.send_private_bot_msg('Key must be at least 6 characters long: ' + str(len(self.key)), msg_sender)
            elif len(new_key) >= 6:
                self.key = new_key
                self.send_private_bot_msg('The key was changed to: *' + self.key + '*', msg_sender)

    def do_clear_bad_nicks(self):
        """ Clears the bad nicks file. """
        if self.user_obj.is_owner:
            tinychat.fh.delete_file_content(OPTIONS['path'], OPTIONS['badnicks'])

    def do_clear_bad_strings(self):
        """ Clears the bad strings file. """
        if self.user_obj.is_owner:
            tinychat.fh.delete_file_content(OPTIONS['path'], OPTIONS['badstrings'])

    def do_clear_bad_accounts(self):
        """ Clears the bad accounts file. """
        if self.user_obj.is_owner:
            tinychat.fh.delete_file_content(OPTIONS['path'], OPTIONS['badaccounts'])

    # == Mod And Bot Controller Command Methods. ==
    def do_op_user(self, msg_sender, msg_parts):
        """
        Lets the room owner, a mod or a bot controller make another user a bot controller.
        NOTE: Mods or bot controllers will have to provide a key, owner does not.
        :param msg_sender: str the message sender.
        :param msg_parts: list the pm message as a list.
        """
        if self.user_obj.is_owner:
            if len(msg_parts) == 1:
                self.send_private_bot_msg('Missing username.', msg_sender)
            elif len(msg_parts) == 2:
                user = self.find_user_info(msg_parts[1])
                if user is not None:
                    user.has_power = True
                    self.send_private_bot_msg(user.nick + ' is now a bot controller.', msg_sender)
                else:
                    self.send_private_bot_msg('No user named: ' + msg_parts[1], msg_sender)

        elif self.user_obj.is_mod or self.user_obj.has_power:
            if len(msg_parts) == 1:
                self.send_private_bot_msg('Missing username.', msg_sender)
            elif len(msg_parts) == 2:
                self.send_private_bot_msg('Missing key.', msg_sender)
            elif len(msg_parts) == 3:
                if msg_parts[2] == self.key:
                    user = self.find_user_info(msg_parts[1])
                    if user is not None:
                        user.has_power = True
                        self.send_private_bot_msg(user.nick + ' is now a bot controller.', msg_sender)
                    else:
                        self.send_private_bot_msg('No user named: ' + msg_parts[1], msg_sender)
                else:
                    self.send_private_bot_msg('Wrong key.', msg_sender)

    def do_deop_user(self, msg_sender, msg_parts):
        """
        Lets the room owner, a mod or a bot controller remove a user from being a bot controller.
        NOTE: Mods or bot controllers will have to provide a key, owner does not.
        :param msg_sender: str the message sender.
        :param msg_parts: list the pm message as a list
        """
        if self.user_obj.is_owner:
            if len(msg_parts) == 1:
                self.send_private_bot_msg('Missing username.', msg_sender)
            elif len(msg_parts) == 2:
                user = self.find_user_info(msg_parts[1])
                if user is not None:
                    user.has_power = False
                    self.send_private_bot_msg(user.nick + ' is not a bot controller anymore.', msg_sender)
                else:
                    self.send_private_bot_msg('No user named: ' + msg_parts[1], msg_sender)

        elif self.user_obj.is_mod or self.user_obj.has_power:
            if len(msg_parts) == 1:
                self.send_private_bot_msg('Missing username.', msg_sender)
            elif len(msg_parts) == 2:
                self.send_private_bot_msg('Missing key.', msg_sender)
            elif len(msg_parts) == 3:
                if msg_parts[2] == self.key:
                    user = self.find_user_info(msg_parts[1])
                    if user is not None:
                        user.has_power = False
                        self.send_private_bot_msg(user.nick + ' is not a bot controller anymore.', msg_sender)
                    else:
                        self.send_private_bot_msg('No user named: ' + msg_parts[1], msg_sender)
                else:
                    self.send_private_bot_msg('Wrong key.', msg_sender)

    def do_nocam(self, msg_sender, key):
        """
        Toggles if broadcasting is allowed or not.
        NOTE: Mods or bot controllers will have to provide a key, owner does not.
        :param msg_sender: str the message sender.
        :param key: str secret key.
        """
        if self.no_cam:
            if self.user_obj.is_owner:
                self.no_cam = False
                self.send_private_bot_msg('*Broadcasting is allowed.*', msg_sender)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_bot_msg('missing key.', msg_sender)
                elif key == self.key:
                    self.no_cam = False
                    self.send_private_bot_msg('*Broadcasting is allowed.*', msg_sender)
                else:
                    self.send_private_bot_msg('Wrong key.', msg_sender)
        else:
            if self.user_obj.is_owner:
                self.no_cam = True
                self.send_private_bot_msg('*Broadcasting is NOT allowed.*', msg_sender)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_bot_msg('missing key.', msg_sender)
                elif key == self.key:
                    self.no_cam = True
                    self.send_private_bot_msg('*Broadcasting is NOT allowed.*', msg_sender)
                else:
                    self.send_private_bot_msg('Wrong key.', msg_sender)

    def do_no_guest(self, msg_sender, key):
        """
        Toggles if guests are allowed to join the room or not.
        NOTE: Mods or bot controllers will have to provide a key, owner does not.
        :param msg_sender: str the m,essage sender.
        :param key: str secret key.
        """
        if self.no_guests:
            if self.user_obj.is_owner:
                self.no_guests = False
                self.send_private_bot_msg('*Guests ARE allowed to join.*', msg_sender)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_bot_msg('missing key.', msg_sender)
                elif key == self.key:
                    self.no_guests = False
                    self.send_private_bot_msg('*Guests ARE allowed to join.*', msg_sender)
                else:
                    self.send_private_bot_msg('Wrong key.', msg_sender)
        else:
            if self.user_obj.is_owner:
                self.no_guests = True
                self.send_private_bot_msg('*Guests are NOT allowed to join.*', msg_sender)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_bot_msg('missing key.', msg_sender)
                elif key == self.key:
                    self.no_guests = True
                    self.send_private_bot_msg('*Guests are NOT allowed to join.*', msg_sender)
                else:
                    self.send_private_bot_msg('Wrong key.', msg_sender)

    # == Public PM Command Methods. ==
    def do_opme(self, msg_sender, key):
        """
        Makes a user a bot controller if user provides the right key.
        :param msg_sender: str the message sender.
        :param key: str the secret key.
        """
        if key == self.key:
            self.user_obj.has_power = True
            self.send_private_bot_msg('You are now a bot controller.', msg_sender)
        else:
            self.send_private_bot_msg('Wrong key.', msg_sender)

    def do_pm_bridge(self, msg_sender, pm_parts):
        """
        Makes the bot work as a PM message bridge between 2 user not signed in.
        :param msg_sender: str the message sender.
        :param pm_parts: list the pm message as a list.
        """
        if len(pm_parts) == 1:
            self.send_private_bot_msg('Missing username.', msg_sender)
        elif len(pm_parts) == 2:
            self.send_private_bot_msg('The command is: !pm username message', msg_sender)
        elif len(pm_parts) == 3:
            pm_to = pm_parts[1]
            msg = ' '.join(pm_parts[2:])
            is_user = self.find_user_info(pm_to)
            if is_user is not None:
                if is_user.id == self.client_id:
                    self.send_private_bot_msg('Action not allowed.', msg_sender)
                else:
                    self.send_private_bot_msg('*<' + msg_sender + '>* ' + msg, pm_to)
            else:
                self.send_private_bot_msg('No user named: ' + pm_to, msg_sender)

    #  Timed auto functions.
    def start_playlist(self):
        """ Start playing media from the playlist. """
        if self.inowplay >= len(self.playlist):
            if self.is_connected:
                self.send_bot_msg('*Resetting playlist.*', self.is_client_mod)
            self.inowplay = 0
            self.playlist[:] = []
        else:
            if self.is_connected:
                if self.playlist[self.inowplay]['type'] == 'youTube':
                    self.play_youtube(self.playlist[self.inowplay]['video_id'])
                elif self.playlist[self.inowplay]['type'] == 'soundCloud':
                    self.play_soundcloud(self.playlist[self.inowplay]['video_id'])
            self.media_timer(self.playlist[self.inowplay]['video_time'])

    def media_timer(self, video_time, auto_play=True):
        """
        Method to time media being played.
        :param video_time: int milliseconds.
        :param auto_play: bool True = play from playlist.
        """
        ts_now = int(tinychat.time.time() * 1000)
        while self.play:
            track_timer = int(tinychat.time.time() * 1000)
            self.elapsed_track_time = track_timer - ts_now
            self.remaining_track_time = video_time - self.elapsed_track_time
            if track_timer == ts_now + video_time:
                if auto_play:
                    self.inowplay += 1
                    self.start_playlist()
                    break
                else:
                    # setting auto_play to False while a playlist is playing,
                    # will prevent next tune in the playlist from being played.
                    break
        if self.play is False:
            if auto_play:
                self.inowplay += 1
                self.play = True
                self.start_playlist()

    def random_msg(self):
        """
        Pick a random message from a list of messages.
        :return: str random message.
        """
        upnext = 'Use !adl youtube title, link or id to add to the playlist'
        plstat = 'Use !adlsc soundcloud title or id to add a soundcloud to the playlist'
        if len(self.playlist) is not 0:
            if self.inowplay + 1 < len(self.playlist):
                next_video_title = self.playlist[self.inowplay + 1]['video_title']
                next_video_time = self.to_human_time(self.playlist[self.inowplay + 1]['video_time'])
                upnext = 'Up next is: ' + next_video_title + ' ' + next_video_time
            inquee = len(self.playlist) - self.inowplay - 1
            plstat = str(len(self.playlist)) + ' *items in the playlist.* ' + str(inquee) + ' *Still in queue.*'

        messages = ['Reporting for duty..', 'Hello, is anyone here?', 'Awaiting command..', 'Observing behavior..',
                    upnext, plstat, 'Uptime: *' + self.to_human_time(self.uptime, is_seconds=True) + '*']

        return random.choice(messages)

    def start_auto_msg_sender(self):
        """
        In rooms with less activity, it can be useful to have the client send auto messages to keep the client alive.
        This method can be disabled by setting BOT_OPTIONS['auto_message_sender'] to False.
        The interval is set in BOT_OPTIONS['auto_message_interval']
        """
        ts_now = int(tinychat.time.time())
        while True:
            counter = int(tinychat.time.time())
            if counter == ts_now + OPTIONS['auto_message_interval']:
                if self.is_connected:
                    self.send_bot_msg(self.random_msg())
                self.start_auto_msg_sender()
                break

    # Helper Methods.
    def to_human_time(self, milliseconds, is_seconds=False):
        """
        Converts milliseconds or seconds to (day(s)) hours minutes seconds.
        :param milliseconds: int the milliseconds or seconds to convert.
        :param is_seconds: bool True if the time is in seconds.
        :return: str in the format (days) hh:mm:ss
        """
        if is_seconds:
            seconds = milliseconds
        else:
            seconds = milliseconds / 1000
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        if d == 0 and h == 0:
            human_time = '%02d:%02d' % (m, s)
        elif d == 0:
            human_time = '%d:%02d:%02d' % (h, m, s)
        else:
            human_time = '%d Day(s) %d:%02d:%02d' % (d, h, m, s)
        return human_time

    def check_msg_for_bad_string(self, msg):
        """
        Checks the chat message for bad string.
        :param msg: str the chat message.
        """
        msg_words = msg.split(' ')
        bad_strings = tinychat.fh.file_reader(OPTIONS['path'], OPTIONS['badstrings'])
        if bad_strings is not None:
            for word in msg_words:
                if word in bad_strings:
                    self.send_ban_msg(self.user_obj.nick, self.user_obj.id)
                    # remove next line to ban.
                    self.send_forgive_msg(self.user_obj.id)
                    self.send_bot_msg('*Auto-banned*: (bad string in message)', self.is_client_mod)


def main():
    room_name = raw_input('Enter room name: ')
    nickname = raw_input('Enter nick name: (optional) ')
    room_password = raw_input('Enter room password: (optional) ')
    login_account = raw_input('Login account: (optional)')
    login_password = raw_input('Login password: (optional)')

    client = TinychatBot(room_name, nick=nickname, account=login_account,
                         password=login_password, room_pass=room_password)

    thread.start_new_thread(client.prepare_connect, ())
    while not client.is_connected:
        tinychat.time.sleep(1)
    while client.is_connected:
        chat_msg = raw_input()
        if chat_msg.lower() == 'q':
            client.disconnect()
        else:
            client.send_bot_msg(chat_msg, client.is_client_mod)

if __name__ == '__main__':
    main()
