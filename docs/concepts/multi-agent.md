# 多 Agent 协作

本文档介绍如何在 Qingyu Backend AI 中实现多个 Agent 之间的协作和通信。

## 概述

多 Agent 系统允许多个专门的 Agent 协同工作，每个 Agent 负责特定的任务，通过消息传递和事件系统进行协作。

### 协作模式

```
┌─────────────────────────────────────────────────────────┐
│                    Coordinator                          │
│  (协调其他 Agent，分发任务)                              │
└───┬─────────┬─────────┬─────────┬─────────┬────────────┘
    │         │         │         │         │
    ▼         ▼         ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Research│ │Writer  │ │Editor  │ │Critic  │ │Checker│
│ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

## 基础模式

### 1. 顺序协作

Agent 按顺序处理任务，每个 Agent 的输出作为下一个 Agent 的输入。

```python
import asyncio
from src.agent_runtime.orchestration.executor import AgentExecutor

async def sequential_workflow():
    # 创建专门的 Agent
    researcher = AgentExecutor(
        agent_id="researcher",
        config=AgentConfig(
            name="researcher",
            description="Researches and gathers information",
            model="gpt-4",
        ),
    )

    writer = AgentExecutor(
        agent_id="writer",
        config=AgentConfig(
            name="writer",
            description="Writes content based on research",
            model="gpt-3.5-turbo",
        ),
    )

    editor = AgentExecutor(
        agent_id="editor",
        config=AgentConfig(
            name="editor",
            description="Edits and polishes content",
            model="gpt-4",
        ),
    )

    # 顺序执行
    context1 = AgentContext(
        agent_id="researcher",
        user_id="user_123",
        session_id="sess_abc",
        current_task="Research the benefits of renewable energy",
    )

    # Researcher 收集信息
    result1 = await researcher.execute(context1)
    research_data = result1.output

    # Writer 基于研究写作
    context2 = AgentContext(
        agent_id="writer",
        user_id="user_123",
        session_id="sess_abc",
        current_task=f"Write an article based on: {research_data}",
    )

    result2 = await writer.execute(context2)
    draft = result2.output

    # Editor 编辑内容
    context3 = AgentContext(
        agent_id="editor",
        user_id="user_123",
        session_id="sess_abc",
        current_task=f"Edit and improve: {draft}",
    )

    result3 = await editor.execute(context3)

    return result3.output
```

### 2. 并行协作

多个 Agent 同时处理不同的任务。

```python
async def parallel_workflow():
    # 创建多个 Agent
    summarizer = AgentExecutor(agent_id="summarizer", config=...)
    translator = AgentExecutor(agent_id="translator", config=...)
    analyzer = AgentExecutor(agent_id="analyzer", config=...)

    # 创建任务
    text = "Long text to process..."

    tasks = [
        summarizer.execute(AgentContext(
            agent_id="summarizer",
            user_id="user_123",
            session_id="sess_abc",
            current_task=f"Summarize: {text}",
        )),

        translator.execute(AgentContext(
            agent_id="translator",
            user_id="user_123",
            session_id="sess_abc",
            current_task=f"Translate to Chinese: {text}",
        )),

        analyzer.execute(AgentContext(
            agent_id="analyzer",
            user_id="user_123",
            session_id="sess_abc",
            current_task=f"Analyze sentiment of: {text}",
        )),
    ]

    # 并发执行
    results = await asyncio.gather(*tasks)

    return {
        "summary": results[0].output,
        "translation": results[1].output,
        "sentiment": results[2].output,
    }
```

### 3. 层次协作

协调者 Agent 管理其他 Agent 的工作。

```python
class CoordinatorAgent:
    def __init__(self):
        self.agents = {
            "researcher": AgentExecutor(...),
            "writer": AgentExecutor(...),
            "editor": AgentExecutor(...),
        }

    async def coordinate(self, user_request: str) -> str:
        """协调多个 Agent 完成任务"""

        # 第一步：分析请求
        analysis = await self._analyze_request(user_request)

        # 第二步：分解任务
        tasks = self._decompose_tasks(analysis)

        # 第三步：分配任务给 Agent
        results = {}
        for task_type, task in tasks.items():
            agent = self.agents[task_type]
            result = await agent.execute(AgentContext(
                agent_id=task_type,
                user_id="user_123",
                session_id="sess_abc",
                current_task=task,
            ))
            results[task_type] = result.output

        # 第四步：整合结果
        final_result = await self._synthesize_results(results)

        return final_result

    async def _analyze_request(self, request: str) -> dict:
        """分析用户请求"""
        # 使用 Agent 分析
        return {"type": "article", "topic": request}

    def _decompose_tasks(self, analysis: dict) -> dict:
        """分解任务"""
        return {
            "researcher": f"Research about {analysis['topic']}",
            "writer": f"Write about {analysis['topic']}",
            "editor": "Review and edit",
        }

    async def _synthesize_results(self, results: dict) -> str:
        """整合结果"""
        # 使用 Agent 整合
        return "\n\n".join(results.values())
```

## 通信模式

### 1. 消息传递

Agent 之间通过直接消息传递通信。

```python
class MessageBus:
    def __init__(self):
        self.queues = {}

    def send(self, from_agent: str, to_agent: str, message: str):
        """发送消息"""
        if to_agent not in self.queues:
            self.queues[to_agent] = asyncio.Queue()

        asyncio.create_task(
            self.queues[to_agent].put({
                "from": from_agent,
                "message": message,
            })
        )

    async def receive(self, agent_id: str, timeout=5.0):
        """接收消息"""
        if agent_id not in self.queues:
            self.queues[agent_id] = asyncio.Queue()

        try:
            msg = await asyncio.wait_for(
                self.queues[agent_id].get(),
                timeout=timeout,
            )
            return msg
        except asyncio.TimeoutError:
            return None

# 使用
message_bus = MessageBus()

# Agent A 发送消息
message_bus.send("agent_a", "agent_b", "Please help with X")

# Agent B 接收消息
msg = await message_bus.receive("agent_b")
```

### 2. 共享状态

通过共享状态管理器通信。

```python
class SharedStateManager:
    def __init__(self):
        self.state = {}

    def set(self, key: str, value: any):
        """设置状态"""
        self.state[key] = value

    def get(self, key: str, default=None):
        """获取状态"""
        return self.state.get(key, default)

    def update(self, updates: dict):
        """批量更新"""
        self.state.update(updates)

    def get_all(self):
        """获取所有状态"""
        return self.state.copy()

# 使用
state_manager = SharedStateManager()

# Agent A 设置状态
state_manager.set("research_data", "...")

# Agent B 读取状态
research_data = state_manager.get("research_data")
```

### 3. 事件驱动

通过事件系统实现松耦合通信。

```python
from src.agent_runtime.event_bus import EventBus, EventType

class AgentCommunication:
    def __init__(self):
        self.event_bus = EventBus()
        self.agent_responses = {}

    async def request(self, from_agent: str, to_agent: str, task: str):
        """请求另一个 Agent 执行任务"""

        # 创建响应等待器
        response_id = f"{from_agent}_{to_agent}_{uuid.uuid4()}"
        response_future = asyncio.Future()

        self.agent_responses[response_id] = response_future

        # 发布请求事件
        await self.event_bus.publish(SystemEvent(
            event_type=EventType.CUSTOM,
            agent_id=from_agent,
            timestamp=datetime.now(),
            metadata={
                "type": "agent_request",
                "to_agent": to_agent,
                "task": task,
                "response_id": response_id,
            },
        ))

        # 等待响应
        try:
            response = await asyncio.wait_for(response_future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            return None

    async def respond(self, event: SystemEvent, response: str):
        """响应请求"""
        response_id = event.metadata.get("response_id")

        if response_id in self.agent_responses:
            future = self.agent_responses[response_id]
            future.set_result(response)
            del self.agent_responses[response_id]
```

## 高级模式

### 1. Agent 团队

将 Agent 组织成团队，每个团队负责特定领域。

```python
class AgentTeam:
    def __init__(self, name: str, members: list):
        self.name = name
        self.members = members
        self.leader = members[0]  # 第一个是领导者

    async def execute_task(self, task: str) -> str:
        """执行任务，领导者协调成员"""

        # 领导者分解任务
        subtasks = await self._decompose_task(task)

        # 分配给成员
        results = []
        for i, member in enumerate(self.members):
            if i == 0:  # 领导者
                continue

            result = await member.execute(AgentContext(
                agent_id=member.agent_id,
                user_id="user_123",
                session_id="sess_abc",
                current_task=subtasks[i],
            ))
            results.append(result.output)

        # 领导者整合结果
        final_result = await self.leader.execute(AgentContext(
            agent_id=self.leader.agent_id,
            user_id="user_123",
            session_id="sess_abc",
            current_task=f"Integrate these results: {results}",
        ))

        return final_result.output

    async def _decompose_task(self, task: str) -> list:
        """分解任务"""
        # 使用 LLM 分解任务
        return [task] * len(self.members)

# 创建团队
research_team = AgentTeam(
    name="research_team",
    members=[
        AgentExecutor(agent_id="lead_researcher", config=...),
        AgentExecutor(agent_id="data_analyst", config=...),
        AgentExecutor(agent_id="fact_checker", config=...),
    ],
)
```

### 2. Agent 竞争

多个 Agent 竞争提供最佳解决方案。

```python
class CompetitiveAgentSystem:
    def __init__(self, agents: list):
        self.agents = agents

    async def compete(self, task: str) -> tuple:
        """让 Agent 竞争完成任务"""

        # 创建任务
        tasks = [
            agent.execute(AgentContext(
                agent_id=agent.agent_id,
                user_id="user_123",
                session_id="sess_abc",
                current_task=task,
            ))
            for agent in self.agents
        ]

        # 并发执行
        results = await asyncio.gather(*tasks)

        # 评估结果
        scored_results = []
        for agent, result in zip(self.agents, results):
            score = await self._evaluate_result(result.output)
            scored_results.append((agent, result, score))

        # 返回最佳结果
        best = max(scored_results, key=lambda x: x[2])
        return best

    async def _evaluate_result(self, result: str) -> float:
        """评估结果质量"""
        # 简单评估：长度、关键词等
        score = len(result.split()) * 0.1
        return score
```

### 3. Agent 辩论

Agent 之间辩论以达成共识。

```python
class DebatingAgentSystem:
    def __init__(self, agents: list, max_rounds=3):
        self.agents = agents
        self.max_rounds = max_rounds

    async def debate(self, topic: str) -> str:
        """让 Agent 辩论达成共识"""

        # 初始观点
        opinions = []
        for agent in self.agents:
            result = await agent.execute(AgentContext(
                agent_id=agent.agent_id,
                user_id="user_123",
                session_id="sess_abc",
                current_task=f"State your opinion on: {topic}",
            ))
            opinions.append(result.output)

        # 辩论轮次
        for round_num in range(self.max_rounds):
            for i, agent in enumerate(self.agents):
                # 构建辩论上下文
                others_opinions = [
                    f"Agent {j}: {op}"
                    for j, op in enumerate(opinions)
                    if j != i
                ]

                debate_prompt = f"""
                Other agents' opinions:
                {chr(10).join(others_opinions)}

                Refute or support these views on: {topic}
                """

                result = await agent.execute(AgentContext(
                    agent_id=agent.agent_id,
                    user_id="user_123",
                    session_id="sess_abc",
                    current_task=debate_prompt,
                ))

                opinions[i] = result.output

        # 整合共识
        consensus = await self._find_consensus(opinions)
        return consensus

    async def _find_consensus(self, opinions: list) -> str:
        """从观点中找出共识"""
        # 使用 Agent 找出共同点
        return "\n".join(opinions)
```

## 实际示例

### 研究助手系统

```python
class ResearchAssistantSystem:
    def __init__(self):
        # 创建专门的 Agent
        self.researcher = AgentExecutor(
            agent_id="researcher",
            config=AgentConfig(
                name="researcher",
                description="Gathers information on topics",
                model="gpt-4",
            ),
        )

        self.analyst = AgentExecutor(
            agent_id="analyst",
            config=AgentConfig(
                name="analyst",
                description="Analyzes research data",
                model="gpt-4",
            ),
        )

        self.writer = AgentExecutor(
            agent_id="writer",
            config=AgentConfig(
                name="writer",
                description="Writes reports",
                model="gpt-3.5-turbo",
            ),
        )

        self.fact_checker = AgentExecutor(
            agent_id="fact_checker",
            config=AgentConfig(
                name="fact_checker",
                description="Verifies facts and claims",
                model="gpt-4",
            ),
        )

    async def create_report(self, topic: str) -> str:
        """创建研究报告"""

        print(f"Creating report on: {topic}")

        # 1. 研究阶段
        print("Step 1: Researching...")
        research_result = await self.researcher.execute(AgentContext(
            agent_id="researcher",
            user_id="user_123",
            session_id="sess_abc",
            current_task=f"Research and gather information about: {topic}",
        ))

        research_data = research_result.output

        # 2. 分析阶段
        print("Step 2: Analyzing...")
        analysis_result = await self.analyst.execute(AgentContext(
            agent_id="analyst",
            user_id="user_123",
            session_id="sess_abc",
            current_task=f"Analyze this research data: {research_data}",
        ))

        analysis = analysis_result.output

        # 3. 写作阶段
        print("Step 3: Writing...")
        draft_result = await self.writer.execute(AgentContext(
            agent_id="writer",
            user_id="user_123",
            session_id="sess_abc",
            current_task=f"""
            Write a comprehensive report based on:
            Research: {research_data}
            Analysis: {analysis}
            """,
        ))

        draft = draft_result.output

        # 4. 事实核查阶段
        print("Step 4: Fact-checking...")
        fact_check_result = await self.fact_checker.execute(AgentContext(
            agent_id="fact_checker",
            user_id="user_123",
            session_id="sess_abc",
            current_task=f"Fact-check this report: {draft}",
        ))

        fact_check = fact_check_result.output

        # 5. 最终修订
        print("Step 5: Final revision...")
        final_result = await self.writer.execute(AgentContext(
            agent_id="writer",
            user_id="user_123",
            session_id="sess_abc",
            current_task=f"""
            Revise the report based on fact-checking:
            Draft: {draft}
            Fact-check: {fact_check}
            """,
        ))

        return final_result.output

# 使用
async def main():
    system = ResearchAssistantSystem()

    report = await system.create_report("The impact of AI on healthcare")

    print("\n=== Final Report ===")
    print(report)
```

### 客户服务系统

```python
class CustomerServiceSystem:
    def __init__(self):
        # 三级支持系统
        self.level1 = AgentExecutor(  # 基础支持
            agent_id="support_l1",
            config=AgentConfig(
                name="support_l1",
                description="Basic customer support",
                system_prompt="You are a helpful customer support agent. Handle common issues.",
                model="gpt-3.5-turbo",
            ),
        )

        self.level2 = AgentExecutor(  # 高级支持
            agent_id="support_l2",
            config=AgentConfig(
                name="support_l2",
                description="Advanced technical support",
                system_prompt="You are a senior technical support agent. Handle complex issues.",
                model="gpt-4",
            ),
        )

        self.level3 = AgentExecutor(  # 专家支持
            agent_id="support_l3",
            config=AgentConfig(
                name="support_l3",
                description="Expert support for critical issues",
                system_prompt="You are an expert support agent. Handle critical and unusual issues.",
                model="gpt-4",
            ),
        )

    async def handle_issue(self, issue: str, user_tier: str = "basic") -> str:
        """处理客户问题"""

        # 根据用户等级和问题复杂度选择 Agent
        if user_tier == "enterprise":
            # 企业客户直接获得高级支持
            agent = self.level2
        else:
            # 普通客户从基础支持开始
            agent = self.level1

        # 尝试解决
        result = await agent.execute(AgentContext(
            agent_id=agent.agent_id,
            user_id="user_123",
            session_id="sess_abc",
            current_task=issue,
        ))

        # 如果未解决，升级到下一级
        if not result.success or "escalate" in result.output.lower():
            if agent == self.level1:
                print("Escalating to level 2...")
                result = await self.level2.execute(AgentContext(
                    agent_id="level2",
                    user_id="user_123",
                    session_id="sess_abc",
                    current_task=f"Handle this escalated issue: {issue}",
                ))

            if not result.success or "escalate" in result.output.lower():
                if agent in [self.level1, self.level2]:
                    print("Escalating to level 3...")
                    result = await self.level3.execute(AgentContext(
                        agent_id="level3",
                        user_id="user_123",
                        session_id="sess_abc",
                        current_task=f"Handle this critical issue: {issue}",
                    ))

        return result.output
```

## 最佳实践

### 1. 明确 Agent 职责

```python
# ✅ 好的设计：职责明确
researcher = AgentExecutor(
    agent_id="researcher",
    config=AgentConfig(
        name="researcher",
        description="Only researches and gathers data",
        system_prompt="You are a researcher. Your job is to find information.",
    ),
)

writer = AgentExecutor(
    agent_id="writer",
    config=AgentConfig(
        name="writer",
        description="Only writes content",
        system_prompt="You are a writer. Your job is to write based on provided information.",
    ),
)

# ❌ 不好的设计：职责重叠
agent1 = AgentExecutor(
    agent_id="agent1",
    config=AgentConfig(
        name="agent1",
        description="Can do everything",
        system_prompt="You can research, write, edit, and analyze.",
    ),
)
```

### 2. 使用状态管理

```python
class MultiAgentOrchestrator:
    def __init__(self):
        self.agents = {}
        self.state = {}

    async def execute_workflow(self, workflow: list):
        """执行多 Agent 工作流"""
        for step in workflow:
            agent_name = step["agent"]
            task = step["task"]

            # 获取 Agent
            agent = self.agents.get(agent_name)
            if not agent:
                raise ValueError(f"Unknown agent: {agent_name}")

            # 执行任务
            context = AgentContext(
                agent_id=agent_name,
                user_id="user_123",
                session_id="sess_abc",
                current_task=task,
                metadata={"state": self.state},  # 传递状态
            )

            result = await agent.execute(context)

            # 更新状态
            if result.success:
                self.state[step.get("output_key", agent_name)] = result.output
```

### 3. 错误处理和回退

```python
async def safe_agent_execute(agent, context, fallback_agent=None):
    """安全的 Agent 执行，带回退"""
    try:
        result = await agent.execute(context)
        if result.success:
            return result

        # 失败时尝试回退
        if fallback_agent:
            print(f"{agent.agent_id} failed, trying fallback...")
            return await fallback_agent.execute(context)

    except Exception as e:
        print(f"Error in {agent.agent_id}: {e}")
        if fallback_agent:
            return await fallback_agent.execute(context)

    return AgentResult(success=False, output="", error="All attempts failed")
```

## 相关文档

- [系统架构](architecture.md) - 整体架构设计
- [Agent 生命周期](lifecycle.md) - Agent 执行流程
- [事件系统](event-system.md) - Agent 间通信机制
- [中间件系统](middleware.md) - 协作流程控制
