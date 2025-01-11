


up:
	docker compose -f docker/docker-compose.yml up -d

down:
	docker compose -f docker/docker-compose.yml down --rmi all

redo:
	make down
	make up

test:
	pytest --disable-warnings .

docker-test:
	docker exec -it py38 pytest
	docker exec -it py39 pytest
	docker exec -it py310 pytest
	docker exec -it py311 pytest
	docker exec -it py312 pytest
