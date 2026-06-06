# OpenAI-compatible (gpt-image-1, dall-e-3, ...) notes

- **Endpoint:** `POST https://api.openai.com/v1/images/generations`
- **Model ids:** `gpt-image-1`, `dall-e-3`, `dall-e-2`, etc.
- **Auth:** `Authorization: Bearer $OPENAI_API_KEY`.
- **Sizes:** OpenAI has fixed sizes per model.
  - `gpt-image-1`: `1024x1024`, `1024x1536`, `1536x1024`, `auto`
  - `dall-e-3`: `1024x1024`, `1792x1024`, `1024x1792`
  - `dall-e-2`: `256x256`, `512x512`, `1024x1024`
- **Output format:** PNG by default. Set `output_format` per request.
  `gpt-image-1` supports `png`, `jpeg`, `webp`.
- **Reference image:** `gpt-image-1` accepts a single input image via the
  `image` field (URL or data URI). Not supported on dall-e-3.
- **Sequential/group:** not supported on OpenAI's API.

## Common errors

- `invalid_api_key` → bad key. Regenerate at https://platform.openai.com/api-keys
- `billing_hard_limit_reached` → top up at https://platform.openai.com/account/billing
- `content_policy_violation` → rephrase the prompt.
