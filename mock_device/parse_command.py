import typing
import shlex


CommandWord = str
CommandArguments = typing.List[str]


class Command(typing.NamedTuple):
    """represents a command entered by a user at a REPL"""

    command_word: CommandWord
    arguments: CommandArguments


def parse_command(line) -> Command:
    """
    parses a line of user input into a :class:`Command`

    :param line: the line of text to parse
    :returns: a command parsed from the user input
    """

    shell_command = shlex.split(line.strip())
    command_word = shell_command[0]
    args = shell_command[1:]
    return Command(command_word, args)
