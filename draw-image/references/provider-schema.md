# Provider YAML schema

A single provider block in `config.yaml` has these fields. All are validated
by Pydantic v2 when the skill loads the config.

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `type` | string | yes | — | One of the built-in types: `volcengine`, `openai-compatible`, `aliyun-bailian`. For new services, `openai-compatible` is the right default. |
| `base_url` | string | yes | — | The provider's API root. No trailing slash. |
| `api_key` | string | yes (unless `requires_api_key: false`) | — | Either a literal key or `${ENV_VAR}` to pull from the environment. |
| `model` | string | yes | — | The model id (or endpoint id, for volcengine custom endpoints). |
| `default_size` | string | no | provider-specific | `WxH` like `2048x2048`, or a preset like `2K`. |
| `output_format` | string | no | `jpeg` | `jpeg` or `png`. volcengine only — ignored by OpenAI providers. |
| `save_dir` | path | no | `~/Pictures/draw-image` | Per-provider override. `~` is expanded. |
| `timeout` | float | no | `120.0` | HTTP timeout in seconds. |
| `requires_api_key` | bool | no | `true` | Set `false` for local services like ComfyUI. |
| `auth_header_name` | string | no | `Authorization` | Override if the provider uses something else (e.g. `x-api-key`). |
| `request_fields` | object | no | `{}` | Map `{internal_name: provider_field_name}`. Used by `GenericOpenAICompatibleProvider`. |
| `response_fields` | object | no | `{}` | Map for response fields (rare). |
| `extra_params` | object | no | `{}` | Pinned extra fields added to every request. |
| `multi_image` | bool | no | `false` | When `true`, even a single reference image is sent as a list (e.g. `["<url>"]`). Some providers (DashScope) require this. |
| `image_field` | string | no | `image` | Wire field name for reference images. Override if the provider expects a different key (e.g. `image_urls`). |

## Minimal example

```yaml
default_provider: myprov

providers:
  myprov:
    type: openai-compatible
    base_url: https://api.example.com/v1
    api_key: ${MYPROV_API_KEY}
    model: myprov-image-v1
    default_size: 1024x1024
```

## Field mapping example

If the provider's API uses `prompt_text` instead of `prompt` and `output_url`
instead of `url`:

```yaml
  weird_api:
    type: openai-compatible
    base_url: https://api.weird.com/v1
    api_key: ${WEIRD_API_KEY}
    model: weird-image
    request_fields:
      prompt: prompt_text
      response_format: response_type
    response_fields:
      url: output_url
    extra_params:
      style: photorealistic
```

## Multi-image & field override

Some providers require reference images to always be an array, even when
there's only one. Set `multi_image: true`:

```yaml
  myprov:
    type: openai-compatible
    multi_image: true      # single image → ["<url>"] instead of "<url>"
```

If the provider's wire protocol uses a different key for reference images
(e.g. `image_urls` instead of the default `image`), override it:

```yaml
  myprov:
    type: openai-compatible
    image_field: image_urls
```

These options work with all provider types — built-in and generic alike.

## Validation rules

- `api_key` is mandatory unless `requires_api_key: false`.
- `api_key: ${...}` placeholders must be set as environment variables; if not,
  the provider fails at first use with an `AuthenticationError`.
- `default_size` (if set) is validated against the model's pixel-range
  constraints at call time, not at config-load time.
- Unknown fields are **ignored** by the YAML loader (Pydantic by default
  rejects extras; we set `extra = 'ignore'` in the model).
