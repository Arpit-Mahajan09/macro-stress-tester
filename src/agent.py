import sys
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.memory import ConversationSummaryBufferMemory

load_dotenv()

from src.tools.simTools import stimulate_supply_chain_shock_tool
from src.decisonEngine import recommend_action

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
           and ask for clarification.
        4. COMBINING SHOCKS: If the user introduces a new disruption on top of one
            already discussed in this conversation, call the tool again for the new
            shock — do not assume the tool combines multiple origins in a single run.
            If a node appears in both results, report each shock's propagated risk to
            it separately and say so explicitly (e.g. "Node X shows 40% risk from the
            Suez disruption and 25% from the Taiwan disruption, evaluated independently
            — these are not additive in the current model"). Never sum or average two
            separate tool outputs yourself and present it as a single combined risk
            score, since that number would not be mathematically grounded
        5. WORKFLOW: After running stimulate_supply_chain_shock, if any node shows
           meaningful risk (>30%), follow up by calling recommend_action for that
           node to give the user an actionable next step, not just a raw percentage."""),
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
        print(f"please check initialization variables {e}")
        sys.exit(1)
    while True: 
        userInput = input("\nUser: ").strip()
        if userInput.lower() in ['exit', 'quit']: 
            break 

        response = agent.invoke({'input': userInput})
        print(f"\nAgent: {response['output']}")