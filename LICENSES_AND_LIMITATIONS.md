# Licenses and limitations

## Software

LiveTalking source code is distributed under Apache License 2.0; the repository
`LICENSE` remains authoritative. Third-party Python, JavaScript, browser and
media dependencies retain their own licenses.

## Wav2Lip and supplied assets

The upstream Wav2Lip repository states that its code and pretrained results are
for personal, research and non-commercial use because of the LRS2 training
dataset. The downloaded Wav2Lip256 checkpoint does not include separate
commercial rights. It must not be used for commercial orders without written
rights covering the model and training data.

The default Avatar archive contains no performer release, likeness license or
commercial-use grant. Replace it with media whose subject, copyright and
commercial permissions you control.

Exact sources and hashes are recorded in `MODEL_SOURCES.md`.

## Online services

EdgeTTS depends on Microsoft's online speech service and network availability.
The operator is responsible for complying with the service terms, regional
rules and content restrictions. OpenAI-compatible API providers have separate
terms, billing, retention and privacy policies; no real provider was certified
by this project.

## Technical boundaries

- Default capacity is one browser session.
- 720×960 at 25 FPS is the accepted profile; 1080×1440 is experimental.
- WebRTC LAN access is not encrypted by this local HTTP setup and is disabled by
  default.
- Browser automation, FPS readings and mock API tests do not replace legal,
  real-provider or subjective lip-sync acceptance.
- MuseTalk is not bundled. LiveTalking's avatar registry remains the replacement
  point for a future, separately licensed implementation.

