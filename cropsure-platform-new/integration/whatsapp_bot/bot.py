"""CropSure WhatsApp bot (Twilio webhook).

This service is intentionally small and self-contained:
- Receives inbound WhatsApp messages from Twilio.
- Responds with TwiML (no Twilio SDK required).
- Optionally calls the main backend for live data.

Environment variables:
- BACKEND_URL: Base URL for the CropSure backend (default: http://backend:8000)
- BOT_NAME: Display name used in help text
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse, Response


logger = logging.getLogger("cropsure.whatsapp_bot")


@dataclass(frozen=True)
class BotConfig:
	backend_url: str = "http://backend:8000"
	bot_name: str = "CropSure Bot"

	@staticmethod
	def from_env() -> "BotConfig":
		import os

		return BotConfig(
			backend_url=os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/"),
			bot_name=os.getenv("BOT_NAME", "CropSure Bot"),
		)


def _twiml(message: str) -> str:
	safe = html.escape(message)
	return (
		"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
		"<Response><Message>"
		f"{safe}"
		"</Message></Response>"
	)


async def _backend_get_json(path: str, cfg: BotConfig) -> Any:
	url = f"{cfg.backend_url}{path}"
	async with httpx.AsyncClient(timeout=10) as client:
		resp = await client.get(url)
		resp.raise_for_status()
		return resp.json()


def _help_text(cfg: BotConfig) -> str:
	return (
		f"{cfg.bot_name} commands:\n"
		"- help\n"
		"- health (backend status)\n"
		"- farms (list enrolled farms)\n"
		"- farm <id> (farm details)\n"
		"\nTip: Reply with 'farms' to see IDs."
	)


def _summarize_farms(farms: list[dict[str, Any]]) -> str:
	if not farms:
		return "No farms enrolled yet."

	lines: list[str] = [f"Farms: {len(farms)}"]
	for f in farms[:10]:
		fid = str(f.get("id", ""))
		name = str(f.get("farmer_name", ""))
		crop = str(f.get("crop_type", ""))
		village = str(f.get("village", ""))
		health = str(f.get("health_status", "unknown"))
		lines.append(f"- {fid[:8]}… | {name} | {crop} | {village} | {health}")
	if len(farms) > 10:
		lines.append(f"…and {len(farms) - 10} more")
	return "\n".join(lines)


def _summarize_farm(farm: dict[str, Any]) -> str:
	fid = str(farm.get("id", ""))
	name = str(farm.get("farmer_name", ""))
	phone = str(farm.get("phone_number", ""))
	village = str(farm.get("village", ""))
	crop = str(farm.get("crop_type", ""))
	area = farm.get("area_acres")
	health = str(farm.get("health_status", "unknown"))
	policy = farm.get("policy")
	policy_status = policy.get("status") if isinstance(policy, dict) else None

	return (
		f"Farm {fid}\n"
		f"Farmer: {name}\n"
		f"Phone: {phone}\n"
		f"Village: {village}\n"
		f"Crop: {crop}\n"
		f"Area: {area} acres\n"
		f"Health: {health}\n"
		f"Policy: {policy_status or 'n/a'}"
	)


app = FastAPI(title="CropSure WhatsApp Bot", version="1.0.0")


@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
	return "ok"


@app.post("/twilio/webhook")
async def twilio_webhook(
	Body: str = Form(default=""),
	From: str = Form(default=""),  # noqa: N803 (Twilio form field)
) -> Response:
	cfg = BotConfig.from_env()
	text = (Body or "").strip()
	sender = (From or "").strip()

	logger.info("Inbound WhatsApp from %s: %s", sender, text)

	if not text or text.lower() in {"hi", "hello", "hey"}:
		return Response(content=_twiml(_help_text(cfg)), media_type="application/xml")

	cmd = text.strip().split()
	head = cmd[0].lower()

	try:
		if head in {"help", "menu"}:
			message = _help_text(cfg)

		elif head in {"health", "status"}:
			backend_health = await _backend_get_json("/health", cfg)
			message = f"Backend health: {backend_health}"

		elif head in {"farms", "list"}:
			farms = await _backend_get_json("/farms", cfg)
			if not isinstance(farms, list):
				message = "Backend returned unexpected farms payload."
			else:
				message = _summarize_farms(farms)

		elif head == "farm":
			if len(cmd) < 2:
				message = "Usage: farm <id>"
			else:
				farm_id = cmd[1]
				farm = await _backend_get_json(f"/farms/{farm_id}", cfg)
				if not isinstance(farm, dict):
					message = "Backend returned unexpected farm payload."
				else:
					message = _summarize_farm(farm)

		else:
			message = (
				"Unknown command. Reply with 'help'.\n\n"
				+ _help_text(cfg)
			)

	except httpx.HTTPStatusError as e:
		logger.warning("Backend HTTP error: %s", e)
		message = "Sorry — backend is unavailable right now. Try again later."
	except Exception as e:
		logger.exception("Bot error: %s", e)
		message = "Sorry — something went wrong. Reply with 'help'."

	return Response(content=_twiml(message), media_type="application/xml")


if __name__ == "__main__":
	import uvicorn

	uvicorn.run(app, host="0.0.0.0", port=8080)

