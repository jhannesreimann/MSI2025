# Parser for the Markdown-format Metrics Timeline table.
#
# This is not a full Markdown parser. It is specialized to the subset of
# Markdown used in the Metrics Timeline table. Table rows must begin and end
# with '|'.
#
# https://docs.gitlab.com/ee/user/markdown.html
# https://spec.commonmark.org/0.29/
#
# The top-level parse function returns an iterator that yields a sequence of
# strings and lists. Strings represent the verbatim text between tables. Lists
# represent tables, with each list element being an Entry structure.

import datetime
import enum
import re

# We bail out if we find a table whose column names are not exactly these.
EXPECTED_COLUMN_NAMES = ("start date", "end date", "places", "protocols", "description", "links", "?")

@enum.unique
class TokenType(enum.Enum):
    LITERAL         = enum.auto()
    TABLE_ROW_BEGIN = enum.auto() # '|' marking the beginning of a table row.
    TABLE_ROW_END   = enum.auto() # Newline or EOF marking the end of a table row.
    TABLE_CELL_END  = enum.auto() # '|' marking the end of a table cell.
    BACKTICK        = enum.auto()
    OPEN_BRACKET    = enum.auto()
    CLOSE_BRACKET   = enum.auto()
    OPEN_PAREN      = enum.auto()
    CLOSE_PAREN     = enum.auto()
    EOF             = enum.auto()

# The tokenize function yields values of this type.
class Token:
    def __init__(self, type, text):
        self.type = type
        self.text = text

    def __repr__(self):
        return f"Token({self.type}, {self.text!r})"

# Reads r and yield a sequence of Token values.
def tokenize(r):
    tokens = []
    unget_buf = []
    # Consolidate adjacent literal tokens so they aren't all single-character
    # tokens. flush_literals converts this list into LITERAL tokens.
    literals_buf = []

    def getchar():
        if unget_buf:
            return unget_buf.pop()
        return r.read(1)

    def ungetchar(c):
        unget_buf.append(c)

    def peekchar():
        c = getchar()
        ungetchar(c)
        return c

    def emit(type, text):
        if type == TokenType.LITERAL:
            literals_buf.append(text)
        else:
            flush_literals()
            tokens.append(Token(type, text))

    def flush_literals():
        if literals_buf:
            tokens.append(Token(TokenType.LITERAL, "".join(literals_buf)))
            literals_buf.clear()

    def state_begin_line():
        # Now at the beginning of a line.
        c = getchar()
        if not c:
            # EOF.
            return state_eof
        elif c == "|":
            emit(TokenType.TABLE_ROW_BEGIN, c)
            return state_begin_table_cell
        else:
            ungetchar(c)
            return state_literal_line

    def state_literal_line():
        # Not a table row. Emit literal tokens until the end of the line.
        c = getchar()
        emit(TokenType.LITERAL, c)
        if not c or c == "\n":
            return state_begin_line
        else:
            return state_literal_line

    def state_begin_table_cell():
        # Now at the beginning of a table cell.
        c = getchar()
        if not c or c == "\n":
            # Table rows end at EOF or newline.
            emit(TokenType.TABLE_ROW_END, c)
            return state_begin_line
        else:
            ungetchar(c)
            return state_table_cell

    def state_table_cell():
        # Now in the middle of a table cell.
        c = getchar()
        if not c or c == "\n":
            raise ValueError("expected '|' at end of table row line")
        elif c == "|":
            emit(TokenType.TABLE_CELL_END, c)
            return state_begin_table_cell
        elif c == "\\":
            # https://spec.commonmark.org/0.29/#backslash-escapes
            # In some contexts, like in code blocks, backslahes are not escape
            # characters, so technically this should not be part of the lexer.
            # But those contexts do not affect us.
            d = getchar()
            if not d or d == "\n":
                # "A backslash at the end of the line is a hard line break"
                raise ValueError("backslash at end of a line is not supported")
            elif d in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~":
                emit(TokenType.LITERAL, d)
            else:
                emit(TokenType.LITERAL, c+d)
        elif c == "`":
            emit(TokenType.BACKTICK, c)
        elif c == "[":
            emit(TokenType.OPEN_BRACKET, c)
        elif c == "]":
            emit(TokenType.CLOSE_BRACKET, c)
        elif c == "(":
            emit(TokenType.OPEN_PAREN, c)
        elif c == ")":
            emit(TokenType.CLOSE_PAREN, c)
        else:
            emit(TokenType.LITERAL, c)
        return state_table_cell

    def state_eof():
        # Now at EOF.
        emit(TokenType.EOF, None)
        # Command the state transition loop to halt.
        return None

    state = state_begin_line
    while state is not None:
        state = state()
        while tokens:
            yield tokens.pop(0)

# Parses a date/time string with an optional "~" prefix signifying
# approximation, or one of the special strings "" or "ongoing". Returns a tuple
# (date, is_approx). The returned date is None if the input is "" or "ongoing".
def parse_datetime(s):
    if s == "" or s == "ongoing":
        return None, False

    is_approx = False
    if s.startswith("~"):
        is_approx = True
        s = s[1:]
    # First try parsing as a datetime, then try parsing as a date.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            result = datetime.datetime.strptime(s, fmt)
            break
        except ValueError:
            pass
    else:
        result = datetime.datetime.strptime(s, "%Y-%m-%d").date()

    return result, is_approx

# https://spec.commonmark.org/0.29/#backslash-escapes
def backslash_escape(s, chars = set()):
    return "".join(("\\" if c == "\\" or c in chars else "") + c for c in s)

# Markdown is a container for a tree of Markdown elements.
class Markdown:
    def __init__(self):
        self.children = []
    def to_text(self):
        return "".join(child.to_text() for child in self.children)
    def to_markdown(self):
        return "".join(child.to_markdown() for child in self.children)

class MarkdownLiteral:
    def __init__(self, text):
        self.text = text
    def to_text(self):
        return self.text
    def to_markdown(self):
        return backslash_escape(self.text)

class MarkdownCode:
    def __init__(self, text):
        self.text = text
    def to_text(self):
        raise ValueError("cannot convert MarkdownCode to text")
    def to_markdown(self):
        return "`" + backslash_escape(self.text, "`") + "`"

class MarkdownLink:
    def __init__(self, label, href):
        self.label = label
        self.href = href
    def to_text(self):
        raise ValueError("cannot convert MarkdownLink to text")
    def to_markdown(self):
        label = backslash_escape(self.label.to_markdown(), "[]")
        href = backslash_escape(self.href, "()")
        return "[" + label + "](" + href + ")"

# Extracts only the MarkdownLink nodes from a Markdown tree, and asserts that
# all other nodes are of type MarkdownLiteral and contain only whitespace.
def extract_links(node):
    links = []
    if isinstance(node, Markdown):
        for child in node.children:
            links.extend(extract_links(child))
    elif isinstance(node, MarkdownLink):
        links.append(node)
    elif isinstance(node, MarkdownLiteral):
        if node.text.strip() != "":
            raise ValueError(f"non-whitespace literal node in link list: {node.to_text()!r}")
    else:
        raise ValueError(f"unexpected node type in link list: {node.to_text()!r}")
    return links

# Entry is a parsed single event from the timeline.
class Entry:
    def __init__(self, row):
        start_date, end_date, places, protocols, description, links, is_unknown = row

        self.start_date, self.start_date_is_approx = parse_datetime(start_date.to_text())
        self.end_date, self.end_date_is_approx = parse_datetime(end_date.to_text())
        self.is_ongoing = end_date.to_text() == "ongoing"
        self.places = set(places.to_text().split())
        self.protocols = set(protocols.to_text().split())
        self.description = description
        self.links = extract_links(links)
        self.is_unknown = bool(is_unknown.to_text())

# parse yields a sequence of strings and lists. Strings represent verbatim text
# between tables. Lists represent tables of Entry.
def parse(r):
    tokenizer = tokenize(r)
    unread_buf = []

    def read_token():
        if unread_buf:
            return unread_buf.pop()
        return next(tokenizer)

    def unread_token(token):
        unread_buf.append(token)

    def peek_token():
        token = read_token()
        unread_token(token)
        return token

    def parse_table():
        # Parse table header.
        column_names = tuple(cell.to_text().strip() for cell in parse_table_row())
        assert column_names == EXPECTED_COLUMN_NAMES, column_names

        # Parse table separator.
        token = read_token()
        assert token.type == TokenType.TABLE_ROW_BEGIN, token
        separator = tuple(cell.to_text().strip() for cell in parse_table_row())
        # Make sure the separator has the right format.
        # https://docs.gitlab.com/ee/user/markdown.html#tables
        # "The second line separates the headers from the cells, and must
        # contain three or more dashes. ... Additionally, you can choose the
        # alignment of text within columns by adding colons (:) to the sides of
        # the dash lines in the second row."
        assert all(re.match(r':?-{3,}:?', sep.strip()) for sep in separator), separator

        # Parse table entries.
        entries = []
        while True:
            token = read_token()
            if token.type != TokenType.TABLE_ROW_BEGIN:
                unread_token(token)
                break
            entries.append(Entry(parse_table_row()))

        return entries

    def parse_table_row():
        row = []
        while True:
            token = read_token()
            if token.type == TokenType.TABLE_ROW_END:
                break
            unread_token(token)
            row.append(parse_table_cell())
        return tuple(row)

    def parse_table_cell():
        node = Markdown()
        while True:
            token = read_token()
            if token.type == TokenType.TABLE_CELL_END:
                break
            elif token.type == TokenType.LITERAL:
                node.children.append(MarkdownLiteral(token.text))
            elif token.type == TokenType.BACKTICK:
                node.children.append(parse_code())
            elif token.type == TokenType.OPEN_BRACKET:
                node.children.append(parse_link())
            else:
                # Other token types, like CLOSE_BRACKET, OPEN_PAREN, etc., just
                # become their text representation in this context.
                node.children.append(MarkdownLiteral(token.text))
        return node

    def parse_code():
        text = []
        while True:
            token = read_token()
            if token.type == TokenType.BACKTICK:
                break
            elif token.type == TokenType.LITERAL:
                text.append(token.text)
            elif token.type in (TokenType.OPEN_BRACKET, TokenType.CLOSE_BRACKET, TokenType.OPEN_PAREN, TokenType.CLOSE_PAREN):
                text.append(token.text)
            else:
                raise ValueError(f"unexpected token {token!r} in inline code")
        return MarkdownCode("".join(text))

    def parse_link():
        label = Markdown()
        while True:
            token = read_token()
            if token.type == TokenType.CLOSE_BRACKET:
                break
            elif token.type == TokenType.OPEN_BRACKET:
                # Another open bracket, this must not actually be a link...
                unread_token(token)
                label.children.insert(0, MarkdownLiteral("["))
                return label
            elif token.type == TokenType.LITERAL:
                label.children.append(MarkdownLiteral(token.text))
            elif token.type == TokenType.BACKTICK:
                label.children.append(parse_code())
            elif token.type in (TokenType.OPEN_PAREN, TokenType.CLOSE_PAREN):
                label.children.append(MarkdownLiteral(token.text))
            else:
                raise ValueError(f"unexpected token {token!r} in link label")

        token = read_token()
        if token.type != TokenType.OPEN_PAREN:
            # This was not actually a link, just bracketed text.
            unread_token(token)
            label.children.insert(0, MarkdownNodeText("["))
            label.children.append(MarkdownNodeText("]"))
            return label

        href = []
        while True:
            token = read_token()
            if token.type == TokenType.CLOSE_PAREN:
                break
            elif token.type == TokenType.LITERAL:
                href.append(token.text)
            elif token.type in (TokenType.BACKTICK, TokenType.OPEN_BRACKET, TokenType.CLOSE_BRACKET):
                href.append(token.text)
            else:
                raise ValueError(f"unexpected token {token!r} in link href")
        return MarkdownLink(label, "".join(href))

    while True:
        token = read_token()
        if token.type == TokenType.EOF:
            break
        elif token.type == TokenType.LITERAL:
            yield token.text
        elif token.type == TokenType.TABLE_ROW_BEGIN:
            yield parse_table()
        else:
            raise ValueError(f"unexpected token {token!r}")
