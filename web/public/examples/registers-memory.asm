; No peripherals required. Inspect A and internal RAM 30H after stepping.
        ORG 0000H
        MOV A,#5
        ADD A,#3
        MOV 30H,A
        END
