; Preset: Switch Input. A low switch level lights its matching LED.
        ORG 0000H
        MOV P2,#0FFH
again:  MOV A,P2
        MOV P1,A
        SJMP again
        END
