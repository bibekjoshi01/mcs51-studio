; Preset: DAC Waveform. Open Instruments > DAC Scope.
; Active-low write remains enabled while P1 counts from 0 to 255.
        ORG 0000H
        CLR P0.7
        MOV A,#0
again:  MOV P1,A
        INC A
        SJMP again
        END
