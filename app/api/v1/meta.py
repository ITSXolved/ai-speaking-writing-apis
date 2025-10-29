"""
Meta endpoints that expose API metadata such as the route list.
"""
from fastapi import APIRouter, Request
from fastapi.routing import APIRoute

router = APIRouter()


@router.get("/meta/endpoints")
async def list_api_endpoints(request: Request):
    """Return a sorted list of available API endpoints."""
    routes = []
    seen = set()

    for route in request.app.routes:
        if not isinstance(route, APIRoute):
            continue

        if not route.path.startswith("/api/"):
            continue

        methods = sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"})
        if not methods:
            continue

        signature = (route.path, tuple(methods))
        if signature in seen:
            continue

        seen.add(signature)
        routes.append({
            "path": route.path,
            "methods": methods,
            "name": route.name,
            "summary": route.summary,
            "tags": route.tags,
        })

    routes.sort(key=lambda item: item["path"])
    return {
        "count": len(routes),
        "routes": routes,
    }
