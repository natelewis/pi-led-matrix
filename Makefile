UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
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
	@black .
