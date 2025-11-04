.PHONY := clean_secrets decrypt encrypt exec test

ifndef AWS_SESSION_TOKEN
  $(error Not logged in, please run 'awsume')
endif

test:
	uv sync --extra dev
	uv run pytest

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
