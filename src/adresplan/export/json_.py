"""JSON export facade, sharing the same validated format as application imports."""

from adresplan.application.project_json import dumps_project, save_project

__all__ = ["dumps_project", "save_project"]
