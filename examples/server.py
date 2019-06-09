import logging
import asyncio
import sys
import os
import typing

import asyncssh

from mock_device.client import Client
from mock_device.repl import Repl
from mock_device.repl.command_based import Command, CommandBasedRepl, command, handler
from mock_device.repl.match_based.matchers import match_on_cmd, match_on_cmd_starts_with


USERNAME = os.environ.get('MOCK_USERNAME', 'root')
PASSWORD = os.environ.get('MOCK_PASSWORD', 'pass')
ENABLE_PASSWORD = PASSWORD
USERS = {
    USERNAME: PASSWORD,
}
HOSTNAME = os.environ.get('MOCK_HOSTNAME', 'hostname')
MOTD = os.environ.get('MOCK_MOTD', "Welcome to my SSH server, {username}!")


def cisco_prompt(enabled: bool, menu: typing.Optional[str] = None) -> str:
    menu_indicator = '' if menu is None else f"({menu})"
    enabled_indicator = '#' if enabled else '>'
    return f"{HOSTNAME}{menu_indicator}{enabled_indicator} "


@command(name='help', help_text='shows this help text')
class HelpCommand(Command):

    @staticmethod
    @handler(matcher=match_on_cmd('help'))
    async def handle_help(repl, _cmd, _args):
        longest_command = max([len(cmd.get_name()) for cmd in repl.commands])

        repl.client.writeln("available commands:")
        for cmd in repl.commands:
            name = cmd.get_name().ljust(longest_command)
            help_text = cmd.get_help_description()
            repl.client.writeln(f"  {name} - {help_text}")


@command(name="exit", help_text="returns to top level menu or quits session if already at top level")
class ExitCommand(Command):

    def __init__(self, to: typing.Type[Repl] = None, exit_if_already_matches=False):
        self.to = to if to is not None else TopLevelRepl
        self.exit_if_already_matches = exit_if_already_matches

    @handler(matcher=match_on_cmd('exit'))
    async def handle_exit(self, repl, _cmd, _args):
        if isinstance(repl, self.to):
            if self.exit_if_already_matches:
                repl.exit()
        else:
            repl.exit_to_repl_class(self.to)


@command(name="end", help_text="exits current menu")
class EndCommand(Command):

    @staticmethod
    @handler(matcher=match_on_cmd('end'))
    async def handle_end(repl, _cmd, _args):
        repl.exit()


@command(name="enable", help_text="gain access to privilege commands")
class EnableCommand(Command):

    @staticmethod
    @handler(matcher=match_on_cmd('enable'))
    async def handle_enable(repl, _cmd, _args):
        password = await repl.client.prompt('Password: ', echo=False)
        if password == PASSWORD:
            repl.enabled = True
            repl.prompt = cisco_prompt(enabled=True)
        else:
            repl.client.writeln("% Bad password or whatever")


@command(name="disable", help_text="disable access to privilege commands")
class DisableCommand(Command):

    @staticmethod
    @handler(matcher=match_on_cmd('disable'))
    async def handle_disable(repl, _cmd, _args):
        repl.enabled = False
        repl.prompt = cisco_prompt(enabled=False)


@command(name="configure", help_text="configure settings")
class ConfigureCommand(Command):

    @staticmethod
    @handler(matcher=match_on_cmd_starts_with('configure', 'terminal'), order=1)
    async def handle_configure_terminal(repl, _cmd, _args):
        if repl.enabled:
            configure_terminal = repl.enter_repl(
                cisco_prompt(repl.enabled, menu='config'),
                repl_class=ConfigureTerminalRepl
            )
            await configure_terminal.run()
        else:
            repl.client.writeln("% Yo you need to be enabled, dummy!")

    @staticmethod
    @handler(matcher=match_on_cmd('configure'), order=2)
    async def handle_configure(repl, _cmd, _args):
        repl.client.writeln("% Wah you suck at this, try 'configure terminal'")


@command(name="snmp", help_text="change SNMP settings")
class SnmpCommand(Command):

    @staticmethod
    @handler(matcher=match_on_cmd('snmp'))
    async def handle_snmp(repl, _cmd, args):
        repl.client.writeln(f"changed some SNMP things with args={args}")

    @staticmethod
    @handler(matcher=match_on_cmd_starts_with('no', 'snmp'))
    async def handle_no_snmp(repl, _cmd, args):
        repl.client.writeln(f"disabled some SNMP things with args={args}")


class CiscoRepl(CommandBasedRepl):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, exit_command=None, **kwargs)

    def register_commands(self, register):
        register(ExitCommand(to=TopLevelRepl, exit_if_already_matches=True))
        register(HelpCommand())

    async def unknown_command(self, cmd, args):
        await super().unknown_command(cmd, args)
        self.client.writeln("% Bad command or hostname or whatever% Stupid error message")


class TopLevelRepl(CiscoRepl):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled = False

    def register_commands(self, register):
        super().register_commands(register)
        register(EnableCommand())
        register(DisableCommand())
        register(ConfigureCommand())


class ConfigureTerminalRepl(CiscoRepl):

    def register_commands(self, register):
        super().register_commands(register)
        register(SnmpCommand())
        register(EndCommand())


async def handle_client(process: asyncssh.SSHServerProcess):
    client = Client(process)
    client.writeln(MOTD.format(username=process.get_extra_info('username')))

    repl = client.enter_repl(cisco_prompt(enabled=False), repl_class=TopLevelRepl)
    await repl.run()

    process.exit(0)


class MySSHServer(asyncssh.SSHServer):
    def connection_made(self, conn):
        print(f"SSH connection received from {conn.get_extra_info('peername')[0]}.")

    def connection_lost(self, exc):
        if exc:
            print(f'SSH connection error: {exc}', file=sys.stderr)
        else:
            print('SSH connection closed.')

    def begin_auth(self, username):
        return USERS.get(username) != ''

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        return USERS.get(username, '*') == password


async def start_server():
    await asyncssh.listen(
        '',
        8022,
        server_host_keys=['./ssh_host_key'],
        process_factory=handle_client,
        server_factory=MySSHServer
    )


def main():
    logging.basicConfig(level=logging.DEBUG)
    asyncssh.set_debug_level(1)

    print("valid users:")
    for user, password in USERS.items():
        print(f" - {user} : {password}")

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(start_server())
    except (OSError, asyncssh.Error) as exc:
        sys.exit(f'Error starting server: {exc}')

    loop.run_forever()


if __name__ == "__main__":
    main()
