"""CLI for planning, subnet calculation and explicit project freezing (Polish or English)."""

from __future__ import annotations

import argparse
import io
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from adresplan import __version__
from adresplan.application.console import (
    calculation_error,
    format_calculation,
    format_finding,
    format_plan,
    safe_text,
)
from adresplan.application.exporting import export_bytes, export_document, save_document
from adresplan.application.project_json import (
    ProjectJSONError,
    dumps_project,
    load_project,
    save_project,
)
from adresplan.core.calc import CalculationError, calculate, preview_subnets
from adresplan.core.freeze import freeze
from adresplan.core.models import FindingLevel, Plan, Project
from adresplan.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    Language,
    language,
    parse_language,
    tr,
    use_language,
)
from adresplan.store.sqlite import StoreError

# argparse writes these English phrases itself; Polish runs replace them.
ARGPARSE_POLISH = {
    "usage:": "Użycie:",
    "positional arguments:": "Argumenty:",
    "options:": "Opcje:",
    "the following arguments are required:": "Brakuje wymaganych argumentów:",
    "unrecognized arguments:": "Nieznane argumenty:",
    "invalid choice:": "niedozwolona wartość:",
    "choose from": "dozwolone:",
    "not allowed with argument": "nie można łączyć z argumentem",
    "expected at least one argument": "oczekiwano co najmniej jednej wartości",
    "expected one argument": "oczekiwano jednej wartości",
}


def _argparse_text(text: str, *, first_only: bool = False) -> str:
    if language() != "pl":
        return text
    for original, polish in ARGPARSE_POLISH.items():
        text = text.replace(original, polish, 1 if first_only else -1)
    return text


class LocalizedArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        return _argparse_text(super().format_help())

    def format_usage(self) -> str:
        return _argparse_text(super().format_usage(), first_only=True)

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(
            2,
            tr("Błąd argumentów: {message}", message=safe_text(_argparse_text(message)))
            + "\n"
            + tr("Pomoc: {command} --help", command=self.prog)
            + "\n",
        )


def _integer(value: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(tr("Wymagana jest liczba całkowita.")) from error


def _help(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-h", "--help", action="help", help=tr("Pokaż pomoc i zakończ."))


def _parser() -> LocalizedArgumentParser:
    parser = LocalizedArgumentParser(
        prog="adresplan",
        add_help=False,
        allow_abbrev=False,
        description=tr("Address Plan — lokalny planer adresacji IPv4 i IPv6."),
        epilog=tr("Interfejs przeglądarkowy: adresplan serve"),
    )
    _help(parser)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help=tr("Pokaż wersję programu."),
    )
    parser.add_argument(
        "--lang",
        choices=LANGUAGES,
        default=DEFAULT_LANGUAGE,
        help=tr("Język komunikatów i raportów (pl lub en); także zmienna ADRESPLAN_LANG."),
    )
    commands = parser.add_subparsers(
        dest="command",
        title=tr("Polecenia"),
        metavar=tr("POLECENIE"),
        parser_class=LocalizedArgumentParser,
    )
    serve = commands.add_parser(
        "serve",
        add_help=False,
        allow_abbrev=False,
        help=tr("Uruchom lokalny interfejs w przeglądarce."),
    )
    _help(serve)
    serve.add_argument(
        "--database", type=Path, help=tr("Ścieżka pliku SQLite (nadpisuje ADRESPLAN_DB).")
    )
    serve.add_argument(
        "--port", type=_integer, default=8000, help=tr("Port localhost (domyślnie 8000).")
    )
    serve.add_argument(
        "--host",
        choices=("127.0.0.1", "0.0.0.0"),
        default="127.0.0.1",
        help=tr("Adres nasłuchu. 0.0.0.0 służy do jawnego uruchomienia w kontenerze."),
    )
    plan = commands.add_parser(
        "plan",
        add_help=False,
        allow_abbrev=False,
        help=tr("Wczytaj projekt JSON i oblicz plan."),
        description=tr("Oblicz plan z danych projektu. Migawka wyniku z JSON jest ignorowana."),
    )
    _help(plan)
    plan.add_argument(
        "project",
        type=Path,
        metavar=tr("PROJEKT.json"),
        help=tr("Plik projektu w formacie schema_version=1."),
    )
    plan.add_argument(
        "--json",
        action="store_true",
        help=tr("Wypisz projekt i świeży plan jako JSON, bez tekstowej tabeli."),
    )
    plan.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar=tr("WYNIK.json"),
        help=tr("Zapisz projekt i plan jako JSON; istniejący plik zostanie zastąpiony."),
    )
    plan.add_argument(
        "--show-free",
        action="store_true",
        help=tr("Pokaż wszystkie wolne bloki w tabeli tekstowej."),
    )
    plan.add_argument(
        "--verbose",
        action="store_true",
        help=tr("Pokaż również komunikaty informacyjne na stderr."),
    )
    calc = commands.add_parser(
        "calc",
        add_help=False,
        allow_abbrev=False,
        help=tr("Oblicz parametry sieci lub podział na podsieci."),
        description=tr(
            "Przykłady: calc 192.168.1.10/24; calc 192.168.1.10 255.255.255.0; calc 2001:db8::/48."
        ),
    )
    _help(calc)
    calc.add_argument(
        "address",
        nargs="+",
        metavar=tr("ADRES"),
        help=tr("Adres/prefiks albo adres IPv4 i maska/wildcard, także w cudzysłowie."),
    )
    split = calc.add_mutually_exclusive_group()
    split.add_argument(
        "--split",
        type=_integer,
        metavar="N",
        help=tr("Podziel na N równych podsieci; N musi być potęgą dwójki."),
    )
    split.add_argument(
        "--new-prefix", type=_integer, metavar="X", help=tr("Podziel na podsieci o prefiksie /X.")
    )
    calc.add_argument(
        "--limit",
        type=_integer,
        default=None,
        metavar="1–256",
        help=tr("Maksymalna liczba wierszy podziału (domyślnie 256)."),
    )
    frozen = commands.add_parser(
        "freeze",
        add_help=False,
        allow_abbrev=False,
        help=tr("Zamroź przydziały kompletnego planu i zapisz JSON."),
        description=tr(
            "Przypnij aktualne IPv4/IPv6 i infrastrukturę. Plan z błędami nie zostanie zapisany."
        ),
    )
    _help(frozen)
    frozen.add_argument(
        "project", type=Path, metavar=tr("PROJEKT.json"), help=tr("Projekt źródłowy.")
    )
    frozen.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        metavar=tr("ZAMROŻONY.json"),
        help=tr("Plik docelowy JSON; istniejący plik zostanie zastąpiony."),
    )
    frozen.add_argument(
        "--verbose",
        action="store_true",
        help=tr("Pokaż również komunikaty informacyjne na stderr."),
    )
    export = commands.add_parser(
        "export",
        add_help=False,
        allow_abbrev=False,
        help=tr("Wyeksportuj CSV, Markdown, JSON, XLSX, DOCX albo konfigurację urządzeń."),
        description=tr(
            "Oblicz świeży plan i wyeksportuj go. Niekompletny wynik jest oznaczony i zwraca kod 1."
        ),
    )
    _help(export)
    export.add_argument(
        "project", type=Path, metavar=tr("PROJEKT.json"), help=tr("Projekt źródłowy JSON.")
    )
    export.add_argument(
        "-f",
        "--format",
        required=True,
        choices=("csv", "md", "json", "xlsx", "docx", "cisco", "mikrotik"),
        help=tr(
            "Format dokumentu: csv, md, json, xlsx, docx "
            "albo konfiguracja startowa cisco / mikrotik."
        ),
    )
    export.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar=tr("PLIK"),
        help=tr("Plik docelowy; wymagany dla XLSX/DOCX. Formaty tekstowe mogą trafić na stdout."),
    )
    export.add_argument(
        "--verbose", action="store_true", help=tr("Pokaż również informacje na stderr.")
    )
    return parser


def _diagnostics(project: Project, plan: Plan, *, verbose: bool) -> None:
    for finding in plan.findings:
        if finding.level is not FindingLevel.INFO or verbose:
            print(format_finding(finding, project), file=sys.stderr, flush=True)


def _configure_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def _language(argv: Sequence[str]) -> tuple[Language, list[str]]:
    """Read --lang anywhere before building the parser, so help text is already translated.

    A valid option is removed from the arguments; an invalid one stays for argparse to report.
    """
    for index, item in enumerate(argv):
        value = argv[index + 1] if item == "--lang" and index + 1 < len(argv) else None
        if item.startswith("--lang="):
            value = item.partition("=")[2]
        chosen = parse_language(value)
        if chosen is not None:
            width = 2 if item == "--lang" else 1
            return chosen, [*argv[:index], *argv[index + width :]]
    return parse_language(os.environ.get("ADRESPLAN_LANG")) or DEFAULT_LANGUAGE, list(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Return 0 on success/warnings, 1 on an incomplete plan, 2 on invalid input/I/O."""
    _configure_encoding()
    language, arguments = _language(sys.argv[1:] if argv is None else argv)
    with use_language(language):
        return _run(arguments)


def _run(arguments: list[str]) -> int:
    parser = _parser()
    args = parser.parse_args(arguments)
    try:
        if args.command is None:
            parser.print_help()
            return 0
        if args.command == "calc":
            result = calculate(" ".join(args.address))
            limit = 256 if args.limit is None else args.limit
            if not 1 <= limit <= 256:
                raise CalculationError("invalid_preview_limit")
            preview = None
            if args.split is not None or args.new_prefix is not None:
                preview = preview_subnets(
                    result.network, count=args.split, new_prefix=args.new_prefix, limit=limit
                )
            elif args.limit is not None:
                parser.error(tr("--limit wymaga podziału przez --split albo --new-prefix."))
            print(format_calculation(result, preview), flush=True)
            return 0
        if args.command == "serve":
            if not 1 <= args.port <= 65535:
                parser.error(tr("Port musi należeć do zakresu 1–65535."))
            import uvicorn

            from adresplan.store.sqlite import database_path
            from adresplan.web.app import create_app

            path = database_path(args.database)
            print(
                tr("Baza projektów: {path}", path=path)
                + "\n"
                + tr("Otwórz: {url}", url=f"http://127.0.0.1:{args.port}"),
                flush=True,
            )
            uvicorn.run(create_app(path), host=args.host, port=args.port, log_level="info")
            return 0
        state = load_project(args.project)
        if args.command == "export":
            if args.format in ("xlsx", "docx") and args.output is None:
                parser.error(tr("Eksport XLSX/DOCX wymaga --output PLIK."))
            if (
                args.output is not None
                and args.format != "json"
                and args.project.resolve() == args.output.resolve()
            ):
                parser.error(
                    tr("Eksport CSV/Markdown wymaga innego pliku niż źródłowy projekt JSON.")
                )
            text = (
                export_bytes(state.project, args.format)
                if args.format in ("xlsx", "docx")
                else export_document(state.project, args.format)
            )
            if args.output is not None:
                save_document(args.output, text, args.format)
                print(
                    tr(
                        "Zapisano eksport {format}: {path}",
                        format=args.format,
                        path=safe_text(args.output),
                    ),
                    file=sys.stderr,
                    flush=True,
                )
            else:
                if isinstance(sys.stdout, io.TextIOWrapper):
                    sys.stdout.reconfigure(newline="")
                print(text, end="", flush=True)
            _diagnostics(state.project, state.plan, verbose=args.verbose)
            return 0 if state.plan.is_complete else 1
        if args.command == "plan":
            if args.output is not None:
                save_project(args.output, state.project)
                print(
                    tr("Zapisano JSON: {path}", path=safe_text(args.output)),
                    file=sys.stderr,
                    flush=True,
                )
            print(
                dumps_project(state.project)
                if args.json
                else format_plan(state.project, state.plan, show_free=args.show_free),
                end="" if args.json else "\n",
                flush=True,
            )
            _diagnostics(state.project, state.plan, verbose=args.verbose)
            return 0 if state.plan.is_complete else 1
        if not state.plan.is_complete:
            print(
                tr("Nie można zamrozić niekompletnego planu. Plik docelowy nie został zmieniony."),
                file=sys.stderr,
                flush=True,
            )
            _diagnostics(state.project, state.plan, verbose=args.verbose)
            return 1
        frozen_project = freeze(state.project, state.plan)
        save_project(args.output, frozen_project)
        print(
            tr(
                "Zamrożono adresy IPv4/IPv6 i infrastrukturę. Zapisano: {path}",
                path=safe_text(args.output),
            ),
            flush=True,
        )
        _diagnostics(state.project, state.plan, verbose=args.verbose)
        return 0
    except ProjectJSONError as error:
        for issue in error.issues:
            print(
                tr(
                    "Błąd danych [{code}] {location}: {message}",
                    code=issue.code,
                    location=safe_text(issue.location),
                    message=safe_text(issue.message),
                ),
                file=sys.stderr,
                flush=True,
            )
        return 2
    except CalculationError as error:
        print(
            tr(
                "Błąd kalkulatora [{code}]: {message}",
                code=error.code,
                message=calculation_error(error),
            ),
            file=sys.stderr,
            flush=True,
        )
        return 2
    except BrokenPipeError:
        return 1
    except StoreError as error:
        print(
            tr("Błąd bazy projektów: {message}", message=safe_text(error)),
            file=sys.stderr,
            flush=True,
        )
        return 2
    except OSError as error:
        print(
            tr("Błąd odczytu/zapisu: {message}", message=safe_text(error.strerror or error)),
            file=sys.stderr,
            flush=True,
        )
        return 2
    except KeyboardInterrupt:
        print(tr("Przerwano."), file=sys.stderr, flush=True)
        return 130
