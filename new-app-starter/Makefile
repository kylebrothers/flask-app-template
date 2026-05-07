# ── new-app-starter/Makefile ──────────────────────────────────────────────────
#
# PLACEHOLDER: Update APP_NAME before use.
# All other values are derived from APP_NAME or read from the NAS .env file.
#
# Self-bootstrapping — on a fresh Debian server with Docker installed:
#   git clone https://github.com/kylebrothers/<appname>
#   cd <appname>
#   make up
#
# The first `make up` will:
#   1. Install nfs-common if missing (requires sudo)
#   2. Create the NAS mount point if missing (requires sudo)
#   3. Mount the NAS if not already mounted (requires sudo)
#   4. Verify the .env file exists on the NAS
#   5. Build and start the container
# ─────────────────────────────────────────────────────────────────────────────

# ── Infrastructure (stable across servers — not read from .env) ───────────────
NAS_IP         := 192.168.0.134
NAS_MOUNT_PATH := /mnt/nas

# ── App identity ──────────────────────────────────────────────────────────────
# PLACEHOLDER: replace myapp with your app name
APP_NAME       := myapp

# ── Derived paths ─────────────────────────────────────────────────────────────
ENV_FILE_PATH  := $(NAS_MOUNT_PATH)/config/$(APP_NAME)/.env
CONTAINER_NAME := $(APP_NAME)

# ── Colours for output ────────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[1;33m
RED    := \033[0;31m
NC     := \033[0m  # No colour

.PHONY: help check-deps mount-nas check-env setup build up down restart \
        logs shell clean status pull dev

# ── Default target ────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  $(GREEN)$(APP_NAME)$(NC) — available make targets"
	@echo ""
	@echo "  $(YELLOW)Setup & deployment$(NC)"
	@echo "    make up        — full bootstrap + build + start (use this first)"
	@echo "    make pull      — git pull + restart (standard deployment)"
	@echo "    make restart   — stop + start without rebuild"
	@echo "    make build     — build Docker image only"
	@echo "    make down      — stop container"
	@echo ""
	@echo "  $(YELLOW)Development$(NC)"
	@echo "    make dev       — start with FLASK_DEBUG=true"
	@echo "    make logs      — tail container logs"
	@echo "    make shell     — bash shell inside container"
	@echo "    make status    — show container status"
	@echo ""
	@echo "  $(YELLOW)Maintenance$(NC)"
	@echo "    make clean     — remove container and image"
	@echo "    make setup     — run checks without starting container"
	@echo ""

# ── Dependency check ──────────────────────────────────────────────────────────
check-deps:
	@printf "Checking nfs-common... "
	@if ! which mount.nfs4 > /dev/null 2>&1; then \
		echo "$(YELLOW)not found — installing$(NC)"; \
		sudo apt-get install -y nfs-common; \
	else \
		echo "$(GREEN)ok$(NC)"; \
	fi

# ── NAS mount ─────────────────────────────────────────────────────────────────
mount-nas: check-deps
	@printf "Checking NAS mount at $(NAS_MOUNT_PATH)... "
	@if ! mountpoint -q $(NAS_MOUNT_PATH); then \
		echo "$(YELLOW)not mounted — mounting$(NC)"; \
		sudo mkdir -p $(NAS_MOUNT_PATH); \
		sudo mount -t nfs4 $(NAS_IP):/ $(NAS_MOUNT_PATH) \
			-o nfsvers=4,nolock,soft,rw || \
			(echo "$(RED)ERROR: Could not mount NAS. Check that $(NAS_IP) is reachable.$(NC)" && exit 1); \
		echo "$(GREEN)NAS mounted at $(NAS_MOUNT_PATH)$(NC)"; \
	else \
		echo "$(GREEN)already mounted$(NC)"; \
	fi

# ── Env file check ────────────────────────────────────────────────────────────
check-env: mount-nas
	@printf "Checking .env at $(ENV_FILE_PATH)... "
	@if [ ! -f "$(ENV_FILE_PATH)" ]; then \
		echo "$(RED)NOT FOUND$(NC)"; \
		echo ""; \
		echo "  Create $(ENV_FILE_PATH) on the NAS using .env.example as a guide."; \
		echo "  Required NAS directories:"; \
		echo "    NAS:/Docker/$(APP_NAME)/logs"; \
		echo "    NAS:/Docker/$(APP_NAME)/server_files"; \
		echo ""; \
		exit 1; \
	else \
		echo "$(GREEN)ok$(NC)"; \
	fi

# ── Setup (checks only, no container) ────────────────────────────────────────
setup: check-env
	@printf "Checking SECRET_KEY... "
	@if grep -q "^SECRET_KEY=$$" "$(ENV_FILE_PATH)" 2>/dev/null; then \
		echo "$(YELLOW)not set — generating$(NC)"; \
		SECRET=$$(python3 -c "import secrets; print(secrets.token_hex(32))"); \
		sed -i "s/^SECRET_KEY=$$/SECRET_KEY=$$SECRET/" "$(ENV_FILE_PATH)"; \
		echo "$(GREEN)SECRET_KEY written to $(ENV_FILE_PATH)$(NC)"; \
	else \
		echo "$(GREEN)already set$(NC)"; \
	fi
	@echo "$(GREEN)Setup complete. Run 'make build' or 'make up' to continue.$(NC)"

# ── Build ─────────────────────────────────────────────────────────────────────
build: check-env
	@echo "$(YELLOW)Building $(APP_NAME)...$(NC)"
	ENV_FILE_PATH=$(ENV_FILE_PATH) NAS_IP=$(NAS_IP) \
		docker-compose build
	@echo "$(GREEN)Build complete.$(NC)"

# ── Up (full bootstrap) ───────────────────────────────────────────────────────
up: setup
	@echo "$(YELLOW)Starting $(APP_NAME)...$(NC)"
	ENV_FILE_PATH=$(ENV_FILE_PATH) NAS_IP=$(NAS_IP) \
		docker-compose up -d --build
	@echo "$(GREEN)$(APP_NAME) started. http://localhost:$$(grep HOST_PORT $(ENV_FILE_PATH) | cut -d= -f2 || echo 5000)$(NC)"

# ── Down ──────────────────────────────────────────────────────────────────────
down:
	@echo "$(YELLOW)Stopping $(APP_NAME)...$(NC)"
	docker-compose down
	@echo "$(GREEN)Stopped.$(NC)"

# ── Restart (no rebuild) ──────────────────────────────────────────────────────
restart: check-env
	@echo "$(YELLOW)Restarting $(APP_NAME)...$(NC)"
	docker-compose down
	ENV_FILE_PATH=$(ENV_FILE_PATH) NAS_IP=$(NAS_IP) \
		docker-compose up -d
	@echo "$(GREEN)Restarted.$(NC)"

# ── Pull + restart (standard deployment command) ──────────────────────────────
pull: check-env
	@echo "$(YELLOW)Pulling latest changes...$(NC)"
	git pull
	@echo "$(YELLOW)Rebuilding and restarting...$(NC)"
	ENV_FILE_PATH=$(ENV_FILE_PATH) NAS_IP=$(NAS_IP) \
		docker-compose up -d --build
	@echo "$(GREEN)Deployment complete.$(NC)"

# ── Development mode ─────────────────────────────────────────────────────────
dev: check-env
	@echo "$(YELLOW)Starting $(APP_NAME) in development mode (FLASK_DEBUG=true)...$(NC)"
	ENV_FILE_PATH=$(ENV_FILE_PATH) NAS_IP=$(NAS_IP) FLASK_DEBUG=true \
		docker-compose up -d --build
	@echo "$(GREEN)Dev server started. Logs: make logs$(NC)"

# ── Logs ──────────────────────────────────────────────────────────────────────
logs:
	docker-compose logs -f $(CONTAINER_NAME)

# ── Shell ─────────────────────────────────────────────────────────────────────
shell:
	docker-compose exec $(CONTAINER_NAME) bash

# ── Status ────────────────────────────────────────────────────────────────────
status:
	@echo "$(YELLOW)Container status:$(NC)"
	docker-compose ps
	@echo ""
	@echo "$(YELLOW)Health check:$(NC)"
	@curl -sf http://localhost:$$(grep HOST_PORT $(ENV_FILE_PATH) 2>/dev/null | cut -d= -f2 || echo 5000)/health \
		| python3 -m json.tool 2>/dev/null || echo "Container not responding"

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	@echo "$(YELLOW)Removing container and image for $(APP_NAME)...$(NC)"
	docker-compose down --rmi local -v
	@echo "$(GREEN)Clean complete.$(NC)"
