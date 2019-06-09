import asyncssh
import typing

from mock_device.repl import Repl


class Client:
    """Thin wrapper around :class:`asyncssh.SSHServerProcess`"""

    def __init__(self, process: asyncssh.SSHServerProcess):
        """
        :param process: the process to provide convenience methods around
        """

        self.process = process
        self.echo = True
        self.line_mode = True

    def write(self, text: str, file: asyncssh.SSHWriter = None):
        """
        write a line of text to one of the process streams, defaults to stdout
        :param text: text to write (will NOT append a newline automatically)
        :param file: output stream to write to, if None defaults to self.process.stdout
        """

        file = file if file else self.process.stdout
        file.write(text)

    def writeln(self, text: str, file: asyncssh.SSHWriter = None):
        """
        write a line of text to one of the process streams, defaults to stdout
        :param text: text to write (WILL append a newline automatically)
        :param file: output stream to write to, if None defaults to self.process.stdout
        """

        self.write(text + "\n", file=file)

    def set_echo(self, echo: bool) -> bool:
        """
        sets whether input text is echo'ed (rendered on the client UI) or not, useful for
        "hidden" inputs like password prompts
        :param echo: if True the input text is 'visible'/echoed, if False it is 'inviisble'/not-echoed
        :return: returns the previous value of self.echo for easily setting it back when done
        """

        old_value = self.echo
        if echo != self.echo:
            self.echo = echo
            self.process.channel.set_echo(self.echo)
        return old_value

    def set_line_mode(self, line_mode: bool) -> bool:
        """
        sets whether input text is processed by line or by character, useful for reacting to individual keys
        such as when asking the user to "press any key to continue"
        :param line_mode: if True the input is processed by line, otherwise it is processed by character
        :return: returns the previous value of self.line_mode for easily setting it back when done
        """

        old_value = self.line_mode
        if line_mode != self.line_mode:
            self.line_mode = line_mode
            self.process.stdin.channel.set_line_mode(self.line_mode)
        return old_value

    async def readline(self) -> str:
        """reads a line from self.process.stdin"""

        return await self.process.stdin.readline()

    async def prompt(self, text: str, echo=True) -> str:
        """
        prompts the user for input and reads a line of response, optionally hiding the response input (disabling echo)
        :param text: text to write prior to prompt (does not include a trailing newline automatically)
        :param echo: whether to echo user input, defaults to True
        :return: the line of text entered by the user, with trailing whitespace removed
        """

        self.write(text)
        previous_echo = self.set_echo(echo)
        result = await self.readline()
        self.set_echo(previous_echo)
        return result.rstrip()

    async def await_any_key(self, message: str = None) -> str:
        """
        waits for the user to press any key, optionally displaying a prompt message first
        :param message: message to display before awaiting key press, defaults to None which displays nothing
        :return: the entered key, in case it is useful
        """

        previous_line_mode = self.set_line_mode(False)
        if message is not None:
            self.write(message)
        entered_key = await self.process.stdin.read(1)
        self.set_line_mode(previous_line_mode)
        if message is not None:
            self.write('\n')
        return entered_key

    def enter_repl(self, prompt: str, repl_class: typing.Type[Repl] = Repl, **kwargs) -> Repl:
        """
        builds a REPL object for entering a loop handling input, allows the specific REPL class to be configured
        :param prompt: text to display at the prompt for each line of input from the user
        :param repl_class: optionally override the class used to create the REPL object
        :param kwargs: any extra arguments for passing to the REPL class constructor
        :return: the constructed REPL instance
        """

        return repl_class(self, prompt, **kwargs)
