import typing

from mock_device.parse_command import parse_command, CommandArguments, CommandWord


if typing.TYPE_CHECKING:
    from mock_device.client import Client


class Repl:
    """Represents a REPL (read-evaluate-print loop), a loop handling input commands and printing output"""

    def __init__(self, client: 'Client', prompt: str, exit_command: typing.Optional[str] = 'exit',
                 parent_repl: typing.Optional['Repl'] = None):
        """
        :param client: reference to utility wrapper for interacting with the client (e.g. input & output)
        :param prompt: the text to display before prompting the user for each input line
        :param exit_command: configurable command to use to automatically exit the REPL, can be disabled with None
        :param parent_repl:
        """

        self.exit_command = exit_command
        self.client = client
        self.prompt = prompt
        self.running = True
        self.parent_repl: Repl = parent_repl

    async def run(self):
        """runs the REP-loop until exit() is called"""

        while self.running:
            line = await self.client.prompt(self.prompt)
            line = line.strip()
            if not line:
                continue

            command_word, args = parse_command(line)

            print(f">>> {line}")
            if self.exit_command is not None and command_word == self.exit_command:
                self.exit()
            else:
                await self.handle_command(command_word, args)

    def exit(self):
        """requests that this REPL exit after processing the current command"""

        self.running = False

    def exit_to_repl_class(self, clazz: typing.Type['Repl']):
        """
        requests that nested REPLs are exited recursively until the type of the
        remaining REPL matches the type specified, note that if the current REPL
        type is ALREADY the requested type this function has no effect
        :param clazz: the type of REPL to exit to
        """

        current = self
        print(f"exiting repls until repl of type '{clazz.__name__}'")
        while current is not None and not isinstance(current, clazz):
            print(f"  exiting repl '{current.__class__.__name__}'")
            current.exit()
            current = current.parent_repl

    def enter_repl(self, prompt: str, repl_class: typing.Type['Repl'] = None, **kwargs) -> 'Repl':
        """
        builds a REPL object for entering a loop handling input, allows the specific REPL class to be configured
        :param prompt: text to display at the prompt for each line of input from the user
        :param repl_class: optionally override the class used to create the REPL object, defaults to the current class
        :param kwargs: any extra arguments for passing to the REPL class constructor
        :return: the constructed REPL instance
        """

        repl_class = repl_class if repl_class else self.__class__
        return repl_class(self.client, prompt, parent_repl=self, **kwargs)

    async def handle_command(self, cmd: CommandWord, args: CommandArguments):
        """
        handles a single command/line of input from the user
        :param cmd: the command entered by the user (the first word)
        :param args: the arguments supplied by the user (tokens following the first word)
        """

        print(f"unhandled command '{cmd}': {args}")
