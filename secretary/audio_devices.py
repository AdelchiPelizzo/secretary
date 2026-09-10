import sounddevice as sd


def list_audio_devices():
    """Return all available audio devices with their capabilities."""
    devices = []

    for index, device in enumerate(sd.query_devices()):
        devices.append({
            "index": index,
            "name": device["name"],
            "hostapi": device["hostapi"],
            "input_channels": device["max_input_channels"],
            "output_channels": device["max_output_channels"],
            "default_samplerate": device["default_samplerate"],
        })

    return devices


def find_audio_device(name_contains, direction):
    """
    Find an audio device by part of its name and required direction.

    direction:
        "input"  -> device must accept audio
        "output" -> device must produce audio

    Returns the complete device record, or None if not found.
    """
    name_contains = name_contains.lower()

    for device in list_audio_devices():
        name = device["name"].lower()

        if name_contains not in name:
            continue

        if direction == "input" and device["input_channels"] > 0:
            return device

        if direction == "output" and device["output_channels"] > 0:
            return device

    return None


def discover_virtual_audio_devices():
    """
    Discover the virtual audio devices used by the local development setup.

    Returns complete device records determined from the current system.
    """
    caller_input = find_audio_device(
        "CABLE Output (VB-Audio Virtual Cable)",
        "input",
    )

    ai_output = find_audio_device(
        "Speakers (VB-Audio Cable A)",
        "output",
    )

    return {
        "caller_input": caller_input,
        "ai_output": ai_output,
    }


def print_audio_devices():
    """Print a readable audio-device inventory."""
    print()
    print("========================================")
    print("AUDIO DEVICE DISCOVERY")
    print("========================================")

    for device in list_audio_devices():
        direction = []

        if device["input_channels"] > 0:
            direction.append("INPUT")

        if device["output_channels"] > 0:
            direction.append("OUTPUT")

        direction_text = " / ".join(direction) or "NONE"

        print(
            f"[AUDIO DEVICE] "
            f"{device['index']:>2} | "
            f"{direction_text:<13} | "
            f"{device['name']} | "
            f"{device['default_samplerate']} Hz"
        )

    print("========================================")


def print_virtual_audio_configuration():
    """Print the virtual audio devices selected by discovery."""
    devices = discover_virtual_audio_devices()

    print()
    print("========================================")
    print("VIRTUAL AUDIO CONFIGURATION")
    print("========================================")

    if devices["caller_input"]:
        print(
            f"[AUDIO CONFIG] Caller input : "
            f"{devices['caller_input']}"
        )
    else:
        print("[AUDIO CONFIG] Caller input : NOT FOUND")

    if devices["ai_output"]:
        print(
            f"[AUDIO CONFIG] AI output    : "
            f"{devices['ai_output']}"
        )
    else:
        print("[AUDIO CONFIG] AI output    : NOT FOUND")

    print("========================================")