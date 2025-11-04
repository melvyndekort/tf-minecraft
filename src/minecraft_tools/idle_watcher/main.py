import os
import time
import signal
import boto3
from datetime import datetime, UTC
import requests
from mcrcon import MCRcon

# ==== Tracking last player and server availability ====
last_seen_players = datetime.now(UTC)
server_available = False

def send_rcon_message(message: str):
    try:
        host = os.getenv("RCON_HOST")
        port = int(os.getenv("RCON_PORT", "25575"))
        password = os.getenv("RCON_PASSWORD")
        
        with MCRcon(host, password, port=port) as mcr:
            mcr.command(f"say {message}")
            print(f"Sent RCON message: {message}")
    except Exception as e:
        print(f"Failed to send RCON message: {e}")

def send_discord_message(message: str):
    webhook = os.getenv("DISCORD_WEBHOOK")
    if not webhook:
        return
    try:
        requests.post(webhook, json={"content": message})
    except Exception as e:
        print(f"Failed to send Discord message: {e}")

def get_player_count():
    global server_available
    try:
        host = os.getenv("RCON_HOST")
        port = int(os.getenv("RCON_PORT", "25575"))
        password = os.getenv("RCON_PASSWORD")
        
        with MCRcon(host, password, port=port) as mcr:
            resp = mcr.command("list")
            
            # If this is the first successful RCON command, notify Discord
            if not server_available:
                server_available = True
                dns_name = os.getenv("DNS_NAME", host)
                send_discord_message(f"🟢 Minecraft server is online and reachable at `{dns_name}`")
            
            # Example response: "There are 1 of a max of 20 players online: Player1"
            parts = resp.split(":")
            if len(parts) >= 2:
                players = parts[1].strip()
                return len(players.split(", ")) if players else 0
            return 0
    except Exception as e:
        server_available = False
        print(f"Failed to get player count: {e}")
        return 0

def shutdown_ecs_service():
    print("Shutting down ECS service...")
    try:
        cluster = os.getenv("ECS_CLUSTER")
        service = os.getenv("ECS_SERVICE")
        region = os.getenv("AWS_REGION", "us-east-1")
        
        client = boto3.client("ecs", region_name=region)
        client.update_service(
            cluster=cluster,
            service=service,
            desiredCount=0
        )
        send_discord_message("Minecraft server is shutting down due to inactivity. 💤")
    except Exception as e:
        print(f"Failed to scale ECS service down: {e}")

def handle_shutdown_signal(signum, frame):
    print(f"Received signal {signum}, preparing for shutdown...")
    send_rcon_message("§c[SERVER] Server will restart in 2 minutes due to AWS maintenance!")
    send_discord_message("⚠️ Minecraft server received shutdown signal - restarting in 2 minutes")
    
    # Wait a bit for the message to be sent, then exit gracefully
    time.sleep(5)
    exit(0)

def main():
    print("Minecraft idle watcher started.")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    
    # Validate required environment variables
    required_vars = ["RCON_HOST", "RCON_PASSWORD", "ECS_CLUSTER", "ECS_SERVICE"]
    for var in required_vars:
        if not os.getenv(var):
            print(f"ERROR: Required environment variable {var} is not set")
            return
    
    global last_seen_players, server_available
    server_available = False  # Reset server availability state on startup
    
    idle_minutes = int(os.getenv("IDLE_MINUTES", "15"))
    check_interval = int(os.getenv("CHECK_INTERVAL", "60"))
    
    print(f"Configuration: idle_minutes={idle_minutes}, check_interval={check_interval}")
    
    try:
        while True:
            player_count = get_player_count()
            now = datetime.now(UTC)

            if player_count > 0:
                last_seen_players = now
                print(f"{now} - Players online: {player_count}")
            else:
                idle_time = now - last_seen_players
                minutes_idle = idle_time.total_seconds() / 60
                print(f"{now} - No players online for {minutes_idle:.1f} minutes")

                if minutes_idle >= idle_minutes:
                    shutdown_ecs_service()
                    break

            time.sleep(check_interval)
    except Exception as e:
        print(f"ERROR: Main loop failed: {e}")
        raise

if __name__ == "__main__":
    main()
