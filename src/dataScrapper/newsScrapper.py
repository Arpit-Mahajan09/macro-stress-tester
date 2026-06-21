import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class NewsScraper: 
    def __init__(self): 
        self.target = [
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258", # CNBC Economy
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147", # CNBC Buiseness
            "https://www.supplychainbrain.com/rss/topic/1140-global-logistics",   # SCB Global Logistics
            "https://www.supplychainbrain.com/rss/topic/1138-freight-forwarding-customs-brokerage",   #SCB Freight Forwad    
            "https://www.supplychainbrain.com/rss/topic/1139-global-gateways", #SCB Global Gateway 
            "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", # WSJ Business
        ]
        self.headers={
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
        }

    def fetchFeedData(self)-> list[dict]: 
        articles = []
        for url in self.target: 
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: 
                articles.append({
                    "title": entry.title, 
                    "link": entry.link, 
                    "published": entry.get("published", datetime.now().isoformat()), 
                    "summary": entry.get("summary", "")
                })
        return articles
    

    def extractFullText(self, url: str)->str: 
        try: 
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            paragraph = soup.find_all('p')

            fullText= " ".join([p.get_text().strip() for p in paragraph if len(p.get_text().strip())>20 and "This copy is for your personal" not in p.get_text()])
            return fullText
        
        except Exception as e: 
            return f"Error extracting {url}: {str(e)}"
        
    def runPipeline(self)->list[dict]: 
        raw_articles = self.fetchFeedData()

        print(f"Extracting full text for {len(raw_articles)} articles...")
        for article in raw_articles:
            article["full_text"] = self.extractFullText(article["link"])
            
        return raw_articles

if __name__ == "__main__":
    scraper = NewsScraper()
    results = scraper.runPipeline()
    
    for res in results[:2]:
        print(f"--- {res['title']} ---")
        print(f"Text: {res['full_text'][:250]}...\n")