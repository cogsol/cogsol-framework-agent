from cogsol.agents import BaseAgent, genconfigs
from cogsol.prompts import Prompts
from ..searches import CogsolFrameworkDocsSearch, CogsolAPIsDocsSearch
from ..tools import CogSolScaffoldGenerator, DetectUserLanguageTool


class CogsolFrameworkAgent(BaseAgent):
    system_prompt = Prompts.load("cogsolframeworkagent.md")
    generation_config = genconfigs.QA()
    pretools = [DetectUserLanguageTool()]
    tools = [CogsolFrameworkDocsSearch(), CogsolAPIsDocsSearch(), CogSolScaffoldGenerator()]
    max_responses = 20
    max_msg_length = 2048
    max_consecutive_tool_calls = 3
    temperature = 0.3

    class Meta:
        name = "Cogsol Framework Agent"
        chat_name = "Cogsol Framework Agent"