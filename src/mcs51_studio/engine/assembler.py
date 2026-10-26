"""Two-pass 8051 assembler with source addresses and Intel HEX I/O."""

import ast
import operator
import re
from dataclasses import dataclass

from .cpu import BITS, ISA, SFR
from .source import normalize_source, quoted_value, split_values, strip_comment


class AssemblyError(ValueError):
    def __init__(self, message, line=None):
        self.message = message
        self.line = line
        super().__init__(f"Line {line}: {message}" if line is not None else message)


@dataclass
class Program:
    code: bytearray
    locations: dict
    symbols: dict
    used: set


def expression(text, symbols, pc=0, unresolved=False):
    text = text.strip()
    if len(text) == 3 and text[0] == text[-1] == "'":
        return ord(text[1])
    text = text.upper().replace("$", str(pc))
    match = re.fullmatch(r"(HIGH|LOW)\s*(?:\((.+)\)|\s+(.+))", text)
    if match:
        v = expression(match[2] or match[3], symbols, pc, unresolved)
        return (v >> 8 if match[1] == "HIGH" else v) & 255
    bit = re.fullmatch(r"([A-Z_][\w]*|[0-9A-F]+H)\.([0-7])", text)
    if bit:
        base = expression(bit[1], symbols, pc, unresolved)
        if 0x20 <= base <= 0x2F:
            return (base - 0x20) * 8 + int(bit[2])
        if 128 <= base <= 248 and base % 8 == 0:
            return base + int(bit[2])
        raise AssemblyError(f"{text}: not bit addressable")
    text = re.sub(r"\b([0-9][0-9A-F]*)H\b", lambda m: str(int(m[1], 16)), text)
    text = re.sub(r"\b([01]+)B\b", lambda m: str(int(m[1], 2)), text)
    text = re.sub(r"\b([0-7]+)[OQ]\b", lambda m: str(int(m[1], 8)), text)
    text = re.sub(r"\b(\d+)D\b", r"\1", text)
    text = re.sub(r"\bAND\b", "&", text)
    text = re.sub(r"\bOR\b", "|", text)
    text = re.sub(r"\bXOR\b", "^", text)
    text = re.sub(r"\bNOT\b", "~", text)
    text = re.sub(r"\bSHL\b", "<<", text)
    text = re.sub(r"\bSHR\b", ">>", text)
    try:
        tree = ast.parse(text, mode="eval").body
    except SyntaxError:
        raise AssemblyError(f"Invalid expression: {text}") from None
    binary = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.floordiv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.BitAnd: operator.and_,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
    }

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        if isinstance(node, ast.Name):
            if node.id in symbols:
                return symbols[node.id]
            if unresolved:
                return 0
            raise AssemblyError(f"Unknown symbol: {node.id}")
        if isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.USub, ast.UAdd, ast.Invert)
        ):
            v = visit(node.operand)
            return (
                -v
                if isinstance(node.op, ast.USub)
                else ~v
                if isinstance(node.op, ast.Invert)
                else v
            )
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, (ast.LShift, ast.RShift)) and not 0 <= b <= 64:
                raise AssemblyError("Shift out of range")
            return binary[type(node.op)](a, b)
        raise AssemblyError(f"Unsupported expression: {text}")

    return visit(tree)


# Match instruction templates, with more specific operand forms first.
TEMPLATES = []
for entry in ISA:
    op = entry["opcode"]
    if op & 31 in (1, 17) and op not in (1, 17):
        continue
    template = entry["display"].upper()
    chunks = [re.sub(r"\s+", "", c) for c in re.split(r"\b[0-9A-F]+H\b", template)]
    pattern = "^" + "(.+?)".join(re.escape(c) for c in chunks) + "$"
    TEMPLATES.append((len(chunks) - 1, re.compile(pattern), entry))
TEMPLATES.sort(key=lambda item: (item[0], -len(item[1].pattern)))


def encode(line, symbols, pc, first=False):
    normalized = "".join(
        p if p.startswith("'") else re.sub(r"\s+", "", p.upper())
        for p in re.split(r"('[^']*')", line)
    )
    # Generic JMP/CALL reserve two bytes and select short/page forms.
    if normalized.startswith("CALL"):
        normalized = "ACALL" + normalized[4:]
    if normalized.startswith("JMP") and normalized != "JMP@A+DPTR":
        target = normalized[3:]
        value = expression(target, symbols, pc, first)
        is_label = target == "$" or any(
            re.search(r"\b" + re.escape(n) + r"\b", target)
            for n in symbols.get("__labels__", set())
        )
        offset = value - pc - 2 if is_label else value
        normalized = ("SJMP" if first or -128 <= offset <= 127 else "AJMP") + target
    reserved = {"A", "C", "AB", "DPTR"} | {f"R{i}" for i in range(8)}
    for _, regex, entry in TEMPLATES:
        match = regex.fullmatch(normalized)
        if not match:
            continue
        fields = match.groups()
        if any(
            (
                field.upper() in reserved
                or any(character in field for character in "@#,")
            )
            and not (len(field) == 3 and field[0] == field[-1] == "'")
            for field in fields
        ):
            continue
        values = [expression(s, symbols, pc, first) for s in fields]
        op, size = entry["opcode"], entry["size"]
        if op in (1, 17):
            dest = values[0]
            if not first and not 0 <= dest <= 65535:
                raise AssemblyError("16-bit address out of range")
            if not first and ((pc + 2) & 0xF800) != (dest & 0xF800):
                raise AssemblyError("AJMP/ACALL crosses a 2 KiB page")
            return [op | ((dest >> 3) & 0xE0), dest & 255]
        if op in (2, 0x12, 0x90):
            if not first and not 0 <= values[0] <= 65535:
                raise AssemblyError("16-bit value out of range")
            return [op, values[0] >> 8 & 255, values[0] & 255]
        if (
            op in (0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80, 0xD5)
            or 0xB4 <= op <= 0xBF
            or 0xD8 <= op <= 0xDF
        ):
            target = fields[-1]
            is_label = target == "$" or any(
                re.search(r"\b" + re.escape(n) + r"\b", target)
                for n in symbols.get("__labels__", set())
            )
            offset = ((values[-1] - pc - size) if is_label else values[-1]) & 65535
            if offset >= 32768:
                offset -= 65536
            if not first and not -128 <= offset <= 127:
                raise AssemblyError("Relative branch is outside -128..127 bytes")
            values[-1] = offset & 255
        if op == 0x85:
            values.reverse()
        if not first and any(not -128 <= v <= 255 for v in values):
            raise AssemblyError("Byte value out of range")
        result = [op] + [v & 255 for v in values]
        if len(result) == size:
            return result
    raise AssemblyError(f"Unknown instruction or operand form: {line}")


def assemble(source):
    source = normalize_source(source)
    symbols = {**SFR, **BITS, **{f"AR{i}": i for i in range(8)}, "__labels__": set()}
    code, locations, used = bytearray(65536), {}, set()
    mutable_symbols = set()
    for first in (True, False):
        symbols.update({f"AR{i}": i for i in range(8)})
        pc = 0
        for number, raw in enumerate(source.splitlines(), 1):
            try:
                if "\0" in raw:
                    raise AssemblyError("NUL characters are not allowed")
                line = strip_comment(raw).strip()
                if not line:
                    continue
                label = re.match(r"^([A-Za-z_]\w*):", line)
                if label:
                    name = label[1].upper()
                    if first and name in symbols:
                        raise AssemblyError(f"Duplicate symbol: {name}")
                    symbols[name] = pc
                    symbols["__labels__"].add(name)
                    line = line[label.end() :].strip()
                    if not line:
                        continue
                equ = re.fullmatch(
                    r"([A-Za-z_]\w*)\s+(EQU|SET)\s+(.+)", line, re.IGNORECASE
                )
                if equ:
                    name, directive = equ[1].upper(), equ[2].upper()
                    if (
                        first
                        and name in symbols
                        and not (directive == "SET" and name in mutable_symbols)
                    ):
                        raise AssemblyError(f"Duplicate symbol: {name}")
                    if directive == "SET":
                        mutable_symbols.add(name)
                    symbols[name] = expression(equ[3], symbols, pc, first)
                    continue
                parts = line.split(None, 1)
                directive = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ""
                if directive == "END":
                    break
                if directive == "ORG":
                    pc = expression(arg, symbols, pc, first)
                    if not 0 <= pc < 65536:
                        raise AssemblyError("ORG out of range")
                    continue
                if directive == "USING":
                    bank = expression(arg, symbols, pc, first)
                    if not 0 <= bank <= 3:
                        raise AssemblyError("Register bank must be 0..3")
                    symbols.update({f"AR{i}": bank * 8 + i for i in range(8)})
                    continue
                if directive == "DB":
                    values = []
                    for value in split_values(arg):
                        value = value.strip()
                        if (
                            len(value) >= 2
                            and value[0] == value[-1]
                            and value[0] in "'\""
                        ):
                            values.extend(quoted_value(value).encode("latin1"))
                        else:
                            v = expression(value, symbols, pc, first)
                            if not first and not -128 <= v <= 255:
                                raise AssemblyError("DB value out of range")
                            values.append(v & 255)
                else:
                    values = encode(line, symbols, pc, first)
                if pc + len(values) > 65536:
                    raise AssemblyError("Code exceeds 64 KiB")
                if not first:
                    if any(p in used for p in range(pc, pc + len(values))):
                        raise AssemblyError("Overlapping code")
                    code[pc : pc + len(values)] = bytes(values)
                    locations[pc] = {
                        "line": number,
                        "source": raw,
                        "size": len(values),
                        "instruction": directive != "DB",
                    }
                    used.update(range(pc, pc + len(values)))
                pc += len(values)
            except (ValueError, ZeroDivisionError, OverflowError) as error:
                raise AssemblyError(str(error), line=number) from None
    return Program(code, locations, symbols, used)


def export_hex(program):
    lines = []
    addresses = sorted(program.used)
    while addresses:
        start = addresses[0]
        group = [start]
        for p in addresses[1:16]:
            if p != group[-1] + 1:
                break
            group.append(p)
        addresses = addresses[len(group) :]
        record = [len(group), start >> 8, start & 255, 0] + [
            program.code[p] for p in group
        ]
        record.append(-sum(record) & 255)
        lines.append(":" + bytes(record).hex().upper())
    return "\n".join(lines + [":00000001FF"]) + "\n"


def import_hex(text):
    code, used, base, ended = bytearray(65536), set(), 0, False
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if ended:
            raise AssemblyError("Records found after EOF")
        try:
            if not line.startswith(":"):
                raise ValueError()
            b = bytes.fromhex(line[1:])
            n, address, kind = b[0], b[1] << 8 | b[2], b[3]
            if len(b) != n + 5 or sum(b) & 255:
                raise ValueError()
        except (ValueError, IndexError):
            raise AssemblyError(f"Invalid HEX record at line {number}") from None
        if kind == 1:
            ended = True
        elif kind in (2, 4):
            if n != 2:
                raise AssemblyError("Invalid extended address")
            base = int.from_bytes(b[4:6], "big") << (4 if kind == 2 else 16)
        elif kind == 0:
            address += base
            if address + n > 65536:
                raise AssemblyError("HEX exceeds 8051 code memory")
            if any(p in used for p in range(address, address + n)):
                raise AssemblyError("Overlapping HEX records")
            code[address : address + n] = b[4 : 4 + n]
            used.update(range(address, address + n))
        elif kind not in (3, 5):
            raise AssemblyError(f"Unsupported HEX record type {kind}")
    if not ended:
        raise AssemblyError("Missing HEX EOF record")
    return Program(code, {}, {}, used)
