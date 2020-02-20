#!/usr/bin/env python3
import argparse
import inspect
import multiprocessing
import shlex
import socket
import socketserver

import paramiko


# settings
default_settings = {
    'max_history': 64,
    'host_key': 'host.key',
    'bind_addr': ('', 2222),
}


# commands
def quit():
    raise ConsoleQuit()


def help(cmd=None, *, name, handler):
    if cmd is None:
        cmd = name

    cmd_func = handler.commands.get(cmd)

    if cmd_func is None:
        handler.channel.send('Command unrecognized: {}\r\n'.format(cmd))
        return

    cmd_spec = inspect.getfullargspec(cmd_func)

    if cmd_spec.varargs is not None:
        kwargs = {}

        if 'channel' in cmd_spec.kwonlyargs:
            kwargs['channel'] = handler.channel
        if 'handler' in cmd_spec.kwonlyargs:
            kwargs['handler'] = handler
        if 'name' in cmd_spec.kwonlyargs:
            kwargs['name'] = cmd

        cmd_func('-h', **kwargs)
    else:
        handler.channel.send('usage: ')
        help_args = [cmd]
        help_args.extend(['<{}>'.format(arg) if idx < (len(cmd_spec.args) - (len(cmd_spec.defaults) if cmd_spec.defaults is not None else 0)) else '[{}]'.format(arg) for idx, arg in enumerate(cmd_spec.args)])
        handler.channel.send(' '.join(help_args))
        handler.channel.send('\r\n')

        if cmd_func.__doc__:
            handler.channel.send('\r\n')

            lines = cmd_func.__doc__.expandtabs().splitlines()

            indent = None
            for line in lines[1:]:
                stripped = line.lstrip()
                if stripped:
                    if indent is not None:
                        indent = min(indent, len(line) - len(stripped))
                    else:
                        indent = len(line) - len(stripped)

            doc = [lines[0].strip()]
            if indent:
                for line in lines[1:]:
                    doc.append(line[indent:].rstrip())

            while doc and not doc[-1]:
                doc.pop()
            while doc and not doc[0]:
                doc.pop(0)

            handler.channel.send('\r\n'.join(doc))

            handler.channel.send('\r\n')


default_commands = {
    'quit': quit,
    'help': help,
    'ping': lambda: None,
}


# console argument parser
class ConsoleArgumentParser(argparse.ArgumentParser):
    def __init__(self, name, channel, *args, **kwargs):
        super().__init__(*args, prog=name, **kwargs)
        self.channel = channel

    def _print_message(self, message, _=None):
        if message:
            self.channel.send(message.replace('\r\n', '\n').replace('\n', '\r\n'))

    def exit(self, _=0, message=None):
        if message:
            self._print_message(message, None)
        raise ConsoleExit()


# quit exception
class ConsoleQuit(Exception):
    pass


# command exit exception
class ConsoleExit(Exception):
    pass


# SSH server
class ConsoleSSH(paramiko.ServerInterface):
    def __init__(self, *args, **kwargs):
        self.shell_requested = multiprocessing.Event()

        super().__init__(*args, **kwargs)

    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED

        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.shell_requested.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def get_allowed_auths(self, username):
        return 'none'


# stream handler which provides the main CLI
class ConsoleHandler(socketserver.StreamRequestHandler):
    settings = default_settings
    commands = default_commands

    def setup(self):
        try:
            self.transport = paramiko.Transport(self.request)
            self.transport.add_server_key(self.settings['host_key'] if isinstance(self.settings['host_key'], paramiko.PKey) else paramiko.RSAKey.from_private_key_file(self.settings['host_key']))

            self.ssh = ConsoleSSH()

            self.transport.start_server(server=self.ssh)

            self.channel = self.transport.accept()

            self.ssh.shell_requested.wait(10)
            if not self.ssh.shell_requested.is_set():
                raise RuntimeError('No shell requested')
        except Exception:
            try:
                self.transport.close()
            except Exception:
                pass

            raise

    def handle(self):
        try:
            self.channel.send('Welcome to {}!\r\n'.format(socket.gethostname()))
            self.channel.send('Available Commands:\r\n  {}\r\n'.format('  '.join(self.commands.keys())))

            cmdline = None
            history = []

            while True:
                self.channel.send('> ')

                chistory = [list(line) for line in history]

                idx = 0
                hidx = len(chistory)

                chistory.append([])
                while True:
                    char = self.channel.recv(1).decode()
                    if char == '\x03':
                        chistory[hidx] = list('quit')
                        self.channel.send('\r')
                        break
                    elif len(chistory[hidx]) == 0 and char == '\x04':
                        chistory[hidx] = list('quit')
                        self.channel.send('\r')
                        break
                    elif char == '\x0d' or char == '\x1a':
                        self.channel.send('\r')
                        break
                    elif char == '\x7e':
                        if idx < len(chistory[hidx]):
                            del chistory[hidx][idx]
                            self.channel.send('\x1b[K')
                            self.channel.send(''.join(chistory[hidx][idx:]))
                            self.channel.send('\x1b[D' * (len(chistory[hidx]) - idx))
                    elif char == '\x7f':
                        if len(chistory[hidx]) > 0:
                            idx = idx - 1
                            del chistory[hidx][idx]
                            self.channel.send('\x1b[D')
                            self.channel.send('\x1b[K')
                            self.channel.send(''.join(chistory[hidx][idx:]))
                            self.channel.send('\x1b[D' * (len(chistory[hidx]) - idx))
                    elif char == '\x01':
                        self.channel.send('\x1b[D' * idx)
                        idx = 0
                    elif char == '\x05':
                        self.channel.send('\x1b[C' * (len(chistory[hidx]) - idx))
                        idx = len(chistory[hidx])
                    elif char == '\x0c':
                        self.channel.send('\x1b[2J\x1b[H')
                        self.channel.send('> ')
                        self.channel.send(''.join(chistory[hidx]))
                        self.channel.send('\x1b[D' * (len(chistory[hidx]) - idx))
                    elif char == '\x1b':
                        char = self.channel.recv(1).decode()
                        if char == '[':
                            char = self.channel.recv(1).decode()
                            num = 1
                            if char.isdigit():
                                num = int(char)
                                char = self.channel.recv(1).decode()
                                while char.isdigit():
                                    num = num * 10 + int(char)
                                    char = self.channel.recv(1).decode()

                            if char == 'A':
                                while num > 0:
                                    if hidx > 0:
                                        hidx = hidx - 1
                                        self.channel.send('\x1b[D' * idx)
                                        self.channel.send('\x1b[K')
                                        self.channel.send(''.join(chistory[hidx]))
                                        idx = len(chistory[hidx])
                                    num -= 1
                            elif char == 'B':
                                while num > 0:
                                    if hidx < len(chistory) - 1:
                                        hidx = hidx + 1
                                        self.channel.send('\x1b[D' * idx)
                                        self.channel.send('\x1b[K')
                                        self.channel.send(''.join(chistory[hidx]))
                                        idx = len(chistory[hidx])
                                    num -= 1
                            elif char == 'C':
                                while num > 0:
                                    if idx < len(chistory[hidx]):
                                        idx = idx + 1
                                        self.channel.send('\x1b[C')
                                    num -= 1
                            elif char == 'D':
                                while num > 0:
                                    if idx > 0:
                                        idx = idx - 1
                                        self.channel.send('\x1b[D')
                                    num -= 1
                            else:
                                while not char.isalpha():
                                    char = self.channel.recv(1).decode()
                        elif char == 'f':
                            while idx < len(chistory[hidx]):
                                if chistory[hidx][idx] == ' ':
                                    idx = idx + 1
                                    self.channel.send('\x1b[C')
                                    break

                                idx = idx + 1
                                self.channel.send('\x1b[C')
                        elif char == 'b':
                            if idx > 1:
                                idx = idx - 2
                                self.channel.send('\x1b[D' * 2)

                            while idx > 0:
                                if idx < len(chistory[hidx]) and chistory[hidx][idx] == ' ':
                                    idx = idx + 1
                                    self.channel.send('\x1b[C')
                                    break

                                idx = idx - 1
                                self.channel.send('\x1b[D')
                    else:
                        chistory[hidx].insert(idx, char)
                        idx = idx + 1
                        self.channel.send(char)
                        if idx < len(chistory[hidx]):
                            self.channel.send('\x1b[K')
                            self.channel.send(''.join(chistory[hidx][idx:]))
                            self.channel.send('\x1b[D' * (len(chistory[hidx]) - idx))
                self.channel.send('\n')

                cmdline = ''.join(chistory[hidx]).strip()

                if cmdline:
                    history.append(cmdline)
                else:
                    continue

                if len(history) > self.settings['max_history']:
                    history = history[-self.settings['max_history']:]

                try:
                    args = shlex.split(cmdline)

                    if not args:
                        continue

                    cmd = self.commands.get(args[0])

                    if cmd is None:
                        self.channel.send('Command unrecognized: {}\r\n'.format(args[0]))
                        continue

                    cmd_spec = inspect.getfullargspec(cmd)

                    kwargs = {}

                    if 'channel' in cmd_spec.kwonlyargs:
                        kwargs['channel'] = self.channel
                    if 'handler' in cmd_spec.kwonlyargs:
                        kwargs['handler'] = self
                    if 'name' in cmd_spec.kwonlyargs:
                        kwargs['name'] = args[0]

                    ret = cmd(*args[1:], **kwargs)

                    if 'channel' not in kwargs:
                        if ret is not None:
                            self.channel.send(str(ret))
                            self.channel.send('\r\n')
                except ValueError as e:
                    self.channel.send('Invalid command syntax: {}\r\n'.format(e))
                except TypeError:
                    self.channel.send('Invalid command arguments\r\n')
                    help(args[0], name=args[0], handler=self)
                except ConsoleExit:
                    pass
        except ConsoleQuit:
            pass
        except UnicodeDecodeError:
            pass
        except KeyboardInterrupt:
            pass

    def finish(self):
        try:
            self.channel.close()
        except Exception:
            pass


# forking server which allows address reuse
class ConsoleServer(socketserver.ForkingTCPServer):
    allow_reuse_address = True

    def __init__(self, settings, commands, *args, handler=ConsoleHandler, **kwargs):
        class GenHandler(handler):
            pass

        GenHandler.settings = settings
        GenHandler.commands = commands

        super().__init__(settings['bind_addr'], GenHandler, *args, **kwargs)


if __name__ == '__main__':
    def docstring(a, b, c='c'):
        """
        This function concatenates input strings.

        Params:
          a: str
          b: str
          c: str = 'c'

        Returns:
          concatenated: str
        """

        return a + b + c

    def argparser(*args, name, channel):
        parser = ConsoleArgumentParser(name, channel)
        parser.add_argument('-t', '--test', action='store_true', dest='test', default=False, help='some test')
        parser.add_argument('-l', '--list', action='append', dest='list', default=[], help='some list')
        parser.add_argument('value', nargs='?', default='no', help='some value')
        margs = parser.parse_args(args)
        channel.send(str(margs))
        channel.send('\r\n')
        channel.send('Channel char: ')
        char = channel.recv(1)
        channel.send(char)
        channel.send('\r\n')

    example_commands = default_commands.copy()
    example_commands.update({
        'params': lambda x, y, z=5: int(x) + int(y) + int(z),
        'docstring': docstring,
        'argparser': argparser,
    })

    # make SSH server
    server = ConsoleServer(default_settings, example_commands)

    # run until SIGINT caught
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
