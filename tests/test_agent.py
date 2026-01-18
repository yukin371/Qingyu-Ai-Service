import asyncio
from src.services.agent_service import AgentService

async def main():
    # 初始化服务
    agent_service = AgentService()
    await agent_service.initialize()

    # 执行创作任务
    result = await agent_service.execute(
        agent_type="creative",
        task="续写一段武侠小说，描述主角李逍遥初遇赵灵儿的场景，风格要古典优美",
        context={
            "constraints": {
                "字数": 500,
                "风格": "武侠",
                "类型": "续写"
            }
        },
        tools=["rag_tool"],  # 可选："character_tool", "outline_tool"
        user_id="test-user-001",
        project_id="test-project-001",
    )

    # 打印结果
    print("=" * 80)
    print("生成内容:")
    print("=" * 80)
    print(result.output)
    print("\n" + "=" * 80)
    print("元数据:")
    print("=" * 80)
    print(f"状态: {result.status}")
    print(f"Token使用: {result.metadata.get('tokens_used', 0)}")
    print(f"重试次数: {result.metadata.get('retry_count', 0)}")
    print(f"审核分数: {result.metadata.get('review_score', 0)}")
    print(f"推理步骤: {len(result.reasoning)}")

    # 关闭服务
    await agent_service.close()

if __name__ == "__main__":
    asyncio.run(main())
