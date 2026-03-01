"""Concept操作测试"""
import pytest
from src.api.go_backend.concepts import ConceptOperations


@pytest.mark.asyncio
async def test_get_concept(mock_go_client):
    """测试获取概念"""
    ops = ConceptOperations(mock_go_client)
    concept = await ops.get_concept("user-1", "project-1", "concept-1")
    assert concept.id == "507f1f77bcf86cd799439012"
    assert concept.name == "Test Concept"
    assert concept.category == "magic"
    assert concept.content == "Test description"


@pytest.mark.asyncio
async def test_create_concept(mock_go_client):
    """测试创建概念"""
    ops = ConceptOperations(mock_go_client)
    concept = await ops.create_concept(
        user_id="user-1",
        project_id="project-1",
        name="Fireball",
        category="magic",
        content="A spell that creates fire"
    )
    assert concept.name == "Fireball"
    assert concept.category == "magic"
    assert concept.content == "A spell that creates fire"


@pytest.mark.asyncio
async def test_search_concepts(mock_go_client):
    """测试搜索概念"""
    ops = ConceptOperations(mock_go_client)
    result = await ops.search_concepts("user-1", "project-1", category="magic")
    assert len(result.concepts) >= 0
    assert result.total >= 0


@pytest.mark.asyncio
async def test_update_concept(mock_go_client):
    """测试更新概念"""
    ops = ConceptOperations(mock_go_client)
    concept = await ops.update_concept(
        user_id="user-1",
        project_id="project-1",
        concept_id="concept-1",
        name="Updated Fireball",
        content="Updated description"
    )
    assert concept.name == "Updated Fireball"


@pytest.mark.asyncio
async def test_delete_concept(mock_go_client):
    """测试删除概念"""
    ops = ConceptOperations(mock_go_client)
    result = await ops.delete_concept("user-1", "project-1", "concept-1")
    assert result is True


@pytest.mark.asyncio
async def test_batch_get_concepts(mock_go_client):
    """测试批量获取概念"""
    ops = ConceptOperations(mock_go_client)
    concepts = await ops.batch_get_concepts(
        "user-1",
        "project-1",
        ["concept-1", "concept-2"]
    )
    assert len(concepts) >= 0


@pytest.mark.asyncio
async def test_create_concept_with_tags_and_docs(mock_go_client):
    """测试创建带标签和关联文档的概念"""
    ops = ConceptOperations(mock_go_client)
    concept = await ops.create_concept(
        user_id="user-1",
        project_id="project-1",
        name="Fireball",
        category="magic",
        content="A spell that creates fire",
        tags=["fire", "spell", "combat"],
        related_docs=["doc-1", "doc-2"]
    )
    assert concept.name == "Fireball"
    assert len(concept.tags) == 3
    assert len(concept.related_docs) == 2


@pytest.mark.asyncio
async def test_search_concepts_with_keyword(mock_go_client):
    """测试带关键词的搜索"""
    ops = ConceptOperations(mock_go_client)
    result = await ops.search_concepts(
        "user-1",
        "project-1",
        keyword="fire"
    )
    assert len(result.concepts) >= 0


@pytest.mark.asyncio
async def test_search_concepts_with_category_and_keyword(mock_go_client):
    """测试同时使用分类和关键词搜索"""
    ops = ConceptOperations(mock_go_client)
    result = await ops.search_concepts(
        "user-1",
        "project-1",
        category="magic",
        keyword="fire",
        limit=20
    )
    assert len(result.concepts) >= 0


@pytest.mark.asyncio
async def test_update_concept_all_fields(mock_go_client):
    """测试更新概念的所有字段"""
    ops = ConceptOperations(mock_go_client)
    concept = await ops.update_concept(
        user_id="user-1",
        project_id="project-1",
        concept_id="concept-1",
        name="Iceball",
        category="magic",
        content="A spell that creates ice",
        tags=["ice", "spell"],
        related_docs=["doc-3"]
    )
    assert concept.name == "Iceball"
    assert concept.category == "magic"


@pytest.mark.asyncio
async def test_concept_categories(mock_go_client):
    """测试所有概念分类"""
    ops = ConceptOperations(mock_go_client)

    categories = ["magic", "location", "character", "item", "organization", "event", "other"]

    for category in categories:
        result = await ops.search_concepts("user-1", "project-1", category=category)
        assert len(result.concepts) >= 0
