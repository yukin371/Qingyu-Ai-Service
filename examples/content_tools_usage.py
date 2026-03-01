"""
AI内容工具使用示例

本示例展示如何使用Python客户端调用Go后端的AI内容工具API，
包括Document(文档草稿)和Concept(设定百科)的操作。
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.go_backend import GoBackendClient
from src.api.go_backend.documents import DocumentOperations
from src.api.go_backend.concepts import ConceptOperations
from src.tools.content import DocumentTool, ConceptTool
from src.tools.registry.tool_registry import ToolRegistry


async def example_basic_document_operations():
    """示例1: 基础Document操作"""
    print("\n=== 示例1: 基础Document操作 ===")

    # 创建客户端
    client = GoBackendClient()
    doc_ops = DocumentOperations(client)

    # 注意: 以下代码需要实际的Go后端运行
    # 这里展示API的使用方式

    print("1. 创建文档:")
    print("   doc = await doc_ops.create_or_update_document(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       chapter_num=1,")
    print("       title='第一章 开始',")
    print("       content='这是一个新的开始...',")
    print("       action='create'")
    print("   )")

    print("\n2. 获取文档:")
    print("   doc = await doc_ops.get_document('user-123', 'proj-123', doc.id)")

    print("\n3. 获取文档列表:")
    print("   result = await doc_ops.list_documents('user-123', 'proj-123', limit=10)")
    print("   for doc in result.documents:")
    print("       print(f'{doc.chapter_num}: {doc.title}')")

    print("\n4. 更新文档:")
    print("   doc = await doc_ops.create_or_update_document(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       chapter_num=1,")
    print("       title='第一章 新的开始',")
    print("       content='更新后的内容...',")
    print("       action='update'")
    print("   )")

    print("\n5. 删除文档:")
    print("   await doc_ops.delete_document('user-123', 'proj-123', doc.id)")


async def example_basic_concept_operations():
    """示例2: 基础Concept操作"""
    print("\n=== 示例2: 基础Concept操作 ===")

    # 创建客户端
    client = GoBackendClient()
    concept_ops = ConceptOperations(client)

    print("1. 创建概念:")
    print("   concept = await concept_ops.create_concept(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       name='火球术',")
    print("       category='magic',")
    print("       content='一种初级火系法术，可以发射火球攻击敌人',")
    print("       tags=['火系', '法术', '攻击']")
    print("   )")

    print("\n2. 获取概念:")
    print("   concept = await concept_ops.get_concept('user-123', 'proj-123', concept.id)")

    print("\n3. 搜索概念:")
    print("   result = await concept_ops.search_concepts(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       category='magic'")
    print("   )")

    print("\n4. 更新概念:")
    print("   concept = await concept_ops.update_concept(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       concept_id=concept.id,")
    print("       content='更新后的描述...'")
    print("   )")

    print("\n5. 按关键词搜索:")
    print("   result = await concept_ops.search_concepts(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       keyword='火'")
    print("   )")


async def example_langchain_integration():
    """示例3: LangChain集成"""
    print("\n=== 示例3: LangChain集成 ===")

    print("1. 初始化工具注册表:")
    print("   from src.api.go_backend import GoBackendClient")
    print("   from src.tools.registry.tool_registry import ToolRegistry")
    print("")
    print("   # 创建客户端")
    print("   go_client = GoBackendClient()")
    print("")
    print("   # 创建工具注册表，注入Go客户端")
    print("   registry = ToolRegistry(go_client=go_client)")
    print("")
    print("   # 获取所有LangChain工具")
    print("   tools = registry.get_langchain_tools()")
    print("   print(f'注册了 {len(tools)} 个工具')")

    print("\n2. 查看可用工具:")
    print("   for tool in tools:")
    print("       print(f'- {tool.name}: {tool.description}')")

    print("\n3. 在Agent中使用:")
    print("   from langchain.agents import initialize_agent, AgentType")
    print("   from langchain.llms import OpenAI")
    print("")
    print("   # 初始化LLM")
    print("   llm = OpenAI(temperature=0.7)")
    print("")
    print("   # 创建Agent，注册工具")
    print("   agent = initialize_agent(")
    print("       tools=tools,")
    print("       llm=llm,")
    print("       agent=AgentType.OPENAI_FUNCTIONS,")
    print("       verbose=True")
    print("   )")
    print("")
    print("   # 使用Agent进行写作")
    print("   response = await agent.arun(")
    print("       '帮我创建第一章，标题是'新的开始'，内容要吸引人'")
    print("   )")
    print("   print(response)")


async def example_document_tool_usage():
    """示例4: Document工具直接使用"""
    print("\n=== 示例4: Document工具直接使用 ===")

    print("1. 创建Document工具:")
    print("   from src.tools.content import DocumentTool")
    print("   from src.api.go_backend import GoBackendClient")
    print("")
    print("   go_client = GoBackendClient()")
    print("   doc_tool = DocumentTool(go_client)")

    print("\n2. 获取LangChain工具:")
    print("   langchain_tools = doc_tool.get_langchain_tools()")
    print("   for tool in langchain_tools:")
    print("       print(f'{tool.name}: {tool.description}')")

    print("\n3. 直接调用工具方法:")
    print("   # 获取文档上下文")
    print("   context = await doc_tool.get_document_for_context(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       document_id='doc-123'")
    print("   )")
    print("   print(context)")

    print("\n   # 创建新章节")
    print("   result = await doc_tool.create_chapter(")
    print("       project_id='proj-123',")
    print("       user_id='user-123',")
    print("       chapter_num=2,")
    print("       title='第二章 旅程',")
    print("       content='主角踏上了新的旅程...'")
    print("   )")
    print("   print(result)")


async def example_concept_tool_usage():
    """示例5: Concept工具直接使用"""
    print("\n=== 示例5: Concept工具直接使用 ===")

    print("1. 创建Concept工具:")
    print("   from src.tools.content import ConceptTool")
    print("   from src.api.go_backend import GoBackendClient")
    print("")
    print("   go_client = GoBackendClient()")
    print("   concept_tool = ConceptTool(go_client)")

    print("\n2. 获取LangChain工具:")
    print("   langchain_tools = concept_tool.get_langchain_tools()")
    print("   for tool in langchain_tools:")
    print("       print(f'{tool.name}: {tool.description}')")

    print("\n3. 直接调用工具方法:")
    print("   # 获取概念信息")
    print("   info = await concept_tool.get_concept_info(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       concept_id='concept-123'")
    print("   )")
    print("   print(info)")

    print("\n   # 创建新概念")
    print("   result = await concept_tool.create_new_concept(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       name='冰霜护盾',")
    print("       category='magic',")
    print("       content='可以抵挡火焰伤害的护盾法术',")
    print("       tags=['冰系', '防御']")
    print("   )")
    print("   print(result)")

    print("\n   # 搜索概念")
    print("   results = await concept_tool.search_project_concepts(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       category='magic'")
    print("   )")
    print("   print(results)")


async def example_complete_workflow():
    """示例6: 完整的AI写作工作流"""
    print("\n=== 示例6: 完整的AI写作工作流 ===")

    print("场景：AI助手帮助用户创作小说章节")
    print("")
    print("1. 初始化环境")
    print("   go_client = GoBackendClient()")
    print("   doc_tool = DocumentTool(go_client)")
    print("   concept_tool = ConceptTool(go_client)")

    print("\n2. 获取相关设定（概念）")
    print("   concepts = await concept_tool.search_project_concepts(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       category='magic'")
    print("   )")
    print("   print('可用的魔法设定:')")
    print("   print(concepts)")

    print("\n3. 获取前一章内容作为参考")
    print("   prev_chapter = await doc_tool.get_document_for_context(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       document_id='chapter-1'")
    print("   )")
    print("   print('上一章内容:')")
    print("   print(prev_chapter)")

    print("\n4. 使用AI创建新章节")
    print("   new_chapter = await doc_tool.create_chapter(")
    print("       project_id='proj-123',")
    print("       user_id='user-123',")
    print("       chapter_num=2,")
    print("       title='第二章 新的冒险',")
    print("       content='[AI生成的内容]...'")
    print("   )")
    print("   print(new_chapter)")

    print("\n5. 保存新发现的概念")
    print("   new_concept = await concept_tool.create_new_concept(")
    print("       user_id='user-123',")
    print("       project_id='proj-123',")
    print("       name='新的魔法物品',")
    print("       category='item',")
    print("       content='在第二章中出现的魔法物品...'")
    print("   )")
    print("   print(new_concept)")


def print_all_examples():
    """打印所有示例代码"""
    print("=" * 60)
    print("AI内容工具使用示例")
    print("=" * 60)

    # 使用同步方式打印示例
    import inspect

    examples = [
        ("基础Document操作", example_basic_document_operations),
        ("基础Concept操作", example_basic_concept_operations),
        ("LangChain集成", example_langchain_integration),
        ("Document工具使用", example_document_tool_usage),
        ("Concept工具使用", example_concept_tool_usage),
        ("完整工作流", example_complete_workflow),
    ]

    for name, func in examples:
        # 获取函数源码并打印
        source = inspect.getsource(func)
        print(f"\n{'=' * 60}")
        print(f"示例: {name}")
        print(f"{'=' * 60}")
        print(source)
        print()


def main():
    """主函数"""
    print("=" * 60)
    print("AI内容工具使用示例")
    print("=" * 60)
    print()
    print("本示例展示如何使用AI内容工具API")
    print()
    print("使用方法:")
    print("1. 确保Go后端服务正在运行 (http://localhost:9090)")
    print("2. 配置正确的API密钥")
    print("3. 运行本示例: python examples/content_tools_usage.py")
    print()
    print("注意: 本示例中的代码需要实际的Go后端才能运行")
    print("      这里展示的是API的使用方式")
    print()
    print("=" * 60)

    # 打印所有示例代码
    print_all_examples()

    print("\n" + "=" * 60)
    print("更多文档请参考: docs/api/ai-content-tools.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
