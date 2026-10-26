"""Source normalization and quote-aware assembly text scanning."""


def normalize_source(source):
    return source.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


def strip_comment(line):
    quote = None
    index = 0
    while index < len(line):
        character = line[index]
        if quote:
            if character == quote:
                if index + 1 < len(line) and line[index + 1] == quote:
                    index += 1
                else:
                    quote = None
        elif character in "'\"":
            quote = character
        elif character == ";":
            return line[:index]
        index += 1
    return line


def split_values(text):
    values, quote, start, index = [], None, 0, 0
    while index < len(text):
        character = text[index]
        if quote:
            if character == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 1
                else:
                    quote = None
        elif character in "'\"":
            quote = character
        elif character == ",":
            values.append(text[start:index].strip())
            start = index + 1
        index += 1
    if quote:
        raise ValueError("Unterminated string")
    values.append(text[start:].strip())
    if any(not value for value in values):
        raise ValueError("DB requires a value between commas")
    return values


def quoted_value(value):
    quote, characters, index = value[0], [], 1
    while index < len(value):
        character = value[index]
        if character == quote:
            if index + 1 < len(value) and value[index + 1] == quote:
                characters.append(quote)
                index += 2
                continue
            if index != len(value) - 1:
                raise ValueError(
                    "Unexpected characters after string; separate DB values with commas"
                )
            return "".join(characters)
        characters.append(character)
        index += 1
    raise ValueError("Unterminated string")
