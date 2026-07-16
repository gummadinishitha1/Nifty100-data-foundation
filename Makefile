load:
	python src/load_database.py

ratios:
	python src/etl/normaliser.py

test:
	pytest -q

report:
	python src/database_validator.py

dashboard:
	echo Dashboard

api:
	echo API

clean:
	echo Cleaning project