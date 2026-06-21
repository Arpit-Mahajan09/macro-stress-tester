import os
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

class DisruptionEvent(BaseModel): 
    isDisruption : bool = Field(
        description="True if the article describes an active physical or economic disruption to supply chains, ports, canals, or manufacturing."
    )
    mappedNode: Optional[str] = Field(
        None, 
        description="The exact identifier of the affected facility or route from our network topology."
    )
    mappedIntensity : Optional[float] = Field(
        None, 
        description="A value between 0.0 and 1.0 representing capacity reduction. Full closure/strike = 1.0, minor delays/tariffs = 0.3."
    )
    impliedObsPeriod: Optional[int] = Field(
        None, 
        description="Estimated duration(in unit of number of days) of the disruption based on the text. If unspecified, default to 30"
    )
    reasoningSummary: Optional[str] = Field(
        None, 
        description="A brief explanation justifying the extracted node and selected intensity metric."
    )

class NewsAnalysisPipeline: 
    def __init__(self): 
        self.llm=ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        self.structured_llm = self.llm.with_structured_output(DisruptionEvent)
    
    def parseArticles(self, title: str, full_text: str) -> DisruptionEvent:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an elite geopolitical intelligence parser. Your objective is to extract structured operational indicators from unstructured financial news.
            
            Valid network nodes available in system context:
            - Suez_Canal
            - Taiwan_Semi_Fab
            - Port_of_Rotterdam
            - Port_of_Kaohsiung
            - Euro_Auto_Factory
            - Port_of_LA
            - US_Tech_Assembly
            - Global_Tech_Corp
            """),
            ("user", "Analyze the following news item:\n\nTitle: {title}\nContent: {text}")
        ])
        chain = prompt | self.structured_llm
        return chain.invoke({"title": title, "text": full_text[:4000]})

if __name__ == "__main__": 
    sample_title = "Massive labor strike brings Port of Rotterdam to an absolute standstill"
    sample_text = "Dockworkers walking out over contract deadlocks have closed shipping channels completely. Terminal operators predict clearing backlogs will take at least three weeks."
    
    parser = NewsAnalysisPipeline()
    result = parser.parseArticles(sample_title, sample_text)
    print(result.model_dump_json(indent=2))