from typing import Dict, List, Any, Optional
import re
import logging

logger = logging.getLogger(__name__)


class IntentionRecognizer:
    def __init__(self, llm=None):
        self.llm = llm
        self._intent_patterns = {
            "bug统计": [
                r"多少.*bug",
                r"bug.*数量",
                r"统计.*缺陷",
                r"缺陷.*多少",
                r"新增.*bug",
            ],
            "缺陷分析": [
                r"分析.*bug",
                r"bug.*根因",
                r"为什么.*bug",
                r"缺陷.*分析",
            ],
            "缺陷详情": [
                r"查看.*缺陷",
                r".*详情",
                r"具体.*信息",
                r"PROJ-\d+",
            ],
            "代码评审": [
                r"评审",
                r"review",
                r"PR",
                r"pull.*request",
                r"代码.*审查",
            ],
            "MR安全扫描": [
                r"安全.*扫描",
                r"扫描.*MR",
                r"扫描.*PR",
                r"检测.*泄露",
                r"敏感.*信息",
                r"安全.*检测",
                r"env.*泄露",
                r"密码.*泄露",
                r"token.*泄露",
            ],
            "周报生成": [
                r"生成.*周报",
                r"周报",
                r"本周.*汇总",
                r"本周.*统计",
                r"本周.*报告",
            ],
            "构建查询": [
                r"构建.*状态",
                r"build.*成功",
                r"ci.*状态",
                r"pipeline",
                r"构建.*历史",
                r"构建.*成功",
                r"最近.*构建",
                r"ci.*成功",
            ],
            "构建分析": [
                r"为什么.*失败",
                r"构建.*分析",
                r"失败.*原因",
                r"build.*fail",
            ],
            "效能指标": [
                r"效能.*报表",
                r"成功率",
                r"构建.*指标",
                r"ci.*效能",
            ],
            "触发构建": [
                r"触发.*构建",
                r"重新.*构建",
                r"跑.*ci",
                r"启动.*构建",
            ],
            "效能报表": [
                r"研发.*报表",
                r"周报",
                r"效能.*报告",
            ],
            "交付周期": [
                r"交付.*周期",
                r"平均.*时间",
            ],
            "贡献统计": [
                r"贡献.*排行",
                r"谁.*代码",
                r"commit.*统计",
            ],
            "知识问答": [
                r"什么是",
                r"如何.*实现",
                r"架构.*是",
            ],
            "故障排查": [
                r"服务.*挂了",
                r"排查",
                r"问题.*在哪",
            ],
            "任务创建": [
                r"创建.*缺陷",
                r"新建.*bug",
            ],
            "状态更新": [
                r"更新.*状态",
                r"改成.*进行中",
                r"状态.*修改",
            ],
        }

    async def recognize(self, user_input: str) -> str:
        user_input_lower = user_input.lower()

        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    logger.debug(f"Matched intent '{intent}' with pattern '{pattern}'")
                    return intent

        if self.llm:
            try:
                llm_intent = await self._recognize_with_llm(user_input)
                if llm_intent:
                    return llm_intent
            except Exception as e:
                logger.warning(f"LLM recognition failed: {e}")

        return "unknown"

    async def _recognize_with_llm(self, user_input: str) -> Optional[str]:
        system_prompt = """你是一个意图识别专家。根据用户输入，返回最合适的意图类型。

可选意图类型：
- bug统计：查询Bug数量、统计Bug
- 缺陷分析：分析Bug原因、根因定位
- 缺陷详情：查看特定Bug的详细信息
- 代码评审：检查PR、CodeReview相关
- 构建查询：查询构建状态、历史
- 构建分析：分析构建失败原因
- 效能指标：构建成功率、效能数据
- 触发构建：手动触发CI/CD构建
- 效能报表：生成研发效能报告
- 交付周期：交付时间、周期分析
- 贡献统计：代码贡献排行
- 知识问答：技术问题咨询
- 故障排查：排查服务故障
- 任务创建：创建新缺陷/任务
- 状态更新：更新任务状态

只输出意图类型中的一种，不要输出其他内容。"""

        response = await self.llm.generate(user_input, system_prompt)
        if response:
            return response.strip()
        return None

    async def clarify(self, user_input: str, possible_intents: List[str]) -> Dict[str, Any]:
        return {
            "possible_intents": possible_intents[:3],
            "questions": [
                f"您是想了解【{intent}】相关的信息吗？" for intent in possible_intents[:3]
            ],
        }
