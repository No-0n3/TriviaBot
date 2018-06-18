# -*- coding: utf-8 -*-

from twisted.internet import protocol, reactor
from twisted.python import log
from .bot import Bot


class BotFactory(protocol.ReconnectingClientFactory):
    """A factory for Bots.

    A new protocol instance will be created each time we connect to the server.
    """

    protocol = Bot

    def __init__(self, config):
        """Init"""

        self.nickname = config['network'].get('nickname',
            config["identity"]["nickname"]).encode('utf8')
        self.password = config['network']['password'].encode('utf8')
        self.username = config['network'].get('username',
            config["identity"]["nickname"]).encode('utf8')
        self.realname = config['network'].get('realname',
            config["identity"]["nickname"]).encode('utf8')
        self.linerate = config['general']['linerate']
        self.prefix = config['general']['prefix'].encode('utf8')
        self.joininvite = config['general']['joininvite']
        self.kickrejoin = config['general']['kickrejoin']

    def startFactory(self):
        """Called when starting factory"""
        protocol.ReconnectingClientFactory.startFactory(self)

    def stopFactory(self):
        """Called when stopping factory"""
        protocol.ReconnectingClientFactory.stopFactory(self)

        if reactor.running:
            reactor.stop()

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""

        protocol.ReconnectingClientFactory.clientConnectionLost(self,
            connector, reason)

    def clientConnectionFailed(self, connector, reason):
        """Is run if the connection fails."""
        log.err(reason)

        protocol.ReconnectingClientFactory.clientConnectionLost(self,
            connector, reason)
