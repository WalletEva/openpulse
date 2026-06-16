"""CLI main entry point using Typer."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from openpulse import __version__

app = typer.Typer(
    name="openpulse",
    help="OpenPulse - Open-source intelligence gathering and aggregation platform",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"OpenPulse v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit"
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
) -> None:
    """OpenPulse CLI - intelligence gathering made simple."""
    pass


@app.command()
def init(
    db_path: Optional[str] = typer.Option(None, "--db", help="Custom database path"),
    force: bool = typer.Option(False, "--force", help="Re-initialize even if already initialized"),
) -> None:
    """Initialize OpenPulse database and default configuration."""
    from openpulse.config import get_default_data_dir, load_settings
    from openpulse.storage.database import get_engine, init_db

    data_dir = get_default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    if db_path:
        db_url = f"sqlite:///{db_path}"
    else:
        db_url = None

    engine = get_engine(db_url)
    init_db(engine)

    # Create default config if not exists
    config_path = data_dir / "config.yaml"
    if not config_path.exists() or force:
        from openpulse.config import OpenPulseSettings
        settings = OpenPulseSettings()
        settings.save_yaml(config_path)
        console.print(f"[green]Created config:[/green] {config_path}")

    console.print(f"[green]OpenPulse initialized successfully![/green]")
    console.print(f"  Data directory: {data_dir}")
    console.print(f"  Database: {db_url or 'default SQLite'}")
    console.print(f"\nNext steps:")
    console.print(f"  1. Edit config: {config_path}")
    console.print(f"  2. Add sources: openpulse source add ...")
    console.print(f"  3. Start collecting: openpulse collect --source <name> --now")


@app.command()
def collect(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Source name to collect"),
    route: Optional[str] = typer.Option(None, "--route", "-r", help="RSSHub route (e.g. /reuters/world)"),
    url: Optional[str] = typer.Option(None, "--url", help="Direct RSS feed URL"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max articles to collect"),
    now: bool = typer.Option(False, "--now", help="Collect immediately (default behavior)"),
) -> None:
    """Collect articles from a source immediately."""
    from openpulse.collector.adapters import CustomRSSCollector, RSSHubCollector
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository

    async def _collect() -> None:
        if route:
            collector = RSSHubCollector()
            source_config = {
                "route": route,
                "limit": limit,
                "source_name": source or route,
            }
        elif url:
            collector = CustomRSSCollector()
            source_config = {
                "url": url,
                "limit": limit,
                "source_name": source or url,
            }
        elif source:
            # Try to look up source from database
            session = get_session()
            from openpulse.storage.repositories.source_repo import SourceRepository
            repo = SourceRepository(session)
            src = repo.get_by_name(source)
            if not src:
                console.print(f"[red]Source '{source}' not found. Add it first with 'openpulse source add'[/red]")
                raise typer.Exit(1)
            source_config = src.config or {}
            source_config["source_name"] = src.name
            source_config["limit"] = limit

            if src.adapter == "rsshub":
                collector = RSSHubCollector()
            else:
                collector = CustomRSSCollector()
            session.close()
        else:
            console.print("[red]Please specify --source, --route, or --url[/red]")
            raise typer.Exit(1)

        console.print(f"[cyan]Collecting from {source_config.get('source_name', 'unknown')}...[/cyan]")
        result = await collector.collect(source_config)

        if not result.success:
            console.print(f"[red]Collection failed: {result.error}[/red]")
            raise typer.Exit(1)

        # Save to database
        session = get_session()
        article_repo = ArticleRepository(session)
        new_articles = article_repo.add_many(result.articles)
        session.commit()
        session.close()

        console.print(f"[green]Collected {result.count} articles ({len(new_articles)} new)[/green]")
        for article in new_articles[:10]:
            console.print(f"  - {article.title[:80]}")
        if len(new_articles) > 10:
            console.print(f"  ... and {len(new_articles) - 10} more")

    asyncio.run(_collect())


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source"),
    language: Optional[str] = typer.Option(None, "--lang", help="Filter by language"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Search collected articles."""
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository

    session = get_session()
    repo = ArticleRepository(session)

    articles = repo.search(
        query=query,
        source=source,
        language=language,
        limit=limit,
    )
    session.close()

    if not articles:
        console.print(f"[yellow]No articles found for '{query}'[/yellow]")
        return

    if json_output:
        data = [
            {
                "id": a.id,
                "title": a.title,
                "source": a.source,
                "url": a.url,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "language": a.language,
                "tags": a.tags,
            }
            for a in articles
        ]
        console.print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        table = Table(title=f"Search results for '{query}' ({len(articles)} found)")
        table.add_column("Title", style="cyan", no_wrap=False)
        table.add_column("Source", style="green")
        table.add_column("Date", style="dim")
        table.add_column("Lang", style="yellow")

        for article in articles:
            date_str = article.published_at.strftime("%Y-%m-%d") if article.published_at else "-"
            table.add_row(
                article.title[:60],
                article.source,
                date_str,
                article.language,
            )
        console.print(table)


@app.command()
def status() -> None:
    """Show system status and statistics."""
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository
    from openpulse.storage.repositories.source_repo import SourceRepository
    from openpulse.storage.repositories.task_repo import TaskRepository

    session = get_session()
    article_repo = ArticleRepository(session)
    source_repo = SourceRepository(session)
    task_repo = TaskRepository(session)

    total_articles = article_repo.count()
    sources = source_repo.list_all()
    tasks = task_repo.list_all()
    enabled_tasks = [t for t in tasks if t.enabled]

    table = Table(title="OpenPulse Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total articles", str(total_articles))
    table.add_row("Configured sources", str(len(sources)))
    table.add_row("Enabled sources", str(len([s for s in sources if s.enabled])))
    table.add_row("Collection tasks", str(len(tasks)))
    table.add_row("Active tasks", str(len(enabled_tasks)))

    console.print(table)

    if sources:
        src_table = Table(title="Sources")
        src_table.add_column("Name", style="cyan")
        src_table.add_column("Type", style="green")
        src_table.add_column("Adapter", style="blue")
        src_table.add_column("Enabled", style="yellow")
        src_table.add_column("Category")

        for src in sources:
            src_table.add_row(
                src.name,
                src.source_type,
                src.adapter,
                "Yes" if src.enabled else "No",
                src.category or "-",
            )
        console.print(src_table)

    session.close()


@app.command(name="source")
def source_cmd(
    action: str = typer.Argument(..., help="Action: add, list, remove, enable, disable"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Source name"),
    source_type: Optional[str] = typer.Option(None, "--type", "-t", help="Source type (rsshub, rss, api)"),
    adapter: Optional[str] = typer.Option(None, "--adapter", "-a", help="Adapter name"),
    route: Optional[str] = typer.Option(None, "--route", "-r", help="RSSHub route"),
    url: Optional[str] = typer.Option(None, "--url", help="Direct feed URL"),
    category: Optional[str] = typer.Option(None, "--category", help="Source category"),
) -> None:
    """Manage information sources."""
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.source_repo import SourceRepository

    session = get_session()
    repo = SourceRepository(session)

    if action == "list":
        sources = repo.list_all()
        if not sources:
            console.print("[yellow]No sources configured.[/yellow]")
            console.print("Add one with: openpulse source add --name reuters --type rsshub --adapter rsshub --route /reuters/world")
            session.close()
            return

        table = Table(title="Configured Sources")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Adapter", style="blue")
        table.add_column("Enabled", style="yellow")
        table.add_column("Category")

        for src in sources:
            table.add_row(
                str(src.id),
                src.name,
                src.source_type,
                src.adapter,
                "Yes" if src.enabled else "No",
                src.category or "-",
            )
        console.print(table)

    elif action == "add":
        if not name:
            console.print("[red]--name is required for 'add' action[/red]")
            raise typer.Exit(1)

        config: dict = {}
        if route:
            config["route"] = route
        if url:
            config["url"] = url

        src = repo.add(
            __import__("openpulse.storage.models", fromlist=["Source"]).Source(
                name=name,
                source_type=source_type or "rss",
                adapter=adapter or "custom_rss",
                config=config,
                category=category or "",
            )
        )
        session.commit()
        console.print(f"[green]Source '{name}' added (ID: {src.id})[/green]")

    elif action == "remove":
        if not name:
            console.print("[red]--name is required for 'remove' action[/red]")
            raise typer.Exit(1)
        src = repo.get_by_name(name)
        if not src:
            console.print(f"[red]Source '{name}' not found[/red]")
            raise typer.Exit(1)
        repo.delete(src.id)
        session.commit()
        console.print(f"[green]Source '{name}' removed[/green]")

    elif action in ("enable", "disable"):
        if not name:
            console.print(f"[red]--name is required for '{action}' action[/red]")
            raise typer.Exit(1)
        src = repo.get_by_name(name)
        if not src:
            console.print(f"[red]Source '{name}' not found[/red]")
            raise typer.Exit(1)
        src.enabled = action == "enable"
        session.commit()
        console.print(f"[green]Source '{name}' {action}d[/green]")

    else:
        console.print(f"[red]Unknown action: {action}. Use: add, list, remove, enable, disable[/red]")
        raise typer.Exit(1)

    session.close()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
) -> None:
    """Start the OpenPulse API server."""
    import uvicorn

    console.print(f"[cyan]Starting OpenPulse server on {host}:{port}...[/cyan]")
    uvicorn.run(
        "openpulse.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
