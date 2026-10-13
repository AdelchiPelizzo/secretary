from secretary import pjsua2 as pj


ep = pj.Endpoint()

try:
    ep.libCreate()

    cfg = pj.EpConfig()
    cfg.uaConfig.threadCnt = 0

    ep.libInit(cfg)

    mgr = ep.audDevManager()

    print()
    print("PJSIP AUDIO DEVICES")
    print("===================")

    devices = mgr.enumDev2()

    for i, dev in enumerate(devices):
        print(
            i,
            dev.name,
            "input=", dev.inputCount,
            "output=", dev.outputCount
        )

finally:

    try:
        ep.libDestroy()
    except Exception:
        pass
