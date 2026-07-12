"""
AI 摘要处理器，支持多种 AI 模型提供商
"""
import asyncio
import json
import logging
import os
from typing import List, Tuple, Optional
from dataclasses import dataclass

from django.conf import settings

from summary.models import AIModelConfig

logger = logging.getLogger(__name__)

try:
    from pydantic_ai import Agent
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.models.groq import GroqModel
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openai import OpenAIProvider
    from pydantic_ai.providers.groq import GroqProvider
    from pydantic_ai.providers.anthropic import AnthropicProvider
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False
    logger.warning("pydantic-ai not installed")

try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False


@dataclass
class Block:
    id: str
    type: str
    content: str
    color: str = ""


@dataclass
class Section:
    title: str
    blocks: List[Block]


@dataclass
class MeetingNotes:
    meeting_name: str
    sections: List[Section]


@dataclass
class SummaryResponse:
    MeetingName: str
    People: dict
    SessionSummary: dict
    CriticalDeadlines: dict
    KeyItemsDecisions: dict
    ImmediateActionItems: dict
    NextSteps: dict
    MeetingNotes: dict


class SummaryProcessor:
    """AI 摘要处理器"""

    SYSTEM_PROMPT_TEMPLATE = """
你是一位专业的会议纪要整理助手。请根据以下会议转录文本，提取关键信息并生成结构化的会议纪要。

请按照以下结构输出 JSON 格式：
{{
    "MeetingName": "会议名称",
    "People": {{
        "title": "参会人员",
        "blocks": [
            {{"id": "1", "type": "bullet", "content": "人员姓名 (角色/部门)"}}
        ]
    }},
    "SessionSummary": {{
        "title": "会议概要",
        "blocks": [
            {{"id": "1", "type": "text", "content": "概要内容"}}
        ]
    }},
    "CriticalDeadlines": {{
        "title": "关键截止日期",
        "blocks": [
            {{"id": "1", "type": "bullet", "content": "截止日期: 任务描述"}}
        ]
    }},
    "KeyItemsDecisions": {{
        "title": "关键事项与决策",
        "blocks": [
            {{"id": "1", "type": "bullet", "content": "决策内容"}}
        ]
    }},
    "ImmediateActionItems": {{
        "title": "立即行动项",
        "blocks": [
            {{"id": "1", "type": "bullet", "content": "行动项 (负责人)"}}
        ]
    }},
    "NextSteps": {{
        "title": "后续步骤",
        "blocks": [
            {{"id": "1", "type": "bullet", "content": "后续计划"}}
        ]
    }},
    "MeetingNotes": {{
        "meeting_name": "会议名称",
        "sections": [
            {{
                "title": "自定义小节标题",
                "blocks": [
                    {{"id": "1", "type": "text", "content": "内容"}}
                ]
            }}
        ]
    }}
}}

Block 类型说明：
- "text": 普通文本段落
- "bullet": 列表项
- "heading1": 一级标题
- "heading2": 二级标题

注意：
1. 如果某部分没有相关信息，返回空的 blocks 数组
2. 转录可能有拼写错误，请根据上下文修正
3. 确保输出纯 JSON，不要包含 markdown 代码块标记
4. 输出语言: {language}

额外上下文: {custom_prompt}

会议转录文本：
---
{text}
---
"""

    def __init__(self):
        self.active_clients = []

    async def process_transcript(self, text: str, provider: str, model_name: str,
                                  chunk_size: int = 5000, overlap: int = 1000,
                                  custom_prompt: str = "", language: str = "zh") -> Tuple[int, List[str]]:
        """
        处理转录文本，生成结构化摘要
        """
        if not text:
            raise ValueError("Empty transcript text provided")

        if chunk_size <= 0:
            chunk_size = 5000
        if overlap < 0:
            overlap = 0
        if overlap >= chunk_size:
            overlap = chunk_size - 1

        step = chunk_size - overlap
        if step <= 0:
            step = 1000

        chunks = [text[i:i+chunk_size] for i in range(0, len(text), step)]
        num_chunks = len(chunks)
        logger.info(f"Split transcript into {num_chunks} chunks")

        all_results = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{num_chunks}...")
            try:
                result = await self._process_chunk(
                    chunk, provider, model_name,
                    custom_prompt, language
                )
                if result:
                    all_results.append(result)
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}: {e}")

        return num_chunks, all_results

    async def _process_chunk(self, text: str, provider: str, model_name: str,
                              custom_prompt: str, language: str) -> Optional[str]:
        """处理单个文本块"""
        prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
            text=text,
            custom_prompt=custom_prompt or "无",
            language=language,
        )

        if provider == "ollama":
            return await self._call_ollama(model_name, prompt)
        elif provider in ["claude", "groq", "openai", "custom"] and HAS_PYDANTIC_AI:
            return await self._call_pydantic_ai(provider, model_name, prompt)
        else:
            # 默认使用 Ollama
            return await self._call_ollama(model_name, prompt)

    async def _call_ollama(self, model_name: str, prompt: str) -> str:
        """调用 Ollama 模型"""
        if not HAS_OLLAMA:
            raise RuntimeError("Ollama not installed")

        ollama_host = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')

        try:
            client = ollama.AsyncClient(host=ollama_host)
            response = await asyncio.wait_for(
                client.chat(
                    model=model_name,
                    messages=[{
                        'role': 'user',
                        'content': prompt,
                    }],
                    stream=False,
                ),
                timeout=300,
            )
            return response['message']['content']
        except asyncio.TimeoutError as e:
            logger.error(f"Ollama timeout after 300s: {e}")
            raise RuntimeError("Ollama请求超时，请检查模型是否正常运行") from e
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise

    async def _call_pydantic_ai(self, provider: str, model_name: str, prompt: str) -> str:
        """调用 pydantic-ai 支持的模型"""
        if not HAS_PYDANTIC_AI:
            raise RuntimeError("pydantic-ai not installed")

        try:
            config = await self._get_model_config(provider)
            api_key = config.api_key if config else None
            base_url = config.base_url if config else None

            provider_kwargs = {"api_key": api_key}
            if base_url:
                provider_kwargs["base_url"] = base_url

            if provider == "claude":
                llm = AnthropicModel(model_name, provider=AnthropicProvider(**provider_kwargs))
            elif provider == "groq":
                llm = GroqModel(model_name, provider=GroqProvider(**provider_kwargs))
            elif provider in ["openai", "custom"]:
                llm = OpenAIModel(model_name, provider=OpenAIProvider(**provider_kwargs))
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            agent = Agent(model=llm)

            logger.info(f"Using {provider} to process the chunk of text: {prompt[:100]}...")
            result = await asyncio.wait_for(agent.run(prompt), timeout=300)
            result_text = result.data if hasattr(result, 'data') else str(result)
            logger.info(f"{provider} processed the chunk of text successfully. Result: {result_text[:100]}...")

            return result_text

        except Exception as e:
            logger.error(f"Pydantic-AI error: {e}")
            raise

    async def _get_model_config(self, provider: str):
        """获取模型配置"""
        from summary.models import AIModelConfig
        try:
            return await AIModelConfig.objects.aget(provider=provider, is_default=True)
        except AIModelConfig.DoesNotExist:
            return None

    def aggregate_summaries(self, all_json_data: List[str]) -> dict:
        """聚合多个 chunk 的摘要结果"""
        final_summary = {
            "MeetingName": "",
            "People": {"title": "参会人员", "blocks": []},
            "SessionSummary": {"title": "会议概要", "blocks": []},
            "CriticalDeadlines": {"title": "关键截止日期", "blocks": []},
            "KeyItemsDecisions": {"title": "关键事项与决策", "blocks": []},
            "ImmediateActionItems": {"title": "立即行动项", "blocks": []},
            "NextSteps": {"title": "后续步骤", "blocks": []},
            "MeetingNotes": {
                "meeting_name": "",
                "sections": []
            }
        }

        for json_str in all_json_data:
            try:
                data = json.loads(json_str)
                if data.get("MeetingName"):
                    final_summary["MeetingName"] = data["MeetingName"]

                for key in final_summary:
                    if key == "MeetingNotes" and key in data:
                        sections = data[key].get("sections", [])
                        for section in sections:
                            if not section.get("blocks"):
                                section["blocks"] = []
                        final_summary[key]["sections"].extend(sections)
                        if data[key].get("meeting_name"):
                            final_summary[key]["meeting_name"] = data[key]["meeting_name"]
                    elif key != "MeetingName" and key in data and isinstance(data[key], dict):
                        blocks = data[key].get("blocks", [])
                        if isinstance(blocks, list):
                            final_summary[key]["blocks"].extend(blocks)
                            # 同时添加到 MeetingNotes
                            section_exists = False
                            for section in final_summary["MeetingNotes"]["sections"]:
                                if section.get("title") == data[key].get("title"):
                                    section["blocks"].extend(blocks)
                                    section_exists = True
                                    break
                            if not section_exists:
                                final_summary["MeetingNotes"]["sections"].append({
                                    "title": data[key].get("title", key),
                                    "blocks": blocks.copy(),
                                })
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
            except Exception as e:
                logger.error(f"Error aggregating summary: {e}")

        return final_summary

    def cleanup(self):
        """清理资源"""
        self.active_clients.clear()
