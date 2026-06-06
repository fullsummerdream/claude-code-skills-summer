# Aliyun Bailian (DashScope) notes

- **Endpoint:** `POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis`
  (the skill's default `openai-compatible` mapping points at
  `https://dashscope.aliyuncs.com/api/v1` + `/images/generations` which works
  for newer models; older models may need the full path).
- **Model ids:** `qwen-image-plus`, `qwen-image`, `wanx-v1`, etc.
- **Auth:** `Authorization: Bearer $ALIYUN_BAILIAN_API_KEY`. The key is
  created in the Bailian console.
- **Sizes:** Bailian models accept preset sizes (`1024x1024`, `720x1280`,
  `1280x720`, etc.). Check the model's docs for the full list.
- **Reference image:** `qwen-image` supports image-to-image. Pass via the
  `image` field as a URL or data URI.

## Common errors

- `InvalidParameter` → check `model:` and `size:` against the model docs.
- `QuotaExceeded` → top up at https://bailian.console.aliyun.com/
- `DataInspectionFailed` → rephrase the prompt (Bailian runs content moderation).
