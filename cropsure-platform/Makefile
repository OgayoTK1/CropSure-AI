# CropSure AI — Makefile
# Run 'make help' to see all available commands

.PHONY: dev demo stop logs reset-db load-demo-data help

help:
	@echo "CropSure AI — Available Commands"
	@echo "================================="
	@echo "make dev            Start all services in background"
	@echo "make demo           Start all services + open browser + print demo script"
	@echo "make logs           Tail live logs from all services"
	@echo "make stop           Stop all running services"
	@echo "make reset-db       Wipe and recreate the database"
	@echo "make load-demo-data Load demo farms into the database"

dev:
	@echo "Starting CropSure AI services..."
	docker compose --env-file .env up --build -d
	@echo ""
	@echo "Services running:"
	@echo "  Frontend:      http://localhost:5173"
	@echo "  Backend API:   http://localhost:8000/docs"
	@echo "  ML Service:    http://localhost:8001/health"
	@echo "  WhatsApp Bot:  http://localhost:5000"
	@echo "  USSD Handler:  http://localhost:5001"

demo:
	@echo "Starting CropSure AI DEMO MODE..."
	docker compose --env-file .env up --build -d
	@sleep 10
	@echo "Loading demo data..."
	docker compose exec postgres psql -U cropsure -d cropsure_db -f /demo_data.sql
	@echo ""
	@echo "Opening dashboard..."
	xdg-open http://localhost:5173 2>/dev/null || open http://localhost:5173 2>/dev/null || echo "Open http://localhost:5173 in your browser"
	@echo ""
	@echo "================================================"
	@echo "DEMO CHECKLIST"
	@echo "================================================"
	@echo "1. Show farmer enrollment screen in Swahili"
	@echo "2. Agent uploads drone photo of farm"
	@echo "3. Trace farm boundary on aerial photo"
	@echo "4. Show premium calculation - KES 460 for 2 acres"
	@echo "5. Farmer pays via M-Pesa STK push"
	@echo "6. Switch to admin dashboard - farm appears on map"
	@echo "7. Click Simulate Drought button"
	@echo "8. NDVI drops below baseline on chart"
	@echo "9. Payout triggers - M-Pesa notification fires"
	@echo "10. WhatsApp message shows explanation to farmer"
	@echo "================================================"

logs:
	docker compose logs -f

stop:
	@echo "Stopping all CropSure services..."
	docker compose down
	@echo "All services stopped."

reset-db:
	@echo "WARNING: This will delete all data in the database."
	@echo "Press Ctrl+C to cancel or wait 5 seconds to continue..."
	@sleep 5
	docker compose down -v
	docker compose --env-file .env up -d postgres
	@echo "Database reset complete."

load-demo-data:
	@echo "Loading demo farm data..."
	docker compose exec postgres psql -U cropsure -d cropsure_db -f /demo_data.sql
	@echo "Demo data loaded successfully."
