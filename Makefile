run:
	@ \
	. .venv/bin/activate; \
	./scripts/run.sh $(effect) '$(config)'; \

playlist:
	@ \
	. .venv/bin/activate; \
	./scripts/playlist.sh; \

off:
	@ \
	. .venv/bin/activate; \
	make run effect=off \

bootstrap:
	@ \
	echo "Setting up virtual python environment"; \
	python3 -m venv .venv; \
	. .venv/bin/activate; \
	echo "Installing module requirements"; \
	pip3 install -r requirements.txt; \

clean:
	@ \
	rm -f *.pyc \
	pip uninstall -r requirements.txt \

lint:
	@find ./src -type f -name "*.py" | xargs pylint

lint-fix:
	@black .
