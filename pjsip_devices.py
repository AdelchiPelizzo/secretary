import secretary.pjsua2 as pj


ep = pj.Endpoint()

ep_cfg = pj.EpConfig()

ep.libCreate()

transport_cfg = pj.TransportConfig()
transport_cfg.port = 5060

ep.transportCreate(
    pj.PJSIP_TRANSPORT_UDP,
    transport_cfg
)

ep.libInit(ep_cfg)

ep.libStart()

print()
print("PJSIP AUDIO DEVICES")
print("===================")

devices = ep.audDevManager().enumDev2()

for i, dev in enumerate(devices):

    print()
    print("ID:", i)
    print("Name:", dev.name)
    print("Driver:", dev.driver)
    print("Input channels:", dev.inputCount)
    print("Output channels:", dev.outputCount)
    print("Sample rate:", dev.defaultSamplesPerSec)

print()
print("===================")

ep.libDestroy()