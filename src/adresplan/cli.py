"""Polish CLI for planning, subnet calculation and explicit project freezing."""

from __future__ import annotations

import argparse
import io
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
from adresplan.store.sqlite import StoreError


class PolishArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "Użycie:", 1)
            .replace("positional arguments:", "Argumenty:")
            .replace("options:", "Opcje:")
        )

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "Użycie:", 1)

    def error(self, message: str) -> NoReturn:
        replacements = {
            "the following arguments are required:": "Brakuje wymaganych argumentów:",
            "unrecognized arguments:": "Nieznane argumenty:",
            "invalid choice:": "niedozwolona wartość:",
            "choose from": "dozwolone:",
            "not allowed with argument": "nie można łączyć z argumentem",
            "expected at least one argument": "oczekiwano co najmniej jednej wartości",
            "expected one argument": "oczekiwano jednej wartości",
        }
        for original, translated in replacements.items():
            message = message.replace(original, translated)
        self.print_usage(sys.stderr)
        self.exit(2, f"Błąd argumentów: {safe_text(message)}\nPomoc: {self.prog} --help\n")


def _integer(value: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Wymagana jest liczba całkowita.") from error


def _help(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-h", "--help", action="help", help="Pokaż pomoc i zakończ.")


def _parser() -> PolishArgumentParser:
    parser = PolishArgumentParser(
        prog="adresplan",
        add_help=False,
        allow_abbrev=False,
        description="Address Plan — lokalny planer adresacji IPv4 i IPv6.",
        epilog="Interfejs przeglądarkowy: adresplan serve",
    )
    _help(parser)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Pokaż wersję programu.",
    )
    commands = parser.add_subparsers(
        dest="command", title="Polecenia", metavar="POLECENIE", parser_class=PolishArgumentParser
    )
    serve = commands.add_parser(
        "serve",
        add_help=False,
        allow_abbrev=False,
        help="Uruchom lokalny interfejs w przeglądarce.",
    )
    _help(serve)
    serve.add_argument(
        "--database", type=Path, help="Ścieżka pliku SQLite (nadpisuje ADRESPLAN_DB)."
    )
    serve.add_argument(
        "--port", type=_integer, default=8000, help="Port localhost (domyślnie 8000)."
    )
    serve.add_argument(
        "--host",
        choices=("127.0.0.1", "0.0.0.0"),
        default="127.0.0.1",
        help="Adres nasłuchu. 0.0.0.0 służy do jawnego uruchomienia w kontenerze.",
    )
    plan = commands.add_parser(
        "plan",
        add_help=False,
        allow_abbrev=False,
        help="Wczytaj projekt JSON i oblicz plan.",
        description="Oblicz plan z danych projektu. Migawka wyniku z JSON jest ignorowana.",
    )
    _help(plan)
    plan.add_argument(
        "project",
        type=Path,
        metavar="PROJEKT.json",
        help="Plik projektu w formacie schema_version=1.",
    )
    plan.add_argument(
        "--json",
        action="store_true",
        help="Wypisz projekt i świeży plan jako JSON, bez tekstowej tabeli.",
    )
    plan.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="WYNIK.json",
        help="Zapisz projekt i plan jako JSON; istniejący plik zostanie zastąpiony.",
    )
    plan.add_argument(
        "--show-free", action="store_true", help="Pokaż wszystkie wolne bloki w tabeli tekstowej."
    )
    plan.add_argument(
        "--verbose", action="store_true", help="Pokaż również komunikaty informacyjne na stderr."
    )
    calc = commands.add_parser(
        "calc",
        add_help=False,
        allow_abbrev=False,
        help="Oblicz parametry sieci lub podział na podsieci.",
        description=(
            "Przykłady: calc 192.168.1.10/24; calc 192.168.1.10 255.255.255.0; calc 2001:db8::/48."
        ),
    )
    _help(calc)
    calc.add_argument(
        "address",
        nargs="+",
        metavar="ADRES",
        help="Adres/prefiks albo adres IPv4 i maska/wildcard, także w cudzysłowie.",
    )
    split = calc.add_mutually_exclusive_group()
    split.add_argument(
        "--split",
        type=_integer,
        metavar="N",
        help="Podziel na N równych podsieci; N musi być potęgą dwójki.",
    )
    split.add_argument(
        "--new-prefix", type=_integer, metavar="X", help="Podziel na podsieci o prefiksie /X."
    )
    calc.add_argument(
        "--limit",
        type=_integer,
        default=None,
        metavar="1–256",
        help="Maksymalna liczba wierszy podziału (domyślnie 256).",
    )
    frozen = commands.add_parser(
        "freeze",
        add_help=False,
        allow_abbrev=False,
        help="Zamroź przydziały kompletnego planu i zapisz JSON.",
        description=(
            "Przypnij aktualne IPv4/IPv6 i infrastrukturę. Plan z błędami nie zostanie zapisany."
        ),
    )
    _help(frozen)
    frozen.add_argument("project", type=Path, metavar="PROJEKT.json", help="Projekt źródłowy.")
    frozen.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        metavar="ZAMROŻONY.json",
        help="Plik docelowy JSON; istniejący plik zostanie zastąpiony.",
    )
    frozen.add_argument(
        "--verbose", action="store_true", help="Pokaż również komunikaty informacyjne na stderr."
    )
    export = commands.add_parser(
        "export",
        add_help=False,
        allow_abbrev=False,
        help="Wyeksportuj CSV, Markdown, JSON, XLSX albo DOCX.",
        description=(
            "Oblicz świeży plan i wyeksportuj go. Niekompletny wynik jest oznaczony i zwraca kod 1."
        ),
    )
    _help(export)
    export.add_argument("project", type=Path, metavar="PROJEKT.json", help="Projekt źródłowy JSON.")
    export.add_argument(
        "-f",
        "--format",
        required=True,
        choices=("csv", "md", "json", "xlsx", "docx"),
        help="Format dokumentu: csv, md, json, xlsx albo docx.",
    )
    export.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PLIK",
        help="Plik docelowy; wymagany dla XLSX/DOCX. Formaty tekstowe mogą trafić na stdout.",
    )
    export.add_argument(
        "--verbose", action="store_true", help="Pokaż również informacje na stderr."
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


def main(argv: Sequence[str] | None = None) -> int:
    """Return 0 on success/warnings, 1 on an incomplete plan, 2 on invalid input/I/O."""
    _configure_encoding()
    parser = _parser()
    args = parser.parse_args(argv)
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
                parser.error("--limit wymaga podziału przez --split albo --new-prefix.")
            print(format_calculation(result, preview), flush=True)
            return 0
        if args.command == "serve":
            if not 1 <= args.port <= 65535:
                parser.error("Port musi należeć do zakresu 1–65535.")
            import uvicorn

            from adresplan.store.sqlite import database_path
            from adresplan.web.app import create_app

            path = database_path(args.database)
            print(f"Baza projektów: {path}\nOtwórz: http://127.0.0.1:{args.port}", flush=True)
            uvicorn.run(create_app(path), host=args.host, port=args.port, log_level="info")
            return 0
        state = load_project(args.project)
        if args.command == "export":
            if args.format in ("xlsx", "docx") and args.output is None:
                parser.error("Eksport XLSX/DOCX wymaga --output PLIK.")
            if (
                args.output is not None
                and args.format != "json"
                and args.project.resolve() == args.output.resolve()
            ):
                parser.error("Eksport CSV/Markdown wymaga innego pliku niż źródłowy projekt JSON.")
            text = (
                export_bytes(state.project, args.format)
                if args.format in ("xlsx", "docx")
                else export_document(state.project, args.format)
            )
            if args.output is not None:
                save_document(args.output, text, args.format)
                print(
                    f"Zapisano eksport {args.format}: {safe_text(args.output)}",
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
                print(f"Zapisano JSON: {safe_text(args.output)}", file=sys.stderr, flush=True)
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
                "Nie można zamrozić niekompletnego planu. Plik docelowy nie został zmieniony.",
                file=sys.stderr,
                flush=True,
            )
            _diagnostics(state.project, state.plan, verbose=args.verbose)
            return 1
        frozen_project = freeze(state.project, state.plan)
        save_project(args.output, frozen_project)
        print(
            f"Zamrożono adresy IPv4/IPv6 i infrastrukturę. Zapisano: {safe_text(args.output)}",
            flush=True,
        )
        _diagnostics(state.project, state.plan, verbose=args.verbose)
        return 0
    except ProjectJSONError as error:
        for issue in error.issues:
            print(
                f"Błąd danych [{issue.code}] {safe_text(issue.location)}: "
                f"{safe_text(issue.message)}",
                file=sys.stderr,
                flush=True,
            )
        return 2
    except CalculationError as error:
        print(
            f"Błąd kalkulatora [{error.code}]: {calculation_error(error)}",
            file=sys.stderr,
            flush=True,
        )
        return 2
    except BrokenPipeError:
        return 1
    except StoreError as error:
        print(f"Błąd bazy projektów: {safe_text(error)}", file=sys.stderr, flush=True)
        return 2
    except OSError as error:
        print(
            f"Błąd odczytu/zapisu: {safe_text(error.strerror or error)}",
            file=sys.stderr,
            flush=True,
        )
        return 2
    except KeyboardInterrupt:
        print("Przerwano.", file=sys.stderr, flush=True)
        return 130
