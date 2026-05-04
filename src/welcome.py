#!/usr/bin/env python3
"""
Banner de bienvenida
Dependencia: pip install rich
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


def _corner_row(left: str, right: str, style: str) -> Table:
    row = Table.grid(expand=True)
    row.add_column(justify="left", no_wrap=True)
    row.add_column(justify="center", ratio=1)
    row.add_column(justify="right", no_wrap=True)
    row.add_row(Text(left, style=style), Text(""), Text(right, style=style))
    return row


def _outer_atom() -> Padding:
    atom = Text(justify="center")
    atom.append("  ⚛  \n", style="bold bright_cyan")
    atom.append("⚛   ⚛\n", style="bold bright_cyan")
    atom.append("  ⚛  ", style="bold bright_cyan")
    return Padding(atom, (0, 2))


def make_banner() -> Table:
    # Título en panel propio
    title_text = Text(justify="center")
    title_text.append("  T H E   B I G   D A T A   T H E O R Y  ", style="bold bright_cyan")
    title_block = Panel(
        Align(title_text, align="center"),
        border_style="bright_cyan",
        box=box.HEAVY,
        padding=(0, 2),
    )

    slogan = Text(justify="center")
    slogan.append("◈  ", style="bright_magenta")
    slogan.append("W E A T H E R   I N N O V A T O R S", style="bold magenta")
    slogan.append("  ◈", style="bright_magenta")

    content = Group(
        _corner_row("⚛   ☁", "☁   ⚛", "bold bright_cyan"),
        Rule(style="dim cyan", characters="·"),
        Text(""),
        title_block,
        Text(""),
        Align(slogan, align="center"),
        Text(""),
        Rule(style="dim cyan", characters="·"),
        _corner_row("⚡   ☀", "☀   ⚡", "bold yellow"),
    )

    panel = Panel(
        content,
        border_style="bold magenta",
        padding=(0, 4),
        title="[bold bright_cyan]◈  MADRID CLIMATE MONITORING SYSTEM  ◈[/bold bright_cyan]",
        subtitle="[dim cyan]◇  Ayuntamiento de Madrid  ◇[/dim cyan]",
    )

    # Marco exterior
    outer = Table.grid(padding=(0, 0))
    outer.add_column(justify="left", no_wrap=True)
    outer.add_column(justify="center")
    outer.add_column(justify="right", no_wrap=True)

    outer.add_row(_outer_atom(), Text(""), _outer_atom())
    outer.add_row(Text(""), panel, Text(""))
    outer.add_row(_outer_atom(), Text(""), _outer_atom())

    return outer


def make_goodbye_banner() -> Table:
    title_text = Text(justify="center")
    title_text.append("  H A S T A   P R O N T O  ", style="bold bright_cyan")
    title_block = Panel(
        Align(title_text, align="center"),
        border_style="bright_cyan",
        box=box.HEAVY,
        padding=(0, 2),
    )

    hand = Text(justify="center")
    hand.append("Gracias por preferirnos", style="bold")

    content = Group(
        _corner_row("⚛   ☁", "☁   ⚛", "bold bright_cyan"),
        Rule(style="dim cyan", characters="·"),
        Text(""),
        title_block,
        Text(""),
        Align(hand, align="center"),
        Text(""),
        Rule(style="dim cyan", characters="·"),
        _corner_row("⚡   ☀", "☀   ⚡", "bold yellow"),
    )

    panel = Panel(
        content,
        border_style="bold magenta",
        padding=(0, 4),
        title="[bold bright_cyan]◈  MADRID CLIMATE MONITORING SYSTEM  ◈[/bold bright_cyan]",
        subtitle="[dim cyan]◇  Ayuntamiento de Madrid  ◇[/dim cyan]",
    )

    outer = Table.grid(padding=(0, 0))
    outer.add_column(justify="left", no_wrap=True)
    outer.add_column(justify="center")
    outer.add_column(justify="right", no_wrap=True)

    outer.add_row(_outer_atom(), Text(""), _outer_atom())
    outer.add_row(Text(""), panel, Text(""))
    outer.add_row(_outer_atom(), Text(""), _outer_atom())

    return outer


def show_goodbye() -> None:
    console = Console()
    console.print()
    console.print(Align(make_goodbye_banner(), align="center"))
    console.print()


def main() -> None:
    console = Console()
    console.print()
    console.print(Align(make_banner(), align="center"))
    console.print()


if __name__ == "__main__":
    main()
