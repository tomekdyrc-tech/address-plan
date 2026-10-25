"""Export dispatch and atomic document storage for CLI and future web use."""

from pathlib import Path
from typing import Literal, TypeAlias

from adresplan.application.files import write_atomic
from adresplan.application.project_json import InputIssue, ProjectJSONError, dumps_project
from adresplan.core.models import Project
from adresplan.export.csv_ import dumps_csv
from adresplan.export.markdown import dumps_markdown
from adresplan.i18n import tr

ExportFormat: TypeAlias = Literal["csv", "md", "json", "xlsx", "docx", "cisco", "mikrotik"]
ReportProfile: TypeAlias = Literal["full", "brief"]


def export_document(project: Project, format: ExportFormat, profile: ReportProfile = "full") -> str:
    if profile == "brief" and format == "md":
        from adresplan.export.brief import dumps_brief_markdown

        return dumps_brief_markdown(project)
    if format == "csv":
        return dumps_csv(project)
    if format == "md":
        return dumps_markdown(project)
    if format == "json":
        return dumps_project(project)
    if format in ("cisco", "mikrotik"):
        from adresplan.export.config import dumps_config

        return dumps_config(project, format)
    raise ValueError("unsupported export format")


def export_bytes(project: Project, format: ExportFormat, profile: ReportProfile = "full") -> bytes:
    if profile == "brief" and format in ("xlsx", "docx"):
        from adresplan.export.brief import brief_office

        return brief_office(project, format)
    if format == "xlsx":
        from adresplan.export.office import dumps_xlsx

        return dumps_xlsx(project)
    if format == "docx":
        from adresplan.export.office import dumps_docx

        return dumps_docx(project)
    return export_document(project, format, profile).encode(
        "utf-8-sig" if format == "csv" else "utf-8"
    )


def save_document(path: str | Path, text: str | bytes, format: ExportFormat) -> None:
    """CSV files use a UTF-8 BOM; stdout and other formats use plain UTF-8."""
    target = Path(path)
    try:
        content = (
            text
            if isinstance(text, bytes)
            else text.encode("utf-8-sig" if format == "csv" else "utf-8")
        )
        write_atomic(target, content)
    except OSError as error:
        raise ProjectJSONError(
            (
                InputIssue(
                    (),
                    "file_write_error",
                    tr(
                        "Nie można zapisać eksportu {path}: {reason}.",
                        path=target,
                        reason=error.strerror,
                    ),
                ),
            )
        ) from error
