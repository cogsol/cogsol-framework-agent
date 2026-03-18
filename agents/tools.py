from cogsol.tools import BaseTool, tool_params


class DetectUserLanguageTool(BaseTool):
    """Detect and enforce the response language from chat history."""

    name = "detect_user_language"
    description = (
        "Detect the user's language from chat messages and inject language instructions "
        "into prompt context before the assistant generates a response."
    )

    def run(self, chat=None, data=None, secrets=None, log=None):
        if data is None:
            data = {}

        prompt_params = data.setdefault("prompt_params", {})
        context = prompt_params.setdefault("context", {})

        first_user_message, last_user_message = self._get_user_messages(chat)

        first_lang_name, first_lang_code, first_reliable = self._detect_language(
            first_user_message
        )
        last_lang_name, last_lang_code, last_reliable = self._detect_language(
            last_user_message
        )

        if first_reliable:
            selected_name, selected_code = first_lang_name, first_lang_code
            policy_source = "first_user_message"
        elif last_reliable:
            selected_name, selected_code = last_lang_name, last_lang_code
            policy_source = "last_user_message_fallback"
        else:
            selected_name, selected_code = "English", "en"
            policy_source = "default_english"

        no_info_source = self._get_no_info_message(chat)
        translated_no_info = self._translate_no_info_message(
            no_info_source=no_info_source,
            target_code=selected_code,
        )

        context["Preferred response language"] = selected_name
        context["Response language policy"] = (
            "Always respond in the language of the first user message unless the user explicitly asks to switch language."
        )
        context["Message of not having information"] = translated_no_info

        if log:
            log(
                "DetectUserLanguageTool => selected="
                f"{selected_name} ({selected_code}), source={policy_source}, "
                f"first_reliable={first_reliable}, last_reliable={last_reliable}"
            )

        return {
            "selected_language": selected_name,
            "selected_language_code": selected_code,
            "policy_source": policy_source,
            "first_message_reliable": first_reliable,
            "last_message_reliable": last_reliable,
        }

    def _get_user_messages(self, chat):
        """Return first and last user messages from chat history."""
        empty = ""
        if chat is None or not hasattr(chat, "messages"):
            return empty, empty

        try:
            user_messages = chat.messages.filter(role="user").order_by("msg_num")

            first_obj = (
                user_messages.first() if hasattr(user_messages, "first") else None
            )
            last_obj = user_messages.last() if hasattr(user_messages, "last") else None

            first_text = getattr(first_obj, "content", "") if first_obj else ""
            last_text = getattr(last_obj, "content", "") if last_obj else ""
            return first_text or "", last_text or ""
        except Exception:
            return empty, empty

    def _get_no_info_message(self, chat):
        """Get the current no-information message from assistant config."""
        default_message = "I don't have information on that topic."

        try:
            assistant = getattr(chat, "assistant", None)
            message = getattr(assistant, "not_info_message", None)
            return message or default_message
        except Exception:
            return default_message

    def _detect_language(self, text):
        """Detect language from text with pycld2, returning safe defaults."""
        if not text or not text.strip():
            return "English", "en", False

        try:
            import pycld2 as cld2

            is_reliable, _text_bytes_found, details = cld2.detect(text)
            if not details:
                return "English", "en", False

            lang_name = details[0][0] or "English"
            lang_code = self._normalize_lang_code(details[0][1])
            return lang_name, lang_code, bool(is_reliable)
        except Exception:
            return "English", "en", False

    def _normalize_lang_code(self, code):
        """Normalize detected language codes into translator-safe two-letter codes."""
        if not code:
            return "en"

        normalized = str(code).strip().lower().replace("_", "-")

        aliases = {
            "zh-hans": "zh",
            "zh-hant": "zh",
            "pt-br": "pt",
            "pt-pt": "pt",
        }

        if normalized in aliases:
            return aliases[normalized]

        if "-" in normalized:
            normalized = normalized.split("-", 1)[0]

        return normalized[:2] if normalized else "en"

    def _translate_no_info_message(self, no_info_source, target_code):
        """Translate no-information message to target language with safe fallback."""
        if not no_info_source:
            return "I don't have information on that topic."

        if not target_code or target_code == "en":
            return no_info_source

        source_lang_name, source_lang_code, source_reliable = self._detect_language(
            no_info_source
        )
        source_code = source_lang_code if source_reliable else "en"

        try:
            from translate import Translator

            translator = Translator(to_lang=target_code, from_lang=source_code)
            translated = translator.translate(no_info_source)
            return translated or no_info_source
        except Exception:
            return no_info_source


class CogSolScaffoldGenerator(BaseTool):
    """Generate boilerplate code for CogSol Framework components."""
    
    name = "cogsol_scaffold_generator"
    description = """Generate ready-to-use boilerplate code for CogSol Framework components.
    Use this tool when the user wants to create a new agent, tool, retrieval tool, FAQ, 
    fixed response, lesson, topic, metadata config, ingestion config, or retrieval.
    Returns properly formatted Python code that can be copied and used directly."""

    @tool_params(
        component_type={
            "description": "Type of component to generate: 'agent', 'tool', 'retrieval_tool', 'faq', 'fixed_response', 'lesson', 'topic', 'metadata_config', 'ingestion_config', or 'retrieval'",
            "type": "string",
            "required": True
        },
        name={
            "description": "Name for the component (e.g., 'CustomerSupport', 'ProductSearch'). Will be used as class name.",
            "type": "string",
            "required": True
        },
        description={
            "description": "Brief description of what this component does. Used in docstrings and description fields.",
            "type": "string",
            "required": False
        },
        extra_options={
            "description": "Optional JSON string with extra options. For tools: parameters list. For agents: tool names, temperature. For retrievals: topic name, num_refs.",
            "type": "string",
            "required": False
        }
    )
    def run(self, chat=None, data=None, secrets=None, log=None, component_type: str = "", name: str = "", description: str = "", extra_options: str = ""):
        """
        component_type: The type of CogSol component to generate.
        name: The name for the new component class.
        description: Description of what the component does.
        extra_options: Additional configuration as JSON string.
        """
        import json
        
        if not component_type or not name:
            return "Error: Both 'component_type' and 'name' are required."
        
        # Parse extra options if provided
        options = {}
        if extra_options:
            try:
                options = json.loads(extra_options)
            except json.JSONDecodeError:
                pass  # Use empty options if parsing fails
        
        # Clean the name to be a valid Python class name
        class_name = self._to_class_name(name)
        snake_name = self._to_snake_case(name)
        desc = description or f"A {component_type} for {name}"
        
        generators = {
            "agent": self._generate_agent,
            "tool": self._generate_tool,
            "retrieval_tool": self._generate_retrieval_tool,
            "faq": self._generate_faq,
            "fixed_response": self._generate_fixed_response,
            "lesson": self._generate_lesson,
            "topic": self._generate_topic,
            "metadata_config": self._generate_metadata_config,
            "ingestion_config": self._generate_ingestion_config,
            "retrieval": self._generate_retrieval,
        }
        
        generator = generators.get(component_type.lower())
        if not generator:
            valid_types = ", ".join(generators.keys())
            return f"Error: Unknown component type '{component_type}'. Valid types are: {valid_types}"
        
        code = generator(class_name, snake_name, desc, options)
        
        return f"## Generated {component_type.replace('_', ' ').title()} Code\n\n```python\n{code}\n```\n\n**Next steps:**\n{self._get_next_steps(component_type, class_name, snake_name)}"
    
    def _to_class_name(self, name: str) -> str:
        """Convert name to PascalCase class name."""
        # Remove non-alphanumeric chars and split
        import re
        words = re.split(r'[\s_\-]+', name)
        return ''.join(word.capitalize() for word in words if word)
    
    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        import re
        # Insert underscore before uppercase letters and convert to lowercase
        s1 = re.sub(r'[\s\-]+', '_', name)
        s2 = re.sub(r'([a-z])([A-Z])', r'\1_\2', s1)
        return s2.lower()
    
    def _generate_agent(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        tools_import = ""
        tools_list = "[]"
        if options.get("tools"):
            tool_names = options["tools"]
            tools_import = f"\nfrom .tools import {', '.join(tool_names)}"
            tools_list = f"[{', '.join(f'{t}()' for t in tool_names)}]"
        
        temperature = options.get("temperature", 0.3)
        
        return f'''from cogsol.agents import BaseAgent, genconfigs
from cogsol.prompts import Prompts{tools_import}


class {class_name}Agent(BaseAgent):
    """
    {desc}
    """
    # Core configuration
    system_prompt = Prompts.load("{snake_name}.md")
    generation_config = genconfigs.QA()
    temperature = {temperature}
    
    # Tools
    tools = {tools_list}
    pretools = []
    
    # Limits
    max_interactions = 20
    user_message_length = 2048
    consecutive_tool_calls_limit = 5
    
    # Behaviors
    initial_message = "Hello! How can I help you today?"
    no_information_message = "I don't have information on that topic."
    
    # Features
    streaming = False
    realtime = False
    
    class Meta:
        name = "{class_name}Agent"
        chat_name = "{class_name.replace('_', ' ')}"
        # logo_url = "https://example.com/logo.png"
        # primary_color = "#007bff"'''

    def _generate_tool(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        # Build parameters from options or use default example
        params = options.get("parameters", [
            {"name": "query", "description": "Input query", "type": "string", "required": True}
        ])
        
        param_decorators = []
        param_args = []
        param_docs = []
        
        for p in params:
            p_name = p.get("name", "param") if isinstance(p, dict) else p
            p_desc = p.get("description", "Parameter description") if isinstance(p, dict) else "Parameter description"
            p_type = p.get("type", "string") if isinstance(p, dict) else "string"
            p_required = p.get("required", False) if isinstance(p, dict) else False
            
            param_decorators.append(
                f'        {p_name}={{"description": "{p_desc}", "type": "{p_type}", "required": {p_required}}}'
            )
            
            py_type = {"string": "str", "integer": "int", "boolean": "bool", "number": "float"}.get(p_type, "str")
            default = {"str": '""', "int": "0", "bool": "False", "float": "0.0"}.get(py_type, '""')
            param_args.append(f"{p_name}: {py_type} = {default}")
            param_docs.append(f"        {p_name}: {p_desc}")
        
        params_str = ",\n".join(param_decorators)
        args_str = ", ".join(param_args)
        docs_str = "\n".join(param_docs)
        
        return f'''from cogsol.tools import BaseTool, tool_params


class {class_name}Tool(BaseTool):
    """
    {desc}
    """
    name = "{snake_name}"
    description = "{desc}"

    @tool_params(
{params_str}
    )
    def run(self, chat=None, data=None, secrets=None, log=None, {args_str}):
        """
{docs_str}
        """
        if log:
            log(f"Running {class_name}Tool...")
        
        # TODO: Implement your tool logic here
        result = "Tool executed successfully"
        
        return result'''

    def _generate_retrieval_tool(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        retrieval_class = options.get("retrieval_class", f"{class_name}Retrieval")
        
        return f'''from cogsol.tools import BaseRetrievalTool
from data.retrievals import {retrieval_class}


class {class_name}Search(BaseRetrievalTool):
    """
    {desc}
    """
    name = "{snake_name}_search"
    description = "{desc}"
    retrieval = {retrieval_class}()
    # Optional: customize parameters (default includes 'question')
    # parameters = [
    #     {{"name": "question", "description": "Search query", "type": "string", "required": True}}
    # ]'''

    def _generate_faq(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        question = options.get("question", "What is the answer to this common question?")
        answer = options.get("answer", desc)
        
        return f'''from cogsol.tools import BaseFAQ


class {class_name}FAQ(BaseFAQ):
    """
    {desc}
    """
    question = "{question}"
    answer = """{answer}"""'''

    def _generate_fixed_response(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        key = options.get("key", snake_name)
        response = options.get("response", desc)
        
        return f'''from cogsol.tools import BaseFixedResponse


class {class_name}Fixed(BaseFixedResponse):
    """
    {desc}
    """
    key = "{key}"
    response = """{response}"""'''

    def _generate_lesson(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        content = options.get("content", desc)
        context = options.get("context_of_application", "general")
        
        return f'''from cogsol.tools import BaseLesson


class {class_name}Lesson(BaseLesson):
    """
    {desc}
    """
    name = "{class_name.replace('_', ' ')}"
    content = """{content}"""
    context_of_application = "{context}"'''

    def _generate_topic(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        return f'''from cogsol.content import BaseTopic


class {class_name}Topic(BaseTopic):
    """
    {desc}
    """
    name = "{snake_name}"

    class Meta:
        description = "{desc}"'''

    def _generate_metadata_config(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        meta_type = options.get("type", "STRING")
        values = options.get("possible_values", [])
        values_str = f"\n    possible_values = {values}" if values else ""
        
        return f'''from cogsol.content import BaseMetadataConfig, MetadataType


class {class_name}Metadata(BaseMetadataConfig):
    """
    {desc}
    """
    name = "{snake_name}"
    type = MetadataType.{meta_type.upper()}{values_str}
    filtrable = True
    required = False'''

    def _generate_ingestion_config(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        pdf_mode = options.get("pdf_parsing_mode", "OCR")
        chunking = options.get("chunking_mode", "AGENTIC_SPLITTER")
        max_size = options.get("max_size_block", 2000)
        
        return f'''from cogsol.content import BaseIngestionConfig, PDFParsingMode, ChunkingMode


class {class_name}Config(BaseIngestionConfig):
    """
    {desc}
    """
    name = "{snake_name}"
    pdf_parsing_mode = PDFParsingMode.{pdf_mode}
    chunking_mode = ChunkingMode.{chunking}
    max_size_block = {max_size}
    chunk_overlap = 100'''

    def _generate_retrieval(self, class_name: str, snake_name: str, desc: str, options: dict) -> str:
        topic = options.get("topic", snake_name)
        num_refs = options.get("num_refs", 10)
        
        return f'''from cogsol.content import BaseRetrieval, ReorderingStrategy
# from data.formatters import DetailedFormatter  # Uncomment if using custom formatters


class {class_name}Retrieval(BaseRetrieval):
    """
    {desc}
    """
    name = "{snake_name}_search"
    topic = "{topic}"
    num_refs = {num_refs}
    reordering = False
    strategy_reordering = ReorderingStrategy.NONE
    # formatters = {{"Text Document": DetailedFormatter}}  # Uncomment for custom formatting
    filters = []'''

    def _get_next_steps(self, component_type: str, class_name: str, snake_name: str) -> str:
        steps = {
            "agent": f"""1. Create the prompt file at `agents/{snake_name}agent/prompts/{snake_name}.md`
2. Add the agent file at `agents/{snake_name}agent/agent.py`
3. Create `__init__.py` that exports your agent
4. Run `python manage.py makemigrations agents` and `python manage.py migrate agents`""",
            
            "tool": """1. Add this class to `agents/tools.py` or `agents/<your_agent>/tools.py`
2. Import and add it to your agent's `tools` list
3. Implement the tool logic in the `run` method""",
            
            "retrieval_tool": """1. Ensure the referenced Retrieval exists in `data/retrievals.py`
2. Add this class to `agents/searches.py`
3. Import and add it to your agent's `tools` list""",
            
            "faq": """1. Add this class to `agents/<your_agent>/faqs.py`
2. The agent will automatically load FAQs from the faqs.py file""",
            
            "fixed_response": """1. Add this class to `agents/<your_agent>/fixed.py`
2. The agent will automatically load fixed responses""",
            
            "lesson": """1. Add this class to `agents/<your_agent>/lessons.py`
2. The agent will automatically load lessons""",
            
            "topic": f"""1. Create directory `data/{snake_name}/`
2. Add this code to `data/{snake_name}/__init__.py`
3. Create `data/{snake_name}/metadata.py` for metadata configs
4. Run migrations: `python manage.py makemigrations data` and `python manage.py migrate data`""",
            
            "metadata_config": """1. Add this class to `data/<topic>/metadata.py`
2. Run `python manage.py makemigrations data`
3. Run `python manage.py migrate data`""",
            
            "ingestion_config": f"""1. Add this class to `data/ingestion.py`
2. Use with: `python manage.py ingest <topic> <path> --ingestion-config {snake_name}`""",
            
            "retrieval": """1. Add this class to `data/retrievals.py`
2. Ensure the topic exists in `data/<topic>/`
3. Run `python manage.py makemigrations data` and `python manage.py migrate data`
4. Create a retrieval tool in `agents/searches.py` to use it"""
        }
        
        return steps.get(component_type, "Check the CogSol documentation for next steps.")
