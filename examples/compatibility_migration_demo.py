# Owner: platform-operations
"""
Example demonstrating the use of the Compatibility Layer to migrate
external agents (LangGraph, CrewAI, AutoGen) to the native control plane.
"""

import asyncio
from app.compat.langgraph.adapters import StateGraph
from app.compat.crewai.adapters import Agent as CrewAgent, Task as CrewTask, Crew
from app.compat.autogen.adapters import ConversableAgent, UserProxyAgent

async def main():
    print("=== 1. LangGraph Compatibility Emulation ===")
    builder = StateGraph(state_schema=dict)
    
    def step_hello(state):
        print("LangGraph node running: Hello!")
        state["msg"] = "Hello from LangGraph"
        return state

    builder.add_node("hello", step_hello)
    builder.set_entry_point("hello")
    builder.set_finish_point("hello")
    
    compiled_graph = builder.compile()
    state_result = await compiled_graph.invoke({"input": "test"})
    print(f"State outcome: {state_result}\n")

    print("=== 2. CrewAI Compatibility Emulation ===")
    researcher = CrewAgent(
        role="Senior Researcher",
        goal="Analyze compatibility frameworks",
        backstory="Expert software architect specialized in migration strategies."
    )
    task = CrewTask(
        description="Verify how CrewAI goals translate to system prompts.",
        expected_output="A list of observations.",
        agent=researcher
    )
    crew = Crew(agents=[researcher], tasks=[task])
    output = crew.kickoff()
    print(f"Crew kickoff output:\n{output}\n")

    print("=== 3. AutoGen Compatibility Emulation ===")
    assistant = ConversableAgent(
        name="assistant",
        system_message="You are a helpful assistant."
    )
    user = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER"
    )
    
    user.initiate_chat(assistant, message="Initiate chat exchange.", max_turns=1)
    chat_result = user.chat_history["assistant"]
    print(f"Chat exchanges recorded: {chat_result}\n")

if __name__ == "__main__":
    asyncio.run(main())
