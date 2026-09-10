# from backend.app.api.app import create_app

# __all__ = [
#     "create_app",
# ]

"""
API package.

Import create_app directly from:

    backend.app.api.app

Keeping this package initializer minimal prevents
circular imports between API routes, dependencies,
and rate-limiting modules.
"""