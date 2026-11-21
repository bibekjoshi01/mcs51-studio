; Preset: LED Counter. After two steps, LED 0 is on and P1 is FEH.
        ORG 0000H
        MOV P1,#0FFH
        CLR P1.0
hold:   SJMP hold
        END
