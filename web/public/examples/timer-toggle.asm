; Preset: Timer / PWM. Probe P1.0 in the Logic Analyzer.
; Mode 1 starts at FC18H: 1000 timer increments until overflow.
; Reload/poll/toggle instructions add overhead to the output period.
        ORG 0000H
        MOV P1,#0FFH
        MOV TMOD,#01H
again:  CLR TR0
        CLR TF0
        MOV TH0,#0FCH
        MOV TL0,#018H
        SETB TR0
wait:   JNB TF0,wait
        CLR TR0
        CPL P1.0
        SJMP again
        END
