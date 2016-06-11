# -*- coding: utf-8 -*-
""" Tinychat bot example by Nortxort (https://github.com/nortxort/pinylib). """

import re
import random
import threading
import logging

import pinylib
from api import soundcloud, youtube, other_apis, lastfm, privacy_settings

__version__ = 3.6

#  Bot Settings.
OPTIONS = {
    'prefix': '!',                                  # Command prefix.
    'key': 'yusd87f',                               # unique secret key.
    'super_key': '87sdysd7s',                       # VERY unique super mod key. NEW
    'auto_message_enabled': True,                   # enable auto message sender.
    'debug_to_file': False,                         # log debug info to file.
    'auto_message_interval': 300,                   # auto message sender interval in seconds.
    'badnicks': 'badnicks.txt',                     # bad nicks file.
    'badstrings': 'badstrings.txt',                 # bad words file.
    'badaccounts': 'badaccounts.txt',               # bad accounts file.
    'debug_file_name': 'bot_example_debug.log'      # debug file name.
}

log = logging.getLogger(__name__)


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


class TinychatBot(pinylib.TinychatRTMPClient):
    """ Overrides event methods in TinychatRTMPClient that the client should to react to. """
    init_time = pinylib.time.time()
    key = OPTIONS['key']
    is_newusers_allowed = True
    is_broadcasting_allowed = True  # RENAMED/DEFAULT VALUE CHANGED
    is_guest_entry_allowed = True  # RENAMED/DEFAULT VALUE CHANGED
    is_guest_nicks_allowed = False  # NEW/ISSUE #24
    privacy_settings = object  # NEW
    # Media Player Related.
    is_mod_playing = False
    playlist = []
    search_list = []
    inowplay = 0
    last_played_media = {}
    media_start_time = 0
    media_timer_thread = None

    def on_join(self, join_info_dict):
        log.info('User join info: %s' % join_info_dict)
        user = self.add_user_info(join_info_dict['nick'])
        user.nick = join_info_dict['nick']
        user.user_account = join_info_dict['account']
        user.id = join_info_dict['id']
        user.is_mod = join_info_dict['mod']
        user.is_owner = join_info_dict['own']

        if join_info_dict['account']:
            tc_info = pinylib.tinychat_api.tinychat_user_info(join_info_dict['account'])
            if tc_info is not None:
                user.tinychat_id = tc_info['tinychat_id']
                user.last_login = tc_info['last_active']
            if join_info_dict['own']:
                self.console_write(pinylib.COLOR['red'], 'Room Owner %s:%d:%s' %
                                   (join_info_dict['nick'], join_info_dict['id'], join_info_dict['account']))
            elif join_info_dict['mod']:
                self.console_write(pinylib.COLOR['bright_red'], 'Moderator %s:%d:%s' %
                                   (join_info_dict['nick'], join_info_dict['id'], join_info_dict['account']))
            else:
                self.console_write(pinylib.COLOR['bright_yellow'], '%s:%d has account: %s' %
                                   (join_info_dict['nick'], join_info_dict['id'], join_info_dict['account']))

                badaccounts = pinylib.fh.file_reader(self.config_path(), OPTIONS['badaccounts'])
                if badaccounts is not None:
                    if join_info_dict['account'] in badaccounts:
                        if self.is_client_mod:
                            self.send_ban_msg(join_info_dict['nick'], join_info_dict['id'])
                            self.send_forgive_msg(join_info_dict['id'])
                            self.send_bot_msg('*Auto-Banned:* (bad account)', self.is_client_mod)
        else:
            if join_info_dict['id'] is not self.client_id:
                if not self.is_guest_entry_allowed:
                    self.send_ban_msg(join_info_dict['nick'], join_info_dict['id'])
                    # remove next line to ban.
                    self.send_forgive_msg(join_info_dict['id'])
                    self.send_bot_msg('*Auto-Banned:* (guests not allowed)', self.is_client_mod)
                else:
                    self.console_write(pinylib.COLOR['cyan'], '%s:%d joined the room.' %
                                       (join_info_dict['nick'], join_info_dict['id']))

    def on_joinsdone(self):  # EDITED
        if not self.is_reconnected:
            if OPTIONS['auto_message_enabled']:
                self.start_auto_msg_timer()
        if self.is_client_mod:
            self.send_banlist_msg()
        if self.is_client_owner and self._roomtype != 'default':
            threading.Thread(target=self.get_privacy_settings).start()

    def on_avon(self, uid, name):  # EDITED
        if not self.is_broadcasting_allowed:
            self.send_close_user_msg(name)
            self.console_write(pinylib.COLOR['cyan'], 'Auto closed broadcast %s:%s' % (name, uid))
        else:
            self.console_write(pinylib.COLOR['cyan'], '%s:%s is broadcasting.' % (name, uid))

    def on_nick(self, old, new, uid):  # EDITED
        old_info = self.find_user_info(old)
        old_info.nick = new
        if old in self.room_users.keys():
            del self.room_users[old]
            self.room_users[new] = old_info

        if str(old).startswith('guest-'):
            if self.client_id != uid:

                if str(new).startswith('guest-'):
                    if self.is_client_mod:
                        if not self.is_guest_nicks_allowed:
                            self.send_ban_msg(new, uid)
                            # remove next line to ban.
                            self.send_forgive_msg(uid)
                            self.send_bot_msg('*Auto-Banned:* (bot nick detected)', self.is_client_mod)

                if str(new).startswith('newuser'):
                    if self.is_client_mod:
                        if not self.is_newusers_allowed:
                            self.send_ban_msg(new, uid)
                            # remove next line to ban.
                            self.send_forgive_msg(uid)
                            self.send_bot_msg('*Auto-Banned:* (wanker detected)', self.is_client_mod)

                else:
                    bn = pinylib.fh.file_reader(self.config_path(), OPTIONS['badnicks'])
                    if bn is not None and new in bn:
                        if self.is_client_mod:
                            self.send_ban_msg(new, uid)
                            # remove next line to ban.
                            self.send_forgive_msg(uid)
                            self.send_bot_msg('*Auto-Banned:* (bad nick)', self.is_client_mod)

                    else:
                        user = self.find_user_info(new)
                        if user is not None:
                            if user.user_account:
                                # Greet user with account name.
                                self.send_bot_msg('*Welcome* ' + new + ':' + str(uid) + ':' + user.user_account,
                                                  self.is_client_mod)
                            else:
                                self.send_bot_msg('*Welcome* ' + new + ':' + str(uid), self.is_client_mod)

                        if self.media_timer_thread is not None and self.media_timer_thread.is_alive():
                            if not self.is_mod_playing:
                                self.send_media_broadcast_start(self.last_played_media['type'],
                                                                self.last_played_media['video_id'],
                                                                time_point=self.current_media_time_point(),
                                                                private_nick=new)
        self.console_write(pinylib.COLOR['bright_cyan'], '%s:%s changed nick to: %s' % (old, uid, new))

    # Media Events.
    def on_media_broadcast_start(self, media_type, video_id, usr_nick):
        """
        A user started a media broadcast.
        :param media_type: str the type of media. youTube or soundCloud.
        :param video_id: str the youtube ID or soundcloud track ID.
        :param usr_nick: str the user name of the user playing media.
        """
        if self.user_obj.is_mod:
            self.is_mod_playing = True
            self.cancel_media_event_timer()

            # are we in pause state?
            if 'pause' in self.last_played_media:
                # delete pause time point.
                del self.last_played_media['pause']

            video_time = 0

            if media_type == 'youTube':
                _youtube = youtube.youtube_time(video_id, check=False)
                if _youtube is not None:
                    self.last_played_media = _youtube
                    video_time = _youtube['video_time']

            elif media_type == 'soundCloud':
                _soundcloud = soundcloud.soundcloud_track_info(video_id)
                if _soundcloud is not None:
                    self.last_played_media = _soundcloud
                    video_time = _soundcloud['video_time']

            self.media_event_timer(video_time)
            self.console_write(pinylib.COLOR['bright_magenta'], '%s is playing %s %s' %
                               (usr_nick, media_type, video_id))

    def on_media_broadcast_close(self, media_type, usr_nick):
        """
        A user closed a media broadcast.
        :param media_type: str the type of media. youTube or soundCloud.
        :param usr_nick: str the user name of the user closing the media.
        """
        if self.user_obj.is_mod:
            self.cancel_media_event_timer()
            # are we in pause state?
            if 'pause' in self.last_played_media:
                # delete pause time point.
                del self.last_played_media['pause']
            self.console_write(pinylib.COLOR['bright_magenta'], '%s closed the %s' % (usr_nick, media_type))

    def on_media_broadcast_paused(self, media_type, usr_nick):
        """
        A user paused the media broadcast.
        :param media_type: str the type of media being paused. youTube or soundCloud.
        :param usr_nick: str the user name of the user pausing the media.
        """
        if self.user_obj.is_mod:
            self.cancel_media_event_timer()
            # are we in pause state already?
            if 'pause' in self.last_played_media:
                # if so delete old pause timepoint.
                del self.last_played_media['pause']
            # make a new pause timepoint.
            ts_now = int(pinylib.time.time() * 1000)
            self.last_played_media['pause'] = ts_now - self.media_start_time

            self.console_write(pinylib.COLOR['bright_magenta'], '%s paused the %s' % (usr_nick, media_type))

    def on_media_broadcast_play(self, media_type, time_point, usr_nick):
        """
        A user resumed playing a media broadcast.
        :param media_type: str the media type. youTube or soundCloud.
        :param time_point: int the time point in the tune in milliseconds.
        :param usr_nick: str the user resuming the tune.
        """
        if self.user_obj.is_mod:
            self.cancel_media_event_timer()
            new_media_time = self.last_played_media['video_time'] - time_point
            self.media_start_time = new_media_time

            # are we in pause state?
            if 'pause' in self.last_played_media:
                # delete pause time point.
                del self.last_played_media['pause']

            self.media_event_timer(new_media_time)
            self.console_write(pinylib.COLOR['bright_magenta'], '%s resumed the %s at: %s' %
                               (usr_nick, media_type, self.to_human_time(time_point)))

    def on_media_broadcast_skip(self, media_type, time_point, usr_nick):
        """
        A user time searched a tune.
        :param media_type: str the media type. youTube or soundCloud.
        :param time_point: int the time point in the tune in milliseconds.
        :param usr_nick: str the user time searching the tune.
        """
        if self.user_obj.is_mod:
            self.cancel_media_event_timer()
            new_media_time = self.last_played_media['video_time'] - time_point
            self.media_start_time = new_media_time

            if 'pause' in self.last_played_media:
                self.last_played_media['pause'] = new_media_time

            self.media_event_timer(new_media_time)
            self.console_write(pinylib.COLOR['bright_magenta'], '%s time searched the %s at: %s' %
                               (usr_nick, media_type, self.to_human_time(time_point)))

    # Media Message Method.
    def send_media_broadcast_start(self, media_type, video_id, time_point=0, private_nick=None):
        """
        Starts a media broadcast.
        NOTE: This method replaces play_youtube and play_soundcloud
        :param media_type: str 'youTube' or 'soundCloud'
        :param video_id: str the media video ID.
        :param time_point: int where to start the media from in milliseconds.
        :param private_nick: str if not None, start the media broadcast for this username only.
        """
        mbs_msg = '/mbs %s %s %s' % (media_type, video_id, time_point)
        if private_nick is not None:
            self.send_undercover_msg(private_nick, mbs_msg)
        else:
            self.is_mod_playing = False
            self.send_chat_msg(mbs_msg)

    # Message Method.
    def send_bot_msg(self, msg, is_mod=False):
        """
        Send a chat message to the room.
        :param msg: str the message to send.
        :param is_mod: boolean True send a owner run message, False send a normal chat message.
        """
        if is_mod:
            self.send_owner_run_msg(msg)
        else:
            self.send_chat_msg(msg)

    def message_handler(self, msg_sender, msg):
        """
        Custom command handler.

        NOTE: Any method using a API should be started in a new thread.
        :param msg_sender: str the user sending a message
        :param msg: str the message
        """

        # Is this a custom command?
        if msg.startswith(OPTIONS['prefix']):
            # Split the message in to parts.
            parts = msg.split(' ')
            # parts[0] is the command..
            cmd = parts[0].lower().strip()
            # The rest is a command argument.
            cmd_arg = ' '.join(parts[1:]).strip()

            # Super mod commands.
            if cmd == OPTIONS['prefix'] + 'mod':  # NEW
                threading.Thread(target=self.do_make_mod, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'rmod':  # NEW
                threading.Thread(target=self.do_remove_mod, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'dir':  # NEW
                threading.Thread(target=self.do_directory).start()

            elif cmd == OPTIONS['prefix'] + 'p2t':  # NEW
                threading.Thread(target=self.do_push2talk).start()

            elif cmd == OPTIONS['prefix'] + 'gr':  # NEW
                threading.Thread(target=self.do_green_room).start()

            elif cmd == OPTIONS['prefix'] + 'crb':  # NEW
                threading.Thread(target=self.do_clear_room_bans).start()

            # Owner and super mod commands.
            elif cmd == OPTIONS['prefix'] + 'kill':
                self.do_kill()

            elif cmd == OPTIONS['prefix'] + 'reboot':
                self.do_reboot()

            # Owner and bot controller commands.
            elif cmd == OPTIONS['prefix'] + 'mi':
                self.do_media_info()

            # Mod and bot controller commands.
            elif cmd == OPTIONS['prefix'] + 'top':
                threading.Thread(target=self.do_lastfm_chart, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'ran':
                threading.Thread(target=self.do_lastfm_random_tunes, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'tag':
                threading.Thread(target=self.search_lastfm_by_tag, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'close':
                self.do_close_broadcast(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'clear':
                self.do_clear()

            elif cmd == OPTIONS['prefix'] + 'skip':
                self.do_skip()

            elif cmd == OPTIONS['prefix'] + 'del':
                self.do_delete_playlist_item(cmd_arg)

            elif cmd == OPTIONS['prefix'] + 'rpl':
                self.do_media_replay()

            elif cmd == OPTIONS['prefix'] + 'cm':
                self.do_close_media()

            elif cmd == OPTIONS['prefix'] + 'cpl':
                self.do_clear_playlist()

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

            elif cmd == OPTIONS['prefix'] + 'yts':
                threading.Thread(target=self.do_youtube_search, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'pyts':
                self.do_play_youtube_search(cmd_arg)

            # Public Commands.
            elif cmd == OPTIONS['prefix'] + 'v':
                self.do_version()

            elif cmd == OPTIONS['prefix'] + 'help':
                self.do_help()

            elif cmd == OPTIONS['prefix'] + 't':
                self.do_uptime()

            elif cmd == OPTIONS['prefix'] + 'pmme':
                self.do_pmme()

            elif cmd == OPTIONS['prefix'] + 'q':
                self.do_playlist_status()

            elif cmd == OPTIONS['prefix'] + 'n':
                self.do_next_tune_in_playlist()

            elif cmd == OPTIONS['prefix'] + 'np':
                self.do_now_playing()

            elif cmd == OPTIONS['prefix'] + 'yt':
                threading.Thread(target=self.do_play_youtube, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'pyt':
                threading.Thread(target=self.do_play_private_youtube, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'sc':
                threading.Thread(target=self.do_play_soundcloud, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'psc':
                threading.Thread(target=self.do_play_private_soundcloud, args=(cmd_arg, )).start()

            # Tinychat API commands.
            elif cmd == OPTIONS['prefix'] + 'spy':
                threading.Thread(target=self.do_spy, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'acspy':
                threading.Thread(target=self.do_account_spy, args=(cmd_arg, )).start()

            # Other API commands.
            elif cmd == OPTIONS['prefix'] + 'urb':
                threading.Thread(target=self.do_search_urban_dictionary, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'wea':
                threading.Thread(target=self.do_weather_search, args=(cmd_arg, )).start()

            elif cmd == OPTIONS['prefix'] + 'ip':
                threading.Thread(target=self.do_whois_ip, args=(cmd_arg, )).start()

            # Just for fun.
            elif cmd == OPTIONS['prefix'] + 'cn':
                threading.Thread(target=self.do_chuck_noris).start()

            elif cmd == OPTIONS['prefix'] + '8ball':
                self.do_8ball(cmd_arg)

            #  Print command to console.
            self.console_write(pinylib.COLOR['yellow'], msg_sender + ':' + cmd + ' ' + cmd_arg)
        else:
            #  Print chat message to console.
            self.console_write(pinylib.COLOR['green'], msg_sender + ':' + msg)
            # Only check chat msg for bad string if we are mod.
            if self.is_client_mod:
                threading.Thread(target=self.check_msg_for_bad_string, args=(msg, )).start()

        # add msg to user object last_msg
        self.user_obj.last_msg = msg

    # == Super Mod Commands Methods. ==
    def do_make_mod(self, account):  # NEW
        """
        Make a tinychat account a room moderator.
        :param account str the account to make a moderator.
        """
        if self.is_client_owner:
            if self.user_obj.is_super:
                if len(account) is 0:
                    self.send_bot_msg('*Missing account name.*', self.is_client_mod)
                else:
                    tc_user = self.privacy_settings.make_moderator(account)
                    if tc_user is None:
                        self.send_bot_msg('*The account is invalid.*', self.is_client_mod)
                    elif not tc_user:
                        self.send_bot_msg('*The account is already a moderator.*', self.is_client_mod)
                    elif tc_user:
                        self.send_bot_msg('*' + account + ' was made a room moderator.*', self.is_client_mod)

    def do_remove_mod(self, account):  # NEW
        """
        Removes a tinychat account from the moderator list.
        :param account str the account to remove from the moderator list.
        """
        if self.is_client_owner:
            if self.user_obj.is_super:
                if len(account) is 0:
                    self.send_bot_msg('*Missing account name.*', self.is_client_mod)
                else:
                    tc_user = self.privacy_settings.remove_moderator(account)
                    if tc_user:
                        self.send_bot_msg('*' + account + ' is no longer a room moderator.*', self.is_client_mod)
                    elif not tc_user:
                        self.send_bot_msg('*' + account + ' is not a room moderator.*', self.is_client_mod)

    def do_directory(self):  # NEW
        """ Toggles if the room should be shown on the directory. """
        if self.is_client_owner:
            if self.user_obj.is_super:
                if self.privacy_settings.show_on_directory():
                    self.send_bot_msg('*Room IS shown on the directory.*', self.is_client_mod)
                else:
                    self.send_bot_msg('*Room is NOT shown on the directory.*', self.is_client_mod)

    def do_push2talk(self):  # NEW
        """ Toggles if the room should be in push2talk mode. """
        if self.is_client_owner:
            if self.user_obj.is_super:
                if self.privacy_settings.set_push2talk():
                    self.send_bot_msg('*Push2Talk is enabled.*', self.is_client_mod)
                else:
                    self.send_bot_msg('*Push2Talk is disabled.*', self.is_client_mod)

    def do_green_room(self):  # NEW
        """ Toggles if the room should be in greenroom mode. """
        if self.is_client_owner:
            if self.user_obj.is_super:
                if self.privacy_settings.set_greenroom():
                    self.send_bot_msg('*Green room is enabled.*', self.is_client_mod)
                else:
                    self.send_bot_msg('*Green room is disabled.*', self.is_client_mod)

    def do_clear_room_bans(self):  # NEW
        """ Clear all room bans. """
        if self.is_client_owner:
            if self.user_obj.is_super:
                if self.privacy_settings.clear_bans():
                    self.send_bot_msg('*All room bans was cleared.*', self.is_client_mod)

    # == Owner And Super Mod Command Methods. ==
    def do_kill(self):  # EDITED
        """ Kills the bot. """
        if self.user_obj.is_owner or self.user_obj.is_super:
            self.disconnect()

    def do_reboot(self):  # EDITED
        """ Reboots the bot. """
        if self.user_obj.is_owner or self.user_obj.is_super:
            self.reconnect()

    # == Owner And Bot Controller Commands Methods. ==
    def do_media_info(self):  # EDITED
        """ Shows basic media info. """
        # This method was used while debugging the media player, and doesnt serve a purpose.
        if self.user_obj.is_owner or self.user_obj.is_super or self.user_obj.has_power:
            if self.is_client_mod:
                self.send_owner_run_msg('*I Now Play:* ' + str(self.inowplay))
                self.send_owner_run_msg('*Playlist Length:* ' + str(len(self.playlist)))
                self.send_owner_run_msg('*Current Time Point:* ' + self.to_human_time(self.current_media_time_point()))
                self.send_owner_run_msg('*Active Threads:* ' + str(threading.active_count()))
                self.send_owner_run_msg('*Is Mod Playing:* ' + str(self.is_mod_playing))

    def do_lastfm_chart(self, chart_items):  # EDITED
        """
        Makes a playlist from the currently most played tunes on last.fm
        :param chart_items: int the amount of tunes we want.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if chart_items is 0 or chart_items is None:
                    self.send_bot_msg('Please specify the amount of tunes you want.', self.is_client_mod)
                else:
                    try:
                        _items = int(chart_items)
                    except ValueError:
                        self.send_bot_msg('Only numbers allowed.', self.is_client_mod)
                    else:
                        if _items > 0:
                            if _items > 30:
                                self.send_bot_msg('No more than 30 tunes.', self.is_client_mod)
                            else:
                                self.send_bot_msg('Please wait while creating a playlist...', self.is_client_mod)
                                last = lastfm.get_lastfm_chart(_items)
                                if last is not None:
                                    if self.media_timer_thread is not None and self.media_timer_thread.is_alive():
                                        self.playlist.extend(last)
                                        self.send_bot_msg('*Added:* ' + str(len(last)) +
                                                          ' *tunes from last.fm chart.*', self.is_client_mod)
                                    else:
                                        self.playlist.extend(last)
                                        self.send_bot_msg('*Added:* ' + str(len(last)) +
                                                          ' *tunes from last.fm chart.*', self.is_client_mod)
                                        self.last_played_media = self.playlist[self.inowplay]
                                        self.send_media_broadcast_start(self.playlist[self.inowplay]['type'],
                                                                        self.playlist[self.inowplay]['video_id'])
                                        self.media_event_timer(self.playlist[self.inowplay]['video_time'])
                                        self.inowplay += 1  # prepare the next tune in the playlist.
                                else:
                                    self.send_bot_msg('Failed to retrieve a result from last.fm.', self.is_client_mod)

    def do_lastfm_random_tunes(self, max_tunes):  # EDITED
        """
        Creates a playlist from what other people are listening to on last.fm.
        :param max_tunes: int the max amount of tunes.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if max_tunes is 0 or max_tunes is None:
                    self.send_bot_msg('Please specify the max amount of tunes you want.', self.is_client_mod)
                else:
                    try:
                        _items = int(max_tunes)
                    except ValueError:
                        self.send_bot_msg('Only numbers allowed.', self.is_client_mod)
                    else:
                        if _items > 0:
                            if _items > 50:
                                self.send_bot_msg('No more than 50 tunes.', self.is_client_mod)
                            else:
                                self.send_bot_msg('Please wait while creating a playlist...', self.is_client_mod)
                                last = lastfm.lastfm_listening_now(max_tunes)
                                if last is not None:
                                    if self.media_timer_thread is not None and self.media_timer_thread.is_alive():
                                        self.playlist.extend(last)
                                        self.send_bot_msg('*Added:* ' + str(len(last)) + ' *tunes from last.fm*',
                                                          self.is_client_mod)
                                    else:
                                        self.playlist.extend(last)
                                        self.send_bot_msg('*Added:* ' + str(len(last)) + ' *tunes from last.fm*',
                                                          self.is_client_mod)
                                        self.last_played_media = self.playlist[self.inowplay]
                                        self.send_media_broadcast_start(self.playlist[self.inowplay]['type'],
                                                                        self.playlist[self.inowplay]['video_id'])
                                        self.media_event_timer(self.playlist[self.inowplay]['video_time'])
                                        self.inowplay += 1  # prepare the next tune in the playlist.
                                else:
                                    self.send_bot_msg('Failed to retrieve a result from last.fm.', self.is_client_mod)

    def search_lastfm_by_tag(self, search_str):  # EDITED
        """
        Searches last.fm for tunes matching the search term and creates a playlist from them.
        :param search_str: str the search term to search for.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(search_str) is 0:
                    self.send_bot_msg('Missing search tag.', self.is_client_mod)
                else:
                    self.send_bot_msg('Please wait while creating playlist..', self.is_client_mod)
                    last = lastfm.search_lastfm_by_tag(search_str)
                    if last is not None:
                        if self.media_timer_thread is not None and self.media_timer_thread.is_alive():
                            self.playlist.extend(last)
                            self.send_bot_msg('*Added:* ' + str(len(last)) + ' *tunes from last.fm*',
                                              self.is_client_mod)
                        else:
                            self.playlist.extend(last)
                            self.send_bot_msg('*Added:* ' + str(len(last)) + ' *tunes from last.fm*',
                                              self.is_client_mod)
                            self.last_played_media = self.playlist[self.inowplay]
                            self.send_media_broadcast_start(self.playlist[self.inowplay]['type'],
                                                            self.playlist[self.inowplay]['video_id'])
                            self.media_event_timer(self.playlist[self.inowplay]['video_time'])
                            self.inowplay += 1  # prepare the next tune in the playlist.
                    else:
                        self.send_bot_msg('Failed to retrieve a result from last.fm.', self.is_client_mod)

    # == Mod And Bot Controller Command Methods. ==
    def do_close_broadcast(self, user_name):  # EDITED
        """
        Close a user broadcasting.
        :param user_name: str the username to close.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(user_name) is 0:
                    self.send_bot_msg('Missing username.', self.is_client_mod)
                else:
                    user = self.find_user_info(user_name)
                    if user is not None:
                        self.send_close_user_msg(user_name)
                    else:
                        self.send_bot_msg('No user named: ' + user_name, self.is_client_mod)

    def do_clear(self):  # EDITED
        """ Clears the chatbox. """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                for x in range(0, 10):
                    self.send_owner_run_msg(' ')
            else:
                clear = '133,133,133,133,133,133,133,133,133,133,133,133,133,133,133'
                self._send_command('privmsg', [clear, u'#262626,en'])

    def do_skip(self):  # EDITED
        """ Play the next item in the playlist. """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if len(self.playlist) is not 0:
                if self.inowplay >= len(self.playlist):
                    self.send_bot_msg('*This is the last tune in the playlist.*', self.is_client_mod)
                else:
                    self.cancel_media_event_timer()
                    self.last_played_media = self.playlist[self.inowplay]
                    self.send_media_broadcast_start(self.playlist[self.inowplay]['type'],
                                                    self.playlist[self.inowplay]['video_id'])
                    self.media_event_timer(self.playlist[self.inowplay]['video_time'])
                    self.inowplay += 1  # prepare the next tune in the playlist.
            else:
                self.send_bot_msg('*No tunes to skip. The playlist is empty.*', self.is_client_mod)

    def do_delete_playlist_item(self, to_delete):  # EDITED
        """
        Delete item(s) from the playlist by index.
        :param to_delete: str index(es) to delete.
        """
        usage = '*' + OPTIONS['prefix'] + 'del 1* or *' + OPTIONS['prefix'] + 'del 1,2,4* or *' \
                + OPTIONS['prefix'] + 'del 2:8*'

        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if len(self.playlist) is 0:
                self.send_undercover_msg(self.user_obj.nick, 'The playlist is empty.')
            if len(to_delete) is 0:
                self.send_undercover_msg(self.user_obj.nick, usage)
            else:
                indexes = None
                deleted_by_range = False
                playlist_copy = list(self.playlist)
                # using : as a separator.
                if ':' in to_delete:
                    try:
                        range_indexes = map(int, to_delete.split(':'))
                        temp_indexes = range(range_indexes[0], range_indexes[1])
                    except ValueError:
                        self.send_undercover_msg(self.user_obj.nick, usage)
                    else:
                        indexes = []
                        for i in temp_indexes:
                            if i < len(self.playlist):
                                if i not in indexes:
                                    indexes.append(i)
                        if len(indexes) > 1:
                            deleted_by_range = True
                else:
                    try:
                        temp_indexes = map(int, to_delete.split(','))
                    except ValueError:
                        self.send_undercover_msg(self.user_obj.nick, usage)
                    else:
                        indexes = []
                        for i in temp_indexes:
                            if i < len(self.playlist):
                                if i not in indexes:
                                    indexes.append(i)
                deleted_indexes = []
                if indexes is not None and len(indexes) is not 0:
                    if len(self.playlist) is not 0:
                        for i in sorted(indexes, reverse=True):
                            if self.inowplay <= i < len(self.playlist):
                                del self.playlist[i]
                                deleted_indexes.append(str(i))
                        deleted_indexes.reverse()
                        if len(deleted_indexes) > 0:
                            if deleted_by_range:
                                self.send_bot_msg('*deleted: index range from(and including)* ' +
                                                  str(deleted_indexes[0]) + ' to ' + str(deleted_indexes[-1]),
                                                  self.is_client_mod)
                            elif len(deleted_indexes) is 1:
                                self.send_bot_msg('Deleted: *' + playlist_copy[int(deleted_indexes[0])]['video_title'] +
                                                  '*', self.is_client_mod)
                            else:
                                self.send_bot_msg('*Deleted tracks at index:* ' + ', '.join(deleted_indexes),
                                                  self.is_client_mod)
                        else:
                            self.send_bot_msg('Nothing was deleted.', self.is_client_mod)
                    else:
                        self.send_bot_msg('The playlist is empty, no tracks to delete.', self.is_client_mod)

    def do_media_replay(self):  # EDITED
        """ Replays the last played media."""
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            self.cancel_media_event_timer()
            self.send_media_broadcast_start(self.last_played_media['type'], self.last_played_media['video_id'])
            self.media_event_timer(self.last_played_media['video_time'])

    def do_close_media(self):  # EDITED
        """ Closes the active media broadcast."""
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.media_timer_thread is not None and self.media_timer_thread.is_alive():
                self.cancel_media_event_timer()
                self.send_media_broadcast_close(self.last_played_media['type'])

    def do_clear_playlist(self):  # EDITED
        """ Clear the playlist. """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if len(self.playlist) is not 0:
                pl_length = str(len(self.playlist))
                self.playlist[:] = []
                self.inowplay = 0
                self.send_bot_msg('*Deleted* ' + pl_length + ' *items in the playlist.*', self.is_client_mod)
            else:
                self.send_bot_msg('*The playlist is empty, nothing to delete.*', self.is_client_mod)

    def do_nick(self, new_nick):  # EDITED
        """
        Set a new nick for the bot.
        :param new_nick: str the new nick.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if len(new_nick) is 0:
                self.client_nick = pinylib.create_random_string(5, 25)
                self.set_nick()
            else:
                if re.match('^[][\{\}a-zA-Z0-9_-]{1,25}$', new_nick):
                    self.client_nick = new_nick
                    self.set_nick()

    def do_topic(self, topic):  # EDITED
        """
        Sets the room topic.
        :param topic: str the new topic.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(topic) is 0:
                    self.send_topic_msg('')
                    self.send_bot_msg('Topic was cleared.', self.is_client_mod)
                else:
                    self.send_topic_msg(topic)
                    self.send_bot_msg('The room topic was set to: ' + topic, self.is_client_mod)
            else:
                self.send_bot_msg('Command not enabled')

    def do_kick(self, user_name):  # EDITED
        """
        Kick a user out of the room.
        :param user_name: str the username to kick.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(user_name) is 0:
                    self.send_bot_msg('Missing username.', self.is_client_mod)
                elif user_name == self.client_nick:
                    self.send_bot_msg('Action not allowed.', self.is_client_mod)
                else:
                    user = self.find_user_info(user_name)
                    if user is None:
                        self.send_bot_msg('No user named: *' + user_name + '*', self.is_client_mod)
                    elif user.is_owner or user.is_super:
                        self.send_bot_msg('Not allowed.', self.is_client_mod)
                    else:
                        self.send_ban_msg(user_name, user.id)
                        self.send_forgive_msg(user.id)
            else:
                self.send_bot_msg('Command not enabled.')

    def do_ban(self, user_name):  # EDITED
        """
        Ban a user from the room.
        :param user_name: str the username to ban.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(user_name) is 0:
                    self.send_bot_msg('Missing username.', self.is_client_mod)
                elif user_name == self.client_nick:
                    self.send_bot_msg('Action not allowed.', self.is_client_mod)
                else:
                    user = self.find_user_info(user_name)
                    if user is None:
                        self.send_bot_msg('No user named: *' + user_name + '*', self.is_client_mod)
                    elif user.is_owner or user.is_super:
                        self.send_bot_msg('Not allowed.', self.is_client_mod)
                    else:
                        self.send_ban_msg(user_name, user.id)

    def do_bad_nick(self, bad_nick):  # EDITED
        """
        Adds a bad username to the bad nicks file.
        :param bad_nick: str the bad nick to write to file.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_nick) is 0:
                    self.send_bot_msg('Missing username.', self.is_client_mod)
                else:
                    badnicks = pinylib.fh.file_reader(self.config_path(), OPTIONS['badnicks'])
                    if badnicks is None:
                        pinylib.fh.file_writer(self.config_path(), OPTIONS['badnicks'], bad_nick)
                    else:
                        if bad_nick in badnicks:
                            self.send_bot_msg(bad_nick + ' is already in list.', self.is_client_mod)
                        else:
                            pinylib.fh.file_writer(self.config_path(), OPTIONS['badnicks'], bad_nick)
                            self.send_bot_msg('*' + bad_nick + '* was added to file.', self.is_client_mod)

    def do_remove_bad_nick(self, bad_nick):  # EDITED
        """
        Removes a bad nick from bad nicks file.
        :param bad_nick: str the bad nick to remove from file.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_nick) is 0:
                    self.send_bot_msg('Missing username', self.is_client_mod)
                else:
                    rem = pinylib.fh.remove_from_file(self.config_path(), OPTIONS['badnicks'], bad_nick)
                    if rem:
                        self.send_bot_msg(bad_nick + ' was removed.', self.is_client_mod)

    def do_bad_string(self, bad_string):  # EDITED
        """
        Adds a bad string to the bad strings file.
        :param bad_string: str the bad string to add to file.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_string) is 0:
                    self.send_bot_msg('Bad string can\'t be blank.', self.is_client_mod)
                elif len(bad_string) < 3:
                    self.send_bot_msg('Bad string to short: ' + str(len(bad_string)), self.is_client_mod)
                else:
                    bad_strings = pinylib.fh.file_reader(self.config_path(), OPTIONS['badstrings'])
                    if bad_strings is None:
                        pinylib.fh.file_writer(self.config_path(), OPTIONS['badstrings'], bad_string)
                    else:
                        if bad_string in bad_strings:
                            self.send_bot_msg(bad_string + ' is already in list.', self.is_client_mod)
                        else:
                            pinylib.fh.file_writer(self.config_path(), OPTIONS['badstrings'], bad_string)
                            self.send_bot_msg('*' + bad_string + '* was added to file.', self.is_client_mod)

    def do_remove_bad_string(self, bad_string):  # EDITED
        """
        Removes a bad string from the bad strings file.
        :param bad_string: str the bad string to remove from file.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_string) is 0:
                    self.send_bot_msg('Missing word string.', self.is_client_mod)
                else:
                    rem = pinylib.fh.remove_from_file(self.config_path(), OPTIONS['badstrings'], bad_string)
                    if rem:
                        self.send_bot_msg(bad_string + ' was removed.', self.is_client_mod)

    def do_bad_account(self, bad_account_name):  # EDITED
        """
        Adds a bad account name to the bad accounts file.
        :param bad_account_name: str the bad account name to add to file.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_account_name) is 0:
                    self.send_bot_msg('Account can\'t be blank.', self.is_client_mod)
                elif len(bad_account_name) < 3:
                    self.send_bot_msg('Account to short: ' + str(len(bad_account_name)), self.is_client_mod)
                else:
                    bad_accounts = pinylib.fh.file_reader(self.config_path(), OPTIONS['badaccounts'])
                    if bad_accounts is None:
                        pinylib.fh.file_writer(self.config_path(), OPTIONS['badaccounts'], bad_account_name)
                    else:
                        if bad_account_name in bad_accounts:
                            self.send_bot_msg(bad_account_name + ' is already in list.', self.is_client_mod)
                        else:
                            pinylib.fh.file_writer(self.config_path(), OPTIONS['badaccounts'], bad_account_name)
                            self.send_bot_msg('*' + bad_account_name + '* was added to file.', self.is_client_mod)

    def do_remove_bad_account(self, bad_account):  # EDITED
        """
        Removes a bad account from the bad accounts file.
        :param bad_account: str the badd account name to remove from file.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(bad_account) is 0:
                    self.send_bot_msg('Missing account.', self.is_client_mod)
                else:
                    rem = pinylib.fh.remove_from_file(self.config_path(), OPTIONS['badaccounts'], bad_account)
                    if rem:
                        self.send_bot_msg(bad_account + ' was removed.', self.is_client_mod)

    def do_list_info(self, list_type):  # EDITED
        """
        Shows info of different lists/files.
        :param list_type: str the type of list to find info for.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(list_type) is 0:
                    self.send_bot_msg('Missing list type.', self.is_client_mod)
                else:
                    if list_type.lower() == 'bn':
                        bad_nicks = pinylib.fh.file_reader(self.config_path(), OPTIONS['badnicks'])
                        if bad_nicks is None:
                            self.send_bot_msg('No items in this list.', self.is_client_mod)
                        else:
                            self.send_bot_msg(str(len(bad_nicks)) + ' bad nicks in list.', self.is_client_mod)

                    elif list_type.lower() == 'bs':
                        bad_strings = pinylib.fh.file_reader(self.config_path(), OPTIONS['badstrings'])
                        if bad_strings is None:
                            self.send_bot_msg('No items in this list.', self.is_client_mod)
                        else:
                            self.send_bot_msg(str(len(bad_strings)) + ' bad strings in list.', self.is_client_mod)

                    elif list_type.lower() == 'ba':
                        bad_accounts = pinylib.fh.file_reader(self.config_path(), OPTIONS['badaccounts'])
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
                                        self.send_owner_run_msg('(%s) *Next tune:*  *%s* %s' % (i, v_title, v_time))
                                    else:
                                        self.send_owner_run_msg('(%s) *%s* %s' % (i, v_title, v_time))
                                    i_count += 1

                    elif list_type.lower() == 'mods':
                        if self.is_client_owner and self.user_obj.is_super:
                            if len(self.privacy_settings.room_moderators) is 0:
                                self.send_bot_msg('*There is currently no moderators for this room.*',
                                                  self.is_client_mod)
                            elif len(self.privacy_settings.room_moderators) is not 0:
                                mods = ', '.join(self.privacy_settings.room_moderators)
                                self.send_bot_msg('*Moderators:* ' + mods, self.is_client_mod)

    def do_user_info(self, user_name):  # EDITED
        """
        Shows user object info for a given user name.
        :param user_name: str the user name of the user to show the info for.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
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
                        self.send_owner_run_msg('*Owner:* ' + str(user.is_owner))
                        if user.tinychat_id is not None:
                            self.send_owner_run_msg('*Account:* ' + str(user.user_account))
                            self.send_owner_run_msg('*Tinychat ID:* ' + str(user.tinychat_id))
                            self.send_owner_run_msg('*Last login:* ' + str(user.last_login))
                        self.send_owner_run_msg('*Last message:* ' + str(user.last_msg))

    def do_youtube_search(self, search_str):  # EDITED
        """
        Searches youtube for a given search term, and adds the results to a list.
        :param search_str: str the search term to search for.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
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

    def do_play_youtube_search(self, int_choice):  # EDITED
        """
        Plays a youtube from the search list.
        :param int_choice: int the index in the search list to play.
        """
        if self.user_obj.is_owner or self.user_obj.is_super \
                or self.user_obj.is_mod or self.user_obj.has_power:
            if self.is_client_mod:
                if len(self.search_list) > 0:
                    try:
                        index_choice = int(int_choice)
                        if 0 <= index_choice <= 4:
                            if self.media_timer_thread is not None and self.media_timer_thread.is_alive():
                                self.playlist.append(self.search_list[index_choice])
                                v_time = self.to_human_time(self.search_list[index_choice]['video_time'])
                                v_title = self.search_list[index_choice]['video_title']
                                self.send_bot_msg('(' + str(len(self.playlist) - 1) + ') *' + v_title + '* ' +
                                                  v_time, self.is_client_mod)
                            else:
                                self.last_played_media = self.search_list[index_choice]
                                self.send_media_broadcast_start(self.search_list[index_choice]['type'],
                                                                self.search_list[index_choice]['video_id'])
                                self.media_event_timer(self.search_list[index_choice]['video_time'])
                        else:
                            self.send_bot_msg('Please make a choice between 0-4', self.is_client_mod)
                    except ValueError:
                        self.send_bot_msg('Only numbers allowed.', self.is_client_mod)

    # == Public Command Methods. ==
    def do_version(self):  # NEW
        """ Show version info. """
        self.send_undercover_msg(self.user_obj.nick, '*bot version:* %s *pinylib version:* %s' %
                                 (__version__, pinylib.__version__))

    def do_help(self):
        """ Posts a link to github readme/wiki or other page about the bot commands. """
        self.send_undercover_msg(self.user_obj.nick, '*Help:* https://github.com/nortxort/pinylib/wiki/commands')

    def do_uptime(self):
        """ Shows the bots uptime. """
        self.send_bot_msg('*Uptime:* ' + self.to_human_time(self.get_uptime()) +
                          ' *Reconnect Delay:* ' + self.to_human_time(self.reconnect_delay * 1000),
                          self.is_client_mod)

    def do_pmme(self):
        """ Opens a PM session with the bot. """
        self.send_private_msg('How can i help you *' + self.user_obj.nick + '*?', self.user_obj.nick)

    #  == Media Related Command Methods. ==
    def do_playlist_status(self):
        """ Shows info about the playlist. """
        if self.is_client_mod:
            if len(self.playlist) is 0:
                self.send_bot_msg('*The playlist is empty.*', self.is_client_mod)
            else:
                inquee = len(self.playlist) - self.inowplay
                self.send_bot_msg(str(len(self.playlist)) + ' *items in the playlist.* ' + str(inquee) +
                                  ' *Still in queue.*', self.is_client_mod)
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_next_tune_in_playlist(self):
        """ Shows next item in the playlist. """
        if self.is_client_mod:
            if len(self.playlist) is 0:
                self.send_bot_msg('*No tunes in the playlist.*', self.is_client_mod)
            elif self.inowplay < len(self.playlist):
                play_time = self.to_human_time(self.playlist[self.inowplay]['video_time'])
                play_title = self.playlist[self.inowplay]['video_title']
                self.send_bot_msg('(' + str(self.inowplay) + ') *' + play_title + '* ' + play_time, self.is_client_mod)
            elif self.inowplay >= len(self.playlist):
                self.send_bot_msg('*This is the last tune in the playlist.*', self.is_client_mod)
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_now_playing(self):
        """ Shows the currently playing media title. """
        if self.is_client_mod:
            if self.media_timer_thread is not None and self.media_timer_thread.is_alive():
                if len(self.playlist) > 0:
                    self.send_undercover_msg(self.user_obj.nick, '(' + str(self.inowplay) + ') *' +
                                             self.last_played_media['video_title'] + '* ' +
                                             self.to_human_time(self.last_played_media['video_time']))
                else:
                    self.send_undercover_msg(self.user_obj.nick, '*' + self.last_played_media['video_title'] + '* ' +
                                             self.to_human_time(self.last_played_media['video_time']))
            else:
                self.send_undercover_msg(self.user_obj.nick, '*No track playing.*')

    def do_play_youtube(self, search_str):
        """
        Plays a youtube video matching the search term.
        :param search_str: str the search term.
        """
        log.info('User: %s:%s is searching youtube: %s' % (self.user_obj.nick, self.user_obj.id,  search_str))
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_bot_msg('Please specify youtube title, id or link.', self.is_client_mod)
            else:
                _youtube = youtube.youtube_search(search_str)
                if _youtube is None:
                    log.warning('Youtube request returned: %s' % _youtube)
                    self.send_bot_msg('Could not find video: ' + search_str, self.is_client_mod)
                else:
                    log.info('Youtube found: %s' % _youtube)
                    if self.media_timer_thread is not None and self.media_timer_thread.is_alive():
                        self.playlist.append(_youtube)
                        self.send_bot_msg('(' + str(len(self.playlist) - 1) + ') *' + _youtube['video_title'] + '* ' +
                                          self.to_human_time(_youtube['video_time']), self.is_client_mod)
                    else:
                        self.last_played_media = _youtube
                        self.send_media_broadcast_start(_youtube['type'], _youtube['video_id'])
                        self.media_event_timer(_youtube['video_time'])
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_play_private_youtube(self, search_str):
        """
        Plays a youtube matching the search term privately.
        NOTE: The video will only be visible for the message sender.
        :param search_str: str the search term.
        """
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_undercover_msg(self.user_obj.nick, 'Please specify youtube title, id or link.')
            else:
                _youtube = youtube.youtube_search(search_str)
                if _youtube is None:
                    self.send_undercover_msg(self.user_obj.nick, 'Could not find video: ' + search_str)
                else:
                    self.send_media_broadcast_start(_youtube['type'], _youtube['video_id'],
                                                    private_nick=self.user_obj.nick)
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_play_soundcloud(self, search_str):
        """
        Plays a soundcloud matching the search term.
        :param search_str: str the search term.
        """
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_bot_msg('Please specify soundcloud title or id.', self.is_client_mod)
            else:
                _soundcloud = soundcloud.soundcloud_search(search_str)
                if _soundcloud is None:
                    self.send_bot_msg('Could not find soundcloud: ' + search_str, self.is_client_mod)
                else:
                    if self.media_timer_thread is not None and self.media_timer_thread.is_alive():
                        self.playlist.append(_soundcloud)
                        self.send_bot_msg('(' + str(len(self.playlist) - 1) + ') *' + _soundcloud['video_title'] +
                                          '* ' + self.to_human_time(_soundcloud['video_time']), self.is_client_mod)
                    else:
                        self.last_played_media = _soundcloud
                        self.send_media_broadcast_start(_soundcloud['type'], _soundcloud['video_id'])
                        self.media_event_timer(_soundcloud['video_time'])
        else:
            self.send_bot_msg('Not enabled right now..')

    def do_play_private_soundcloud(self, search_str):
        """
        Plays a soundcloud matching the search term privately.
        NOTE: The video will only be visible for the message sender.
        :param search_str: str the search term.
        """
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_undercover_msg(self.user_obj.nick, 'Please specify soundcloud title or id.')
            else:
                _soundcloud = soundcloud.soundcloud_search(search_str)
                if _soundcloud is None:
                    self.send_undercover_msg(self.user_obj.nick, 'Could not find video: ' + search_str)
                else:
                    self.send_media_broadcast_start(_soundcloud['type'], _soundcloud['video_id'],
                                                    private_nick=self.user_obj.nick)
        else:
            self.send_bot_msg('Not enabled right now..')

    # == Tinychat API Command Methods. ==
    def do_spy(self, roomname):
        """
        Shows info for a given room.
        :param roomname: str the room name to find info for.
        """
        if self.is_client_mod:
            if len(roomname) is 0:
                self.send_undercover_msg(self.user_obj.nick, 'Missing room name.')
            else:
                spy_info = pinylib.tinychat_api.spy_info(roomname)
                if spy_info is None:
                    self.send_undercover_msg(self.user_obj.nick, 'The room is empty.')
                elif spy_info == 'PW':
                    self.send_undercover_msg(self.user_obj.nick, 'The room is password protected.')
                else:
                    self.send_undercover_msg(self.user_obj.nick,
                                             '*mods:* ' + spy_info['mod_count'] +
                                             ' *Broadcasters:* ' + spy_info['broadcaster_count'] +
                                             ' *Users:* ' + spy_info['total_count'])
                    if self.user_obj.is_owner or self.user_obj.is_mod or self.user_obj.has_power:
                        users = ', '.join(spy_info['users'])
                        self.send_undercover_msg(self.user_obj.nick, '*' + users + '*')

    def do_account_spy(self, account):
        """
        Shows info about a tinychat account.
        :param account: str tinychat account.
        """
        if self.is_client_mod:
            if len(account) is 0:
                self.send_undercover_msg(self.user_obj.nick, 'Missing username to search for.')
            else:
                tc_usr = pinylib.tinychat_api.tinychat_user_info(account)
                if tc_usr is None:
                    self.send_undercover_msg(self.user_obj.nick, 'Could not find tinychat info for: ' + account)
                else:
                    self.send_undercover_msg(self.user_obj.nick, 'ID: ' + tc_usr['tinychat_id'] +
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

        # Is this a custom PM command?
        if private_msg.startswith(OPTIONS['prefix']):
            # Split the message in to parts.
            pm_parts = private_msg.split(' ')
            # pm_parts[0] is the command.
            pm_cmd = pm_parts[0].lower().strip()
            # The rest is a command argument.
            pm_arg = ' '.join(pm_parts[1:]).strip()

            # Super mod commands.
            if pm_cmd == OPTIONS['prefix'] + 'rp':  # NEW
                threading.Thread(target=self.do_set_room_pass, args=(pm_arg, )).start()

            elif pm_cmd == OPTIONS['prefix'] + 'bp':  # NEW
                threading.Thread(target=self.do_set_braodcast_pass, args=(pm_arg, )).start()

            # Owner and super mod commands.
            if pm_cmd == OPTIONS['prefix'] + 'key':
                self.do_key(pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'clrbn':
                self.do_clear_bad_nicks()

            elif pm_cmd == OPTIONS['prefix'] + 'clrbs':
                self.do_clear_bad_strings()

            elif pm_cmd == OPTIONS['prefix'] + 'clrba':
                self.do_clear_bad_accounts()

            # Mod and bot controller commands.
            elif pm_cmd == OPTIONS['prefix'] + 'op':
                self.do_op_user(pm_parts)

            elif pm_cmd == OPTIONS['prefix'] + 'deop':
                self.do_deop_user(pm_parts)

            elif pm_cmd == OPTIONS['prefix'] + 'up':
                self.do_cam_up(pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'down':
                self.do_cam_down(pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'nocam':
                self.do_nocam(pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'noguest':
                self.do_no_guest(pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'guestnick':  # NEW
                self.do_no_guest_nicks(pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'newusers':
                self.do_newusers(pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'skip':
                self.do_skip()

            # Public commands.
            elif pm_cmd == OPTIONS['prefix'] + 'sudo':  # NEW
                self.do_super_user(pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'opme':
                self.do_opme(pm_arg)

            elif pm_cmd == OPTIONS['prefix'] + 'pm':
                self.do_pm_bridge(pm_parts)

        # Print to console.
        self.console_write(pinylib.COLOR['white'], 'Private message from ' + msg_sender + ':' + str(private_msg)
                           .replace(self.key, '***KEY***')
                           .replace(OPTIONS['super_key'], '***SUPER KEY***'))

    # == Super Mod Command Methods. ==
    def do_set_room_pass(self, password):  # NEW
        """
        Set a room password for the room.
        :param password: str the room password
        """
        if self.is_client_owner:
            if self.user_obj.is_super:
                if not password:
                    self.privacy_settings.set_room_password()
                    self.send_bot_msg('*The room password was removed.*', self.is_client_mod)
                    pinylib.time.sleep(1)
                    self.send_private_msg('The room password was removed.', self.user_obj.nick)
                elif len(password) > 1:
                    self.privacy_settings.set_room_password(password)
                    self.send_private_msg('*The room password is now:* ' + password, self.user_obj.nick)
                    pinylib.time.sleep(1)
                    self.send_bot_msg('*The room is now password protected.*', self.is_client_mod)

    def do_set_braodcast_pass(self, password):  # NEW
        """
        Set a broadcast password for the room.
        :param password: str the password
        """
        if self.is_client_owner:
            if self.user_obj.is_super:
                if not password:
                    self.privacy_settings.set_broadcast_password()
                    self.send_bot_msg('*The broadcast password was removed.*', self.is_client_mod)
                    pinylib.time.sleep(1)
                    self.send_private_msg('The broadcast password was removed.', self.user_obj.nick)
                elif len(password) > 1:
                    self.privacy_settings.set_broadcast_password(password)
                    self.send_private_msg('*The broadcast password is now:* ' + password, self.user_obj.nick)
                    pinylib.time.sleep(1)
                    self.send_bot_msg('*Broadcast password is enabled.*', self.is_client_mod)

    # == Owner And Super Mod Command Methods. ==
    def do_key(self, new_key):  # EDITED
        """
        Shows or sets a new secret key.
        :param new_key: str the new secret key.
        """
        if self.user_obj.is_owner or self.user_obj.is_super:
            if len(new_key) is 0:
                self.send_private_msg('The current key is: *' + self.key + '*', self.user_obj.nick)
            elif len(new_key) < 6:
                self.send_private_msg('Key must be at least 6 characters long: ' + str(len(self.key)),
                                      self.user_obj.nick)
            elif len(new_key) >= 6:
                self.key = new_key
                self.send_private_msg('The key was changed to: *' + self.key + '*', self.user_obj.nick)

    def do_clear_bad_nicks(self):  # EDITED
        """ Clears the bad nicks file. """
        if self.user_obj.is_owner or self.user_obj.is_super:
            pinylib.fh.delete_file_content(self.config_path(), OPTIONS['badnicks'])

    def do_clear_bad_strings(self):  # EDITED
        """ Clears the bad strings file. """
        if self.user_obj.is_owner or self.user_obj.is_super:
            pinylib.fh.delete_file_content(self.config_path(), OPTIONS['badstrings'])

    def do_clear_bad_accounts(self):  # EDITED
        """ Clears the bad accounts file. """
        if self.user_obj.is_owner or self.user_obj.is_super:
            pinylib.fh.delete_file_content(self.config_path(), OPTIONS['badaccounts'])

    # == Mod And Bot Controller Command Methods. ==
    def do_op_user(self, msg_parts):  # EDITED
        """
        Lets the room owner, a mod or a bot controller make another user a bot controller.
        NOTE: Mods or bot controllers will have to provide a key, owner and super does not.
        :param msg_parts: list the pm message as a list.
        """
        if self.user_obj.is_owner or self.user_obj.is_super:
            if len(msg_parts) == 1:
                self.send_private_msg('Missing username.', self.user_obj.nick)
            elif len(msg_parts) == 2:
                user = self.find_user_info(msg_parts[1])
                if user is not None:
                    user.has_power = True
                    self.send_private_msg(user.nick + ' is now a bot controller.', self.user_obj.nick)
                    # self.send_private_msg('You are now a bot controller.', user.nick)
                else:
                    self.send_private_msg('No user named: ' + msg_parts[1], self.user_obj.nick)

        elif self.user_obj.is_mod or self.user_obj.has_power:
            if len(msg_parts) == 1:
                self.send_private_msg('Missing username.', self.user_obj.nick)
            elif len(msg_parts) == 2:
                self.send_private_msg('Missing key.', self.user_obj.nick)
            elif len(msg_parts) == 3:
                if msg_parts[2] == self.key:
                    user = self.find_user_info(msg_parts[1])
                    if user is not None:
                        user.has_power = True
                        self.send_private_msg(user.nick + ' is now a bot controller.', self.user_obj.nick)
                    else:
                        self.send_private_msg('No user named: ' + msg_parts[1], self.user_obj.nick)
                else:
                    self.send_private_msg('Wrong key.', self.user_obj.nick)

    def do_deop_user(self, msg_parts):  # EDITED
        """
        Lets the room owner, a mod or a bot controller remove a user from being a bot controller.
        NOTE: Mods or bot controllers will have to provide a key, owner and super does not.
        :param msg_parts: list the pm message as a list
        """
        if self.user_obj.is_owner or self.user_obj.is_super:
            if len(msg_parts) == 1:
                self.send_private_msg('Missing username.', self.user_obj.nick)
            elif len(msg_parts) == 2:
                user = self.find_user_info(msg_parts[1])
                if user is not None:
                    user.has_power = False
                    self.send_private_msg(user.nick + ' is not a bot controller anymore.', self.user_obj.nick)
                else:
                    self.send_private_msg('No user named: ' + msg_parts[1], self.user_obj.nick)

        elif self.user_obj.is_mod or self.user_obj.has_power:
            if len(msg_parts) == 1:
                self.send_private_msg('Missing username.', self.user_obj.nick)
            elif len(msg_parts) == 2:
                self.send_private_msg('Missing key.', self.user_obj.nick)
            elif len(msg_parts) == 3:
                if msg_parts[2] == self.key:
                    user = self.find_user_info(msg_parts[1])
                    if user is not None:
                        user.has_power = False
                        self.send_private_msg(user.nick + ' is not a bot controller anymore.', self.user_obj.nick)
                    else:
                        self.send_private_msg('No user named: ' + msg_parts[1], self.user_obj.nick)
                else:
                    self.send_private_msg('Wrong key.', self.user_obj.nick)

    def do_cam_up(self, key):  # EDITED
        """
        Makes the bot camup.
        NOTE: Mods or bot controllers will have to provide a key, owner and super does not.
        :param key str the key needed for moderators/bot controllers.
        """
        if self.user_obj.is_owner or self.user_obj.is_super:
            self.send_bauth_msg()
            self.send_create_stream()
            self.send_publish()
        elif self.user_obj.is_mod or self.user_obj.has_power:
            if len(key) is 0:
                self.send_private_msg('Missing key.', self.user_obj.nick)
            elif key == self.key:
                self.send_bauth_msg()
                self.send_create_stream()
                self.send_publish()
            else:
                self.send_private_msg('Wrong key.', self.user_obj.nick)

    def do_cam_down(self, key):  # EDITED
        """
        Makes the bot cam down.
        NOTE: Mods or bot controllers will have to provide a key, owner and super does not.
        :param key: str the key needed for moderators/bot controllers.
        """
        if self.user_obj.is_owner or self.user_obj.is_super:
            self.send_close_stream()
        elif self.user_obj.is_mod or self.user_obj.has_power:
            if len(key) is 0:
                self.send_private_msg('Missing key.', self.user_obj.nick)
            elif key == self.key:
                self.send_close_stream()
            else:
                self.send_private_msg('Wrong key.', self.user_obj.nick)

    def do_nocam(self, key):  # EDITED
        """
        Toggles if broadcasting is allowed or not.
        NOTE: Mods or bot controllers will have to provide a key, owner and super does not.
        :param key: str secret key.
        """
        if self.is_broadcasting_allowed or self.user_obj.is_super:
            if self.user_obj.is_owner:
                self.is_broadcasting_allowed = False
                self.send_private_msg('*Broadcasting is NOT allowed.*', self.user_obj.nick)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_msg('missing key.', self.user_obj.nick)
                elif key == self.key:
                    self.is_broadcasting_allowed = False
                    self.send_private_msg('*Broadcasting is NOT allowed.*', self.user_obj.nick)
                else:
                    self.send_private_msg('Wrong key.', self.user_obj.nick)
        else:
            if self.user_obj.is_owner or self.user_obj.is_super:
                self.is_broadcasting_allowed = True
                self.send_private_msg('*Broadcasting is allowed.*', self.user_obj.nick)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_msg('missing key.', self.user_obj.nick)
                elif key == self.key:
                    self.is_broadcasting_allowed = True
                    self.send_private_msg('*Broadcasting is allowed.*', self.user_obj.nick)
                else:
                    self.send_private_msg('Wrong key.', self.user_obj.nick)

    def do_no_guest(self, key):  # EDITED
        """
        Toggles if guests are allowed to join the room or not.
        NOTE: Mods or bot controllers will have to provide a key, owner and super does not.
        :param key: str secret key.
        """
        if self.is_guest_entry_allowed:
            if self.user_obj.is_owner or self.user_obj.is_super:
                self.is_guest_entry_allowed = False
                self.send_private_msg('*Guests are NOT allowed to join the room.*', self.user_obj.nick)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_msg('missing key.', self.user_obj.nick)
                elif key == self.key:
                    self.is_guest_entry_allowed = False
                    self.send_private_msg('*Guests are NOT allowed to join.*', self.user_obj.nick)
                else:
                    self.send_private_msg('Wrong key.', self.user_obj.nick)
        else:
            if self.user_obj.is_owner or self.user_obj.is_super:
                self.is_guest_entry_allowed = True
                self.send_private_msg('*Guests ARE allowed to join the room.*', self.user_obj.nick)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_msg('missing key.', self.user_obj.nick)
                elif key == self.key:
                    self.is_guest_entry_allowed = True
                    self.send_private_msg('*Guests ARE allowed to join.*', self.user_obj.nick)
                else:
                    self.send_private_msg('Wrong key.', self.user_obj.nick)

    def do_no_guest_nicks(self, key):  # NEW/ISSUE #24
        """
        Toggles if guest nicks are allowed or not.
        NOTE: Mods or bot controllers will have to provide a key, owner and super does not.
        :param key: str secret key.
        """
        if self.is_guest_nicks_allowed:
            if self.user_obj.is_owner or self.user_obj.is_super:
                self.is_guest_nicks_allowed = False
                self.send_private_msg('*Guests nicks are NOT allowed.*', self.user_obj.nick)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_msg('missing key.', self.user_obj.nick)
                elif key == self.key:
                    self.is_guest_nicks_allowed = False
                    self.send_private_msg('*Guests nicks are NOT allowed.*', self.user_obj.nick)
                else:
                    self.send_private_msg('wrong key.', self.user_obj.nick)
        else:
            if self.user_obj.is_owner or self.user_obj.is_super:
                self.is_guest_nicks_allowed = True
                self.send_private_msg('*Guests nicks ARE allowed.*', self.user_obj.nick)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_msg('missing key.', self.user_obj.nick)
                elif key == self.key:
                    self.is_guest_nicks_allowed = True
                    self.send_private_msg('*Guests nicks ARE allowed.*', self.user_obj.nick)
                else:
                    self.send_private_msg('wrong key.', self.user_obj.nick)

    def do_newusers(self, key):  # EDITED
        """
        Toggles if newusers are allowed to join the room or not.
        NOTE: Mods or bot controllers will have to provide a key, owner and super does not.
        :param key: str secret key.
        """
        if self.is_newusers_allowed:
            if self.user_obj.is_owner or self.user_obj.is_super:
                self.is_newusers_allowed = False
                self.send_private_msg('*Newusers are NOT allowed to join the room.*', self.user_obj.nick)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_msg('missing key.', self.user_obj.nick)
                elif key == self.key:
                    self.is_newusers_allowed = False
                    self.send_private_msg('*Newusers are NOT allowed to join the room.*', self.user_obj.nick)
                else:
                    self.send_private_msg('Wrong key.', self.user_obj.nick)
        else:
            if self.user_obj.is_owner or self.user_obj.is_super:
                self.is_newusers_allowed = True
                self.send_private_msg('*Newusers ARE allowed to join the room.*', self.user_obj.nick)
            elif self.user_obj.is_mod or self.user_obj.has_power:
                if len(key) is 0:
                    self.send_private_msg('missing key.', self.user_obj.nick)
                elif key == self.key:
                    self.is_newusers_allowed = True
                    self.send_private_msg('*Newusers ARE allowed to join the room.*', self.user_obj.nick)
                else:
                    self.send_private_msg('Wrong key.', self.user_obj.nick)

    # == Public PM Command Methods. ==
    def do_super_user(self, super_key):  # NEW
        """
        Makes a user super mod, the highest level of mod.
        It is only possible to be a super mod if the client is owner.
        :param super_key: str the super key
        """
        if self.is_client_owner:
            if len(super_key) is 0:
                self.send_private_msg('Missing super key.', self.user_obj.nick)
            elif super_key == OPTIONS['super_key']:
                self.user_obj.is_super = True
                self.send_private_msg('*You are now a super mod.*', self.user_obj.nick)
            else:
                self.send_private_msg('Wrong super key.', self.user_obj.nick)
        else:
            self.send_private_msg('Client is owner: *' + str(self.is_client_owner) + '*',
                                  self.user_obj.nick)

    def do_opme(self, key):
        """
        Makes a user a bot controller if user provides the right key.
        :param key: str the secret key.
        """
        if len(key) is 0:
            self.send_private_msg('Missing key.', self.user_obj.nick)
        elif key == self.key:
            self.user_obj.has_power = True
            self.send_private_msg('You are now a bot controller.', self.user_obj.nick)
        else:
            self.send_private_msg('Wrong key.', self.user_obj.nick)

    def do_pm_bridge(self, pm_parts):
        """
        Makes the bot work as a PM message bridge between 2 user who are not signed in.
        :param pm_parts: list the pm message as a list.
        """
        if len(pm_parts) == 1:
            self.send_private_msg('Missing username.', self.user_obj.nick)
        elif len(pm_parts) == 2:
            self.send_private_msg('The command is: ' + OPTIONS['prefix'] + 'pm username message', self.user_obj.nick)
        elif len(pm_parts) >= 3:
            pm_to = pm_parts[1]
            msg = ' '.join(pm_parts[2:])
            is_user = self.find_user_info(pm_to)
            if is_user is not None:
                if is_user.id == self.client_id:
                    self.send_private_msg('Action not allowed.', self.user_obj.nick)
                else:
                    self.send_private_msg('*<' + self.user_obj.nick + '>* ' + msg, pm_to)
            else:
                self.send_private_msg('No user named: ' + pm_to, self.user_obj.nick)

    #  Timed auto functions.
    def media_event_handler(self):
        """ This method gets called whenever a media is done playing. """
        if len(self.playlist) is not 0:
            if self.inowplay >= len(self.playlist):
                if self.is_connected:
                    self.send_bot_msg('*Resetting playlist.*', self.is_client_mod)
                self.inowplay = 0
                self.playlist[:] = []
            else:
                if self.is_connected:
                    self.last_played_media = self.playlist[self.inowplay]
                    self.send_media_broadcast_start(self.playlist[self.inowplay]['type'],
                                                    self.playlist[self.inowplay]['video_id'])
                self.media_event_timer(self.playlist[self.inowplay]['video_time'])
                self.inowplay += 1

    def media_event_timer(self, video_time):
        """
        Set of a timed event thread.
        :param video_time: int the time in milliseconds.
        """
        video_time_in_seconds = video_time / 1000
        # The next line should be where ever send_media_broadcast_start is called.
        # For now ill leave it here as it doesn't seem to cause any problems.
        # However if a tune gets paused, then current_media_time_point will return a wrong time
        # this could affect user joining the room and therefor it should be fixed.
        self.media_start_time = int(pinylib.time.time() * 1000)
        self.media_timer_thread = threading.Timer(video_time_in_seconds, self.media_event_handler)
        self.media_timer_thread.start()

    def random_msg(self):
        """
        Pick a random message from a list of messages.
        :return: str random message.
        """
        upnext = 'Use *' + OPTIONS['prefix'] + 'yt* youtube title, link or id to add or play youtube.'
        plstat = 'Use *' + OPTIONS['prefix'] + 'sc* soundcloud title or id to add or play soundcloud.'
        if len(self.playlist) is not 0:
            if self.inowplay + 1 < len(self.playlist):
                next_video_title = self.playlist[self.inowplay]['video_title']
                next_video_time = self.to_human_time(self.playlist[self.inowplay]['video_time'])
                upnext = '*Next is:* (' + str(self.inowplay) + ') *' + next_video_title + '* ' + next_video_time
            inquee = len(self.playlist) - self.inowplay
            plstat = str(len(self.playlist)) + ' *items in the playlist.* ' + str(inquee) + ' *Still in queue.*'

        messages = ['Reporting for duty..', 'Hello, is anyone here?', 'Awaiting command..', 'Observing behavior..',
                    upnext, plstat, '*Uptime:* ' + self.to_human_time(self.get_uptime()),
                    'Type: *' + OPTIONS['prefix'] + 'help* for a list of commands']

        return random.choice(messages)

    def auto_msg_handler(self):
        """ The event handler for auto_msg_timer. """
        if self.is_connected:
            self.send_bot_msg(self.random_msg())
        self.start_auto_msg_timer()

    def start_auto_msg_timer(self):
        """
        In rooms with less activity, it can be useful to have the client send auto messages to keep the client alive.
        This method can be disabled by setting BOT_OPTIONS['auto_message_sender'] to False.
        The interval for when a message should be sent, is set in BOT_OPTIONS['auto_message_interval']
        """
        threading.Timer(OPTIONS['auto_message_interval'], self.auto_msg_handler).start()

    # Helper Methods.
    def get_privacy_settings(self):  # NEW
        """ Parse the privacy settings page. """
        log.info('Parsing %s\'s privacy page. Proxy %s' % (self.account, self.proxy))
        self.privacy_settings = privacy_settings.TinychatPrivacyPage(self.proxy)
        self.privacy_settings.parse_privacy_settings()

    def config_path(self):
        """ Returns the path to the rooms configuration directory. """
        path = pinylib.SETTINGS['config_path'] + self.roomname + '/'
        return path

    def current_media_time_point(self):
        """
        Returns the currently playing medias time point.
        :return: int the currently playing medias time point in milliseconds.
        """
        if 'pause' in self.last_played_media:
            return self.last_played_media['pause']
        else:
            if self.media_timer_thread is not None:
                if self.media_timer_thread.is_alive():
                    ts_now = int(pinylib.time.time() * 1000)
                    elapsed_track_time = ts_now - self.media_start_time
                    return elapsed_track_time
                return 0
            return 0

    def cancel_media_event_timer(self):
        """
        Cancel the media event timer if it is running.
        :return: True if canceled, else False
        """
        if self.media_timer_thread is not None:
            if self.media_timer_thread.is_alive():
                self.media_timer_thread.cancel()
                self.media_timer_thread = None
                return True
            return False
        return False

    def get_uptime(self):
        """
        Gets the bots uptime.
        NOTE: This will not get reset after a reconnect.
        :return: int milliseconds.
        """
        up = int(pinylib.time.time() - self.init_time)
        return up * 1000

    @staticmethod
    def to_human_time(milliseconds):
        """
        Converts milliseconds or seconds to (day(s)) hours minutes seconds.
        :param milliseconds: int the milliseconds or seconds to convert.
        :return: str in the format (days) hh:mm:ss
        """
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
        bad_strings = pinylib.fh.file_reader(self.config_path(), OPTIONS['badstrings'])
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

    t = threading.Thread(target=client.prepare_connect)
    t.daemon = True
    t.start()

    while not client.is_connected:
        pinylib.time.sleep(1)
    while client.is_connected:
        chat_msg = raw_input()
        if chat_msg.lower() == 'q':
            client.disconnect()
        else:
            client.send_bot_msg(chat_msg, client.is_client_mod)

if __name__ == '__main__':
    if OPTIONS['debug_to_file']:
        formater = '%(asctime)s : %(levelname)s : %(filename)s : %(lineno)d : %(funcName)s() : %(name)s : %(message)s'
        logging.basicConfig(filename=OPTIONS['debug_file_name'], level=logging.DEBUG, format=formater)
        log.info('Starting bot_example.py version: %s, pinylib version: %s' % (__version__, pinylib.__version__))
    else:
        log.addHandler(logging.NullHandler())
    main()
