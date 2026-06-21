import os
import time
from rich.console import Console
from rich.table import Table 
from rich.panel import Panel
from rich.layout import Layout
from rich import print as rprint 
from dotenv import load_dotenv

from src.dataScrapper.newsScrapper import NewsScraper
from src.dataScrapper.eventParser import NewsAnalysisPipeline
from src.tools.simTools import stimulate_supply_chain_shock_tool

console = Console()
load_dotenv()

def displayDashB(): 
    console.clear()
    header= Panel(
        "[bold cyan]GEOPOLITICAL STRESS-TESTER[/bold cyan]\n"
        "[dim]Live Autonomous Supply Chain Monitoring[/dim]\n",
        style="on black"
    )
    console.print(header)

def runCycle(): 
    with console.status("[bold green]Scanning geopolitical feeds...[/bold green]", spinner="dots"): 
        scraper = NewsScraper()
        rawArticle = scraper.runPipeline()

    parser = NewsAnalysisPipeline()
    active_threat = []

    with console.status("[bold yellow]Analyzing threat vectors...[/bold yellow]", spinner="dots"): 
        for article in rawArticle: 
            event = parser.parseArticles(article['title'], article['full_text'][:4000])
            if event and event.isDisruption and event.mappedNode: 
                active_threat.append((article["title"], event))

    if not active_threat: 
        console.print("[bold green]No Anomalies Detected[/bold green]\n")
        return 
    
    console.print("[bold red]Disrupition in Supply Chain Found[/bold red]")
    threatTable = Table(show_header=True, header_style="bold magenta")
    threatTable.add_column("Threat Intelligence", width=50)
    threatTable.add_column("Target Node", style="cyan")
    threatTable.add_column("Severity", justify="right", style="red")

    for title, event in active_threat: 
        threatTable.add_row(
            title, 
            event.mappedNode, 
            f"{event.mappedIntensity: .0%}" if event.mappedIntensity else "Unknown"
        )

    highestThreat = max(active_threat, key=lambda x: x[1].mappedIntensity or 0)[1]
    console.print(f"\n[bold blue]Executing NetworkX Cascade Simulation for {highestThreat.mappedNode}...[/bold blue]")

    try: 
        simulation_report = stimulate_supply_chain_shock_tool.invoke({
            "source": highestThreat.mappedNode,
            "intensity": highestThreat.mappedIntensity or 0.5,
            "obsPeriod": highestThreat.impliedObsPeriod or 30
        })
        
        # Display the final mathematical impact
        report_panel = Panel(
            simulation_report, 
            title="[bold yellow]Agent Impact Projections[/bold yellow]", 
            border_style="yellow"
        )
        console.print(report_panel)
        
    except Exception as e:
        console.print(f"[bold red]Simulation Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        console.print("[bold red]ERROR: GROQ_API_KEY missing from .env[/bold red]")
        exit(1)

    while True:
        displayDashB()
        runCycle()
        
        # The agent sleeps before checking the feeds again
        console.print("\n[dim]Next cycle initiating in 60 seconds... (Press Ctrl+C to exit)[/dim]")
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            console.print("\n[bold green]Agent shutting down. Goodbye.[/bold green]")
            break
        