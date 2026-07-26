# Model sources

This file records the exact stage 2 assets deployed on 2026-07-26.

## Wav2Lip256 checkpoint

- Model name: LiveTalking Wav2Lip256
- Official source listed by LiveTalking:
  <https://drive.google.com/drive/folders/1FOC_MD6wdogyyX_7V1d4NDIO7P9NlSAJ?usp=sharing>
- Google Drive file ID: `1wu6XujFL9rF-0P2l44G6kpeapeY0cME7`
- Downloaded file name: `wav2lip256.pth`
- Target file: `models/wav2lip.pth`
- File size: `214,670,409 bytes` (`204.73 MiB`)
- SHA-256:
  `b22d7ac86295df667644b17254dc71250c2600b89e20403e90e58812450bc173`
- License: no separate license or model card is included with the downloaded
  weight. The LiveTalking source repository uses Apache-2.0, but that software
  license does not by itself establish the training-data or weight rights.
- Commercial use: **not approved by the available asset documentation**.
  The upstream open-source Wav2Lip project explicitly limits its repository and
  pretrained-model results to personal, research and non-commercial use because
  of the LRS2 training dataset. Obtain separate written commercial rights or use
  a commercially licensed replacement before commercial deployment.
- Upstream license notice:
  <https://github.com/Rudrabha/Wav2Lip#license-and-citation>

## Default Wav2Lip256 avatar

- Asset name: LiveTalking default Avatar `wav2lip256_avatar1`
- Official source listed by LiveTalking:
  <https://drive.google.com/drive/folders/1FOC_MD6wdogyyX_7V1d4NDIO7P9NlSAJ?usp=sharing>
- Google Drive file ID: `1aU-9SMEAZWN00hbvAGlRHG2iB17r9dEW`
- Downloaded file name: `wav2lip256_avatar1.tar.gz`
- Target directory: `data/avatars/wav2lip256_avatar1`
- Compressed size: `353,005,497 bytes` (`336.65 MiB`)
- Uncompressed file payload: `377,313,625 bytes` in `1,101` files
- SHA-256:
  `8e8c82bf973b91db799ed8b557d1b869438e094bcd1b0cf0bd72b208d5329369`
- License and likeness rights: no separate license, model card, performer
  release or commercial likeness permission is included in the archive.
- Commercial use: **not approved by the available documentation**. Replace the
  default avatar with media for which the operator has explicit likeness and
  commercial-use rights before commercial deployment.

## Verified command

The current README and current code accept the same command:

```powershell
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1
```

The project launcher adds the explicit local defaults for EdgeTTS and port 8010:

```powershell
.\start.ps1
```

The model weights and prepared Avatar data are excluded from Git by
`.gitignore`.
