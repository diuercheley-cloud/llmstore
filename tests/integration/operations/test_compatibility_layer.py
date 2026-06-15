"""Tests for the compatibility layer (langgraph, crewai, autogen).

Run with: pytest tests/integration/operations/test_compatibility_layer.py -v
"""

import pytest

from scripts.llm_harness.compat.report import CompatibilityAnalyzer, FrameworkSupport

# ---------------------------------------------------------------------------
# 1. CompatibilityAnalyzer tests
# ---------------------------------------------------------------------------


class TestCompatibilityAnalyzer:
    def test_langgraph_fully_compatible(self):
        code = """
from compat.langgraph import StateGraph

def my_node(state):
    return {"key": "value"}

graph = StateGraph(dict)
graph.add_node("my_node", my_node)
graph.add_edge("__start__", "my_node")
graph.set_entry_point("__start__")
graph.set_finish_point("__end__")
compiled = graph.compile()
"""
        report = CompatibilityAnalyzer.analyze_source_code("langgraph", code)
        assert report.framework == "langgraph"
        assert report.score >= 90.0
        assert report.status == FrameworkSupport.FULLY_COMPATIBLE

    def test_langgraph_with_conditional_edges(self):
        code = """
def condition(state):
    return "path_a" if state["x"] > 0 else "path_b"

graph.add_conditional_edges("node_a", condition, {"path_a": "node_b", "path_b": "node_c"})
"""
        report = CompatibilityAnalyzer.analyze_source_code("langgraph", code)
        assert report.score < 90.0
        assert report.status == FrameworkSupport.PARTIALLY_COMPATIBLE
        assert any("conditional" in r.lower() for r in report.remediation_steps)

    def test_crewai_sequential_compatible(self):
        code = """
from compat.crewai import Agent, Task, Crew

researcher = Agent(role="researcher", goal="find info", backstory="expert")
writer = Agent(role="writer", goal="write docs", backstory="author")
task = Task(description="research", expected_output="report", agent=researcher)
crew = Crew(agents=[researcher, writer], tasks=[task], process="sequential")
"""
        report = CompatibilityAnalyzer.analyze_source_code("crewai", code)
        assert report.framework == "crewai"
        assert report.status in (
            FrameworkSupport.FULLY_COMPATIBLE,
            FrameworkSupport.PARTIALLY_COMPATIBLE,
        )

    def test_crewai_hierarchical(self):
        code = """
from compat.crewai import Agent, Task, Crew

manager = Agent(role="manager", goal="manage", backstory="boss")
worker = Agent(role="worker", goal="work", backstory="worker")
crew = Crew(agents=[manager, worker], tasks=[], process=Process.hierarchical)
"""
        report = CompatibilityAnalyzer.analyze_source_code("crewai", code)
        assert any("hierarchical" in f.feature.lower() for f in report.analyzed_features)
        assert len(report.remediation_steps) > 0

    def test_autogen_with_groupchat(self):
        code = """
from compat.autogen import ConversableAgent, GroupChat

alice = ConversableAgent(name="alice")
bob = ConversableAgent(name="bob")
group = GroupChat(agents=[alice, bob], max_round=10)
"""
        report = CompatibilityAnalyzer.analyze_source_code("autogen", code)
        assert report.framework == "autogen"
        assert any("GroupChat" in f.feature for f in report.analyzed_features)

    def test_autogen_code_execution(self):
        code = """
from compat.autogen import ConversableAgent

agent = ConversableAgent(name="coder", code_execution_config={"work_dir": "/tmp"})
"""
        report = CompatibilityAnalyzer.analyze_source_code("autogen", code)
        assert report.score < 100.0
        assert any("code execution" in f.feature.lower() for f in report.analyzed_features)

    def test_unsupported_framework(self):
        code = "print('hello')"
        report = CompatibilityAnalyzer.analyze_source_code("unknown_framework", code)
        assert report.score == 0.0
        assert report.status == FrameworkSupport.INCOMPATIBLE

    def test_report_to_dict(self):
        code = "StateGraph(dict)"
        report = CompatibilityAnalyzer.analyze_source_code("langgraph", code)
        d = report.to_dict()
        assert d["framework"] == "langgraph"
        assert "compatibility_score" in d
        assert "features_analyzed" in d
        assert "remediation_steps" in d


# ---------------------------------------------------------------------------
# 2. LangGraph adapter + importer + converter tests
# ---------------------------------------------------------------------------


class TestLangGraphCompat:
    @pytest.fixture
    def importer(self):
        from scripts.llm_harness.compat.langgraph import LangGraphImporter

        return LangGraphImporter()

    def test_import_from_source(self, importer):
        code = """
from scripts.llm_harness.compat.langgraph import StateGraph

def node_a(state):
    state["a"] = 1
    return state

graph = StateGraph(dict)
graph.add_node("a", node_a)
graph.set_entry_point("a")
graph.set_finish_point("b")
"""
        result = importer.from_source(code, target_variable="graph")
        assert result.success
        assert result.data is not None

    def test_import_no_graph_found(self, importer):
        result = importer.from_source("x = 42", target_variable="graph")
        assert not result.success
        assert "No StateGraph" in (result.error or "")

    def test_import_file_not_found(self, importer):
        result = importer.from_file("/nonexistent/file.py")
        assert not result.success
        assert "not found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_compiled_graph_invoke(self):
        from scripts.llm_harness.compat.langgraph import StateGraph

        def node_a(state):
            state["visited"] = state.get("visited", []) + ["a"]
            state["val"] = 1
            return state

        def node_b(state):
            state["visited"] = state.get("visited", []) + ["b"]
            state["val"] = 2
            return state

        graph = StateGraph(dict)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        compiled = graph.compile()

        result = await compiled.invoke({"start": True})
        assert "a" in result["visited"]
        assert "b" in result["visited"]
        assert result["val"] == 2

    def test_converter(self):
        from scripts.llm_harness.compat.langgraph import LangGraphConverter, StateGraph
        from scripts.llm_harness.mas.schemas import AgentTeam

        graph = StateGraph(dict)
        graph.add_node("researcher", lambda s: s)
        graph.add_node("writer", lambda s: s)
        graph.set_entry_point("researcher")
        graph.set_finish_point("writer")

        converter = LangGraphConverter()
        result = converter.convert(graph, team_name="test_team")
        assert result.success
        assert isinstance(result.data, AgentTeam)
        assert result.data.name == "test_team"
        assert len(result.data.members) == 2

    def test_converter_invalid_input(self):
        from scripts.llm_harness.compat.langgraph import LangGraphConverter

        converter = LangGraphConverter()
        result = converter.convert("not_a_graph")
        assert not result.success

    def test_converter_empty_graph(self):
        from scripts.llm_harness.compat.langgraph import LangGraphConverter, StateGraph

        graph = StateGraph(dict)
        converter = LangGraphConverter()
        result = converter.convert(graph)
        assert not result.success

    def test_convert_batch(self):
        from scripts.llm_harness.compat.langgraph import LangGraphConverter, StateGraph

        g1 = StateGraph(dict)
        g1.add_node("n1", lambda s: s)
        g2 = StateGraph(dict)
        g2.add_node("n2", lambda s: s)

        converter = LangGraphConverter()
        results = converter.convert_batch([g1, g2])
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_import_and_convert(self, importer):
        from scripts.llm_harness.compat.langgraph import LangGraphConverter

        code = """
from scripts.llm_harness.compat.langgraph import StateGraph

def n1(state):
    return state

graph = StateGraph(dict)
graph.add_node("agent1", n1)
graph.set_entry_point("agent1")
"""
        import_result = importer.from_source(code, target_variable="graph")
        assert import_result.success

        converter = LangGraphConverter()
        convert_result = converter.convert(import_result.data)
        assert convert_result.success
        assert convert_result.data is not None


# ---------------------------------------------------------------------------
# 3. CrewAI adapter + importer + converter tests
# ---------------------------------------------------------------------------


class TestCrewAICompat:
    @pytest.fixture
    def importer(self):
        from scripts.llm_harness.compat.crewai import CrewAIImporter

        return CrewAIImporter()

    def test_import_from_source(self, importer):
        code = """
from scripts.llm_harness.compat.crewai import Agent, Task, Crew

researcher = Agent(role="researcher", goal="research", backstory="")
writer = Agent(role="writer", goal="write", backstory="")
task1 = Task(description="do research", expected_output="paper", agent=researcher)
task2 = Task(description="write report", expected_output="report", agent=writer)
crew = Crew(agents=[researcher, writer], tasks=[task1, task2])
"""
        result = importer.from_source(code, target_variable="crew")
        assert result.success
        assert result.data is not None

    def test_import_no_crew(self, importer):
        result = importer.from_source("x = 1", target_variable="crew")
        assert not result.success

    def test_convert(self):
        from scripts.llm_harness.compat.crewai import Agent, Crew, CrewAIConverter, Task
        from scripts.llm_harness.mas.schemas import AgentTeam

        agents = [
            Agent(role="researcher", goal="find data", backstory="data expert"),
            Agent(role="writer", goal="write docs", backstory="author"),
        ]
        tasks = [
            Task(description="research topic", expected_output="notes", agent=agents[0]),
            Task(description="write article", expected_output="article", agent=agents[1]),
        ]
        crew = Crew(agents=agents, tasks=tasks)

        converter = CrewAIConverter()
        result = converter.convert(crew, team_name="research_team")
        assert result.success
        assert isinstance(result.data, AgentTeam)
        assert result.data.name == "research_team"

    def test_convert_hierarchical(self):
        from scripts.llm_harness.compat.crewai import Agent, Crew, CrewAIConverter, Task

        crew = Crew(
            agents=[Agent(role="manager", goal="manage", backstory="")],
            tasks=[Task(description="t", expected_output="o")],
            process="hierarchical",
        )
        converter = CrewAIConverter()
        result = converter.convert(crew)
        assert result.success
        assert "hierarchical" in str(result.warnings).lower()

    def test_convert_invalid(self):
        from scripts.llm_harness.compat.crewai import CrewAIConverter

        result = CrewAIConverter().convert("invalid")
        assert not result.success

    def test_crew_kickoff(self):
        from scripts.llm_harness.compat.crewai import Agent, Crew, Task

        agent = Agent(role="tester", goal="test", backstory="")
        task = Task(description="run {test_name}", expected_output="pass", agent=agent)
        crew = Crew(agents=[agent], tasks=[task])
        result = crew.kickoff(inputs={"test_name": "unit_test"})
        assert "unit_test" in result
        assert "pass" in result

    def test_agent_to_dict(self):
        from scripts.llm_harness.compat.crewai import Agent

        a = Agent(role="dev", goal="code", backstory="engineer")
        d = a.to_dict()
        assert d["role"] == "dev"
        assert d["goal"] == "code"


# ---------------------------------------------------------------------------
# 4. AutoGen adapter + importer + converter tests
# ---------------------------------------------------------------------------


class TestAutoGenCompat:
    @pytest.fixture
    def importer(self):
        from scripts.llm_harness.compat.autogen import AutoGenImporter

        return AutoGenImporter()

    def test_import_from_source(self, importer):
        code = """
from scripts.llm_harness.compat.autogen import ConversableAgent, UserProxyAgent

assistant = ConversableAgent(name="assistant", system_message="helpful")
user = UserProxyAgent(name="user")
"""
        result = importer.from_source(code, target_variable="assistant")
        assert result.success
        assert result.data is not None

    def test_import_no_agent(self, importer):
        result = importer.from_source("pass", target_variable="agent")
        assert not result.success

    def test_import_groupchat(self, importer):
        code = """
from scripts.llm_harness.compat.autogen import ConversableAgent, GroupChat

a1 = ConversableAgent(name="a1")
a2 = ConversableAgent(name="a2")
gc = GroupChat(agents=[a1, a2], max_round=5)
"""
        result = importer.from_source(code, target_variable="gc")
        assert result.success

    def test_adapter_send_receive(self):
        from scripts.llm_harness.compat.autogen import ConversableAgent

        alice = ConversableAgent(name="alice", system_message="I am Alice")
        bob = ConversableAgent(name="bob", system_message="I am Bob")

        alice.initiate_chat(bob, "Hello Bob!")
        assert bob.name in alice.chat_history
        assert alice.name in bob.chat_history

    def test_adapter_to_dict(self):
        from scripts.llm_harness.compat.autogen import ConversableAgent

        a = ConversableAgent(name="test", system_message="hello")
        d = a.to_dict()
        assert d["name"] == "test"
        assert d["system_message"] == "hello"

    def test_convert_single_agent(self):
        from scripts.llm_harness.compat.autogen import AutoGenConverter, ConversableAgent
        from scripts.llm_harness.mas.schemas import AgentTeam

        agent = ConversableAgent(
            name="helper",
            system_message="You are helpful",
            llm_config={"config_list": [{"model": "gpt-4"}]},
        )
        converter = AutoGenConverter()
        result = converter.convert(agent, team_name="helper_team")
        assert result.success
        assert isinstance(result.data, AgentTeam)
        assert result.data.name == "helper_team"

    def test_convert_group_chat(self):
        from scripts.llm_harness.compat.autogen import AutoGenConverter, ConversableAgent, GroupChat

        agents = [
            ConversableAgent(name="agent1"),
            ConversableAgent(name="agent2"),
            ConversableAgent(name="agent3"),
        ]
        gc = GroupChat(agents=agents, max_round=10)

        converter = AutoGenConverter()
        result = converter.convert(gc, team_name="chat_team")
        assert result.success
        assert len(result.data.members) == 3

    def test_convert_invalid(self):
        from scripts.llm_harness.compat.autogen import AutoGenConverter

        result = AutoGenConverter().convert("invalid")
        assert not result.success

    def test_assistant_agent(self):
        from scripts.llm_harness.compat.autogen import AssistantAgent, ConversableAgent

        asst = AssistantAgent(name="coder", system_message="write code")
        user = ConversableAgent(name="user")
        reply = asst.generate_reply([{"content": "write hello world", "role": "user"}], user)
        assert "coder" in (reply or "")

    def test_user_proxy_agent(self):
        from scripts.llm_harness.compat.autogen import ConversableAgent, UserProxyAgent

        proxy = UserProxyAgent(name="proxy")
        agent = ConversableAgent(name="agent")
        reply = proxy.generate_reply([{"content": "run tests", "role": "user"}], agent)
        assert "UserProxy" in (reply or "")

    def test_convert_with_code_exec_warning(self):
        from scripts.llm_harness.compat.autogen import AutoGenConverter, ConversableAgent

        agent = ConversableAgent(
            name="coder",
            code_execution_config={"work_dir": "/tmp"},
        )
        converter = AutoGenConverter()
        result = converter.convert(agent)
        assert result.success
        assert any("code_execution" in w for w in result.warnings)
