""" Tinychat bot with some basic commands. """
import re
import random
import thread
import tinychat
from api import tiny_media

#  Bot Settings.
BOT_OPTIONS = {
    'prefix': '!',                  # Command prefix.
    'opme_key': 'hk93jsdj',         # key used when doing opme command.
    'op_another': 'eisdi3js',       # key used as command name when oping another.
    'deop_another': 'd_eisdi3js',   # key used as command name when deoping another.
    'auto_message_enabled': True,   # auto message sender.
    'file_path': 'files/',          # the path to files.
    'badnicks': 'badnicks.txt',     # badnicks file.
    'badwords': 'badwords.txt'      # bad words file.
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
    """ Overrides event methods in TinychatRTMPClient that we want the bot to react to. """
    def on_joinsdone(self):
        if not self.is_reconnected:
            if BOT_OPTIONS['auto_message_enabled']:
                thread.start_new_thread(self.start_auto_msg_sender, ())
        thread.start_new_thread(self.send_userinfo_request_to_all, ())  # NEW

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
            del self.id_and_nick[uid]  # NEW
            # Update user info
            self.room_users[new] = old_info
            self.id_and_nick[uid] = new  # NEW
        # Is it a new user joining?
        if str(old).startswith('guest-') and uid != self.client_id:
            bad_nicks = tinychat.fh.file_reader(BOT_OPTIONS['file_path'], BOT_OPTIONS['badnicks'])
            # Check if the user name is in the badnicks file.
            if bad_nicks is not None and new in bad_nicks:
                # User name is in the badnicks file, ban the user.
                self.send_ban_msg(new, uid)
            else:
                # Else greet the user. Should we have a command to enable/disable greetings?
                self.send_bot_msg('*Welcome to* ' + self.roomname + ' *' + new + '*', self.is_client_mod)
                # Is media playing?
                if len(self.playlist) is not 0:
                    play_type = self.playlist[self.inowplay]['type']
                    video_id = self.playlist[self.inowplay]['video_id']
                    elapsed_time = str(self.elapsed_track_time)
                    # Play the media at the correct start time.
                    self.send_undercover_msg(new, '/mbs ' + play_type + ' ' + video_id + ' ' + elapsed_time)

        tinychat.console_write([tinychat.COLOR['cyan'], old + ':' + uid + ' changed nick to: ' + new, self.roomname])

    def message_handler(self, msg_sender, msg):
        """
        Custom command handler.
        :param msg_sender: str the user sending a message
        :param msg: str the message
        """
        user_check = self.find_user_info(msg_sender)
        user_check.last_msg = msg
        if msg.startswith(BOT_OPTIONS['prefix']):
            parts = msg.split(' ')
            cmd = parts[0].lower().strip()
            cmd_param = ' '.join(parts[1:])

            # Mod and bot controller commands.
            if user_check.is_mod or user_check.has_power:
                if cmd == BOT_OPTIONS['prefix'] + 'reboot':
                    # Reboots the client. Only room owner can use this command.
                    if user_check.user_account == self.roomname:
                        self.reconnect()
                    else:
                        self.send_bot_msg('You must be the room owner to use this command.')

                elif cmd == BOT_OPTIONS['prefix'] + 'close':
                    # Closes a users broadcast.
                    if self.is_client_mod:
                        if len(cmd_param) is 0:
                            self.send_bot_msg('Missing username.')
                        else:
                            self.send_close_user_msg(cmd_param)

                elif cmd == BOT_OPTIONS['prefix'] + 'clear':
                    # Clears the chatbox.
                    if self.is_client_mod:
                        for x in range(0, 10):
                            self.send_owner_run_msg(' ')
                    else:
                        clear = '133,133,133,133,133,133,133,133,133,133,133,133,133,133,133'
                        self._sendCommand('privmsg', [clear, tinychat.random_color() + ',en'])

                elif cmd == BOT_OPTIONS['prefix'] + 'skip':
                    # Plays next tune in the playlist.
                    if len(self.playlist) is not 0:
                        self.play = False

                elif cmd == BOT_OPTIONS['prefix'] + 'up':
                    # Cams the client up.
                    self.send_bauth_msg()
                    self._sendCreateStream()
                    self._sendPublish()

                elif cmd == BOT_OPTIONS['prefix'] + 'down':
                    # Cams the client down.
                    self._sendCloseStream()

                elif cmd == BOT_OPTIONS['prefix'] + 'nick':
                    # Give the client a new nick name.
                    if len(cmd_param) is 0:
                        self.client_nick = tinychat.create_random_string(5, 25)
                        self.set_nick()
                    else:
                        if re.match('^[][\{\}a-zA-Z0-9_-]{1,25}$', cmd_param):
                            self.client_nick = cmd_param
                            self.set_nick()

                elif cmd == BOT_OPTIONS['prefix'] + 'topic':
                    # Sets the room topic.
                    if self.is_client_mod:
                        if len(cmd_param) is 0:
                            self.send_bot_msg('Missing topic.', self.is_client_mod)
                        else:
                            self.send_topic_msg(cmd_param)
                            self.send_bot_msg('The room topic was set to: ' + cmd_param, self.is_client_mod)
                    else:
                        self.send_bot_msg('Command not enabled.')

                elif cmd == BOT_OPTIONS['prefix'] + 'kick':
                    # Kicks a user from the room.
                    if self.is_client_mod:
                        if len(cmd_param) is 0:
                            self.send_bot_msg('Missing username.', self.is_client_mod)
                        elif cmd_param == self.client_nick:
                            self.send_bot_msg('Action not allowed.', self.is_client_mod)
                        else:
                            user = self.find_user_info(cmd_param)
                            if user is None:
                                self.send_bot_msg('No user named: *' + cmd_param + '*', self.is_client_mod)
                            else:
                                self.send_ban_msg(cmd_param, user.id)
                                self.send_forgive_msg(user.id)
                    else:
                        self.send_bot_msg('Command not enabled.')

                elif cmd == BOT_OPTIONS['prefix'] + 'ban':
                    # Bans a user from the room.
                    if self.is_client_mod:
                        if len(cmd_param) is 0:
                            self.send_bot_msg('Missing username.', self.is_client_mod)
                        elif cmd_param == self.client_nick:
                            self.send_bot_msg('Action not allowed.', self.is_client_mod)
                        else:
                            user = self.find_user_info(cmd_param)
                            if user is None:
                                self.send_bot_msg('No user named: *' + cmd_param + '*', self.is_client_mod)
                            else:
                                self.send_ban_msg(cmd_param, user.id)
                    else:
                        self.send_bot_msg('Command not enabled.')

                elif cmd == BOT_OPTIONS['prefix'] + 'bn':
                    # Adds a nick to the bad nick file.
                    if self.is_client_mod:
                        if len(cmd_param) is 0:
                            self.send_bot_msg('Missing username.', self.is_client_mod)
                        else:
                            badnicks = tinychat.fh.file_reader(BOT_OPTIONS['file_path'], BOT_OPTIONS['badnicks'])
                            if badnicks is None:
                                tinychat.fh.file_writer(BOT_OPTIONS['file_path'], BOT_OPTIONS['badnicks'], cmd_param)
                            else:
                                if cmd_param in badnicks:
                                    self.send_bot_msg(cmd_param + ' is already in list.', self.is_client_mod)
                                else:
                                    tinychat.fh.file_writer(BOT_OPTIONS['file_path'], BOT_OPTIONS['badnicks'], cmd_param)
                    else:
                        self.send_bot_msg('Command not enabled.')

                elif cmd == BOT_OPTIONS['prefix'] + 'rmbn':
                    # Removes a nick from the bad nick file.
                    if self.is_client_mod:
                        if len(cmd_param) is 0:
                            self.send_bot_msg('Missing username', self.is_client_mod)
                        else:
                            rem = tinychat.fh.remove_from_file(BOT_OPTIONS['file_path'], BOT_OPTIONS['badnicks'], cmd_param)
                            if rem:
                                self.send_bot_msg(cmd_param + ' was removed.')
                    else:
                        self.send_bot_msg('Command not enabled.')

                elif cmd == BOT_OPTIONS['prefix'] + 'clrbn':
                    # Clears the bad nick file.
                    tinychat.fh.delete_file_content(BOT_OPTIONS['file_path'], BOT_OPTIONS['badnicks'])

                elif cmd == BOT_OPTIONS['prefix'] + 'bw':
                    # Adds a bad word to the bad words file.
                    if self.is_client_mod:
                        bad_word = cmd_param.strip()
                        if len(bad_word) is 0:
                            self.send_bot_msg('Bad word can\'t be blank string', self.is_client_mod)
                        elif len(bad_word) < 3:
                            self.send_bot_msg('Bad word to short: ' + str(len(bad_word)), self.is_client_mod)
                        else:
                            badwords = tinychat.fh.file_reader(BOT_OPTIONS['file_path'], BOT_OPTIONS['badwords'])
                            if badwords is None:
                                tinychat.fh.file_writer(BOT_OPTIONS['file_path'], BOT_OPTIONS['badwords'], bad_word)
                            else:
                                if bad_word in badwords:
                                    self.send_bot_msg(cmd_param + ' is already in list.', self.is_client_mod)
                                else:
                                    tinychat.fh.file_writer(BOT_OPTIONS['file_path'], BOT_OPTIONS['badwords'], bad_word)
                    else:
                        self.send_bot_msg('Command not enabled.')

                elif cmd == BOT_OPTIONS['prefix'] + 'rmbw':
                    # Removes a bad word from the bad words file.
                    if self.is_client_mod:
                        if len(cmd_param.strip()) is 0:
                            self.send_bot_msg('Missing word string', self.is_client_mod)
                        else:
                            rem = tinychat.fh.remove_from_file(BOT_OPTIONS['file_path'], BOT_OPTIONS['badwords'], cmd_param)
                            if rem:
                                self.send_bot_msg(cmd_param + ' was removed.')
                    else:
                        self.send_bot_msg('Command not enabled.')

                elif cmd == BOT_OPTIONS['prefix'] + 'clrbw':
                    # Clears the bad words file.
                    tinychat.fh.delete_file_content(BOT_OPTIONS['file_path'], BOT_OPTIONS['badwords'])

                elif cmd == BOT_OPTIONS['prefix'] + 'list':
                    # Shows info about different lists.
                    if self.is_client_mod:
                        if len(cmd_param) is 0:
                            self.send_bot_msg('Missing list type.', self.is_client_mod)
                        else:
                            if cmd_param.lower().strip() == 'bn':
                                bad_nicks = tinychat.fh.file_reader(BOT_OPTIONS['file_path'], BOT_OPTIONS['badnicks'])
                                if bad_nicks is None:
                                    self.send_bot_msg('No items in this list.', self.is_client_mod)
                                else:
                                    self.send_bot_msg(str(len(bad_nicks)) + ' items in list.', self.is_client_mod)
                            elif cmd_param.lower().strip() == 'pl':
                                if len(self.playlist) is not 0:
                                    counter = 0
                                    for i in range(self.inowplay, len(self.playlist)):
                                        v_time = self.milliseconds_to_HMS(self.playlist[i]['video_time'])
                                        v_title = self.playlist[i]['video_title']
                                        if counter <= 4:
                                            if counter == 0:
                                                self.send_owner_run_msg('*>>> %s* %s' % (v_title, v_time))
                                            else:
                                                self.send_owner_run_msg('(%s) *%s* %s' % (i, v_title, v_time))
                                            counter += 1

                elif cmd == BOT_OPTIONS['prefix'] + 'info':
                    # Gets user info for a user in the room.
                    if self.is_client_mod:
                        if len(cmd_param) is 0:
                            self.send_bot_msg('Missing username', self.is_client_mod)
                        else:
                            user = self.find_user_info(cmd_param)
                            if user is None:
                                self.send_bot_msg('No user named: ' + cmd_param, self.is_client_mod)
                            else:
                                self.send_owner_run_msg('*Userinfo for:* ' + cmd_param)
                                self.send_owner_run_msg('*ID:* ' + user.id)
                                self.send_owner_run_msg('*Mod:* ' + str(user.is_mod))
                                self.send_owner_run_msg('*Bot Control:* ' + str(user.has_power))
                                if user.tinychat_id is not None:
                                    self.send_owner_run_msg('*Account:* ' + str(user.user_account))
                                    self.send_owner_run_msg('*Tinychat ID:* ' + str(user.tinychat_id))
                                    self.send_owner_run_msg('*Last login:* ' + str(user.last_login))
                                self.send_owner_run_msg('*Last message:* ' + str(user.last_msg))
                    else:
                        self.send_bot_msg('Command not enabled')

                elif cmd == BOT_OPTIONS['prefix'] + 'search':
                    # Searches youtube for a list of candidates.
                    if self.is_client_mod:
                        if len(cmd_param) is 0:
                            self.send_bot_msg('Missing search term.', self.is_client_mod)
                        else:
                            self.search_list = tiny_media.youtube_search_list(cmd_param, results=5)
                            if len(self.search_list) is not 0:
                                for i in range(0, len(self.search_list)):
                                    v_time = self.milliseconds_to_HMS(self.search_list[i]['video_time'])
                                    v_title = self.search_list[i]['video_title']
                                    self.send_owner_run_msg('(%s) *%s* %s' % (i, v_title, v_time))
                            else:
                                self.send_bot_msg('Could not find: ' + cmd_param, self.is_client_mod)
                    else:
                        self.send_bot_msg('Command not enabled.')

                elif cmd == BOT_OPTIONS['prefix'] + 'plys':
                    # Plays from the search list.
                    if len(self.search_list) > 0:
                        try:
                            index_choice = int(cmd_param)
                            if 0 <= index_choice <= 4:
                                if len(self.playlist) <= 2:
                                    self.play_youtube(self.search_list[index_choice]['video_id'])
                                else:
                                    self.send_bot_msg('No can do, when playlist is playing.', self.is_client_mod)
                            else:
                                self.send_bot_msg('Please make a choice between 0-4', self.is_client_mod)
                        except ValueError:
                            self.send_bot_msg('Only numbers allowed.', self.is_client_mod)
                    else:
                        self.send_bot_msg('The search list is empty.', self.is_client_mod)

                elif cmd == BOT_OPTIONS['prefix'] + 'adls':
                    # Adds a youtube from the search list to the playlist.
                    if len(self.search_list) > 0:
                        try:
                            index_choice = int(cmd_param)
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
                    else:
                        self.send_bot_msg('The search list is empty.', self.is_client_mod)

            # Start of public commands.
            if cmd == BOT_OPTIONS['prefix'] + 'pmme':
                # Makes the client private message a user.
                self.send_private_bot_msg('How can i help you *' + msg_sender + '*?', msg_sender)

            elif cmd == BOT_OPTIONS['prefix'] + 'uptime':
                # Shows the clients up time.
                self.send_bot_msg('*Uptime: ' + str(self.uptime) + '*', self.is_client_mod)

            elif cmd == BOT_OPTIONS['prefix'] + 'help':
                # Prints some of the commands on the screen. Maybe this should be a pastebin url instead?
                if self.is_client_mod:
                    if user_check.is_mod or user_check.has_power:
                        self.send_owner_run_msg('*!skip* - skips the currently playing media.')
                        self.send_owner_run_msg('*!close* username - closes a users broadcast.')
                        self.send_owner_run_msg('*!kick* username - kicks a user out of the room.')
                        self.send_owner_run_msg('*!ban* username - bans a user from the room.')
                        self.send_owner_run_msg('*!clear* - clears the screen.')
                    self.send_owner_run_msg('*!adl* youtube title or link - adds a youtube to the playlist.')
                    self.send_owner_run_msg('*!adlsc* soundcloud title or id - adds a soundcloud to the playlist.')
                    self.send_owner_run_msg('*!ply* youtube title or link - plays youtube.')
                    self.send_owner_run_msg('*!plysc* soundcloud title - plays soundcloud.')
                else:
                    self.send_bot_msg('Command not enabled.')

            # Media related commands.
            elif cmd == BOT_OPTIONS['prefix'] + 'plstat':
                # Prints info about the playlist.
                if len(self.playlist) == 0:
                    self.send_bot_msg('*The playlist is empty.*', self.is_client_mod)
                else:
                    inquee = len(self.playlist) - self.inowplay - 1
                    self.send_bot_msg(str(len(self.playlist)) + ' *items in the playlist.* ' + str(inquee) +
                                      ' *Still in queue.*', self.is_client_mod)

            elif cmd == BOT_OPTIONS['prefix'] + 'next?':
                # Tells us the next tune in the playlist.
                if len(self.playlist) == 0:
                    self.send_bot_msg('No tunes in the playlist.', self.is_client_mod)
                else:
                    if self.inowplay + 1 == len(self.playlist):
                        self.send_bot_msg('This is the last tune in the playlist.', self.is_client_mod)
                    else:
                        play_time = self.milliseconds_to_HMS(self.playlist[self.inowplay + 1]['video_time'])
                        play_title = self.playlist[self.inowplay + 1]['video_title']
                        self.send_bot_msg('*Next tune is:* ' + play_title + ' ' + play_time, self.is_client_mod)

            elif cmd == BOT_OPTIONS['prefix'] + 'adl':
                # Adds a youtube to the playlist.
                if len(cmd_param) is 0:
                    self.send_bot_msg('Please specify youtube title, id or link.', self.is_client_mod)
                else:
                    youtube = tiny_media.youtube_search(cmd_param)
                    if youtube is None:
                        self.send_bot_msg('Could not find video: ' + cmd_param, self.is_client_mod)
                    else:
                        play_time = self.milliseconds_to_HMS(youtube['video_time'])
                        video_title = youtube['video_title']
                        self.send_bot_msg('*Added:* ' + video_title + ' *to playlist.* ' + play_time, self.is_client_mod)
                        self.playlist.append(youtube)
                        if len(self.playlist) == 2:
                            thread.start_new_thread(self.start_playlist, ())

            elif cmd == BOT_OPTIONS['prefix'] + 'adlsc':
                # Adds a soundcloud to the playlist.
                if len(cmd_param) is 0:
                    self.send_bot_msg('Please specify soundcloud title or id.', self.is_client_mod)
                else:
                    soundcloud = tiny_media.soundcloud_search(cmd_param)
                    if soundcloud is None:
                        self.send_bot_msg('Could not find video: ' + cmd_param, self.is_client_mod)
                    else:
                        self.send_bot_msg('*Added:* ' + soundcloud['video_title'] + ' *to playlist.* ' +
                                          self.milliseconds_to_HMS(soundcloud['track_time']), self.is_client_mod)
                        self.playlist.append(soundcloud)
                        if len(self.playlist) == 2:
                            thread.start_new_thread(self.start_playlist, ())

            elif cmd == BOT_OPTIONS['prefix'] + 'ply':
                # Plays a youtube video.
                if len(self.playlist) >= 2:
                    self.send_bot_msg('Cannot play youtube when playlist is playing. Use *!adl* instead.',
                                      self.is_client_mod)
                else:
                    if len(cmd_param) is 0:
                        self.send_bot_msg('Please specify youtube title, id or link.', self.is_client_mod)
                    else:
                        youtube = tiny_media.youtube_search(cmd_param)
                        if youtube is None:
                            self.send_bot_msg('Could not find video: ' + cmd_param, self.is_client_mod)
                        else:
                            self.play_youtube(youtube['video_id'])

            elif cmd == BOT_OPTIONS['prefix'] + 'sply':
                # Plays a private youtube video.
                if len(cmd_param) is 0:
                    self.send_undercover_msg(msg_sender, 'Please specify youtube title, id or link.')
                else:
                    youtube = tiny_media.youtube_search(cmd_param)
                    if youtube is None:
                        self.send_undercover_msg(msg_sender, 'Could not find video: ' + cmd_param)
                    else:
                        self.send_undercover_msg(msg_sender, '/mbs youTube ' + youtube['video_id'] + ' 0')

            elif cmd == BOT_OPTIONS['prefix'] + 'plysc':
                # Plays a soundcloud.
                if len(self.playlist) >= 2:
                    self.send_bot_msg('Cannot play soundcloud when playlist is playing. Use *!adlsc* instead.',
                                      self.is_client_mod)
                else:
                    if len(cmd_param) is 0:
                        self.send_bot_msg('Please specify soundcloud title or id.', self.is_client_mod)
                    else:
                        soundcloud = tiny_media.soundcloud_search(cmd_param)
                        if soundcloud is None:
                            self.send_bot_msg('Could not find soundcloud: ' + cmd_param, self.is_client_mod)
                        else:
                            self.play_soundcloud(soundcloud['video_id'])

            elif cmd == BOT_OPTIONS['prefix'] + 'splysc':
                # Plays a private soundcloud.
                if len(cmd_param) is 0:
                    self.send_undercover_msg(msg_sender, 'Please specify soundcloud title or id.')
                else:
                    soundcloud = tiny_media.soundcloud_search(cmd_param)
                    if soundcloud is None:
                        self.send_undercover_msg(msg_sender, 'Could not find video: ' + cmd_param)
                    else:
                        self.send_undercover_msg(msg_sender, '/mbs soundCloud ' + soundcloud['video_id'] + ' 0')

            # Tinychat API commands.
            elif cmd == BOT_OPTIONS['prefix'] + 'spy':
                # Finds information about a tinychat room.
                if len(cmd_param) is 0:
                    self.send_undercover_msg(msg_sender, 'Missing room name.')
                else:
                    spy_info = tinychat.tinychat_api.spy_info(cmd_param)
                    if spy_info is None:
                        self.send_undercover_msg(msg_sender, 'The room is empty.')
                    elif spy_info == 'PW':
                        self.send_undercover_msg(msg_sender, 'The room is password protected.')
                    else:
                        self.send_undercover_msg(msg_sender,
                                                 '*mods:* ' + spy_info['mod_count'] +
                                                 ' *Broadcasters:* ' + spy_info['broadcaster_count'] +
                                                 ' *Users:* ' + spy_info['total_count'])
                        if user_check.is_mod or user_check.has_power:
                            users = ', '.join(spy_info['users'])
                            self.send_undercover_msg(msg_sender, '*' + users + '*')

            elif cmd.lower() == BOT_OPTIONS['prefix'] + 'usrspy':
                # Finds information for a tinychat account.
                if len(cmd_param) is 0:
                    self.send_undercover_msg(msg_sender, 'Missing username to search for.')
                else:
                    tc_usr = tinychat.tinychat_api.tinychat_user_info(cmd_param)
                    if tc_usr is None:
                        self.send_undercover_msg(msg_sender, 'Could not find tinychat info for: ' + cmd_param)
                    else:
                        self.send_undercover_msg(msg_sender, 'ID: ' + tc_usr['tinychat_id'] + ', Last login: ' + tc_usr['last_active'])

            # Other API commands.
            elif cmd == BOT_OPTIONS['prefix'] + 'urb':
                # Searches urbandictionary.
                if len(cmd_param) is 0:
                    self.send_bot_msg('Please specify something to look up.', self.is_client_mod)
                else:
                    urban = tiny_media.urbandictionary_search(cmd_param)
                    if urban is None:
                        self.send_bot_msg('Could not find a definition for: ' + cmd_param, self.is_client_mod)
                    else:
                        if len(urban) > 70:
                            urb_parts = str(urban).split('.')
                            self.send_bot_msg(urb_parts[0].strip(), self.is_client_mod)
                            self.send_bot_msg(urb_parts[1].strip(), self.is_client_mod)
                        else:
                            self.send_bot_msg(urban, self.is_client_mod)

            elif cmd == BOT_OPTIONS['prefix'] + 'wea':
                # Searches worldweatheronline.
                if len(cmd_param) is 0:
                    self.send_bot_msg('Please specify a city to search for.', self.is_client_mod)
                else:
                    weather = tiny_media.weather_search(cmd_param)
                    if weather is None:
                        self.send_bot_msg('Could not find weather data for: ' + cmd_param, self.is_client_mod)
                    else:
                        self.send_bot_msg(weather, self.is_client_mod)

            elif cmd == BOT_OPTIONS['prefix'] + 'ip':
                # Finds info about a IP.
                if len(cmd_param) is 0:
                    self.send_bot_msg('Please provide an IP address.', self.is_client_mod)
                else:
                    whois = tiny_media.whois(cmd_param)
                    if whois is None:
                        self.send_bot_msg('No info found for: ' + cmd_param, self.is_client_mod)
                    else:
                        self.send_bot_msg(whois)

            elif cmd == BOT_OPTIONS['prefix'] + 'cn':
                # Finds a Chuck Norris joke/quote.
                self.send_bot_msg(tiny_media.chuck_norris(), self.is_client_mod)

            elif cmd == BOT_OPTIONS['prefix'] + '8ball':
                # Magic eight ball.
                if len(cmd_param) is 0:
                    self.send_bot_msg('Question.', self.is_client_mod)
                else:
                    self.send_bot_msg('*8Ball* ' + eightball(), self.is_client_mod)

            #  Print command to console.
            tinychat.console_write([tinychat.COLOR['yellow'], msg_sender + ':' + cmd + ' ' + cmd_param, self.roomname])
        else:
            #  Print chat message to console.
            tinychat.console_write([tinychat.COLOR['green'], msg_sender + ':' + msg, self.roomname])
            # Only check for bad words if we are mod.
            if self.is_client_mod:
                self.check_msg_for_bad_word(msg, user_check)

    def private_message_handler(self, msg_sender, private_msg):
        """
        Custom private message commands.
        :param msg_sender: str the user sending the private message.
        :param private_msg: str the private message.
        :return:
        """
        user_check = self.find_user_info(msg_sender)
        priv_msg_parts = private_msg.split(' ')
        pm_cmd = priv_msg_parts[0].lower()
        pm_cmd_params = ' '.join(priv_msg_parts[1:])

        if pm_cmd == BOT_OPTIONS['prefix'] + 'opme':
            # Enables the user to control the client.
            if pm_cmd_params == BOT_OPTIONS['opme_key']:
                user_check.has_power = True
                self.send_private_bot_msg('You are now a bot controller.', msg_sender)
            else:
                self.send_private_bot_msg('Wrong key.', msg_sender)

        elif pm_cmd == BOT_OPTIONS['prefix'] + BOT_OPTIONS['op_another']:
            # Enable another user to control the client.
            if user_check.has_power:
                if len(pm_cmd_params) is 0:
                    self.send_private_bot_msg('Missing user name.', msg_sender)
                else:
                    op_user = self.find_user_info(pm_cmd_params)
                    if op_user is not None:
                        op_user.has_power = True
                        self.send_private_bot_msg(pm_cmd_params + ' is now a bot controller.', msg_sender)
                        # Send a PM to the user, alerting them that they now are a bot controller.
                        self.send_private_bot_msg('You are now a bot controller.', pm_cmd_params)
                    else:
                        self.send_private_bot_msg('No user named: ' + pm_cmd_params, msg_sender)

        elif pm_cmd == BOT_OPTIONS['prefix'] + BOT_OPTIONS['deop_another']:
            # Disable a user from controlling the client.
            if user_check.has_power:
                if len(pm_cmd_params) is 0:
                    self.send_private_bot_msg('Missing user name.', msg_sender)
                else:
                    op_user = self.find_user_info(pm_cmd_params)
                    if op_user is not None:
                        op_user.has_power = False
                        self.send_private_bot_msg('Removed bot controls from: ' + pm_cmd_params, msg_sender)
                    else:
                        self.send_private_bot_msg('No user named: ' + pm_cmd_params, msg_sender)

        elif pm_cmd == BOT_OPTIONS['prefix'] + 'opuser':
            # A mod enables a user to control the client.
            if user_check.is_mod:
                up_user = self.find_user_info(pm_cmd_params)
                if up_user is not None:
                    up_user.has_power = True
                    self.send_private_bot_msg(pm_cmd_params + ' now has privileges', msg_sender)
                else:
                    self.send_private_bot_msg('No user named: ' + pm_cmd_params, msg_sender)

        elif pm_cmd == BOT_OPTIONS['prefix'] + 'deopuser':
            # A mod disables a user from controlling the client.
            if user_check.is_mod:
                up_user = self.find_user_info(pm_cmd_params)
                if up_user is not None:
                    up_user.has_power = False
                    self.send_private_bot_msg('Removed privileges from: ' + pm_cmd_params, msg_sender)
                else:
                    self.send_private_bot_msg('No user named: ' + pm_cmd_params, msg_sender)

        elif pm_cmd == BOT_OPTIONS['prefix'] + 'nocam':
            # Toggles no broadcasting on/off
            if user_check.is_mod or user_check.has_power:
                if self.no_cam:
                    self.no_cam = False
                    self.send_private_bot_msg('*Broadcasting is allowed.*', msg_sender)
                else:
                    self.no_cam = True
                    self.send_private_bot_msg('*Broadcasting is NOT allowed.*', msg_sender)

        elif pm_cmd == BOT_OPTIONS['prefix'] + 'noguest':
            # Toggles no guest allowed to join on/off.
            if user_check.is_mod or user_check.has_power:
                if self.no_guests:
                    self.no_guests = False
                    self.send_private_bot_msg('*Guests ARE allowed to join.*', msg_sender)
                else:
                    self.no_guests = True
                    self.send_private_bot_msg('*Guests are NOT allowed to join.*', msg_sender)

        # Public PM commands.
        elif pm_cmd == BOT_OPTIONS['prefix'] + 'pm':
            # Makes the bot work as a PM bridge between 2 users who are NOT signed in.
            # User a does !pmme to start a pm session, then does !pm b message
            # and user b responds with !pm a message
            # Thereby user a and b will be able to PM each other using the bot as a bridge.
            if len(priv_msg_parts[1]) is not 0:
                user = self.find_user_info(priv_msg_parts[1])
                if user is not None:
                    pm_msg = ' '.join(priv_msg_parts[2:])
                    self.send_private_bot_msg(msg_sender + ': ' + pm_msg, str(user.nick))
                else:
                    self.send_private_bot_msg('No user named: ' + str(priv_msg_parts[1]), msg_sender)

        # Print to console.
        tinychat.console_write([tinychat.COLOR['white'], 'Private message from ' + msg_sender + ':' + private_msg,
                                self.roomname])

    # User Info Events
    def user_is_guest(self, uid):  # NEW
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

    #  Timed auto functions.
    def start_playlist(self):
        """
        Start playing media from the playlist.
        :return:
        """
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
        Method to time media being played by the start_playlist method.
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
        if self.play is False:
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
                next_video_time = self.milliseconds_to_HMS(self.playlist[self.inowplay + 1]['video_time'])
                upnext = 'Up next is: ' + next_video_title + ' ' + next_video_time
            inquee = len(self.playlist) - self.inowplay - 1
            plstat = str(len(self.playlist)) + ' *items in the playlist.* ' + str(inquee) + ' *Still in queue.*'

        messages = ['Reporting for duty..', 'Hello, is anyone here?', 'Awaiting command..', 'Observing behavior..',
                    upnext, plstat, 'Uptime: *' + str(self.uptime) + '*']

        return random.choice(messages)

    def start_auto_msg_sender(self):
        """
        In rooms with less activity, it can be useful to have the client send auto messages to keep the client alive.
        The default interval is 5 minutes.
        This method can be disabled by setting BOT_OPTIONS['auto_message_sender'] to False.
        """
        ts_now = int(tinychat.time.time())
        while True:
            counter = int(tinychat.time.time())
            if counter == ts_now + 300:  # 300 seconds = 5 minutes
                if self.is_connected:
                    self.send_bot_msg(self.random_msg())
                self.start_auto_msg_sender()
                break

    # Helper Methods.
    def milliseconds_to_HMS(self, milliseconds):
        """
        Converts milliseconds to hours minutes seconds.
        :param milliseconds: int the milliseconds to convert.
        :return: str in the format hh:mm:ss
        """
        seconds = milliseconds / 1000
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h == 0:
            human_time = '%02d:%02d' % (m, s)
        else:
            human_time = '%d:%02d:%02d' % (h, m, s)
        return human_time

    def check_msg_for_bad_word(self, msg, user):
        """
        Checks the chat message for bad words.
        :param msg: str the chat message.
        :param user: object user object.
        """
        msg_words = msg.split(' ')
        bad_words = tinychat.fh.file_reader(BOT_OPTIONS['file_path'], BOT_OPTIONS['badwords'])
        if bad_words is not None:
            for word in msg_words:
                if word in bad_words:
                    self.send_ban_msg(user.nick, user.id)
                    # If you wanted to ban the user, then remove next line.
                    self.send_forgive_msg(user.id)
                    self.send_bot_msg('*Auto-banned*: (bad word in message)', self.is_client_mod)


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
