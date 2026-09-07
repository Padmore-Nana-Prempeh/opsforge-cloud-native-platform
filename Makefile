.PHONY: help verify-zero

help:
	@echo "OpsForge commands"
	@echo "-----------------"
	@echo "make help         Show available commands"
	@echo "make verify-zero  Verify that no billable OpsForge AWS resources remain"

verify-zero:
	@./scripts/verify-zero.sh
