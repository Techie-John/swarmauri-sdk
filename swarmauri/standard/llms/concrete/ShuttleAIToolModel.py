import json
import logging
from typing import List, Literal, Dict, Any
import requests 
from swarmauri.core.typing import SubclassUnion

from swarmauri.standard.messages.base.MessageBase import MessageBase
from swarmauri.standard.messages.concrete.AgentMessage import AgentMessage
from swarmauri.standard.messages.concrete.FunctionMessage import FunctionMessage
from swarmauri.standard.llms.base.LLMBase import LLMBase
from swarmauri.standard.schema_converters.concrete.ShuttleAISchemaConverter import ShuttleAISchemaConverter

class ShuttleAIToolModel(LLMBase):
    api_key: str
    allowed_models: List[str] = [
        "shuttle-2-turbo",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-0125-preview",
        "gpt-4-1106-preview",
        "gpt-4-0613",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-1106",
        "claude-instant-1.1",
        "wizardlm-2-8x22b",
        "mistral-7b-instruct-v0.2",
        "gemini-1.5-pro-latest",
        "gemini-1.0-pro-latest"
    ]
    name: str = "shuttle-2-turbo"
    type: Literal['ShuttleAIToolModel'] = 'ShuttleAIToolModel'
    
    def _schema_convert_tools(self, tools) -> List[Dict[str, Any]]:
        return [ShuttleAISchemaConverter().convert(tools[tool]) for tool in tools]

    def _format_messages(self, messages: List[SubclassUnion[MessageBase]]) -> List[Dict[str, str]]:
        message_properties = ['content', 'role', 'name', 'tool_call_id', 'tool_calls']
        formatted_messages = [message.model_dump(include=message_properties, exclude_none=True) for message in messages]
        return formatted_messages
    
    def predict(self, 
        conversation, 
        toolkit=None, 
        tool_choice=None, 
        temperature=0.7, 
        max_tokens=1024, 
        top_p=1.0, 
        internet=True, 
        raw=False, 
        image=None, 
        citations=True, 
        tone='precise'):

        formatted_messages = self._format_messages(conversation.history)

        if toolkit and not tool_choice:
            tool_choice = "auto"

        url = "https://api.shuttleai.app/v1/chat/completions"
        headers = { 
            "Authorization": f"Bearer {self.api_key}", 
            "Content-Type": "application/json", 
        }

        formatted_messages = self._format_messages(conversation.history) 
 
        payload = { 
            "model": self.name, 
            "messages": formatted_messages, 
            "max_tokens": max_tokens, 
            "temperature": temperature, 
            "top_p": top_p, 
            "internet": internet, 
            "raw": raw, 
            "image": image, 
            "tool_choice": tool_choice, 
            "tools": self._schema_convert_tools(toolkit.tools),
        } 

        if self.name in ['gpt-4-bing', 'gpt-4-turbo-bing']: 
            payload['tone'] = tone 
            payload['citations'] = citations  

        agent_response = requests.request("POST", url, json=payload, headers=headers) 
        logging.info(agent_response.json()) 

        try: 
            messages = [formatted_messages[-1], agent_response.json()['choices'][0]['message']['content']]
        except Exception as error: 
            logging.warn(error) 
        tool_calls = agent_response.json()['choices'][0]['message'].get('tool_calls', None) 
        if tool_calls:
            for tool_call in tool_calls:
                func_name = tool_call['function']['name'] 
                func_call = toolkit.get_tool_by_name(func_name)
                func_args = json.loads(tool_call['function']['arguments']) 
                func_result = func_call(**func_args)
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": func_name,
                        "content": func_result,
                    }
                )
        logging.info(f'messages: {messages}')
        logging.info(f"agent_response: {agent_response.json()}")
        agent_message = AgentMessage(content=agent_response.json()['choices'][0]['message']['content'])
        conversation.add_message(agent_message)
        logging.info(f"conversation: {conversation}")
        return conversation