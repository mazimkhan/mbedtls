# CI test dispatch

## CI and test entities relation

```
                                         ----------
                                         |   CI   |
                                         ----------
                                              | 1
                                              |
                                              | m
                                         ----------
                                         |  Job   |
                                         ----------
                                              | m
                                              |
                                              | m
                 ------------ m      m --------------- 1      m --------------------
                 | Platform |----------| Test script |----------| Test environment |
                 ------------          ---------------          --------------------

```

