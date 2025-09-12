.PHONY := clean_secrets decrypt encrypt

ifndef AWS_SESSION_TOKEN
  $(error Not logged in, please run 'assume')
endif

clean_secrets:
	@rm -f secrets.yaml

decrypt: clean_secrets
	@aws kms decrypt \
		--ciphertext-blob $$(cat secrets.yaml.encrypted) \
		--output text \
		--query Plaintext \
		--encryption-context target=tf-minecraft | base64 -d > secrets.yaml

encrypt:
	@aws kms encrypt \
		--key-id alias/generic \
		--plaintext fileb://secrets.yaml \
		--encryption-context target=tf-minecraft \
		--output text \
		--query CiphertextBlob > secrets.yaml.encrypted
	@rm -f secrets.yaml
