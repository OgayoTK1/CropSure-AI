"""Placeholder auth middleware — no auth required for hackathon demo."""

from fastapi import Request


async def optional_auth(request: Request, call_next):
    """Pass-through middleware. Extend here to add API key or JWT auth."""
    response = await call_next(request)
    return response
