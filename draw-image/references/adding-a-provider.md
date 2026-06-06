# Adding a new provider

Three approaches, easiest first. Pick the one that matches the provider's
API shape.

## 1. It's OpenAI-compatible (most common)

If the provider's API matches OpenAI's `POST /v1/images/generations`
endpoints, just add a block:

```yaml
  replicate:
    type: openai-compatible
    base_url: https://api.replicate.com/v1   # or whatever the provider's base is
    api_key: ${REPLICATE_API_KEY}
    model: black-forest-labs/flux-schnell
    default_size: 1024x1024
```

Save the file, then:

```bash
python scripts/draw.py --validate-config
```

Done.

## 2. Semi-auto: extract from a PDF

If the provider ships a PDF API doc (most Chinese providers do):

```bash
python scripts/auto_add_provider.py ~/Downloads/provider-api.pdf \
    --provider-name newprov
```

The script prints a YAML block. The block has TODO markers for things the
script can't infer (exact field names, authentication header, etc.).

Fill in the TODOs. You can do this yourself, or paste the block to an AI
agent along with the PDF and ask the agent to complete it. Then append
the block to `config.yaml` and run `--validate-config`.

## 3. Manual: write the YAML yourself

Open `references/provider-schema.md` for the full field reference.

Key questions to answer from the provider's docs:

1. **What's the request URL?** It's usually `<base>/v1/images/generations`
   or `<base>/api/v3/images/generations`. Set `base_url` to everything
   *before* that path.
2. **How is auth done?** Most use `Authorization: Bearer <key>`. Some use
   `x-api-key: <key>`. Set `auth_header_name` accordingly.
3. **What fields does the request take?** At minimum: `model` and `prompt`.
   Common extras: `size`, `n`, `image`, `response_format`. Use
   `request_fields` to rename them if the provider's names differ.
4. **What fields does the response return?** `data[]` with `url` and/or
   `b64_json` is the OpenAI default. Some providers nest under `output` or
   `images`. Use `response_fields` for simple renames, or write a custom
   provider subclass in `lib/providers/` for complex shapes.
5. **Is it text-only or does it accept reference images?** Look for
   `image` or `images` in the docs. If absent, the `--image` flag will
   be rejected at the server.

## 4. Custom Python provider (last resort)

If the provider has a non-standard API shape (ComfyUI queue+websocket, AWS
Bedrock, etc.), drop a Python file in `lib/providers/`:

```python
# lib/providers/my_comfy.py
from ..base import Provider
from ..registry import register
from typing import Any, Dict


@register
class ComfyUIProvider(Provider):
    name = "comfyui"

    def build_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # ... build your custom payload
        return {"prompt": prompt}

    def parse_response(self, data: Dict[str, Any]) -> "GenerateResponse":
        # ... parse the custom response
        ...

    def validate_size(self, size):
        return size or self.config.default_size or "1024x1024"
```

Then add the import in `lib/providers/__init__.py` so it gets registered
when the skill loads.

## Validation

Always finish with:

```bash
python scripts/draw.py --validate-config
```

This runs `build_payload` for every provider without sending the request.
If a provider's payload is malformed, you'll see a clear error pointing
at the failing provider and field.
