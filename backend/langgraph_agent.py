import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict, List, Optional, Any
from langgraph.graph import StateGraph as Graph

# Import agent classes
from .agents import SearchAgent, CuratorAgent, WriterAgent, DesignerAgent, EditorAgent, PublisherAgent, CritiqueAgent

class NewsState(TypedDict):
    query: str
    sources: Optional[List[dict]]
    image: Optional[str]
    title: Optional[str]
    date: Optional[str]
    paragraphs: Optional[List[str]]
    summary: Optional[str]
    critique: Optional[str]
    message: Optional[str]
    html: Optional[str]
    path: Optional[str]


class MasterAgent:
    def __init__(self):
        self.output_dir = f"outputs/run_{int(time.time())}"
        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, queries: list, layout: str):
        # Initialize agents
        search_agent = SearchAgent()
        curator_agent = CuratorAgent()
        writer_agent = WriterAgent()
        critique_agent = CritiqueAgent()
        designer_agent = DesignerAgent(self.output_dir)
        editor_agent = EditorAgent(layout)
        publisher_agent = PublisherAgent(self.output_dir)

        # Define a Langchain graph
        workflow = Graph(NewsState)

        # Add nodes for each agent
        workflow.add_node("search", search_agent.run)
        workflow.add_node("curate", curator_agent.run)
        workflow.add_node("write", writer_agent.run)
        workflow.add_node("critique", critique_agent.run)
        workflow.add_node("design", designer_agent.run)

        # Set up edges
        workflow.add_edge('search', 'curate')
        workflow.add_edge('curate', 'write')
        workflow.add_edge('write', 'critique')
        workflow.add_conditional_edges(
            'critique',
            lambda x: "accept" if x.get('critique') is None else "revise",
            {"accept": "design", "revise": "write"}
        )

        # set up start and end nodes
        workflow.add_edge("__start__", "search")
        workflow.add_edge("design", "__end__")

        # compile the graph
        chain = workflow.compile()

        # Execute the graph for each query in parallel
        with ThreadPoolExecutor() as executor:
            parallel_results = list(executor.map(lambda q: chain.invoke({"query": q}), queries))

        # Compile the final newspaper
        newspaper_html = editor_agent.run(parallel_results)
        newspaper_path = publisher_agent.run(newspaper_html)

        return newspaper_path
