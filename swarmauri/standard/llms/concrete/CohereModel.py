import json
import logging
from typing import List, Dict, Literal
import cohere
from swarmauri.core.typing import SubclassUnion

from swarmauri.standard.messages.base.MessageBase import MessageBase
from swarmauri.standard.messages.concrete.AgentMessage import AgentMessage
from swarmauri.standard.llms.base.LLMBase import LLMBase

class CohereModel(LLMBase):
    api_key: str
    allowed_models: List[str] = ['command-light',
    'command', 
    'command-r',
    'command-r-plus']
    name: str = "command-light"
    type: Literal['CohereModel'] = 'CohereModel'
    
    def _format_messages(self, messages: List[SubclassUnion[MessageBase]]) -> List[Dict[str,str]]:
        """
        Cohere utilizes the following roles: CHATBOT, SYSTEM, TOOL, USER
        """
        message_properties = ['content', 'role']

        messages = [message.model_dump(include=message_properties) for message in messages]
        for message in messages:
            message['message'] = message.pop('content')
            if message.get('role') == 'assistant':
                message['role'] = 'chatbot'
            message['role'] = message['role'].upper()
            del message['content']
        logging.info(messages)
        return messages


    def predict(self, 
        conversation, 
        temperature=0.7, 
        max_tokens=256):
        # Get next message
        next_message = conversation.history[-1].content

        # Format chat_history
        messages = self._format_messages(conversation.history[:-1])


        client = cohere.Client(api_key=self.api_key)
        response = client.chat(
            model=self.name,
            chat_history=messages,
            message=next_message,
            temperature=temperature,
            max_tokens=max_tokens,
            prompt_truncation='OFF',
            connectors=[]
        )
        
        result = json.loads(response.json())
        message_content = result['text']
        conversation.add_message(AgentMessage(content=message_content))
        return conversation