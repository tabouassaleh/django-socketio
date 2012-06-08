from re import match
from thread import start_new_thread
from time import sleep
from os import getpid, kill, environ
from signal import SIGINT

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.core.management.base import BaseCommand, CommandError
from django.core.management.commands.runserver import naiveip_re
from django.utils.autoreload import code_changed, restart_with_reloader
from socketio.server import SocketIOServer

from django_socketio.clients import client_end_all
from django_socketio.settings import HOST, PORT


RELOAD = False

def reload_watcher():
    global RELOAD
    while True:
        RELOAD = code_changed()
        if RELOAD:
            kill(getpid(), SIGINT)
        sleep(1)

class Command(BaseCommand):

    def handle(self, addrport="", *args, **options):

        if not addrport:
            self.addr = HOST
            self.port = PORT
        else:
            m = match(naiveip_re, addrport)
            if m is None:
                raise CommandError('"%s" is not a valid port number '
                                   'or address:port pair.' % addrport)
            self.addr, _, _, _, self.port = m.groups()

        # Make the port available here for the path:
        #   socketio_tags.socketio ->
        #   socketio_scripts.html ->
        #   io.Socket JS constructor
        # allowing the port to be set as the client-side default there.
        environ["DJANGO_SOCKETIO_PORT"] = str(self.port)

        start_new_thread(reload_watcher, ())
        try:
            bind = (self.addr, int(self.port))
            print
            print "SocketIOServer running on %s:%s" % bind
            print
            handler = get_wsgi_application()
            server = SocketIOServer(bind, handler, namespace="socket.io")
            server.serve_forever()
        except KeyboardInterrupt:
            client_end_all()
            if RELOAD:
                server.kill()
                print
                print "Reloading..."
                restart_with_reloader()
            else:
                raise
