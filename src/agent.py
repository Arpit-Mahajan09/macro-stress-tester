import sys
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.memory import ConversationSummaryBufferMemory

from tools.simTools import stimulate_supply_chain_shock_tool


load_dotenv()

def stressTesterAgent(): 
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    tools= [stimulate_supply_chain_shock_tool]

    memory= ConversationSummaryBufferMemory(
        llm=llm,
        max_token_limit = 1000, 
        memory_key = "chat_history", 
        return_messages = True
    )

    prompt = ChatPromptTemplate([
        ("system", """You are the Core Orchestrator of the Macroeconomic Geopolitical Stress-Tester.
        Your job is to analyze user queries regarding geopolitical shocks, extract the affected entities, 
        and use your tools to report analytical projections.
        
        CRITICAL INSTRUCTIONS:
        1. ZERO HALLUCINATION: You do not possess real-time knowledge of supply networks. 
           You MUST rely entirely on the output of your tools.
        2. Always translate natural language concepts (e.g., "Suez is completely blocked") 
           into the strict numeric arguments your tools require (intensity = 1.0).
        3. If the tool returns an error (e.g., "node not found"), apologize to the user 
           and ask for clarification."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent= create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools,memory=memory, verbose=True)

    return agent_executor 

if __name__ == "__main__": 
    print("Initializing Supply Chain\n")
    try: 
        agent = stressTesterAgent()
    except Exception as e: 
        print("please check initialization variables")
        sys.exit(1)
    while True: 
        userInput = input("\nUser: ").strip()
        if userInput.lower() in ['exit', 'quit']: 
            break 

        response = agent.invoke({'input': userInput})
        print(f"\nAgent: {response['output']}")