# Atajos de desarrollo. El venv se CREA aquí, no se entrega como archivo.

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: venv install run smoke clean

# Crea el entorno virtual local
venv:
	python3 -m venv $(VENV)

# Crea el venv (si no existe) e instala dependencias
install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# Corre el servidor con el cerebro en modo mock
run:
	NEXUS_MOCK_BRAIN=true $(VENV)/bin/uvicorn app.main:app --reload

# Ejercita el multiplex SSE sin levantar servidor
smoke:
	NEXUS_MOCK_BRAIN=true $(PY) -m scripts.smoke

# Borra venv y artefactos
clean:
	rm -rf $(VENV) **/__pycache__ .pytest_cache .ruff_cache
