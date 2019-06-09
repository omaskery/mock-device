from mock_device.repl.match_based.match_based import Matcher


def match_on_cmd(expected_cmd: str) -> Matcher:
    """
    builds a matcher that handles commands if the command word matches
    :param expected_cmd: the command word to match against
    :return: matcher for registering with a :class:`MatchBasedRepl`

    :examples:

    >>> # it matches if the command word is the same
    >>> match_on_cmd("hello")("hello", [])
    True
    >>> # it does not match if the command word differs
    >>> match_on_cmd("hello")("bye", [])
    False
    >>> # it doesn't care what the arguments are
    >>> match_on_cmd("hello")("hello", ["some", "args"])
    True
    """

    class _Matcher:
        def __call__(self, cmd, _args):
            return cmd == expected_cmd

        def __str__(self):
            return f"command word == '{expected_cmd}'"

    return _Matcher()


def match_on_cmd_starts_with(*expected_cmd: str) -> Matcher:
    """
    builds a matcher that handles commands if the leading tokens match the expected ones
    :param expected_cmd: the tokens to check against the beginning of the command
    :return: matcher for registering with a :class:`MatchBasedRepl`

    :examples:

    >>> match_on_cmd_starts_with("hello")("hello", [])
    True
    >>> match_on_cmd_starts_with("hello", "there")("hello", ["there", "matey"])
    True
    >>> match_on_cmd_starts_with("hello")("bye", [])
    False
    >>> match_on_cmd_starts_with("hello", "there")("hello", ["my", "matey"])
    False
    """

    class _Matcher:
        def __call__(self, cmd, args):
            entire_cmd = [cmd] + args
            parts_to_match = entire_cmd[:len(expected_cmd)]
            return parts_to_match == list(expected_cmd)

        def __str__(self):
            return f"command starts with '{' '.join(expected_cmd)}'"

    return _Matcher()
