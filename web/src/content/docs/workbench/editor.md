---
title: Editor and files
description: Write, assemble, save, and troubleshoot assembly source; work with Intel HEX images.
---

The editor accepts 8051 assembly source. Syntax highlighting, line numbers, completion, and inline errors help you write and check small programs.

## Open and save source

Use **File → New**, **Open**, or **Save**. A dot on the editor tab marks unsaved source or project settings. New and Open prompt you to Save, Discard, or Cancel when there are unsaved changes.

Save plain assembly as `.asm`. On macOS, use **Command** wherever these guides say Ctrl. Saving uses atomic replacement so a failed write does not truncate the previous file.

:::note[Save and Assemble do different jobs]
Save writes your work to a file. **Assemble (F6)** builds executable bytes in the simulator. Assembling a modified document does not save it to disk.
:::

## Write and navigate

- Press **Ctrl+Space** for instruction, register, and symbol completion. On macOS this is **Control+Space**.
- Press **Ctrl+G** to go to a line.
- Use **Ctrl+/** to toggle comments.
- Use **Tab / Shift+Tab** to indent or unindent.
- Use **Ctrl+D** to duplicate lines and **Alt+Up / Alt+Down** to move them.
- Use **Ctrl++**, **Ctrl+-**, and **Ctrl+0** to increase, decrease, or reset text size.

The toolbar and context menu include normal clipboard and undo commands. Windows and Unix line endings are accepted when pasting.

## Find and replace

Open **Ctrl+F** for Find/Replace. It supports case-sensitive and whole-word matching, forward/backward navigation, and match counts. Search and replacement text are literal; regular expressions are not used.

Replace All is a single undoable operation. Press **Escape** to close the search controls.

## Assemble and fix errors

Press **F6**. On success, inspect addresses and bytes in **Listing**. On failure:

1. Read the message in **Activity**.
2. Find the marked source line.
3. Check the spelling, operand form, numeric range, and label names.
4. Correct the source and assemble again.

Editing clears the previous inline diagnostic and pauses execution. A failed assembly blocks execution of the previously assembled program, so you do not accidentally run stale code. Empty or comments-only buffers cannot run.

Read [Assembly syntax](../../reference/assembly/) for supported directives and expressions.

## Import and export Intel HEX

An Intel HEX file contains machine code and addresses. It does not contain the original source, comments, or labels.

Opening a HEX file loads its image and displays an explanatory editor buffer. Use Listing and Memory to inspect the bytes. Editing that buffer begins a new assembly program. **Export Intel HEX** writes the current loaded machine image.

If you edit **Code** memory directly, Listing marks the code as modified. HEX export includes those edits; **Reset** or **Assemble** reloads the original assembled bytes.

Use a [portable project](../projects/) to keep source and experiment configuration together. HEX-only imports cannot be saved as source projects.
