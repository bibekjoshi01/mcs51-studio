; MCS51 Studio — LED counter
; P1 LEDs are active low. Step to inspect each instruction.
        ORG 0000H
        MOV A,#0FFH
loop:   MOV P1,A
        ACALL delay
        DEC A
        SJMP loop

delay:  MOV R0,#20
outer:  MOV R1,#250
inner:  DJNZ R1,inner
        DJNZ R0,outer
        RET
        END
