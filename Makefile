IMAGE   := opencode-docker
TAG     := local
PORT    := 4096

.DEFAULT_GOAL := help

.PHONY: help
help: ## 📖 Show this help
	@echo "🐳 opencode-docker — dev tasks"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: ## 🔨 Build the image locally
	docker build -t $(IMAGE):$(TAG) .

.PHONY: run
run: ## 🚀 Run the image locally on :4096
	docker run --rm -it \
		--name $(IMAGE) \
		-p $(PORT):$(PORT) \
		-e UI_PASSWORD=$${UI_PASSWORD:-password} \
		-v $$(pwd)/workspace:/workspace \
		$(IMAGE):$(TAG)

.PHONY: shell
shell: ## 🐚 Shell into the running container
	docker exec -it $(IMAGE) bash

.PHONY: test
test: ## 🧪 Run the version-bump script's unit tests
	pytest test_update_versions.py

.PHONY: update-versions
update-versions: ## ⬆️  Check npm for newer opencode-ai / @openchamber/web and update Dockerfile + VERSION
	python3 update_versions.py

.PHONY: clean
clean: ## 🧹 Remove local image and Python cache
	docker rmi $(IMAGE):$(TAG) 2>/dev/null || true
	rm -rf __pycache__ .pytest_cache
