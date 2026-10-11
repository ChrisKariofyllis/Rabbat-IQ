.PHONY: run test

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8642 --reload

test:
	pytest
