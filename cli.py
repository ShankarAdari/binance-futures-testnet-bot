"""
cli.py
======
Binance Futures Testnet Trading Bot — CLI Entry Point
=====================================================
Vibrant "Dopamine / Retro-Futuristic" terminal theme via Rich.

Commands
--------
  place-order   — Interactive or flag-driven order placement
  open-orders   — List all open orders (optional symbol filter)
  cancel-order  — Cancel an order by ID
  price         — Fetch current market price
  account       — Show account overview

Run:
  python cli.py --help
  python cli.py place-order --help
"""

from __future__ import annotations

import io
import os
import sys
import time
from decimal import Decimal
from typing import Optional

# ── Force UTF-8 output on Windows so Rich emoji / box chars render correctly ──
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import typer
from dotenv import load_dotenv
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import get_logger, setup_logging
from bot.orders import OrderManager, OrderResult

# ── Bootstrap ──────────────────────────────────────────────────────────────────
load_dotenv()
setup_logging()
log = get_logger(__name__)

# ── Rich console (force UTF-8 file so Windows legacy mode doesn't strip chars) ─
console = Console(highlight=False, file=open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", closefd=False))

# ── Colour palette (Dopamine / Retro-Futuristic) ───────────────────────────────
C_NEON_CYAN = "bright_cyan"
C_NEON_MAGENTA = "bright_magenta"
C_NEON_GREEN = "bright_green"
C_NEON_RED = "bright_red"
C_NEON_YELLOW = "bright_yellow"
C_PURPLE = "medium_purple1"
C_ORANGE = "orange1"
C_DIM = "dim white"

# gradient-style header gradient (Rich doesn't support true CSS gradients,
# so we alternate neon segment colours)
GRADIENT_COLOURS = [C_NEON_CYAN, C_PURPLE, C_NEON_MAGENTA, C_ORANGE, C_NEON_YELLOW]


# ── Typer app ──────────────────────────────────────────────────────────────────
app = typer.Typer(
    name="trading-bot",
    help="[*] Binance Futures Testnet Trading Bot",
    rich_markup_mode="rich",
    add_completion=False,
    pretty_exceptions_show_locals=False,
)


# ── Branding — pure ASCII so cp1252 / any legacy codepage can render it ────────

LOGO_LINES = [
    r"  ____  ___ _   _   _    _   _  ____ _____  ",
    r" | __ )|_ _| \ | | / \  | \ | |/ ___| ____|  ",
    r" |  _ \ | ||  \| |/ _ \ |  \| | |   |  _|    ",
    r" | |_) || || |\  |/ ___ \| |\  | |___| |___   ",
    r" |____/___|_| \_/_/   \_|_| \_|\____|_____|  ",
    r"                                               ",
    r"   FUTURES TESTNET BOT  --  USDT-M PERPETUALS  ",
    r"         [*] Paper Trading  [*] Binance API     ",
]


def _print_banner() -> None:
    """Render the neon banner using safe ASCII + Rich colour styling."""
    styled_lines: list[Text] = []
    for i, line in enumerate(LOGO_LINES):
        colour = GRADIENT_COLOURS[i % len(GRADIENT_COLOURS)]
        styled_lines.append(Text(line, style=f"bold {colour}"))
    banner = Text("\n").join(styled_lines)
    console.print(
        Panel(
            Align.center(banner),
            border_style=C_NEON_MAGENTA,
            padding=(0, 2),
        )
    )
    console.print()


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _get_client() -> BinanceFuturesClient:
    """
    Build a BinanceFuturesClient from environment variables.
    Exits with a styled error if credentials are missing.
    """
    api_key = os.getenv("BINANCE_TESTNET_API_KEY", "")
    api_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "")

    if not api_key or not api_secret:
        console.print(
            Panel(
                "[bold bright_red]✗  Missing API credentials![/]\n\n"
                "Set the following environment variables or add them to a "
                "[bold cyan].env[/] file in the project root:\n\n"
                "  [bright_cyan]BINANCE_TESTNET_API_KEY[/]    = your testnet key\n"
                "  [bright_cyan]BINANCE_TESTNET_API_SECRET[/] = your testnet secret\n\n"
                "Get testnet keys at: "
                "[link=https://testnet.binancefuture.com]https://testnet.binancefuture.com[/]",
                title="[bold bright_red]Configuration Error[/]",
                border_style="bright_red",
                padding=(1, 2),
            )
        )
        log.error("API credentials not found in environment.")
        raise typer.Exit(1)

    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)


def _spin(message: str, fn, *args, **kwargs):
    """Run *fn* with a neon spinner. Returns fn's result."""
    result = None
    exc_holder: list[Exception] = []

    with console.status(
        f"[bold {C_NEON_CYAN}]{message}[/]",
        spinner="dots",
        spinner_style=C_NEON_MAGENTA,
    ):
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            exc_holder.append(exc)

    if exc_holder:
        raise exc_holder[0]
    return result


def _print_order_result(result: OrderResult, title: str = "Order Placed") -> None:
    """Render a beautiful neon table for an order result."""
    table = Table(
        title=f"[bold {C_NEON_CYAN}]✦  {title}  ✦[/]",
        box=box.DOUBLE_EDGE,
        border_style=C_NEON_MAGENTA,
        header_style=f"bold {C_NEON_CYAN}",
        show_lines=True,
        padding=(0, 1),
        title_style=f"bold {C_NEON_CYAN}",
    )

    table.add_column("Field", style=f"bold {C_PURPLE}", no_wrap=True)
    table.add_column("Value", style=C_NEON_YELLOW)

    row_data = OrderManager.format_result(result)
    status_colour = {
        "FILLED": C_NEON_GREEN,
        "NEW": C_NEON_CYAN,
        "PARTIALLY_FILLED": C_NEON_YELLOW,
        "CANCELED": C_NEON_RED,
        "EXPIRED": C_DIM,
    }

    for key, value in row_data.items():
        if key == "Status":
            colour = status_colour.get(str(value), C_NEON_YELLOW)
            table.add_row(key, Text(str(value), style=f"bold {colour}"))
        elif key == "Side":
            colour = C_NEON_GREEN if value == "BUY" else C_NEON_RED
            table.add_row(key, Text(str(value), style=f"bold {colour}"))
        else:
            table.add_row(key, str(value))

    console.print(table)


def _print_success(msg: str) -> None:
    console.print(f"[bold {C_NEON_GREEN}]✔  {msg}[/]")


def _print_error(msg: str) -> None:
    console.print(f"[bold {C_NEON_RED}]✘  {msg}[/]")


def _print_warning(msg: str) -> None:
    console.print(f"[bold {C_NEON_YELLOW}]⚠  {msg}[/]")


def _print_info(msg: str) -> None:
    console.print(f"[bold {C_NEON_CYAN}]ℹ  {msg}[/]")


def _section(title: str) -> None:
    console.print(Rule(f"[bold {C_NEON_MAGENTA}]{title}[/]", style=C_PURPLE))


# ── Command: place-order ───────────────────────────────────────────────────────

ORDER_TYPE_CHOICES = typer.Option(
    None,
    "--type", "-t",
    help="Order type: MARKET | LIMIT | STOP_MARKET | STOP_LIMIT",
    show_default=False,
)

@app.command("place-order", help="[bold cyan]Place a new futures order[/]")
def place_order(
    symbol: Optional[str] = typer.Option(
        None, "--symbol", "-s", help="Trading pair, e.g. [cyan]BTCUSDT[/]"
    ),
    side: Optional[str] = typer.Option(
        None, "--side", help="[green]BUY[/] or [red]SELL[/]"
    ),
    order_type: Optional[str] = typer.Option(
        None, "--type", "-t",
        help="MARKET | LIMIT | STOP_MARKET | STOP_LIMIT"
    ),
    quantity: Optional[float] = typer.Option(
        None, "--qty", "-q", help="Order quantity (base asset)"
    ),
    price: Optional[float] = typer.Option(
        None, "--price", "-p", help="Limit price (required for LIMIT / STOP_LIMIT)"
    ),
    stop_price: Optional[float] = typer.Option(
        None, "--stop-price", help="Stop trigger price (STOP_MARKET / STOP_LIMIT)"
    ),
    time_in_force: Optional[str] = typer.Option(
        "GTC", "--tif", help="Time-in-force: GTC | IOC | FOK | GTX"
    ),
    reduce_only: bool = typer.Option(
        False, "--reduce-only", help="Close-only (reduce existing position)"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Prompt for any missing fields"
    ),
) -> None:
    _print_banner()
    _section("New Order")

    # ── Interactive prompts for missing fields ─────────────────────────────────
    if interactive or symbol is None:
        symbol = Prompt.ask(
            f"[bold {C_NEON_CYAN}]  Symbol[/]",
            default=symbol or "BTCUSDT",
        ).strip().upper()

    if interactive or side is None:
        side = Prompt.ask(
            f"[bold {C_NEON_CYAN}]  Side[/]",
            choices=["BUY", "SELL"],
            default=side or "BUY",
        ).strip().upper()

    if interactive or order_type is None:
        order_type = Prompt.ask(
            f"[bold {C_NEON_CYAN}]  Order type[/]",
            choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"],
            default=order_type or "MARKET",
        ).strip().upper()

    if interactive or quantity is None:
        qty_str = Prompt.ask(
            f"[bold {C_NEON_CYAN}]  Quantity[/]",
            default=str(quantity) if quantity else "0.001",
        )
        try:
            quantity = float(qty_str)
        except ValueError:
            _print_error(f"Invalid quantity: {qty_str!r}")
            raise typer.Exit(1)

    order_type_upper = (order_type or "").upper()
    if order_type_upper in {"LIMIT", "STOP_LIMIT"} and (interactive or price is None):
        price_str = Prompt.ask(
            f"[bold {C_NEON_CYAN}]  Limit price[/]",
            default=str(price) if price else "",
        )
        try:
            price = float(price_str)
        except ValueError:
            _print_error(f"Invalid price: {price_str!r}")
            raise typer.Exit(1)

    if order_type_upper in {"STOP_MARKET", "STOP_LIMIT"} and (interactive or stop_price is None):
        sp_str = Prompt.ask(
            f"[bold {C_NEON_CYAN}]  Stop price[/]",
            default=str(stop_price) if stop_price else "",
        )
        try:
            stop_price = float(sp_str)
        except ValueError:
            _print_error(f"Invalid stop price: {sp_str!r}")
            raise typer.Exit(1)

    # ── Request summary ────────────────────────────────────────────────────────
    _section("Order Summary")
    summary = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    summary.add_column(style=f"bold {C_PURPLE}", no_wrap=True)
    summary.add_column(style=C_NEON_YELLOW)
    summary.add_row("Symbol", symbol)
    summary.add_row("Side", Text(side, style=f"bold {'bright_green' if side == 'BUY' else 'bright_red'}"))
    summary.add_row("Type", order_type_upper)
    summary.add_row("Quantity", str(quantity))
    if price:
        summary.add_row("Price", str(price))
    if stop_price:
        summary.add_row("Stop Price", str(stop_price))
    if order_type_upper in {"LIMIT", "STOP_LIMIT"}:
        summary.add_row("Time In Force", time_in_force or "GTC")
    if reduce_only:
        summary.add_row("Reduce Only", "Yes")
    console.print(summary)

    if not Confirm.ask(
        f"[bold {C_NEON_MAGENTA}]  Confirm order submission?[/]",
        default=True,
    ):
        _print_warning("Order cancelled by user.")
        raise typer.Exit(0)

    # ── Execute ────────────────────────────────────────────────────────────────
    try:
        with _get_client() as client:
            manager = OrderManager(client)

            def _do_place():
                if order_type_upper == "MARKET":
                    return manager.place_market_order(
                        symbol=symbol, side=side, quantity=quantity,
                        reduce_only=reduce_only,
                    )
                elif order_type_upper == "LIMIT":
                    return manager.place_limit_order(
                        symbol=symbol, side=side, quantity=quantity,
                        price=price, time_in_force=time_in_force or "GTC",
                        reduce_only=reduce_only,
                    )
                elif order_type_upper == "STOP_MARKET":
                    return manager.place_stop_market_order(
                        symbol=symbol, side=side, quantity=quantity,
                        stop_price=stop_price, reduce_only=reduce_only,
                    )
                elif order_type_upper == "STOP_LIMIT":
                    return manager.place_stop_limit_order(
                        symbol=symbol, side=side, quantity=quantity,
                        price=price, stop_price=stop_price,
                        time_in_force=time_in_force or "GTC",
                        reduce_only=reduce_only,
                    )
                else:
                    raise ValueError(f"Unsupported order type: {order_type_upper}")

            result: OrderResult = _spin(
                f"Submitting {order_type_upper} order...", _do_place
            )

    except ValueError as exc:
        _print_error(f"Validation failed: {exc}")
        log.error("Validation error: %s", exc)
        raise typer.Exit(1)
    except BinanceAPIError as exc:
        _print_error(f"Binance API error [{exc.api_code}]: {exc.api_message}")
        log.error("API error: %s", exc)
        raise typer.Exit(1)
    except Exception as exc:
        _print_error(f"Unexpected error: {exc}")
        log.exception("Unexpected error placing order")
        raise typer.Exit(1)

    _section("Result")
    _print_order_result(result, title="Order Placed Successfully")
    _print_success(f"Order ID {result.order_id} | Status: {result.status}")
    console.print()


# ── Command: open-orders ───────────────────────────────────────────────────────

@app.command("open-orders", help="[bold cyan]List all open orders[/]")
def open_orders(
    symbol: Optional[str] = typer.Option(
        None, "--symbol", "-s", help="Filter by symbol, e.g. BTCUSDT"
    ),
) -> None:
    _print_banner()
    _section("Open Orders")

    try:
        with _get_client() as client:
            manager = OrderManager(client)
            orders: list[OrderResult] = _spin(
                "Fetching open orders…",
                manager.get_open_orders,
                symbol,
            )
    except BinanceAPIError as exc:
        _print_error(f"API error [{exc.api_code}]: {exc.api_message}")
        raise typer.Exit(1)
    except Exception as exc:
        _print_error(f"Error: {exc}")
        log.exception("Error fetching open orders")
        raise typer.Exit(1)

    if not orders:
        _print_info("No open orders found.")
        return

    table = Table(
        title=f"[bold {C_NEON_CYAN}]Open Orders ({len(orders)})[/]",
        box=box.ROUNDED,
        border_style=C_NEON_MAGENTA,
        header_style=f"bold {C_NEON_CYAN}",
        show_lines=True,
    )
    for col in ["Order ID", "Symbol", "Side", "Type", "Qty", "Price", "Stop", "Status", "TIF"]:
        table.add_column(col, no_wrap=True)

    for o in orders:
        side_text = Text(o.side, style=f"bold {'bright_green' if o.side == 'BUY' else 'bright_red'}")
        table.add_row(
            str(o.order_id),
            o.symbol,
            side_text,
            o.order_type,
            str(o.quantity),
            str(o.price) if o.price > 0 else "-",
            str(o.stop_price) if o.stop_price > 0 else "-",
            Text(o.status, style=C_NEON_GREEN if o.status == "NEW" else C_NEON_YELLOW),
            o.time_in_force or "-",
        )

    console.print(table)
    console.print()


# ── Command: cancel-order ──────────────────────────────────────────────────────

@app.command("cancel-order", help="[bold cyan]Cancel an open order[/]")
def cancel_order(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    order_id: int = typer.Option(..., "--order-id", "-o", help="Order ID to cancel"),
) -> None:
    _print_banner()
    _section("Cancel Order")

    _print_info(f"Cancelling order {order_id} on {symbol}…")

    if not Confirm.ask(f"[bold {C_NEON_MAGENTA}]  Confirm cancellation?[/]", default=True):
        _print_warning("Cancelled by user.")
        raise typer.Exit(0)

    try:
        with _get_client() as client:
            manager = OrderManager(client)
            result = _spin(
                "Sending cancel request…",
                manager.cancel_order,
                symbol,
                order_id,
            )
    except BinanceAPIError as exc:
        _print_error(f"API error [{exc.api_code}]: {exc.api_message}")
        raise typer.Exit(1)
    except Exception as exc:
        _print_error(f"Error: {exc}")
        log.exception("Error cancelling order")
        raise typer.Exit(1)

    _print_success(
        f"Order {result.get('orderId', order_id)} cancelled — "
        f"Status: {result.get('status', 'CANCELED')}"
    )
    console.print()


# ── Command: price ─────────────────────────────────────────────────────────────

@app.command("price", help="[bold cyan]Get current market price for a symbol[/]")
def get_price(
    symbol: str = typer.Option(
        "BTCUSDT", "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"
    ),
) -> None:
    _print_banner()
    _section(f"Market Price — {symbol}")

    try:
        with _get_client() as client:
            manager = OrderManager(client)
            price: Decimal = _spin(
                f"Fetching {symbol} price…",
                manager.get_symbol_price,
                symbol.upper(),
            )
    except BinanceAPIError as exc:
        _print_error(f"API error [{exc.api_code}]: {exc.api_message}")
        raise typer.Exit(1)
    except Exception as exc:
        _print_error(f"Error: {exc}")
        raise typer.Exit(1)

    panel = Panel(
        Align.center(
            Text(f"${price:,}", style=f"bold {C_NEON_GREEN}", justify="center")
        ),
        title=f"[bold {C_NEON_CYAN}]{symbol}[/]  Current Price",
        border_style=C_NEON_MAGENTA,
        padding=(1, 4),
    )
    console.print(panel)
    console.print()


# ── Command: account ───────────────────────────────────────────────────────────

@app.command("account", help="[bold cyan]Display account balances and summary[/]")
def account_info() -> None:
    _print_banner()
    _section("Account Overview")

    try:
        with _get_client() as client:
            info = _spin("Fetching account info…", client.get_account_info)
    except BinanceAPIError as exc:
        _print_error(f"API error [{exc.api_code}]: {exc.api_message}")
        raise typer.Exit(1)
    except Exception as exc:
        _print_error(f"Error: {exc}")
        log.exception("Error fetching account info")
        raise typer.Exit(1)

    # Summary panel
    total_wallet  = Decimal(str(info.get("totalWalletBalance", "0")))
    unrealised_pnl = Decimal(str(info.get("totalUnrealizedProfit", "0")))
    avail_balance  = Decimal(str(info.get("availableBalance", "0")))
    total_margin   = Decimal(str(info.get("totalInitialMargin", "0")))

    summary = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    summary.add_column(style=f"bold {C_PURPLE}", no_wrap=True)
    summary.add_column(style=C_NEON_YELLOW, justify="right")
    summary.add_row("Wallet Balance (USDT)",    f"{total_wallet:,.4f}")
    summary.add_row("Available Balance (USDT)", f"{avail_balance:,.4f}")
    summary.add_row("Unrealised PnL (USDT)",
                    Text(f"{unrealised_pnl:,.4f}",
                         style=C_NEON_GREEN if unrealised_pnl >= 0 else C_NEON_RED))
    summary.add_row("Total Initial Margin",     f"{total_margin:,.4f}")

    console.print(
        Panel(
            summary,
            title=f"[bold {C_NEON_CYAN}]Account Summary[/]",
            border_style=C_NEON_MAGENTA,
            padding=(0, 1),
        )
    )

    # Non-zero positions
    positions = [p for p in info.get("positions", []) if Decimal(str(p.get("positionAmt", "0"))) != 0]
    if positions:
        _section("Open Positions")
        pos_table = Table(
            box=box.ROUNDED,
            border_style=C_NEON_MAGENTA,
            header_style=f"bold {C_NEON_CYAN}",
            show_lines=True,
        )
        for col in ["Symbol", "Side", "Amount", "Entry Price", "Unrealised PnL", "Leverage"]:
            pos_table.add_column(col)
        for p in positions:
            amt = Decimal(str(p.get("positionAmt", "0")))
            upnl = Decimal(str(p.get("unrealizedProfit", "0")))
            side_label = "LONG" if amt > 0 else "SHORT"
            side_colour = C_NEON_GREEN if amt > 0 else C_NEON_RED
            pos_table.add_row(
                p.get("symbol", ""),
                Text(side_label, style=f"bold {side_colour}"),
                str(abs(amt)),
                str(p.get("entryPrice", "-")),
                Text(f"{upnl:,.4f}", style=C_NEON_GREEN if upnl >= 0 else C_NEON_RED),
                str(p.get("leverage", "-")) + "x",
            )
        console.print(pos_table)
    else:
        _print_info("No open positions.")

    console.print()


# ── Main ───────────────────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """
    [*] Binance Futures Testnet Trading Bot

    Use --help on any sub-command for detailed options.
    """
    if ctx.invoked_subcommand is None:
        _print_banner()
        console.print(
            Panel(
                "[bold bright_cyan]Available commands:[/]\n\n"
                "  [bright_cyan]place-order[/]   — Place MARKET / LIMIT / STOP orders\n"
                "  [bright_cyan]open-orders[/]   — List all open orders\n"
                "  [bright_cyan]cancel-order[/]  — Cancel an order by ID\n"
                "  [bright_cyan]price[/]         — Get current market price\n"
                "  [bright_cyan]account[/]       — Account balances and positions\n\n"
                "Run [bold]python cli.py <command> --help[/] for details.",
                title="[bold medium_purple1]Trading Bot Help[/]",
                border_style=C_NEON_MAGENTA,
                padding=(1, 2),
            )
        )


if __name__ == "__main__":
    app()
