.PHONY := clean_secrets decrypt encrypt exec test lint format type-check coverage dev-all

# Development commands (using uv)
test:
	uv run --extra dev pytest tests/ -v

coverage:
	uv run --extra dev pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

lint:
	uv run --extra dev ruff check .

format:
	uv run --extra dev ruff format .

type-check:
	uv run --extra dev mypy src tests

dev-all: format lint type-check test

# AWS-related commands require session
decrypt encrypt exec: check-aws

check-aws:
ifndef AWS_SESSION_TOKEN
	$(error Not logged in, please run 'awsume')
endif

clean_secrets:
	@rm -f terraform/secrets.yaml

decrypt: clean_secrets
	@aws kms decrypt \
		--ciphertext-blob $$(cat terraform/secrets.yaml.encrypted) \
		--output text \
		--query Plaintext \
		--encryption-context target=tf-minecraft | base64 -d > terraform/secrets.yaml

encrypt:
	@aws kms encrypt \
		--key-id alias/generic \
		--plaintext fileb://terraform/secrets.yaml \
		--encryption-context target=tf-minecraft \
		--output text \
		--query CiphertextBlob > terraform/secrets.yaml.encrypted
	@rm -f terraform/secrets.yaml

exec:
	@TASK_ARN=$$(aws ecs list-tasks --cluster minecraft-cluster --service-name minecraft-service --query 'taskArns[0]' --output text); \
	if [ "$$TASK_ARN" = "None" ]; then \
		echo "No running tasks found. Start the server first."; \
		exit 1; \
	fi; \
	aws ecs execute-command \
		--cluster minecraft-cluster \
		--task $$TASK_ARN \
		--container minecraft \
		--interactive \
		--command "/bin/bash"
