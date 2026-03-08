"""
API layer — Central router. Sub-routers are attached in api/routes.py via register_routes().
"""
from fastapi import APIRouter
api_router = APIRouter()
