"""Service package marker.

Avoid eager imports here to prevent circular import issues between
`agents.pipeline` and `services.pipeline_service` during test discovery.
"""

__all__: list[str] = []

