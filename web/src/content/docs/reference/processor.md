---
title: Processor model
description: The exact Classic 8051 profile, memory organization, timers, interrupt rules, and timing model.
---

The current profile is **Classic 8051 · 12 MHz · 12 clocks per machine cycle**. One machine cycle is 1 µs. The interface does not expose arbitrary clock selection.

## Resources

- 128 bytes of internal RAM, addresses 00–7FH.
- Four register banks and one DPTR.
- Separate 64 KB code and 64 KB external-data address spaces.
- Timer 0 and Timer 1.
- Five interrupt sources and two priority levels.

8052 and AT89S52 are future profiles. Upper internal RAM, Timer 2, and derivative features are not enabled.

## Memory and stack behavior

Direct 00–7FH selects internal RAM; implemented direct 80–FFH selects SFRs. Indirect `@R0` / `@R1` and stack accesses select internal RAM only.

SP resets to 07H. PUSH increments SP before storing. POP decrements SP before its destination is written. Calls push the return PC low byte followed by high byte.

`MOVC` reads code memory. All six `MOVX` encodings access external RAM. `@DPTR` uses a 16-bit address; `@Ri` combines the P2 latch with the selected register. MOVX releases P0 to FFH and leaves P2 unchanged. Bus strobes are not rendered.

Undefined upper indirect RAM, unimplemented SFRs, and reserved opcode A5H stop with an explanatory error. This is a teaching safeguard, not a claim that physical silicon raises the same error.

Reset clears simulated RAM/XDATA for repeatable exercises. Physical power-on RAM values are not guaranteed.

## Flags

ADD, ADDC, and SUBB update CY, AC, and OV. MUL, DIV, and decimal adjustment follow their instruction-specific rules. Parity reflects ACC at each instruction boundary.

Division by zero sets OV and clears CY. The simulator retains ACC and B as a deterministic choice for the undefined result.

## Timers and counters

Modes 0, 1, and 2 provide 13-bit counting, 16-bit counting, and 8-bit reload. Counter inputs count sampled falling edges. GATE and TR control counting.

In Timer 0 mode 3, TL0 uses its own controls while TH0 uses TR1/TF1 independently. Timer 1 can continue as a baud generator without TF1; Timer 1's own mode 3 halts it. Only full Timer 1 overflows clock serial modes 1 and 3.

Try [Wait for a timer](../../examples/#wait-for-a-timer) for a simple polling example.

## Interrupt behavior

Polling uses the preceding machine-cycle sample at instruction boundaries. EA, individual enables, priority, and in-service nesting determine acceptance.

Equal-priority requests are ordered INT0, Timer 0, INT1, Timer 1, then serial. Hardware entry pushes PC, preserves PSW, and takes two machine cycles while timers continue.

`RETI` releases active interrupt priority; `RET` does not. RETI and IE/IP accesses allow one following instruction before another interrupt can be accepted. Timer and edge-triggered external flags clear on acceptance. RI and TI must be cleared in software. Level-triggered external flags follow sampled pins.

To inject an external input, open Experiment Settings, choose P3.2/INT0 or P3.3/INT1, set a low-pulse width, and select **Apply And Pulse**. Configure TCON/IE in your source first. A shared device may also hold that pin low.

## Resolution and sources

Instructions commit at machine-cycle boundaries; board devices update after each instruction. S-state/P-phase timing, sub-instruction pin transitions, and electrical contention are outside the model.

For the implementation contract and validation details, see the repository's [processor profile](https://github.com/bibekjoshi01/mcs51-studio/blob/main/docs/processor.md). Its primary references are the [Atmel 8051 instruction set](https://www.keil.com/dd/docs/datashts/atmel/at_c51ism.pdf) and [8051 hardware manual](https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/UserGuides/doc4316.pdf). Derivative extensions described in those documents may not apply to this profile.
