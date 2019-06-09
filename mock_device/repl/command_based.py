import inspect
import typing

from mock_device.parse_command import CommandArguments, CommandWord
from mock_device.repl import Repl
from mock_device.repl.match_based import MatchBasedRepl
from mock_device.repl.match_based.match_based import RegisterHandler, Matcher


class Command:
    """interface that describes commands to the :class:`CommandBasedRepl`"""

    def get_name(self) -> str:
        """get a descriptive name for the command, often equal to the command word, used in help dialogs"""
        pass

    def get_help_description(self) -> str:
        """get some descriptive text explaining the purpose of the command for help dialogs"""
        pass

    def register_handlers(self, register: 'RegisterCommandHandler'):
        """
        method to override in order to register handlers w/ their matchers
        :param register: allows registering of command handlers and their matchers
        """

        pass


CommandHandler = typing.Callable[[Repl, CommandWord, CommandArguments], typing.Awaitable]
RegisterCommand = typing.Callable[[Command], None]
RegisterCommandHandler = typing.Callable[[Matcher, CommandHandler], None]


class CommandBasedRepl(MatchBasedRepl):
    """REPL that is based on commands which register handlers w/ matchers to the underlying :class:`MatchBasedRepl`"""

    def __init__(self, *args, **kwargs):
        # must register commands before parent constructor, as MatchBasedRepl registers its handlers in its constructor
        self.commands: typing.List[Command] = []
        self.register_commands(self._register_command)

        super().__init__(*args, **kwargs)

    def register_handlers(self, register: RegisterHandler):
        """implementation of parent method in order to register handlers for all the commands"""

        def _wrapped_register(matcher: Matcher, handler_fn: CommandHandler):
            async def _wrapped_handler(cmd: CommandWord, args: CommandArguments):
                await handler_fn(self, cmd, args)

            print(f"    matches: {matcher}")

            register(matcher, _wrapped_handler)

        print(f"{self.__class__.__name__} registering commands:")
        for registered_command in self.commands:
            print(f"  {registered_command.get_name()}:")
            registered_command.register_handlers(_wrapped_register)

    def register_commands(self, register: RegisterCommand):
        """method to be overriden by derived classes to register commands with the REPL"""

        pass

    def _register_command(self, command_to_register: Command):
        """
        registers a command witht he REPL
        :param command_to_register: the command to register
        """

        self.commands.append(command_to_register)


HANDLER_ATTR_NAME = '_handler'


class HandlerData(typing.NamedTuple):
    """metadata attached to functions decorated with @handler"""

    matcher: typing.Callable[[str, typing.List[str]], bool]
    order: int = None


def handler(order: typing.Optional[int] = None, *, matcher: Matcher)\
        -> typing.Callable[[CommandHandler], CommandHandler]:
    """
    attaches metadata to a command handler function so that it can be automatically
    registered by the `command` decorator
    :param order: optionally specify the order of the handlers in a class, otherwise they are registered alphabetically
    :param matcher: the matcher to register this handler with
    :return: the original decorated function with metadata attached
    """

    def _decorator(fn: CommandHandler) -> CommandHandler:
        setattr(fn, HANDLER_ATTR_NAME, HandlerData(
            matcher=matcher,
            order=order,
        ))
        return fn

    return _decorator


def command(*, name: str, help_text: str) -> typing.Callable[[typing.Type[Command]], typing.Type[Command]]:
    """
    decorates a Command class such that it auto-generates the get_name, get_help_description and
    extends the register_commands function with any methods decorated with the `handler` decorator
    :param name: the command's name (will be returned from get_name())
    :param help_text: the command's help description (will be returned from get_help_description())
    :return: class that inherits from the decorated class, with auto generated methods
    """

    def _decorator(clazz: typing.Type[Command]) -> typing.Type[Command]:
        def _predicate(member: typing.Any) -> bool:
            return callable(member) and hasattr(member, HANDLER_ATTR_NAME)

        # get all the methods decorated with our handler meta-data
        handler_methods = inspect.getmembers(clazz, predicate=_predicate)

        # extract the meta-data from the methods
        handlers_with_data = [
            (method_name, method, getattr(method, HANDLER_ATTR_NAME))
            for method_name, method in handler_methods
        ]

        # extract the order information from the meta-data and determine if any conditions have been violated
        all_handlers_order_value = [handler_data.order for _, _, handler_data in handlers_with_data]
        any_have_order = any([order_data is not None for order_data in all_handlers_order_value])
        all_have_order = all([order_data is not None for order_data in all_handlers_order_value])

        # if they all specify an order we should sort them by that order
        if all_have_order:
            handlers_with_data = list(
                sorted(handlers_with_data, key=lambda entry: entry[2].order)
            )
        # if only some are ordered we don't know what to do with them, so fail
        elif any_have_order:
            raise Exception("if you mark any handler with an order, you must mark all with an order")

        # record the method names, in whatever order we've determined so far, for use in the
        # auto-generated `register_handlers` method below
        handler_method_names = [method_name for method_name, _, _ in handlers_with_data]

        # build the auto-generated class, inherited from the decorated class, implementing the
        # methods from the `Command` class
        class _Wrapped(clazz):

            def get_name(self):
                return name

            def get_help_description(self):
                return help_text

            def register_handlers(self, register):
                # ensure any implementation by the decorated class is preserved
                super().register_handlers(register)

                # go through the method names we calculated earlier, extract the
                # meta-data we attached to the methods and use it to register the
                # method as a handler, using the matcher we stored in the meta-data
                for method_name in handler_method_names:
                    method = getattr(self, method_name)
                    handler_data = getattr(method, HANDLER_ATTR_NAME)
                    register(handler_data.matcher, method)

        return _Wrapped

    return _decorator
