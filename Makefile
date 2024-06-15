run:
	make bootstrap
	./scripts/run.sh $(effect) '$(config)'

playlist:
	make bootstrap
	./scripts/playlist.sh

off:
	make run effect=off

bootstrap:
	pip install -r requirements.txt

clean:
	rm -f *.pyc
	pip uninstall -r requirements.txt

lint:
	find ./src ./effects -type f -name "*.py" | xargs pylint

lint-fix:
	black .
