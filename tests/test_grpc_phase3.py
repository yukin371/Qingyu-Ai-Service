"""
Phase3 gRPC服务测试脚本

测试所有Phase3 Agent gRPC接口
"""
import asyncio
import grpc
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from grpc_service import ai_service_pb2, ai_service_pb2_grpc
from core.logger import get_logger

logger = get_logger(__name__)


async def test_health_check():
    """测试健康检查"""
    print("\n" + "="*60)
    print("🏥 测试健康检查")
    print("="*60)

    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ai_service_pb2_grpc.AIServiceStub(channel)

        request = ai_service_pb2.HealthCheckRequest()
        response = await stub.HealthCheck(request)

        print(f"✅ 健康状态: {response.status}")
        print(f"📋 检查结果:")
        for name, status in response.checks.items():
            print(f"  - {name}: {status}")


async def test_generate_outline():
    """测试大纲生成"""
    print("\n" + "="*60)
    print("📖 测试大纲生成")
    print("="*60)

    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ai_service_pb2_grpc.AIServiceStub(channel)

        request = ai_service_pb2.OutlineRequest(
            task="创作一个修仙小说大纲，主角是天才少年，包含5章内容",
            user_id="test_user",
            project_id="test_project"
        )

        print("📝 任务: 创作修仙小说大纲...")
        response = await stub.GenerateOutline(request)

        print(f"\n✅ 大纲生成成功!")
        print(f"📖 标题: {response.outline.title}")
        print(f"🎭 类型: {response.outline.genre}")
        print(f"📚 章节数: {len(response.outline.chapters)}")
        print(f"⏱️  耗时: {response.execution_time:.2f}秒")

        print(f"\n📋 章节列表:")
        for i, chapter in enumerate(response.outline.chapters[:3], 1):
            print(f"  {i}. {chapter.title}")
            print(f"     概要: {chapter.summary[:50]}...")

        if len(response.outline.chapters) > 3:
            print(f"  ... 还有 {len(response.outline.chapters) - 3} 章")

        return response.outline


async def test_generate_characters(outline):
    """测试角色生成"""
    print("\n" + "="*60)
    print("👤 测试角色生成")
    print("="*60)

    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ai_service_pb2_grpc.AIServiceStub(channel)

        request = ai_service_pb2.CharactersRequest(
            task="根据大纲创建主要角色",
            user_id="test_user",
            project_id="test_project",
            outline=outline
        )

        print("📝 任务: 生成主要角色...")
        response = await stub.GenerateCharacters(request)

        print(f"\n✅ 角色生成成功!")
        print(f"👥 角色数量: {len(response.characters.characters)}")
        print(f"⏱️  耗时: {response.execution_time:.2f}秒")

        print(f"\n📋 角色列表:")
        for i, char in enumerate(response.characters.characters[:3], 1):
            print(f"  {i}. {char.name} ({char.role_type})")
            print(f"     性格: {', '.join(char.personality.traits[:3])}")

        if len(response.characters.characters) > 3:
            print(f"  ... 还有 {len(response.characters.characters) - 3} 个角色")

        return response.characters


async def test_generate_plot(outline, characters):
    """测试情节生成"""
    print("\n" + "="*60)
    print("📊 测试情节生成")
    print("="*60)

    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ai_service_pb2_grpc.AIServiceStub(channel)

        request = ai_service_pb2.PlotRequest(
            task="根据大纲和角色设计情节",
            user_id="test_user",
            project_id="test_project",
            outline=outline,
            characters=characters
        )

        print("📝 任务: 生成情节事件...")
        response = await stub.GeneratePlot(request)

        print(f"\n✅ 情节生成成功!")
        print(f"📅 事件数量: {len(response.plot.timeline_events)}")
        print(f"🧵 情节线数: {len(response.plot.plot_threads)}")
        print(f"⏱️  耗时: {response.execution_time:.2f}秒")

        print(f"\n📋 主要事件:")
        for i, event in enumerate(response.plot.timeline_events[:3], 1):
            print(f"  {i}. {event.title} ({event.timestamp})")
            print(f"     类型: {event.event_type}")

        if len(response.plot.timeline_events) > 3:
            print(f"  ... 还有 {len(response.plot.timeline_events) - 3} 个事件")

        return response.plot


async def test_creative_workflow():
    """测试完整创作工作流"""
    print("\n" + "="*60)
    print("🎨 测试完整创作工作流")
    print("="*60)

    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ai_service_pb2_grpc.AIServiceStub(channel)

        request = ai_service_pb2.CreativeWorkflowRequest(
            task="创作一个都市爱情小说的完整设定，包含3章内容",
            user_id="test_user",
            project_id="test_project",
            max_reflections=3,
            enable_human_review=False
        )

        print("📝 任务: 执行完整创作工作流...")
        print("⏳ 这可能需要30-60秒...")

        response = await stub.ExecuteCreativeWorkflow(request)

        print(f"\n✅ 工作流执行成功!")
        print(f"🆔 执行ID: {response.execution_id}")
        print(f"✓  审核状态: {'通过' if response.review_passed else '未通过'}")
        print(f"🔄 反思次数: {response.reflection_count}")

        print(f"\n📖 大纲: {response.outline.title}")
        print(f"👥 角色数: {len(response.characters.characters)}")
        print(f"📊 事件数: {len(response.plot.timeline_events)}")

        print(f"\n⏱️  执行时间:")
        total_time = 0
        for stage, time_val in response.execution_times.items():
            print(f"  - {stage}: {time_val:.2f}秒")
            total_time += time_val
        print(f"  总计: {total_time:.2f}秒")


async def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("🚀 Phase3 gRPC服务测试")
    print("="*60)
    print("确保gRPC服务器正在运行：")
    print("  python src/grpc_service/server.py")
    print("="*60)

    try:
        # 1. 健康检查
        await test_health_check()

        # 2. 测试大纲生成
        outline = await test_generate_outline()

        # 3. 测试角色生成
        characters = await test_generate_characters(outline)

        # 4. 测试情节生成
        plot = await test_generate_plot(outline, characters)

        # 5. 测试完整工作流
        await test_creative_workflow()

        print("\n" + "="*60)
        print("✅ 所有测试通过!")
        print("="*60)

    except grpc.RpcError as e:
        print(f"\n❌ gRPC错误: {e.code()}")
        print(f"详情: {e.details()}")
        print("\n请确保gRPC服务器正在运行:")
        print("  cd python_ai_service")
        print("  set GOOGLE_API_KEY=your_api_key")
        print("  python src/grpc_service/server.py")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

