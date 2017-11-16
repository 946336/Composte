#!/usr/bin/env python3

import zmq
# A REP socket replies to the client who sent the last message. This means
# that we can't really get away with worker threads here, as
# REQ/Processing/REP must be serialized as a cohesive unit.

from threading import Lock

from fake.encryption import Encryption, Log
from fake.exceptions import DecryptError, EncryptError, GenericError

# Need signal handlers to properly run as daemon
import signal
import sys

DEBUG = True

# Broadcast socket   -> Publish/Subscribe
# Interactive socket -> Request/Reply
class Server:
    __context = zmq.Context()
    def __init__(self, interactive_address, broadcast_address,
            encryption_scheme = Encryption()):
        """
        The network server for Composte.
        interactive_address and broadcast_address must be available for this
        application to bind to.
        encryption_scheme must provide encrypt and decrypt methods
        """

        self.__translator = encryption_scheme

        self.__iaddr = interactive_address
        self.__isocket = self.__context.socket(zmq.REP)
        self.__isocket.bind(self.__iaddr)

        self.__baddr = broadcast_address
        self.__bsocket = self.__context.socket(zmq.PUB)
        self.__bsocket.bind(self.__baddr)

        self.__done = False

        self.__ilock = Lock()
        self.__block = Lock();

        # print("Bound to {} and {}".format(self.__iaddr, self.__baddr))

    def broadcast(self, message):
        """
        Send a broadcast to all subscribed clients
        """
        with self.__block:
            self.__bsocket.send_string(message)

    def fail(self, message, reason):
        """
        Send a failure message to a client
        """
        with self.__ilock:
            # Probably need a better generic failure message format, but eh
            self.__isocket.send_string("Failure ({}): {}".format(reason,
                message))

    def listen_almost_forever(self, handler = lambda x: x,
            preprocess = lambda x: x):
        """
        Listen for messages on the interactive socket until the server is
        stopped.
        Messages are handed off first to a user-provided preprocessor, the
        result of that is handed to the user-provided handler, and the result
        of that is sent back as a reply
        """
        try:
            while True:
                with self.__ilock:
                    if self.__done: break

                    nmsg = self.__isocket.poll(2000)
                    if nmsg == 0:
                        continue
                    message =  self.__isocket.recv_string()
                    try:
                        message = self.__translator.decrypt(message)
                    except DecryptError as e:
                        self.fail(message, "Decrypt failure")
                        continue
                    except:
                        continue

                    try:
                        message = preprocess(message)
                    except GenericError as e:
                        self.fail(message, "Internal server error")
                        continue
                    except:
                        continue

                    try:
                        reply = handler(self, message)
                    except GenericError as e:
                        self.fail(message, "Internal server error")
                        continue
                    except:
                        continue

                    try:
                        reply = self.__translator.encrypt(message)
                    except EncryptError as e:
                        self.fail(message, "encrypt failure")
                        continue
                    except:
                        continue

                    self.__isocket.send_string(reply)
        except KeyboardInterrupt as e:
            self.stop()
            print()

    def stop(self):
        """
        Stop the server
        """
        with self.__ilock:
            self.__done = True
            self.__isocket.unbind(self.__iaddr)

        with self.__block:
            self.__bsocket.unbind(self.__baddr)

def echo(server, message):
    """
    Echo the message back to the client
    """
    server.broadcast(message)
    return message

def id(elem):
    return elem

def stop_server(sig, frame, server):
    server.stop()

if __name__ == "__main__":

    if not DEBUG:
        signal.signal(signal.SIGINT, lambda sig, f: stop_server(sig, f, s))
        signal.signal(signal.SIGQUIT, lambda sig, f: stop_server(sig, f, s))
        signal.signal(signal.SIGTERM, lambda sig, f: stop_server(sig, f, s))
        signal.signal(signal.SIGSTOP, lambda sig, f: stop_server(sig, f, s))

    # Set up the server
    s = Server("ipc:///tmp/interactive", "ipc:///tmp/broadcast",
            Log(sys.stderr))

    # Start listening
    s.listen_almost_forever(echo, id)

