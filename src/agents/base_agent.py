"""
Base Agent - Agent基类

提供所有Agent的统一接口和通用功能：
1. WorkspaceContextTool集成
2. 标准化的执行流程
3. 统一的错误处理
4. 日志记录
5. 性能监控
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import time
import structlog

from src.agents.states.pipeline_state_v2 import PipelineStateV2, WorkspaceContext
from src.tools.workspace import WorkspaceContextTool


logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """
    Agent基类
    
    所有专业Agent（OutlineAgent、CharacterAgent等）都应该继承此类。
    
    提供的通用功能：
    - 工作区上下文获取
    - 标准化执行流程
    - 错误处理和日志
    - 性能监控
    
    子类需要实现：
    - _execute_impl(): 实际的Agent逻辑
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        workspace_tool: Optional[WorkspaceContextTool] = None,
        llm_model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7
    ):
        """
        初始化BaseAgent
        
        Args:
            name: Agent名称
            description: Agent描述
            workspace_tool: 工作区上下文工具
            llm_model: LLM模型名称
            temperature: 温度参数
        """
        self.name = name
        self.description = description
        self.workspace_tool = workspace_tool or WorkspaceContextTool()
        self.llm_model = llm_model
        self.temperature = temperature
        
        self.logger = logger.bind(agent=name)
        self._execution_count = 0
        self._total_tokens = 0
        self._total_duration = 0.0
    
    async def execute(
        self,
        state: PipelineStateV2,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行Agent（公共接口）
        
        这是Agent的主要入口方法，处理通用逻辑并调用子类的实现。
        
        执行流程：
        1. 获取工作区上下文
        2. 执行前处理
        3. 调用子类实现（_execute_impl）
        4. 执行后处理
        5. 更新状态和统计
        
        Args:
            state: Pipeline状态
            **kwargs: 额外参数
        
        Returns:
            状态更新字典
        """
        start_time = time.time()
        self._execution_count += 1
        
        self.logger.info(
            "Agent execution started",
            execution_id=state.get("execution_id"),
            task=state.get("task", "")[:50]
        )
        
        try:
            # 1. 获取工作区上下文
            workspace_context = await self._get_workspace_context(state)
            
            # 2. 执行前处理
            await self._before_execute(state, workspace_context)
            
            # 3. 调用子类实现
            result = await self._execute_impl(
                state=state,
                workspace_context=workspace_context,
                **kwargs
            )
            
            # 4. 执行后处理
            result = await self._after_execute(state, result)
            
            # 5. 更新统计信息
            duration = time.time() - start_time
            self._update_stats(duration, result.get("tokens_used", 0))
            
            # 6. 添加执行时间到结果
            agent_execution_times = state.get("agent_execution_times", {}).copy()
            agent_execution_times[self.name] = duration
            result["agent_execution_times"] = agent_execution_times
            
            self.logger.info(
                "Agent execution completed",
                agent=self.name,
                duration=f"{duration:.2f}s",
                output_length=len(str(result.get("output", "")))
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            self.logger.error(
                "Agent execution failed",
                agent=self.name,
                error=str(e),
                duration=f"{duration:.2f}s",
                exc_info=True
            )
            
            # 返回错误状态
            return {
                "errors": [f"{self.name} failed: {str(e)}"],
                "agent_outputs": {
                    self.name: {
                        "success": False,
                        "error": str(e)
                    }
                }
            }
    
    async def _get_workspace_context(
        self,
        state: PipelineStateV2
    ) -> Optional[WorkspaceContext]:
        """
        获取工作区上下文
        
        优先使用state中已有的上下文，如果没有则通过WorkspaceContextTool获取。
        
        Args:
            state: Pipeline状态
        
        Returns:
            工作区上下文（如果可用）
        """
        # 优先使用已有的上下文
        if state.get("workspace_context"):
            try:
                return WorkspaceContext(**state["workspace_context"])
            except Exception as e:
                self.logger.warning(
                    "Failed to parse existing workspace context",
                    error=str(e)
                )
        
        # 如果没有，尝试获取新的上下文
        if self.workspace_tool and state.get("project_id"):
            try:
                structured_context = await self.workspace_tool.get_context(
                    user_input=state.get("task", ""),
                    project_id=state["project_id"],
                    user_id=state.get("user_id")
                )
                
                # 转换为WorkspaceContext
                return WorkspaceContext(
                    task_type=structured_context.task_type,
                    project_info=structured_context.project_info,
                    characters=structured_context.characters,
                    outline_nodes=structured_context.outline_nodes,
                    previous_content=structured_context.previous_content,
                    retrieved_docs=structured_context.retrieved_docs
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to get workspace context",
                    error=str(e)
                )
        
        return None
    
    async def _before_execute(
        self,
        state: PipelineStateV2,
        workspace_context: Optional[WorkspaceContext]
    ) -> None:
        """
        执行前处理（子类可重写）
        
        Args:
            state: Pipeline状态
            workspace_context: 工作区上下文
        """
        pass
    
    @abstractmethod
    async def _execute_impl(
        self,
        state: PipelineStateV2,
        workspace_context: Optional[WorkspaceContext],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Agent的实际执行逻辑（子类必须实现）
        
        Args:
            state: Pipeline状态
            workspace_context: 工作区上下文
            **kwargs: 额外参数
        
        Returns:
            状态更新字典，应包含：
            - agent_outputs: {agent_name: {...}}
            - 其他需要更新的状态字段
        """
        raise NotImplementedError("Subclass must implement _execute_impl")
    
    async def _after_execute(
        self,
        state: PipelineStateV2,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行后处理（子类可重写）
        
        Args:
            state: Pipeline状态
            result: 执行结果
        
        Returns:
            处理后的结果
        """
        # 添加推理步骤
        if "reasoning" not in result:
            result["reasoning"] = [f"{self.name} executed successfully"]
        
        return result
    
    def _update_stats(self, duration: float, tokens: int) -> None:
        """
        更新统计信息
        
        Args:
            duration: 执行时间
            tokens: Token使用量
        """
        self._total_duration += duration
        self._total_tokens += tokens
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取Agent统计信息
        
        Returns:
            统计信息
        """
        avg_duration = (
            self._total_duration / self._execution_count
            if self._execution_count > 0
            else 0
        )
        
        return {
            "name": self.name,
            "execution_count": self._execution_count,
            "total_tokens": self._total_tokens,
            "total_duration": round(self._total_duration, 2),
            "avg_duration": round(avg_duration, 2),
            "avg_tokens_per_execution": (
                self._total_tokens // self._execution_count
                if self._execution_count > 0
                else 0
            )
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self._execution_count = 0
        self._total_tokens = 0
        self._total_duration = 0.0
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<{self.__class__.__name__}(name='{self.name}')>"


# ===== LLM辅助方法 =====

class LLMAgentMixin:
    """
    LLM Agent Mixin
    
    提供LLM相关的通用方法，可以被Agent类混入使用。
    """
    
    def build_system_prompt(self, role_description: str, guidelines: List[str]) -> str:
        """
        构建系统提示词
        
        Args:
            role_description: 角色描述
            guidelines: 指导原则列表
        
        Returns:
            系统提示词
        """
        guidelines_text = "\n".join([f"- {g}" for g in guidelines])
        
        return f"""{role_description}

指导原则：
{guidelines_text}

请严格按照指导原则执行任务，确保输出高质量的结果。"""
    
    def build_user_prompt_with_context(
        self,
        task: str,
        workspace_context: Optional[WorkspaceContext],
        additional_context: Optional[str] = None
    ) -> str:
        """
        构建包含上下文的用户提示词
        
        Args:
            task: 任务描述
            workspace_context: 工作区上下文
            additional_context: 额外上下文
        
        Returns:
            用户提示词
        """
        sections = [f"## 任务\n{task}\n"]
        
        # 添加工作区上下文
        if workspace_context:
            sections.append("## 工作区上下文")
            
            if workspace_context.project_info:
                sections.append(f"**项目**: {workspace_context.project_info.get('title', 'N/A')}")
            
            if workspace_context.characters:
                sections.append(f"**相关角色**: {len(workspace_context.characters)}个")
                for char in workspace_context.characters[:3]:
                    sections.append(f"  - {char.get('name', 'N/A')}")
            
            if workspace_context.outline_nodes:
                sections.append(f"**大纲节点**: {len(workspace_context.outline_nodes)}个")
            
            if workspace_context.previous_content:
                preview = workspace_context.previous_content[-200:]
                sections.append(f"**前序内容**: ...{preview}")
            
            sections.append("")
        
        # 添加额外上下文
        if additional_context:
            sections.append(f"## 额外信息\n{additional_context}\n")
        
        return "\n".join(sections)
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算Token数量（粗略估计）
        
        Args:
            text: 文本
        
        Returns:
            估算的Token数
        """
        # 简单估算：英文1个词约1.3个token，中文1个字约1.5个token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        return int(chinese_chars * 1.5 + other_chars / 4)


# ===== 示例Agent实现 =====

class ExampleAgent(BaseAgent, LLMAgentMixin):
    """
    示例Agent实现
    
    展示如何继承BaseAgent并实现自定义逻辑。
    """
    
    def __init__(self, workspace_tool: Optional[WorkspaceContextTool] = None):
        """初始化"""
        super().__init__(
            name="example_agent",
            description="示例Agent，用于演示BaseAgent的使用",
            workspace_tool=workspace_tool
        )
    
    async def _execute_impl(
        self,
        state: PipelineStateV2,
        workspace_context: Optional[WorkspaceContext],
        **kwargs
    ) -> Dict[str, Any]:
        """
        实现具体逻辑
        
        Args:
            state: Pipeline状态
            workspace_context: 工作区上下文
            **kwargs: 额外参数
        
        Returns:
            状态更新
        """
        # 1. 构建提示词
        system_prompt = self.build_system_prompt(
            role_description="你是一个示例Agent",
            guidelines=["遵循用户指令", "生成高质量内容"]
        )
        
        user_prompt = self.build_user_prompt_with_context(
            task=state.get("task", ""),
            workspace_context=workspace_context
        )
        
        # 2. 调用LLM（这里只是示例）
        output = f"Processed task: {state.get('task', '')}"
        
        # 3. 返回结果
        return {
            "agent_outputs": {
                self.name: {
                    "success": True,
                    "output": output
                }
            },
            "reasoning": [f"{self.name}: 成功处理任务"],
            "tokens_used": self.estimate_tokens(system_prompt + user_prompt + output)
        }

