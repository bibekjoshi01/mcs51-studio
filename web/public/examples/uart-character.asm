; Preset: UART Link. Terminal: 2400 baud, 8 data, no parity, 1 stop.
; 12 MHz / (12 * 32 * 13) = approximately 2404 baud, SMOD = 0.
        ORG 0000H
        MOV PCON,#00H
        MOV TMOD,#20H
        MOV TH1,#0F3H
        MOV TL1,#0F3H
        MOV SCON,#50H
        CLR TI
        SETB TR1
        MOV SBUF,#'A'
wait:   JNB TI,wait
        CLR TI
hold:   SJMP hold
        END
