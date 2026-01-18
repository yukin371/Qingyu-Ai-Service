"""
健康检查 API 测试
"""
import pytest
from fastapi import status


def test_health_check(client):
    """测试健康检查端点"""
    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "timestamp" in data
    assert "version" in data


def test_readiness_check(client):
    """测试就绪检查端点"""
    response = client.get("/api/v1/health/ready")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "status" in data
    assert "checks" in data


def test_liveness_check(client):
    """测试存活检查端点"""
    response = client.get("/api/v1/health/live")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "alive"


def test_root_endpoint(client):
    """测试根路径"""
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "running"
    assert "version" in data

