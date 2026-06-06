# volcengine (Doubao-Seedream) notes

- **Endpoint:** `POST https://ark.cn-beijing.volces.com/api/v3/images/generations`
- **Model id:** `doubao-seedream-5-0-260128` (or any custom endpoint id you
  created in the ARK console).
- **Auth:** `Authorization: Bearer $ARK_API_KEY`. ARK API keys are
  long-lived; rotate them in the console.
- **Size constraints** (5.0-lite): total pixels must be in
  `[3,686,400, 16,777,216]`, aspect ratio `[1/16, 16]`. Resolutions `2K`,
  `3K`, `4K` are also accepted (model picks the actual size).
- **Reference images:** `image: <url | data-uri | string>`. Up to 14.
  Single string for one image, array for multiple.
- **Sequential generation:** `sequential_image_generation: "auto"` plus
  `sequential_image_generation_options: {max_images: N}`. Max 15.
- **Streaming:** the server supports SSE. Use `python scripts/draw.py --stream`.
  Requires `pip install aiohttp`.
- **Tools:** `tools: [{type: "web_search"}]` enables internet search
  before generating. Increases latency.
- **Optimize prompt:** `optimize_prompt_options: {mode: "standard"}`.
  `fast` mode is not supported on 5.0-lite.
- **Watermark:** default `true`. Set `false` to disable.
- **Output format:** `jpeg` (default) or `png`. 5.0-lite only.

## Common errors

- `InvalidEndpointOrModel.NotFound` → wrong `model:` value. Use the
  `ep-...` id from your console, not the human-readable name.
- `image size must be at least 3686400 pixels` → use `--size 2K` or larger.
- `SensitiveContentBlocked` → rephrase the prompt.
