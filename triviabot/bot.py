# -*- coding: utf-8 -*-

from twisted.words.protocols import irc
from twisted.internet import threads
from twisted.python import log
import requests
import urllib
import time
import random

class Bot(irc.IRCClient):
    """ChatBot class"""

    nickname = ""
    password = ""
    username = ""
    realname = ""
    kickrejoin = False
    joininvite = False
    trivia = {}

    def connectionMade(self):
        """Is run when the connection is successful."""
        self.nickname = self.factory.nickname
        self.password = self.factory.password
        self.username = self.factory.username
        self.realname = self.factory.realname
        self.lineRate = self.factory.linerate
        self.joininvite = self.factory.joininvite
        self.kickrejoin = self.factory.kickrejoin

        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        """Is run if the connection is lost."""
        irc.IRCClient.connectionLost(self, reason)

    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.mode(self.nickname, True, "B")

    def kickedFrom(self, channel, kicker, message):
        """Called when I am kicked from a channel."""
        if self.kickrejoin:
            self.join(channel)

        log.msg("I was kicked from {} by {} because: {}".format(
            channel, kicker, message))

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        log.msg("I joined {}".format(channel))
        self.trivia[channel] = {'current': 0, 'questions': None, 'answers': {}, 'scores': {}}

    def left(self, channel):
        """This will get called when the bot leaves a channel."""
        del self.trivia[channel]

    def noticed(self, user, channel, msg):
        """Called when a notice is recieved."""
        log.msg("From %s/%s: %s" % (user, channel, msg))

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""

        if msg.startswith(self.factory.prefix):
            cmd = msg.split()[0].strip(self.factory.prefix)
            args = msg.split()[1:] or [None, ]
            func = None

            if cmd == "a":
                func = getattr(self, 'cmd_' + cmd, None)
                threads.deferToThread(func, user, channel, msg.split(" ", 2)[1], msg.split(" ", 2)[2])
            elif cmd == "start":
                func = getattr(self, 'cmd_' + cmd, None)
                threads.deferToThread(func, user, channel, *args)
            else:
                if user.split('!', 1)[0] == "No-0n3":
                    func = getattr(self, 'cmd_' + cmd, None)

                    if func is not None:
                        threads.deferToThread(func, user, channel, *args)
                    else:
                        self.notice(user.split('!', 1)[0], "Unknown command!")

    def irc_INVITE(self, inviter, params):
        """Action when the bot recevies an invite."""
        log.msg("{} invited {} to {}.".format(inviter, params[0], params[1]))

        if self.joininvite:
            self.join(params[1])

    # User-defined commands
    def cmd_join(self, user, src_chan, channel, password=None):
        """Join a channel. @join <channel> [<password>]"""
        if channel:
            self.join(channel, password)

    def cmd_part(self, user, src_chan, channel, password=None):
        """Leave a channel. @part <channel>"""
        if channel:
            self.part(channel)

    def cmd_help(self, user, src_chan, cmd=None):
        """Lists help about commands. @help [<cmd>]"""
        user = user.split('!', 1)[0]

        if cmd is None:
            self.notice(user, "Commands:")

            for func in dir(self):
                if func.startswith("cmd_"):
                    self.notice(user, self.factory.prefix + func[4:] + " - " +
                                getattr(self, func).__doc__)
        else:
            func = getattr(self, "cmd_" + cmd)
            self.notice(user, self.factory.prefix + func.__name__[4:] + " - " + func.__doc__)

    def cmd_quit(self, user, src_chan, *args):
        """Shutdown the bot."""
        self.quit(message="Shutting down.")

    def cmd_a(self, user, src_chan, chan, answer):
        """Send an answer to the question"""
        nick = user.split('!', 1)[0]

        if answer == "":
            self.notice(user, "Invalid answer! (Empty)")
            return

        if nick in self.trivia[chan]['answers']:
            self.notice(user, "You've already answered!")
            return

        if nick not in self.trivia[chan]['scores']:
            self.trivia[chan]['scores'][nick] = 0

        self.trivia[chan]['answers'][nick] = answer

    def cmd_kickrejoin(self, user, src_chan, *args):
        """Command to toggle kickrejoin. @kickrejoin"""
        self.kickrejoin = not self.kickrejoin
        self.notice(user.split('!', 1)[0], "Kickrejoin: %s" % self.kickrejoin)

    def cmd_joininvite(self, user, src_chan, *args):
        """Command to toggle joininvite. @joininvite"""
        self.joininvite = not self.joininvite
        self.notice(user.split('!', 1)[0], "Joininvite: %s" % self.joininvite)

    def cmd_start(self, user, src_chan, *args):
        """Command to start a trivia of 10 questions"""
        try:
            r = requests.get('https://opentdb.com/api.php?amount=10&encode=url3986')
            r.raise_for_status()
            self.trivia[src_chan]['questions'] = r.json()
            self.trivia[src_chan]['current'] = 0
        except requests.exceptions.RequestException as e:
            self.notice(user.split('!', 1)[0], "Error: Couldn't load questions (%s)" % e)
            return

        if self.trivia[src_chan]['questions']['response_code'] != 0:
            self.notice(user.split('!', 1)[0], "Error: Couldn't load questions (Code: %s)" % self.trivia[channel]['questions']['response_code'])
            return

        self.msg(src_chan, "=== Trivia Time ===")
        self.msg(src_chan, "Answer questions by sending command '%sa <channel> <answer>', you can only answer once. You have 1 minute to respond. For boolean type question answer with \"true\" or \"false\". For mulitple type question answer with one of the presented answers, spelling is important. First question in 30 seconds." % self.factory.prefix)
        time.sleep(30)
        threads.deferToThread(self.next_question, src_chan)

    def next_question(self, channel):
        """Function that sends next question to channel."""
        correct_answer = urllib.unquote(self.trivia[channel]['questions']['results'][self.trivia[channel]['current']]['correct_answer'])
        incorrect_answers = [urllib.unquote(a) for a in self.trivia[channel]['questions']['results'][self.trivia[channel]['current']]['incorrect_answers']]
        type = urllib.unquote(self.trivia[channel]['questions']['results'][self.trivia[channel]['current']]['type'])
        difficulty = urllib.unquote(self.trivia[channel]['questions']['results'][self.trivia[channel]['current']]['difficulty'])
        category = urllib.unquote(self.trivia[channel]['questions']['results'][self.trivia[channel]['current']]['category'])
        question = urllib.unquote(self.trivia[channel]['questions']['results'][self.trivia[channel]['current']]['question'])
        score = {"easy": 1, "medium": 2, "hard": 3}

        self.msg(channel, "Question: %s (%s, %s, %s)" % (question, category, type, difficulty))

        if type == "multiple":
            answers = incorrect_answers + [correct_answer,]
            random.shuffle(answers);

            self.msg(channel, "Answers: %s, %s, %s, %s" % (answers[0], answers[1], answers[2], answers[3]))

        time.sleep(60)

        self.msg(channel, "Times-up! Correct answer: %s" % correct_answer)

        for nick, answer in self.trivia[channel]['answers'].items():
            if answer.lower() == correct_answer.lower():
                self.trivia[channel]['scores'][nick] += score[difficulty]

        self.trivia[channel]['current'] += 1
        self.trivia[channel]['answers'] = {}

        if self.trivia[channel]['current'] < 10:
            threads.deferToThread(self.next_question, channel)
        else:
            scores = sorted(self.trivia[channel]['scores'].items(), key=lambda x: x[1], reverse=True)

            self.msg(channel, "=== Scores (Only Top 3) ===")

            for n, s in scores:
                self.msg(channel, "%s: %s" % (n, s))

            self.trivia[channel]['scores'] = {}
