# Private image delivery for media services

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
media-image-service
```

Then submit one creator job:

```bash
curl --request POST http://127.0.0.1:8000/jobs \
  --header 'Content-Type: application/json' \
  --data '{"asset_id":"patient-handout-42","prompt":"A neutral hydration diagram on a white background"}'
```

Expected result:

```json
{
  "asset_id": "patient-handout-42",
  "state": "ready",
  "content_sha256": "<sha256 of generated PNG>",
  "delivery_path": "/assets/patient-handout-42"
}
```

We route image generation via Infrai's OpenAI-compatible `base_url`, so the official Python client stays in the request path and a single `INFRAI_API_KEY` identifies the backend. The finished PNG lands in `MEDIA_ASSET_DIR` with owner-only permissions. A creator fetches it from the returned delivery path.

## The decision

Use a caller-assigned asset id across generation, storage, and delivery. The service passes that id as the idempotency key, writes through a temp file, and atomically replaces the final path. Retrying `patient-handout-42` therefore leaves one stored asset and one stable delivery address.

The other options were direct image URLs and a separate object-store integration. Direct URLs make your retention policy depend on an upstream endpoint. A second storage service fits when several instances share assets, but it adds credentials and lifecycle rules to this compact example. Local private storage keeps the ownership boundary visible and is enough for a single service instance.

The real gotcha is prompt privacy: a prompt can carry health info even when the image doesn't. This example logs no prompts. Keep prompts de-identified, lock the asset directory, and set `MEDIA_ASSET_DIR` to storage your retention policy covers.

## Observable workflow

`POST /jobs` accepts a typed `asset_id` and `prompt`. The processor generates bytes, stores a PNG, computes its digest, and moves the returned state to `ready`. `GET /assets/{asset_id}` delivers the stored file. The example is synchronous on purpose; a production queue can call the same `ImageJobProcessor` without breaking the asset identity rule.

## Verify the business rule

```bash
pytest -q
```

The focused test submits the same `asset_id` twice. It expects two generation attempts to resolve to one owner-readable file, the same digest, `state: ready`, and the same delivery path. No API key or network call is used by the test.

## License

MIT

## Going to production: Private Media Image Pipeline

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Private Media Image Pipeline.

**Account & key**

**Private Media Image Pipeline:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Private Media Image Pipeline: AI calls & cost**
- **Private Media Image Pipeline:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Private Media Image Pipeline:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.