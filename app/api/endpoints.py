from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from app.agents.core import AgentCore, AgentConfig
from app.agents.intention import IntentionRecognizer
from app.agents.decompose import TaskDecomposer
from app.agents.executor import ToolExecutor
from app.agents.reflect import Reflector
from app.memory.manager import MemoryManager
from app.memory.context import ContextBuilder
from app.tools.github_client import GitHubClient
from app.tools.jira_client import JiraClient
from app.tools.cicd_client import CICDClient
from app.llm.client import llm_client
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["agent"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    intent: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str


class ToolResult(BaseModel):
    tool: str
    result: Any
    duration_ms: float


_agent_core: Optional[AgentCore] = None
_memory_manager: Optional[MemoryManager] = None
_executor: Optional[ToolExecutor] = None


def get_agent_components():
    global _agent_core, _memory_manager, _executor

    if _agent_core is None:
        llm_client.initialize()

        github_client = GitHubClient(
            token=settings.github_token,
            owner=settings.github_owner,
            repo=settings.github_repo,
        )
        jira_client = JiraClient(
            url=settings.jira_url,
            email=settings.jira_email,
            api_token=settings.jira_api_token,
        )
        cicd_client = CICDClient(github_token=settings.github_token)

        intention_recognizer = IntentionRecognizer(llm=llm_client if llm_client.is_available() else None)
        task_decomposer = TaskDecomposer()
        executor = ToolExecutor()
        executor.set_clients(github_client, jira_client, cicd_client)
        reflector = Reflector(max_retries=3)

        agent_config = AgentConfig(
            max_retries=3,
            enable_reflection=True,
            enable_memory=True,
            enable_rag=True,
        )

        _agent_core = AgentCore(config=agent_config)
        _agent_core.set_components(
            intention_recognizer=intention_recognizer,
            task_decomposer=task_decomposer,
            executor=executor,
            reflector=reflector,
        )

        _executor = executor
        _memory_manager = MemoryManager()

    return _agent_core, _memory_manager, _executor


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())

    agent, memory_manager, _ = get_agent_components()

    try:
        result = await agent.run(request.message, session_id)

        if memory_manager:
            await memory_manager.store_interaction(
                role="user",
                content=request.message,
                metadata={"intent": result.get("intent"), "session_id": session_id},
            )
            await memory_manager.store_interaction(
                role="assistant",
                content=str(result.get("result", "")),
                metadata={"session_id": session_id},
            )

        if llm_client.is_available():
            formatted_message = await _generate_llm_response(result, request.message)
        else:
            formatted_message = _format_chat_result(result)

        return ChatResponse(
            session_id=session_id,
            message=formatted_message,
            intent=result.get("intent", "unknown"),
            success=result.get("success", False),
            result=result,
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        return ChatResponse(
            session_id=session_id,
            message=f"Error: {str(e)}",
            intent="error",
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat(),
        )


def _format_chat_result(result: Dict[str, Any]) -> str:
    if not result:
        return "处理完成，无返回结果"

    step_results = result.get("step_results", [])
    if not step_results:
        return str(result.get("result", result))

    output_parts = []
    for sr in step_results:
        tool = sr.get("tool", "unknown")
        if sr.get("success"):
            tool_result = sr.get("result", {})

            if isinstance(tool_result, list):
                if tool == "jira_get_bugs" and len(tool_result) > 0:
                    output_parts.append(f"共发现 {len(tool_result)} 个Bug：")
                    for bug in tool_result[:5]:
                        output_parts.append(f"  - {bug.get('key')}: {bug.get('summary', '无描述')}")
                elif tool == "github_get_pulls" and len(tool_result) > 0:
                    output_parts.append(f"共 {len(tool_result)} 个PR待评审：")
                    for pr in tool_result[:5]:
                        output_parts.append(f"  - #{pr.get('number')}: {pr.get('title', '无标题')}")
                elif tool == "github_get_commits" and len(tool_result) > 0:
                    output_parts.append(f"最近 {len(tool_result)} 条提交：")
                    for commit in tool_result[:5]:
                        output_parts.append(f"  - {commit.get('message', '无描述')[:50]}...")
                elif tool == "cicd_get_build_history" and len(tool_result) > 0:
                    output_parts.append(f"最近 {len(tool_result)} 次构建：")
                    for b in tool_result[:5]:
                        status = "成功" if b.get("conclusion") == "success" else "失败"
                        output_parts.append(f"  - {b.get('workflow_name', 'workflow')} #{b.get('run_number', '?')}: {status}")
                else:
                    output_parts.append(f"{tool}返回{len(tool_result)}条数据")

            elif isinstance(tool_result, dict):
                if "success_rate" in tool_result:
                    rate = tool_result.get("success_rate", 0)
                    total = tool_result.get("total_builds", 0)
                    output_parts.append(f"本周构建成功率：{rate}%（共{total}次构建）")
                elif "builds" in tool_result:
                    builds = tool_result["builds"]
                    output_parts.append(f"最近 {len(builds)} 次构建：")
                    for b in builds[:5]:
                        status = "成功" if b.get("status") == "success" else "失败"
                        output_parts.append(f"  - {b.get('workflow', 'workflow')} #{b.get('run_number', '?')}: {status}")
                else:
                    output_parts.append(str(tool_result))
            else:
                output_parts.append(str(tool_result))
        else:
            output_parts.append(f"{tool}: 执行失败 - {sr.get('error', '未知错误')}")

    return "\n".join(output_parts) if output_parts else str(result)


async def _generate_llm_response(result: Dict[str, Any], original_question: str) -> str:
    intent = result.get("intent", "unknown")
    step_results = result.get("step_results", [])

    data_summary = []
    for sr in step_results:
        if sr.get("success"):
            tool_result = sr.get("result", {})
            if isinstance(tool_result, list):
                data_summary.append(f"{sr.get('tool')}返回了{len(tool_result)}条数据")
            elif isinstance(tool_result, dict):
                data_summary.append(f"{sr.get('tool')}返回数据: {tool_result}")

    system_prompt = """你是一个研发效能助手。根据查询到的数据，用自然语言回答用户的问题。
数据是什么就如实说什么，不要编造数据。
如果数据较少或为空，直接说明即可。
回答要简洁有条理。"""

    data_str = "\n".join(data_summary) if data_summary else "无数据"
    user_prompt = f"""用户问题：{original_question}
意图类型：{intent}
查询到的数据：
{data_str}

请用自然语言回答用户的问题："""

    response = await llm_client.generate(user_prompt, system_prompt)
    if response:
        return response

    return _format_chat_result(result)


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    _, memory_manager, _ = get_agent_components()

    if not memory_manager:
        return {"history": []}

    context = await memory_manager.get_relevant_context(session_id)
    return {"session_id": session_id, "context": context}


@router.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    _, memory_manager, _ = get_agent_components()

    if memory_manager:
        memory_manager.clear_short_term()

    return {"message": "Session cleared", "session_id": session_id}


@router.get("/intents")
async def list_intents():
    return {
        "intents": [
            "bug统计",
            "缺陷分析",
            "缺陷详情",
            "代码评审",
            "构建查询",
            "构建分析",
            "效能指标",
            "触发构建",
            "效能报表",
            "交付周期",
            "贡献统计",
            "知识问答",
            "故障排查",
            "任务创建",
            "状态更新",
        ]
    }


@router.get("/tools")
async def list_tools():
    return {
        "tools": [
            "jira_get_issues",
            "jira_get_bugs",
            "jira_get_issue",
            "github_get_issues",
            "github_get_commits",
            "github_get_pulls",
            "github_get_workflow_runs",
            "cicd_get_build_history",
            "cicd_get_workflow_logs",
            "cicd_get_metrics",
            "cicd_trigger_workflow",
        ]
    }
