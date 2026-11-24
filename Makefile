.PHONY: run playlist off bootstrap clean lint lint-fix web-build web web-dev web-test

UNAME_S := $(shell uname -s)
IS_VIRTUAL := $(shell python3 -c "import json, os; f='config.json' if os.path.exists('config.json') else 'default_config.json'; print('1' if json.load(open(f)).get('virtual') or os.environ.get('VIRTUAL_MATRIX')=='1' else '')" 2>/dev/null)
ifeq ($(UNAME_S),Linux)
    ifneq ($(IS_VIRTUAL),1)
        MACHINE_TYPE := $(shell uname -m)
        ifeq ($(MACHINE_TYPE),armv7l) # Common architecture for Raspberry Pi 3
            PRE_CMD := sudo
        endif
        ifeq ($(MACHINE_TYPE),armv6l) # Common architecture for older Raspberry Pi
            PRE_CMD := sudo
        endif
        ifeq ($(MACHINE_TYPE),aarch64) # For newer Raspberry Pi models
            PRE_CMD := sudo
        endif
    endif
endif

run:
	@ \
	. .venv/bin/activate; \
	$(PRE_CMD) ./scripts/run.sh $(effect) '$(config)'; \

playlist:
	@ \
	. .venv/bin/activate; \
	$(PRE_CMD) ./scripts/playlist.sh; \

off:
	@ \
	. .venv/bin/activate; \
	make run effect=off \

bootstrap:
	@ \
	echo "Setting up python virtual environment"; \
	python3 -m venv .venv; \
	. .venv/bin/activate; \
	echo "Installing module requirements ( NOTE: This takes up to 2 hours )"; \
	./.venv/bin/pip install -r requirements.txt; \

clean:
	@ \
	echo "Cleaning..."
	rm -f *.pyc; \
	./.venv/bin/pip uninstall -r requirements.txt -y; \

lint:
	@find ./src -type f -name "*.py" | xargs pylint

lint-fix:
	@ ./.venv/bin/black .

web-build:
	@cd web/client && npm install && npm run build

web:
	@python3 -m web.server.app --host $${LED_MATRIX_WEB_HOST:-0.0.0.0} --port $${LED_MATRIX_WEB_PORT:-8080}

web-dev:
	@trap 'kill 0' INT TERM EXIT; \
	python3 -m web.server.app --host 127.0.0.1 --port 8080 --reload & \
	cd web/client && npm run dev

web-test:
	@python3 -m unittest discover -s web/server/tests -t . -v
