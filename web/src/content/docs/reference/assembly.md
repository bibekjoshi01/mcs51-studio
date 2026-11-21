---
title: Assembly syntax
description: Supported number formats, operands, labels, directives, and expressions in the MCS51 Studio assembler.
---

MCS51 Studio includes a two-pass 8051 assembler. Use this page for the syntax it accepts; do not assume that every directive from another assembler is supported.

## Source lines

A line can contain a label, an instruction or directive, and a comment:

```asm
repeat: MOV A,#10H   ; Load sixteen into the accumulator
```

Labels end with a colon. A semicolon begins a comment outside quoted data. Instruction and symbol matching is case-insensitive. Keep label names clear and distinct from register names.

## Number formats

- **Decimal:** `25` or `25D`.
- **Hexadecimal:** `19H`, `0FFH`. A leading numeric digit is required.
- **Binary:** `00011001B`.
- **Octal:** `31O` or `31Q`.
- **Character operand:** `'A'` represents one character's value.

Use `#` for an immediate operand. `MOV A,#30H` loads 30H; `MOV A,30H` reads a direct location.

## Common operand forms

```asm
        MOV A,#42H       ; Immediate value
        MOV 30H,A        ; Direct internal RAM
        MOV R0,#30H
        MOV A,@R0        ; Indirect internal RAM
        CLR P1.0         ; Bit-addressable port bit
        MOV DPTR,#1234H
        MOVX @DPTR,A     ; External data memory
        MOVC A,@A+DPTR   ; Code-memory lookup
```

Only instruction-defined operand combinations are valid. Use the built-in Instruction Reference or [instruction catalog](../instructions/) to check an encoding.

## Directives

### ORG

Set the assembly location, within `0000H–FFFFH`:

```asm
        ORG 0000H
        LJMP start
        ORG 0030H
start:  MOV A,#1
```

Regions must not overlap. The layout value must already be resolved.

### EQU and SET

`EQU` defines a fixed symbol. Forward EQU chains are resolved before code emission; circular chains report an error.

```asm
LED_PORT EQU 90H
COUNT    EQU 10
        MOV LED_PORT,#0FFH
```

`SET` defines a mutable assembly-time value. It must be initialized before use and is evaluated in source order. It does not allocate a runtime variable.

### DB

Emit bytes or Latin-1 quoted strings into code memory:

```asm
message: DB 'HELLO',0
patterns: DB 0FFH,0FEH,0FCH
```

Data is not automatically skipped during execution. Jump around data regions when needed.

### USING

`USING 0` through `USING 3` selects the assembler's `AR0–AR7` direct-address aliases. It does not change the processor's PSW register-bank bits at runtime.

### END

`END` ends assembly and takes no operands. It does not emit an instruction or stop a running loop.

## Expressions

Expressions support arithmetic, parentheses, bitwise operations, and the word operators `AND`, `OR`, `XOR`, `NOT`, `SHL`, and `SHR`. `HIGH` and `LOW` extract bytes. `$` represents the current assembly address.

```asm
BUFFER EQU 1234H
        MOV DPH,#HIGH BUFFER
        MOV DPL,#LOW BUFFER
        MOV A,#(1 SHL 3)
```

Use a label for a branch destination. **Numeric relative operands are signed offsets**, while labels and label aliases are absolute destinations. Relative offsets must fit the instruction's range.

## Limits and unsupported syntax

The supported directives are `ORG`, `EQU`, `SET`, `DB`, `USING`, and `END`. Broader assembler syntax, include systems, and macros are not documented as supported.

Source is limited to 512 KiB of characters; instruction/expression text to 4,096 characters; expression trees to 256 nodes and integers to 64 bits; forward EQU dependency depth to 128. Out-of-range direct/bit addresses and branch offsets are rejected.

If a program from another tool fails, compare its directives and operand forms with this page before changing the processor logic.
