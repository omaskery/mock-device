import typing

from mock_device.parse_command import CommandWord, CommandArguments
from ..repl import Repl


Matcher = typing.Callable[[CommandWord, CommandArguments], bool]
Handler = typing.Callable[[CommandWord, CommandArguments], typing.Awaitable]
RegisterHandler = typing.Callable[[Matcher, Handler], None]


class KnownMatcher(typing.NamedTuple):
    """represents a known handler and the matcher that triggers it"""

    matcher: Matcher
    handler: Handler


class MatchBasedRepl(Repl):
    """REPL that stores command handlers with a 'matcher', handling each command with the matching handler"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.matchers: typing.List[KnownMatcher] = []
        self.register_handlers(self._register_handler)

    def register_handlers(self, register: RegisterHandler):
        """method to be overriden by derived classes to register their handlers"""

        pass

    async def handle_command(self, cmd: CommandWord, args: CommandArguments):
        """
        implements method inherited from parent
        """

        print(f"{self.__class__.__name__}.handle_command: cmd='{cmd}' args={args}")
        for matcher, handler in self.matchers:
            print(f"  trying matcher: {matcher}")
            if matcher(cmd, args):
                print("    matched")
                await handler(cmd, args)
                break
        else:
            await self.unknown_command(cmd, args)

    async def unknown_command(self, cmd: CommandWord, args: CommandArguments):
        """method that can be overriden by derived classes to handle commands which did not match any matchers"""

        print(f"unhandled command '{cmd}': {args}")

    def _register_handler(self, matcher: Matcher, handler: Handler):
        """
        used to register a handler and its matcher
        :param matcher: matcher that must match an input command to trigger this handler
        :param handler: function to handle a command that matches the matcher
        """

        self.matchers.append(KnownMatcher(matcher, handler))
