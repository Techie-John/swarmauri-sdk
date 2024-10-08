import json
from typing import List, Dict, Literal
import ai21 
from ai21.models.chat import ChatMessage 
from swarmauri.core.typing import SubclassUnion

from swarmauri.standard.messages.base.MessageBase import MessageBase
from swarmauri.standard.messages.concrete.AgentMessage import AgentMessage
from swarmauri.standard.llms.base.LLMBase import LLMBase

class AI21StudioModel(LLMBase):
    api_key: str
    allowed_models: List[str] = ['j2-light', 
                                 'j2-light-instruct', 
                                 'j2-mid', 
                                 'j2-mid-instruct', 
                                 'j2-ultra', 
                                 'j2-ultra-instruct', 
                                 'j2-grande-chat', 
                                 'j2-jumbo-chat',
                                 'jamba-instruct'
                                 ]
    name: str = "j2-light"
    type: Literal['AI21StudioModel'] = 'AI21StudioModel'

    def _format_messages(self, messages: List[SubclassUnion[MessageBase]]) -> List[Dict[str, str]]:
       # Get only the properties that we require
        message_properties = ["content", "role"]

        # Exclude FunctionMessages
        formatted_messages = [ChatMessage(content=message.content, role=message.role) for message in messages if message.role != 'system']
        return formatted_messages

    def _get_system_context(self, messages: List[SubclassUnion[MessageBase]]) -> str:
        system_context = None
        for message in messages:
            if message.role == 'system':
                system_context = message.content
        return system_context

    
    def predict(self, 
        conversation, 
        temperature=0.7, 
        max_tokens=256, 
        top_p=1.0, 
        stop='\n', 
        n=1, 
        stream=False): 
        ''' 
        Args: 
            top_p (0.01 to 1.0)  Limit the pool of next tokens in each step to the top {top_p*100} percentile of possible tokens
            stop: stop the message when model generates one of these strings. 
            n: how many chat responses to generate
            stream: whether or not to stream the result, for long answers. if set to true n must be 1. 
        '''

        # Create client
        client = ai21.AI21Client(api_key=self.api_key)
        
        # Get system_context from last message with system context in it
        system_context = self._get_system_context(conversation.history)
        formatted_messages = self._format_messages(conversation.history)

        if system_context:
            response = client.chat.completions.create(
                model=self.name,
                messages=formatted_messages,
                system=system_context,
                temperature=temperature,
                max_tokens=max_tokens, 
                top_p=top_p, 
                stop=stop, 
                n=n, 
                stream=stream
            )
        else:
            response = client.chat.completions.create(
                model=self.name,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens, 
                top_p=top_p, 
                stop=stop, 
                n=n, 
                stream=stream
            )
        
        message_content = response.content[0].text
        conversation.add_message(AgentMessage(content=message_content))
        
        return conversation
