# Self-hosted ComfyUI (no built-in support)

ComfyUI is a local Stable Diffusion frontend. It has a queue-based HTTP API
on port 8188 by default. **This skill does not ship a built-in ComfyUI
provider** because its API surface is very different from cloud providers
(workflow JSON submission + polling for completion, not a single
request/response call).

## To add ComfyUI support

You'll need to write a small custom provider. The shape of the API:

1. `POST http://127.0.0.1:8188/prompt` with the workflow JSON. Returns
   `{prompt_id: "..."}`.
2. Poll `GET http://127.0.0.1:8188/history/<prompt_id>` until done.
3. The result is on disk in ComfyUI's output directory.

A minimal provider in `lib/providers/comfyui.py`:

```python
import time, json
import urllib.request
from pathlib import Path
from ..base import Provider
from ..registry import register
from ..response import GenerateResponse, ImageResult


@register
class ComfyUIProvider(Provider):
    name = "comfyui"

    def build_payload(self, prompt, **kwargs):
        # Build your ComfyUI workflow JSON here.
        # Most users export a workflow from the ComfyUI web UI and modify it.
        return {"prompt": prompt}

    def parse_response(self, data):
        # ... parse whatever shape the API returns
        ...

    def validate_size(self, size):
        return size or self.config.default_size or "1024x1024"
```

Then in `config.yaml`:

```yaml
  comfyui:
    type: comfyui
    base_url: http://127.0.0.1:8188
    requires_api_key: false
    model: default-workflow
    default_size: 1024x1024
```

The skill's main loop (save to `~/Pictures/draw-image/`, error handling,
retries) will work as long as `build_payload`, `parse_response`, and
`validate_size` are correct.

## Why not built-in?

Every ComfyUI workflow is different (custom nodes, custom schedulers, etc.).
A built-in provider would have to assume a specific workflow and would
break for anyone using a different setup. The custom provider path is
clearer and lets you adapt to your own installation.
