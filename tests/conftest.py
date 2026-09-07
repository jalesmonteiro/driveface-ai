import os
import pytest
from rest_framework.test import APIClient

# Para testes unitários, utiliza SQLite em memória se o PostgreSQL não estiver disponível
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def api_client():
    """Fixture para cliente de teste da API REST."""
    return APIClient()
