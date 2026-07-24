from src.dataScrapper.newsScrapper import NewsScraper
from src.dataScrapper.eventParser import NewsAnalysisPipeline

def dataGatherer(): 
    scrapper = NewsScraper()
    rawArticles = scrapper.runPipeline()
    parser = NewsAnalysisPipeline()
    actionableData = []

    print(f"Parsing {len(rawArticles)}...")
    for article in rawArticles: 
        parsedEvent = parser.parseArticles(article['title'], article['full_text'][:4000])

        if parsedEvent.isDisruption and parsedEvent.mappedNode: 
            print(f"Disruption detected in {article['title']}")
            print(f" -> Mapped Node: {parsedEvent.mappedNode}")
            print(f" -> Intensity: {parsedEvent.mappedIntensity}")
            print(f" -> Reasoning: {parsedEvent.reasoningSummary}\n")

            actionableData.append(parsedEvent)

    print(f"Total Actionable Threats: {len(actionableData)}")
    return actionableData


if __name__ == "__main__":
    active_threats = dataGatherer()