# OpenAI TTS Deprecation Investigation
# MIGRATION COMPLETED — 2026-10-07

## Final status

The Secretary application's production TTS migration is complete.

The deprecated `gpt-4o-mini-tts` Speech API is no longer used by the active application.

### New production TTS

The active `server.py` now uses:

- Model: `gpt-realtime-2.1-mini`
- Realtime API
- Output: 24 kHz PCM
- Resampled to: 8 kHz PCM
- Existing `AudioBridge` / VB-CABLE audio path retained
- Existing PJSIP/SIP architecture retained

### Verification

The migration has been tested successfully in live SIP calls.

Verified:

- Business-configured greeting is spoken correctly.
- Normal AI-generated responses are spoken correctly.
- Realtime audio reaches the caller through the existing SIP/PJSIP path.
- Windows audio channels remain unchanged.
- No PJSIP rebuild was required.

### Important implementation detail

The Realtime session uses explicit instructions to speak the supplied text exactly:

> Speak the user's message exactly as provided. Do not answer it, interpret it, or add anything. The user's message is the exact text that must be spoken.

This prevents the Realtime model from interpreting the supplied TTS text as a conversational request.

### Deprecated implementation

The old `client.audio.speech.create()` implementation using `gpt-4o-mini-tts` remains only in historical backup files/documentation and is **not part of the active runtime**.

Migration completed: **2026-10-07**
Date: 2026-10-05

Scope: current Secretary Python project. This is investigation only. No source files were modified.

## CURRENT IMPLEMENTATION

### Runtime entrypoint and call flow

The active runtime entrypoint appears to be `server.py`.

- `server.py`, module scope, around line 733:
  - creates `server = CallServer()`
  - creates `server.sip = SipServer(server)`
  - starts HTTP server thread
  - starts SIP server
  - runs the PJSIP event loop

Core runtime files:

- `server.py`
  - `CallServer`
  - `CallServer.process_call`
  - `CallServer.wait_for_speech`
  - `CallServer.text_to_speech_to_sip`
  - `CallServer.resample`
- `secretary/sip.py`
  - `SipServer`
  - `SecretaryAccount`
  - `SecretaryCall`
- `secretary/call.py`
  - `Call`
  - `AudioBridge`
- `secretary/ai_service.py`
  - `speech_to_text`
  - `ask_ai`
  - `generate_availability_response`
  - `generate_appointment_confirmation_response`
  - `generate_appointment_created_response`
  - `text_to_speech`

Backup and experiment files also contain relevant OpenAI/audio code, but they do not appear to be the active runtime path unless run directly:

- `server_bak.py`
- `secretary/ai_service_bak.py`
- `secretary/call.backup.py`
- `secretary/call_before_cable_a.py`
- `test_realtime_tts.py`
- `test_realtime_sip.py`
- `test_sip_audio.py`
- `test_vbcable.py`
- `secretary/sip_audio_bridge.py`

### Speech-to-text

Active function:

- File: `secretary/ai_service.py`
- Function: `speech_to_text(audio)`
- Approximate lines: 10-28
- OpenAI client: `OpenAI()`
- API/method: `client.audio.transcriptions.create(...)`
- Model: `gpt-4o-mini-transcribe`
- Input format:
  - Python audio array passed into `speech_to_text`
  - written to `caller.wav` with `soundfile.write`
  - sample rate: 44100 Hz
  - then opened as binary file and submitted to OpenAI
- Output:
  - text from `transcription.text`

Caller audio path into STT:

- `secretary/call.py`, `AudioBridge._input_callback`, around lines 108-123:
  - receives sounddevice input stream frames
  - configured as 8000 Hz, mono, int16
  - converts first channel to bytes
  - puts raw int16 PCM bytes into `input_queue`
- `server.py`, `CallServer.wait_for_speech`, around lines 284-357:
  - reads chunks from `audio_port.input_queue`
  - interprets chunks as `np.int16`
  - performs RMS threshold speech detection
  - joins chunks into raw audio
  - converts int16 PCM to float32 normalized audio
  - resamples from 8000 Hz to 44100 Hz using `CallServer.resample`
  - returns float audio to `speech_to_text`
- `secretary/ai_service.py`, `speech_to_text`, around lines 13-17:
  - writes `caller.wav` at 44100 Hz

Important STT note:

- OpenAI separately lists `gpt-4o-mini-transcribe` as deprecated with shutdown on February 26, 2027.
- That is not the TTS deprecation, but it affects this project later.

### AI/chat response generation

Active functions:

1. Main conversational parser/response:

- File: `secretary/ai_service.py`
- Function: `ask_ai(call, message)`
- Approximate lines: 30-368
- API/method: `client.chat.completions.create(...)`
- Model: `gpt-5.4-mini`
- Input format:
  - Chat Completions `messages` array
  - system prompt plus `call.messages`
- Output format:
  - text response in `response.choices[0].message.content`
  - parsed into fields:
    - `LANGUAGE`
    - `ACTION`
    - `TITLE`
    - `DATE`
    - `TIME`
    - `DURATION`
    - `DESCRIPTION`
    - `NOTE`
    - `RESPONSE`

2. Availability response:

- File: `secretary/ai_service.py`
- Function: `generate_availability_response(call, alternatives)`
- Approximate lines: 370-410
- API/method: `client.chat.completions.create(...)`
- Model: `gpt-5.4-mini`
- Input format:
  - Chat Completions `messages` array
- Output:
  - spoken response text

3. Appointment confirmation response:

- File: `secretary/ai_service.py`
- Function: `generate_appointment_confirmation_response(call)`
- Approximate lines: 412-449
- API/method: `client.chat.completions.create(...)`
- Model: `gpt-5.4-mini`
- Input format:
  - Chat Completions `messages` array
- Output:
  - spoken response text

4. Appointment created response:

- File: `secretary/ai_service.py`
- Function: `generate_appointment_created_response(call)`
- Approximate lines: 451-483
- API/method: `client.chat.completions.create(...)`
- Model: `gpt-5.4-mini`
- Input format:
  - Chat Completions `messages` array
- Output:
  - spoken response text

Runtime use:

- `server.py`, `CallServer.process_call`, around lines 451-591:
  - initial greeting is sent to TTS
  - waits for caller speech
  - calls `speech_to_text(audio)`
  - calls `ask_ai(app_call, message)`
  - may call appointment/note APIs
  - calls helper AI response functions when needed
  - sends final answer to TTS

### Text-to-speech

Active runtime TTS function:

- File: `server.py`
- Function: `CallServer.text_to_speech_to_sip(text, audio_port)`
- Approximate lines: 359-449
- OpenAI client: `OpenAI()`, created around line 39
- API/method: `client.audio.speech.create(...)`
- Model: `gpt-4o-mini-tts`
- Voice: `coral`
- Input format:
  - plain text string
- Output file:
  - written to `ai_response.wav`
- Output audio format requested:
  - no `response_format` is specified
- Practical output format:
  - OpenAI Speech API default is MP3 when `response_format` is not set
  - therefore the code likely writes MP3 bytes into a file named `ai_response.wav`
- Sample rate requested:
  - none
- Sample rate actually used by code:
  - discovered after decode with `soundfile.read(filename, dtype="float32")`
  - logged as `[TTS] Original samplerate: ...`
  - then resampled to 8000 Hz

Duplicate non-runtime helper:

- File: `secretary/ai_service.py`
- Function: `text_to_speech(text)`
- Approximate lines: 485-500
- API/method: `client.audio.speech.create(...)`
- Model: `gpt-4o-mini-tts`
- Voice: `coral`
- Input format:
  - plain text string
- Output:
  - writes `ai_response.wav`
- This function is not imported by the current `server.py`, but it remains in the codebase.

Backup duplicates:

- `server_bak.py`, `CallServer.text_to_speech_to_sip`, around lines 317-407:
  - same `gpt-4o-mini-tts` Speech API call
- `secretary/ai_service_bak.py`, `text_to_speech`, around lines 275-290:
  - same `gpt-4o-mini-tts` Speech API call

### Exact OpenAI models currently used

Active runtime models:

- STT:
  - `gpt-4o-mini-transcribe`
  - API: `client.audio.transcriptions.create`
  - File/function: `secretary/ai_service.py`, `speech_to_text`
- AI/chat:
  - `gpt-5.4-mini`
  - API: `client.chat.completions.create`
  - File/functions:
    - `secretary/ai_service.py`, `ask_ai`
    - `secretary/ai_service.py`, `generate_availability_response`
    - `secretary/ai_service.py`, `generate_appointment_confirmation_response`
    - `secretary/ai_service.py`, `generate_appointment_created_response`
- TTS:
  - `gpt-4o-mini-tts`
  - API: `client.audio.speech.create`
  - File/function:
    - `server.py`, `CallServer.text_to_speech_to_sip`
  - Additional non-runtime duplicate:
    - `secretary/ai_service.py`, `text_to_speech`

Experiment/test-only models:

- `gpt-realtime-2.1-mini`
  - API: `client.realtime.connect`
  - Files:
    - `test_realtime_tts.py`, `main`
    - `test_realtime_sip.py`, `realtime_tts`

Models not found in active source:

- `tts-1`
- `tts-hd`
- `tts-1-hd`

## CURRENT TELEPHONE AUDIO ASSUMPTIONS

### AudioBridge assumptions

File: `secretary/call.py`

Constants:

- `SAMPLE_RATE = 8000`
- `CHANNELS = 1`
- `BLOCKSIZE = 320`

Input stream:

- Function: `AudioBridge.start`
- Approximate lines: 85-92
- `sounddevice.InputStream`
- device: `"CABLE Output (VB-Audio Virtual Cable)"`
- sample rate: 8000 Hz
- channels: 1
- dtype: `int16`
- blocksize: 320
- callback: `_input_callback`

Output stream:

- Function: `AudioBridge.start`
- Approximate lines: 94-101
- `sounddevice.OutputStream`
- device: `"Speakers (VB-Audio Cable A)"`
- sample rate: 8000 Hz
- channels: 1
- dtype: `int16`
- blocksize: 320
- callback: `_output_callback`

PCM assumptions:

- signed 16-bit integer PCM
- little-endian by NumPy/platform convention for `np.int16`
- mono
- 8000 Hz

Chunking:

- `BLOCKSIZE = 320` samples at 8000 Hz
- 320 samples / 8000 samples per second = 0.04 seconds
- current chunks are 40 ms, not 20 ms
- code comments in `server.py` and tests sometimes say 20 ms, but `320 * 2 = 640` bytes is 40 ms at 8 kHz mono int16

### SIP/PJSIP assumptions

File: `secretary/sip.py`

SIP provider:

- `SERVER = "sip.vivavox.it"`
- `PORT = 5060`

PJSIP audio device setup:

- Function: `SipServer.start`
- Approximate lines: 224-225
- `setCaptureDev(3)`
- `setPlaybackDev(7)`

`windows-channels.txt` says device indexes are volatile after reboot and should be re-discovered.

PJSIP media connection:

- Function: `SecretaryCall.onCallMediaState`
- Approximate lines: 67-96
- On active audio media:
  - call audio transmits to PJSIP playback device:
    - `audio_media.startTransmit(getPlaybackDevMedia())`
  - PJSIP capture device transmits to call audio:
    - `getCaptureDevMedia().startTransmit(audio_media)`

Therefore:

- Audio from telephone caller:
  - SIP call media -> PJSIP playback device -> VB-Cable path -> `AudioBridge` input stream
- Audio to telephone caller:
  - `AudioBridge` output stream -> VB-Cable path -> PJSIP capture device -> SIP call media

### VB-Audio virtual cable assumptions

The current app uses VB-Audio devices as an audio bridge between Python/sounddevice and PJSIP.

Relevant names in source:

- `secretary/call.py`
  - input to Python:
    - `"CABLE Output (VB-Audio Virtual Cable)"`
  - output from Python:
    - `"Speakers (VB-Audio Cable A)"`
- `secretary/sip.py`
  - comments/logs say PJSIP capture is `CABLE Output`
  - comments/logs say PJSIP playback is `CABLE Input`
- `windows-channels.txt`
  - current intended PJSIP capture:
    - `CABLE-A Output (VB-Audio Cable A)`
  - current intended PJSIP playback:
    - `CABLE Input (VB-Audio Virtual Cable)`

There is naming inconsistency between comments, current code, and backup variants. The actual device indexes set in `secretary/sip.py` are currently numeric, so the effective routing depends on the Windows audio device ordering at runtime.

## COMPLETE TTS AUDIO PATH TO TELEPHONE CALLER

1. `server.py`, `CallServer.process_call`, around lines 459-462:
   - initial greeting text is passed to `text_to_speech_to_sip`

2. `server.py`, `CallServer.process_call`, around lines 572-574:
   - AI answer text is passed to `text_to_speech_to_sip`

3. `server.py`, `CallServer.text_to_speech_to_sip`, around line 372:
   - calls:
     - `client.audio.speech.create(model="gpt-4o-mini-tts", voice="coral", input=text)`

4. `server.py`, around line 374:
   - writes response to `ai_response.wav`
   - despite `.wav` extension, default OpenAI Speech API output is MP3 unless `response_format` is specified

5. `server.py`, around lines 380-383:
   - decodes file with `soundfile.read(filename, dtype="float32")`
   - captures decoded sample rate as `samplerate`

6. `server.py`, around lines 388-393:
   - if decoded audio has more than one channel, averages channels to mono

7. `server.py`, around lines 395-400:
   - resamples from decoded OpenAI output sample rate to 8000 Hz

8. `server.py`, around lines 402-413:
   - applies gain `* 3.0`
   - clips to `[-1.0, 1.0]`
   - converts float audio to signed int16 PCM

9. `server.py`, around lines 415-436:
   - converts int16 array to bytes
   - chunks bytes in `320 * 2 = 640` byte chunks
   - puts chunks into `audio_port.output_queue`

10. `secretary/call.py`, `AudioBridge._output_callback`, around lines 124-151:
    - sounddevice requests output frames
    - callback reads one chunk from `output_queue`
    - pads with zero bytes if chunk is short
    - converts bytes to `np.int16`
    - writes to output stream channel 0

11. `secretary/call.py`, `AudioBridge.start`, around lines 94-101:
    - output stream plays to `"Speakers (VB-Audio Cable A)"`
    - format is 8000 Hz, mono, int16

12. VB-Audio virtual cable carries Python output into the device that PJSIP is using as capture input.

13. `secretary/sip.py`, `SecretaryCall.onCallMediaState`, around line 92:
    - PJSIP capture device media transmits to SIP call audio media

14. PJSIP sends RTP audio through the VivaVox SIP call.

15. Telephone caller hears AI speech.

## DEPRECATED COMPONENT

The affected component is the TTS component.

OpenAI official deprecation notice:

- Source: OpenAI API deprecations page
- URL: https://developers.openai.com/api/docs/deprecations
- Section: `2026-10-01: Text-to-speech models`
- Shutdown date: January 6, 2027
- Deprecated models:
  - `tts-1`
  - `tts-1-hd`
  - `gpt-4o-mini-tts-2025-03-20`
  - `gpt-4o-mini-tts-2025-12-15`
- Recommended replacement:
  - `gpt-realtime-2.1-mini`

The model page for `gpt-4o-mini-tts` also marks it as deprecated:

- URL: https://developers.openai.com/api/docs/models/gpt-4o-mini-tts

Current project impact:

- Active runtime TTS uses `gpt-4o-mini-tts` in `server.py`.
- The alias maps to the deprecated GPT-4o Mini TTS model family/snapshots.
- Therefore the active runtime TTS path is affected.

Current project is not affected by `tts-1` or `tts-hd` directly because those model names do not appear in the project source.

Separate non-TTS deprecation:

- OpenAI also lists `gpt-4o-mini-transcribe` for shutdown on February 26, 2027.
- The current STT implementation uses that model.
- This is separate from the TTS migration, but should be tracked.

## OPENAI RECOMMENDED REPLACEMENT

OpenAI recommends migrating deprecated TTS models to:

- `gpt-realtime-2.1-mini`

Relevant OpenAI docs:

- Deprecations:
  - https://developers.openai.com/api/docs/deprecations
- Realtime conversations:
  - https://developers.openai.com/api/docs/guides/realtime-conversations
- Realtime/WebSocket audio formats:
  - https://developers.openai.com/api/docs/guides/voice-websockets
- GPT-Realtime-2.1 Mini model:
  - https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini

Project experiments already use the recommended replacement:

- `test_realtime_tts.py`
  - `AsyncOpenAI`
  - `client.realtime.connect(model="gpt-realtime-2.1-mini")`
  - requests `audio/pcm` output at 24000 Hz
  - receives `response.output_audio.delta`
  - decodes base64 PCM deltas
  - resamples 24000 Hz PCM to 8000 Hz PCM
  - writes `realtime_tts_8khz_test.wav`
- `test_realtime_sip.py`
  - same Realtime model
  - sends generated audio toward `AudioBridge`

## COMPATIBILITY WITH CURRENT SIP AUDIO

`gpt-realtime-2.1-mini` is compatible with the architecture, but not as a one-line model replacement.

Why it is not a drop-in replacement:

- Current production TTS uses synchronous Speech API:
  - `client.audio.speech.create`
  - write whole response to file
  - decode file
  - resample
  - enqueue PCM to `AudioBridge`
- Realtime uses a connection/session:
  - `client.realtime.connect`
  - `session.update`
  - `conversation.item.create`
  - `response.create`
  - stream `response.output_audio.delta` events
  - base64 decode audio bytes

Why it is still compatible:

- The existing telephone output path only requires raw 8000 Hz mono signed int16 PCM chunks in `audio_port.output_queue`.
- Realtime can produce PCM audio.
- Existing test code already demonstrates converting Realtime PCM to 8000 Hz int16 PCM.
- The existing `AudioBridge`, VB-Audio cable path, PJSIP devices, and VivaVox SIP call can remain unchanged if the replacement TTS helper produces the same 8000 Hz int16 PCM chunks currently queued by `text_to_speech_to_sip`.

OpenAI Realtime audio format considerations:

- OpenAI docs show `audio/pcm` commonly at 24000 Hz.
- OpenAI Realtime/WebSocket docs also list telephony formats:
  - `audio/pcmu` at 8000 Hz, G.711 μ-law
  - `audio/pcma` at 8000 Hz, G.711 A-law
- The current `AudioBridge` does not accept μ-law or A-law bytes.
- The current `AudioBridge` accepts int16 PCM bytes.
- Therefore the safest compatibility path is PCM output from Realtime plus resampling/conversion to the existing 8000 Hz int16 PCM format.

Using Realtime G.711 directly would not be minimum change because it would require changing the local bridge or adding codec conversion.

## IS `gpt-realtime-2.1-mini` ACTUALLY THE BEST REPLACEMENT?

For strict alignment with OpenAI's deprecation notice:

- Yes. OpenAI explicitly recommends `gpt-realtime-2.1-mini` for the deprecated TTS models.

For minimum engineering disruption:

- It is the best future-proof replacement listed by OpenAI.
- It is not the smallest possible syntactic change.
- The smallest syntactic change would be another Speech API model, but the current OpenAI deprecation notice points away from the Speech TTS models and toward Realtime.

For this architecture:

- Best migration approach is to use `gpt-realtime-2.1-mini` only as a TTS renderer.
- Do not migrate the whole Secretary conversation to a Realtime voice agent unless there is a product reason to do so.
- Keep current STT, current AI/chat model, current appointment logic, current SIP/VB-Audio path, and current 8 kHz `AudioBridge`.

Why not fully migrate to Realtime conversation now:

- Current code already has conversation state, appointment extraction, calendar/note logic, and deterministic post-processing in `ask_ai`.
- Replacing the whole loop with Realtime would require rethinking STT, turn detection, barge-in, tool calls, and state handling.
- That is unnecessary for the TTS deprecation.

## MINIMUM-CHANGE MIGRATION

Recommended minimum-change strategy:

1. Keep:
   - VivaVox SIP
   - PJSIP 2.17
   - `secretary/sip.py`
   - `secretary/call.py` `AudioBridge`
   - 8000 Hz mono int16 telephone audio path
   - current STT call for now
   - current AI/chat calls for now
   - current conversation and appointment logic

2. Replace only the internals of:
   - `server.py`
   - `CallServer.text_to_speech_to_sip`

3. New TTS internals should:
   - connect to OpenAI Realtime with `gpt-realtime-2.1-mini`
   - configure output audio voice
   - send the existing response text as `input_text`
   - request audio output only
   - receive `response.output_audio.delta` events
   - base64 decode audio deltas
   - interpret output as PCM16 at the configured sample rate, likely 24000 Hz if using current experiment structure
   - resample to 8000 Hz
   - convert to signed int16 PCM
   - push chunks into `audio_port.output_queue` in the same format the current `AudioBridge` expects

4. Preserve the external behavior of:
   - `text_to_speech_to_sip(text, audio_port)`

5. Do not introduce a new SIP bridge unless needed.

6. Do not change PJSIP device routing as part of the TTS migration.

Files likely needing changes for minimum migration:

- Required:
  - `server.py`
    - `CallServer.text_to_speech_to_sip`
    - possibly imports to support async/base64, depending on implementation
- Optional cleanup later:
  - `secretary/ai_service.py`
    - unused `text_to_speech` still references deprecated TTS
  - `server_bak.py`
    - backup still references deprecated TTS
  - `secretary/ai_service_bak.py`
    - backup still references deprecated TTS

Do not change for minimum TTS migration:

- `secretary/sip.py`
- `secretary/call.py`
- `secretary/ai_service.py` STT and chat functions
- appointment/note logic
- current 8000 Hz `AudioBridge`

## SAMPLE-RATE AND RESAMPLING ISSUES

### Current production path

Caller to STT:

- `AudioBridge` captures 8000 Hz mono int16 PCM.
- `server.py` converts int16 bytes to float32.
- `server.py` resamples 8000 Hz to 44100 Hz.
- `secretary/ai_service.py` writes `caller.wav` at 44100 Hz.
- OpenAI STT receives the WAV file.

TTS to caller:

- OpenAI Speech API returns audio with unspecified requested format/sample rate.
- Code writes it to `ai_response.wav`.
- Code decodes it with `soundfile`.
- Code resamples decoded audio to 8000 Hz.
- Code converts to mono int16 PCM.
- Code queues bytes to the 8000 Hz `AudioBridge`.

### Realtime experiment path

`test_realtime_tts.py`:

- Realtime output requested as:
  - `audio/pcm`
  - `rate: 24000`
- Decoded bytes interpreted as:
  - `np.int16`
  - PCM16
  - 24000 Hz
- Resampled to:
  - 8000 Hz
  - int16 PCM
- Written as:
  - mono
  - 16-bit
  - 8000 Hz WAV

`test_realtime_sip.py`:

- Realtime output requested as 24000 Hz PCM.
- Code resamples to 48000 Hz, then sends to `AudioBridge`.
- This is inconsistent with the active `AudioBridge`, which is 8000 Hz.
- For production migration, follow the `test_realtime_tts.py` 24000 Hz -> 8000 Hz path, not the 24000 Hz -> 48000 Hz path.

### Risks

1. Misnamed TTS file:
   - current code writes default Speech API output to `ai_response.wav`
   - OpenAI docs say default is MP3 unless `response_format` is set
   - decoding works only if `soundfile` can infer/decode the actual content

2. Chunk duration mismatch:
   - comments say 20 ms
   - code sends 640-byte chunks
   - at 8000 Hz mono int16, 640 bytes = 320 samples = 40 ms
   - avoid changing chunk size during the TTS migration unless separately tested

3. Resampler quality:
   - current resampler uses `np.interp`
   - acceptable for simple tests, but not high-quality audio resampling
   - downsampling 24000 Hz to 8000 Hz may alias without proper filtering
   - if audio quality is poor, consider a better resampler later

4. Gain/clipping:
   - current TTS path multiplies by 3.0 and clips
   - can cause distortion
   - preserve initially for behavior compatibility, then tune after migration

5. Voice differences:
   - `coral` may behave differently on Realtime than Speech API
   - test language coverage and telephone intelligibility

6. Device routing:
   - `secretary/sip.py` uses numeric PJSIP device indexes
   - `windows-channels.txt` says indexes change after reboot
   - TTS migration testing must confirm actual PJSIP capture/playback devices before judging audio failure

7. STT deprecation later:
   - current STT model `gpt-4o-mini-transcribe` has its own deprecation date
   - do not mix that migration with the TTS migration unless intentionally planned

## FILES THAT WOULD NEED CHANGING

Minimum required:

- `server.py`
  - `CallServer.text_to_speech_to_sip`
  - reason: active runtime TTS uses deprecated `gpt-4o-mini-tts`

Optional but recommended after minimum migration:

- `secretary/ai_service.py`
  - `text_to_speech`
  - reason: unused duplicate still references deprecated `gpt-4o-mini-tts`

Optional housekeeping only:

- `server_bak.py`
  - duplicate deprecated TTS call
- `secretary/ai_service_bak.py`
  - duplicate deprecated TTS call

No change recommended for minimum TTS migration:

- `secretary/call.py`
  - keep existing 8000 Hz mono int16 `AudioBridge`
- `secretary/sip.py`
  - keep existing PJSIP/VivaVox path
- `secretary/ai_service.py`
  - keep STT/chat logic initially, except optional unused `text_to_speech`

## CONCLUSION

The current Secretary application does not use `tts-1` or `tts-hd`. It uses `gpt-4o-mini-tts` through the OpenAI Speech API for active runtime TTS in `server.py`.

That active TTS model family is deprecated with shutdown on January 6, 2027. OpenAI recommends `gpt-realtime-2.1-mini`.

`gpt-realtime-2.1-mini` is compatible with the current SIP/PJSIP architecture if used as a TTS-only renderer and its audio output is converted to the existing 8000 Hz mono signed int16 PCM format expected by `AudioBridge`.

The minimum-change migration is to replace only the internals of `CallServer.text_to_speech_to_sip`, leaving VivaVox SIP, PJSIP, VB-Audio routing, `AudioBridge`, STT, AI/chat generation, and conversation logic unchanged.
